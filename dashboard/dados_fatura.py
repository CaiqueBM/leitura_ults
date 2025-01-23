import fitz  # PyMuPDF
import pytesseract
import re
import pandas as pd
import requests
import sqlite3
from datetime import datetime
import configparser

config = configparser.ConfigParser()
config.read(r"./config.ini")

# Função para extrair os textos
def extrair_texto_pdf(pdf_path):
    # Abre o arquivo PDF
    doc = fitz.open(pdf_path)
    
    all_text = ""
    
    # Itera sobre cada página do PDF
    for page_num in range(doc.page_count):
        page = doc[page_num]
        
        # Extrair o texto da página
        page_text = page.get_text()
        all_text += page_text + "\n"  # Adiciona o texto da página ao conteúdo total
    
    return all_text

# corrigir os dados com formatação errada
def corrigir_formatacao(valor):
    if '.' in valor and ',' in valor:
        # Troca ',' por '.'
        valor = valor.replace('.','').replace(',', '.')
    else: 
        valor = valor.replace(',', '.')
    valor = valor.strip()  # Remove espaços em branco desnecessários
    if valor.endswith('-'):
        valor = valor[:-1]
    return valor

# Função para tratar a lista completa
def processar_lista_tusd(lista):
    def processar_valor(valor):
        try:
            # Substituir vírgula por ponto e converter para float
            return float(valor.replace(",", "."))
        except ValueError:
            # Retornar o valor original caso não seja possível converter
            return valor

    # Iterar sobre a lista e processar cada valor
    return [[processar_valor(valor) for valor in grupo] for grupo in lista]

# Buscar geração no solarz
def buscar_geracao(data_inicio, data_final, nome_geradora):
    geradora = {578496: "ULT 1", 767468: "ULT 2", 667618: "ULT 3", 686932: "ULT 4", 1115966:"Lucas Generoso", 0000:"Gilles", 0000:"DCN", 0000:"Poleto"}

    for key, valor in geradora.items():
        if valor == nome_geradora:
            usina_id = key

            url = f"https://app.solarz.com.br/shareable/generation/period?usinaId={usina_id}&start={data_inicio}&end={data_final}&uniteMonths=false"

            # Realiza a requisição GET para obter os dados da página
            response = requests.get(url)

            # Verificar o código de status da resposta
            if response.status_code != 200:
                raise ValueError(f"Erro na requisição: {response.status_code} - {response.text}")

            # Verificar se a resposta contém JSON
            try:
                data = response.json()
                # Obtém o valor de "totalGerado"
                total_gerado = data.get('totalGerado')
            except requests.exceptions.JSONDecodeError:
                raise ValueError(f"Resposta não é JSON válido: {response.text}")
            return total_gerado
        else:
            break
            # return total_gerado

# Guardar consumo no DB
def guardar_consumo(numero_instalacao, intervalo_bandeiras, mes_fatura, tusd, valor_fatura, energia_inj_mes, data_leitura_inicio, data_leitura_final):
    conn = sqlite3.connect(r"./dashboard/ult.sqlite")
    cursor = conn.cursor()

    tusd_formatada = corrigir_formatacao(tusd[0][0])
    valor_fatura_formatada = corrigir_formatacao(valor_fatura[0])

    # Tipo de bandeira e dias em vigencia
    bandeira_cor_inicial = intervalo_bandeiras[0][0]
    bandeira_dias_inicial = intervalo_bandeiras[0][3]

    if len(intervalo_bandeiras) > 1:
        # Tipo de bandeira e dias em vigencia
        bandeira_cor_final = intervalo_bandeiras[1][0]
        bandeira_dias_final = intervalo_bandeiras[1][3]

    if len(intervalo_bandeiras) == 1:
        # Define a query para atualizar os dados
        query = f"""
        INSERT INTO consumos (
            UNIDADE_EDP,
            MES_DE_CONSUMO,
            MONTANTE,
            VALOR_FATURA
        ) VALUES ('{numero_instalacao[0]}', '{mes_fatura}', {tusd_formatada}, '{valor_fatura[0]}');
        """
        cursor.execute(query)
        conn.commit()
    else:
        dados = [
                (numero_instalacao[0], mes_fatura, tusd_formatada, valor_fatura_formatada, 'NULL', 'NULL'),
                (numero_instalacao[0], mes_fatura, float(tusd_formatada) * (float(bandeira_dias_inicial)/(float(bandeira_dias_inicial) + float(bandeira_dias_final))), 'NULL', bandeira_cor_inicial, bandeira_dias_inicial),
                (numero_instalacao[0], mes_fatura, float(tusd_formatada) * (float(bandeira_dias_final)/(float(bandeira_dias_inicial) + float(bandeira_dias_final))), 'NULL', bandeira_cor_final, bandeira_dias_final)
            ]
        
        for linha in dados:
            instalacao = linha[0]
            mes = linha[1]
            montante = linha[2]
            vlr_fatura = linha[3]
            bandeira = linha[4]
            dias_bandeira = linha[5]
            # instalacao = str(instalacao).strip().replace("'", "''")

            # Define a query para atualizar os dados
            query = f"""
            INSERT INTO consumos (
                UNIDADE_EDP,
                MES_DE_CONSUMO,
                MONTANTE,
                VALOR_FATURA,
                BANDEIRA,
                QUANT_DIAS_BANDEIRA
            ) VALUES ('{instalacao}', '{mes}', {montante}, {vlr_fatura}, '{bandeira}', {dias_bandeira});
            """
            # Executa a query para atualizar os dados
            cursor.execute(query)
            conn.commit()

    # Commit para salvar as mudanças no banco de dados
    
    cursor.close()
    conn.close()

# Guardar geracao no DB
def guardar_geracao(df_inj_tusd, numero_instalacao, mes_fatura, energia_inj_mes, data_leitura_inicio, data_leitura_final, geradora):
    
    conn = sqlite3.connect(r"./dashboard/ult.sqlite")
    cursor = conn.cursor()
    
    # SE FOR UNIDADE CONSUMIDORA
    if len(df_inj_tusd) > 0 and geradora == '0':
        # INJECOES
        for index, row in df_inj_tusd.iterrows():
            valor = corrigir_formatacao(row.iloc[3])
            
            #  INJECOES PROPRIAS (SALVAR NA TABELA GERACOES)
            if row.iloc[0] == 'm':
                # print(row.iloc[3])
                # Define a query para atualizar os dados
                query = f"""
                INSERT INTO geracoes (
                    UNID_CONSUMIDORA,
                    FATURAMENTO,
                    CONSUMO,
                    LEITURA_FATURA,
                    MES_PRODUCAO,
                    UNIDADE_EDP
                ) VALUES ('{numero_instalacao[0]}', '{mes_fatura}', '{valor}', '{valor}', '{row.iloc[2]}', '{numero_instalacao[0]}');
                """
                # Executa a query para atualizar os dados
                cursor.execute(query)
                conn.commit()

            # INJECAO DE OUTROS
            elif row.iloc[0] == 'o':
                conn = sqlite3.connect(r"./dashboard/ult.sqlite")
                cursor = conn.cursor()
                
                # Define a query para atualizar os dados
                query = f"""
                INSERT INTO geracoes (
                    UNID_CONSUMIDORA,
                    FATURAMENTO,
                    CONSUMO,
                    MES_PRODUCAO
                ) VALUES ('{numero_instalacao[0]}', '{mes_fatura}', '{valor}', '{row.iloc[2]}');
                """

                # Executa a query para atualizar os dados
                cursor.execute(query)
                conn.commit()
                
    # SE FOR GERADOR
    elif geradora == '1':
        # FORMATAR A DATA DE LEITURA INICIAL DA FATURA
        data_inicio_temp = datetime.strptime(data_leitura_inicio, "%d/%m/%Y")
        data_inicio_formatada = data_inicio_temp.strftime("%Y-%m-%d")

        # FORMATAR A DATA DE LEITURA FINAL DA FATURA
        data_final_temp = datetime.strptime(data_leitura_final, "%d/%m/%Y")
        data_final_formatada = data_final_temp.strftime("%Y-%m-%d")

        query = f"SELECT NOME FROM NOMES WHERE UNIDADE_EDP = {numero_instalacao[0]}"

        cursor.execute(query)
        resultado = cursor.fetchone()

        telemetria_total = buscar_geracao(data_inicio_formatada, data_final_formatada, resultado[0])

        consumo = 0
        
        # Define a query para atualizar os dados
        query = f"""
        INSERT INTO geracoes (
            UNIDADE_EDP,
            CONSUMO,
            LEITURA_FATURA,
            MES_PRODUCAO,
            LEITURA_TELEM
        ) VALUES ('{numero_instalacao[0]}','{consumo}','{energia_inj_mes[0].replace(",", ".")}','{mes_fatura}', '{telemetria_total}');
        """

        # Executa a query para atualizar os dados
        cursor.execute(query)
        conn.commit()

    # Commit para salvar as mudanças no banco de dados
    cursor.close()
    conn.close()

def busca_path(path, tem_fatura, geradora):
# if __name__ == "__main__":

    # IF mes_anterior == mes_atual - 2

    # Dicionário para traduzir número do mês para nome em português
    meses_split = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4,
        "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8,
        "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
    }

    if path is not None:
        texto_extraido = extrair_texto_pdf(path)

        #Texto extraido formatado
        etext = texto_extraido.replace(r'\n','\n')

        #REGEX para buscar dados das faturas
        regex_instalacao = r'''(?<=\n)(?:[^\n]+\n){0,1}([^\n]+)(?=\nClassificação:)'''
        #regex_tusd = re.compile(r'''TUSD - Energia Ativa Fornecida\WkWh\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)''',re.MULTILINE)
        regex_tusd = re.compile(r'''TUSD.*?\WkWh\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)''',re.MULTILINE)
        regex_bandeiras = re.compile(r'''(?:^Adicional Bandeira)[ -]?([\w ]+)\.?\WkWh\W(\d*\.?\d+,\d+)\n\r?(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)''',re.MULTILINE)
        regex_injecoes_tusd = re.compile(r'''(?:^TUSD - En. At. Inj. )(\w)UC[ ]+(\w)PT (\d{2}/\d{4})\WkWh\W(\d*\.?\d+,\d+)-?\W(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)-?\W(\d*\.?\d+,\d+)-?\W(\d*\.?\d+,\d+)-?\W(\d*\.?\d+,\d+)-?\W(\d*\.?\d+,\d+)-?\W(\d*\.?\d+,\d+)-?''',re.MULTILINE)
        regex_iluminacao_publica = re.compile(r'''(?<=Contribuição)(?:.*\W?\n?)(?:\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)''')
        regex_juros_mora = re.compile(r'''(?<=Juros)(?:.*\W?\n?)(\d*\.?\d+,\d+)\W(\d*\.?\d+,\d+)''')
        regex_datas_leitura = re.compile(r'''\b\d{2}/\d{2}/\d{4}\b''') # Intervalo de leitura de dados
        regex_data_mes = re.compile(r'''\b[A-Z]{3}\/\d{4}\b''') # Mes de referencia da fatura
        regex_valor_fatura = re.compile(r'''(?<=R\$ )(?:.*)''') # Valor da fatura EDP
        regex_intervalo_bandeiras = r'''(?P<cor>[A-Za-z0-9 ]+):\s(?P<data_inicio>\d{2}/\d{2}/\d{4})\sa\s(?P<data_fim>\d{2}/\d{2}/\d{4})-(?P<dias>\d+)\sdias'''
        regex_energia_injetada_mes = r'''(?<=Energia Inj)(?:.*\W?\n?)(\d*\.?\d+,\d+)'''

        numero_instalacao = re.findall(regex_instalacao, etext)
        # Buscar valores das faturas
        tusd = re.findall(regex_tusd, etext)        
        bandeiras = re.findall(regex_bandeiras, etext)
        injecoes_tusd = re.findall(regex_injecoes_tusd, etext)
        iluminacao_publica = re.findall(regex_iluminacao_publica, etext)

        # Encontrar todas as datas
        datas_leitura = re.findall(regex_datas_leitura, etext)
        print(f"PATH: {path}")
        # Data da leitura anterior
        data_leitura_inicio = datas_leitura[0]
        # Data da leitura atual
        data_leitura_final = datas_leitura[1]

        #Pegar mes de referencia
        mes_fatura_inicio = re.findall(regex_data_mes, etext)[0]
        mes_fatura = mes_fatura_inicio.split("/")[0]
        ano_fatura = mes_fatura_inicio.split("/")[1]

        mes_fatura = meses_split[mes_fatura]

        mes_fatura = f"""{mes_fatura}/{ano_fatura}"""

        # Pegar Valor da fatura
        valor_fatura = re.findall(regex_valor_fatura, etext)

        # Intervalo bandeiras
        intervalo_bandeiras = re.findall(regex_intervalo_bandeiras, etext)

        # Tipo de bandeira e dias em vigencia
        bandeira_cor_inicial = intervalo_bandeiras[0][0]
        bandeira_dias_inicial = intervalo_bandeiras[0][3]

        if len(intervalo_bandeiras) > 1:
            # Tipo de bandeira e dias em vigencia
            bandeira_cor_final = intervalo_bandeiras[1][0]
            bandeira_dias_final = intervalo_bandeiras[1][3]

        energia_inj_mes = re.findall(regex_energia_injetada_mes, etext)

        # Criação dos DataFrames
        tusd_processado = processar_lista_tusd(tusd)

        df_tusd = pd.DataFrame(tusd, columns=["Quantidade", "PrecoUnitcTributos", "Total", "PISCOFINS", "BaseICMS", "AliquotaICMS", "ICMS", "Tarifa_Unit"])
        df_bandeiras = pd.DataFrame(bandeiras, columns=["Tipo", "Quantidade", "Tarifa", "Total"])
        df_inj_tusd = pd.DataFrame(injecoes_tusd, columns=["Prefixo1", "Prefixo2", "Data", "Quantidade", "Tarifa", "Total", "PISCOFINS", "BaseICMS", "AliquotaICMS", "ICMS", "TarifaUnit"])
        df_iluminacao_publica = pd.DataFrame(iluminacao_publica, columns=["Total"])

        tusd_total = df_tusd["Total"].apply(corrigir_formatacao).astype(float).sum()
        bandeiras_total = df_bandeiras["Total"].apply(corrigir_formatacao).astype(float).sum()
        tusd_inj_total = df_inj_tusd["Total"].apply(corrigir_formatacao).astype(float).sum()
        iluminacao_publica_total = df_iluminacao_publica["Total"].apply(corrigir_formatacao).astype(float).sum()

        guardar_consumo(numero_instalacao, intervalo_bandeiras, mes_fatura, tusd, valor_fatura, energia_inj_mes, data_leitura_inicio, data_leitura_final)

        guardar_geracao(df_inj_tusd, numero_instalacao, mes_fatura, energia_inj_mes, data_leitura_inicio, data_leitura_final, geradora)

        conexao = sqlite3.connect("./dashboard/ult.sqlite")  # Ajuste o nome do banco de dados
        cursor = conexao.cursor()

        query = f"""
            INSERT INTO historico (
                TEM_FATURA,
                MES_DE_CONSUMO,
                UNIDADE_EDP
            ) VALUES ({tem_fatura}, '{mes_fatura}', {numero_instalacao[0]});
            """
        cursor.execute(query)
        conexao.commit()
        cursor.close()  
        conexao.close()
    else:
        print()