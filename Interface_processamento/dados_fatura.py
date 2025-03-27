import fitz  # PyMuPDF
import re
import pandas as pd
import requests
import sqlite3
from datetime import datetime
import subprocess
import os
import sys

# Adiciona o diretório pai ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import configparser

config = configparser.ConfigParser()
config.read(os.path.join(parent_dir, 'config.ini'))

# Função para extrair os textos
def extrair_texto_pdf(pdf_path):
    try:
        
        # Adiciona o diretório pai ao sys.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # parent_dir = os.path.dirname(current_dir)
        # sys.path.append(parent_dir)
        
        # Caminho para o executável destrinchaPDF
        destrincha_path = os.path.join(current_dir, 'destrinchaPDF')
        
        # Comando a ser executado
        comando = [destrincha_path, pdf_path]
        
        # Configuração do ambiente
        env = os.environ.copy()  # Copia o ambiente atual
        env['DOTNET_SYSTEM_GLOBALIZATION_INVARIANT'] = '1'
        
        # Adiciona a configuração para o diretório de extração do bundle
        env['DOTNET_BUNDLE_EXTRACT_BASE_DIR'] = './tmp/dotnet_bundles'
        
        # Garante que o diretório de extração existe
        os.makedirs('./tmp/dotnet_bundles', exist_ok=True)
        
        # Executa o comando e captura a saída
        resultado = subprocess.run(comando,
                                   env=env,
                                   capture_output=True,
                                   text=True,
                                   check=True)
        
        # Retorna o texto de saída
        return resultado.stdout
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o destrinchaPDF: {e}")
        print(f"Saída de erro: {e.stderr}")
        return None
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return None

def remove_zeros(text):
    # Este padrão procura por zeros no início de um número
    # (?<!\d) garante que não há um dígito antes (para não afetar números como 101)
    # 0+ captura um ou mais zeros
    # (?=\d) garante que há um dígito após os zeros (para não remover todos os zeros)
    pattern = r'(?<!\d)0+(?=\d)'
    return re.sub(pattern, '', text)

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
    try:
        # geradora = {578496: "ULT 1", 767468: "ULT 2", 667618: "ULT 3", 686932: "ULT 4", 1115966:"Lucas Generoso 1", 806251:"Gilles", 1115966:"DCN", 0000:"Poleto"}
        geradora = {"ULT 1": "ULT 1", "ULT 2": "ULT 2", "ULT 3": "ULT 3", "ULT 4": "ULT 4", "Lucas Generoso":"LUCAS GENEROSO 1", "Gilles":"Gilles 1", "1115966":"GD3 - MAIS ALIMENTOS", "0000":"POLETO 1"}
        
        for key, valor in geradora.items():
            if valor == nome_geradora:
                usina_id = key
                
                db_geracao = config['database']['dbusinas']
                conn = sqlite3.connect(db_geracao)
                cursor = conn.cursor()
                cursor.execute(f"""SELECT SUM(GERACAO) as geracao_total
                                FROM dados_diarios
                                WHERE ULT = '{usina_id}' AND DATA BETWEEN '{data_inicio}' AND '{data_final}'""")
                geracao = cursor.fetchone()
                cursor.close()
                conn.close()

                return geracao[0]
            else:
                continue
                # return total_gerado
    except Exception as e:
        print(f"Erro ao buscar fatura: {str(e)}")
        return "0"
    
    
    "{:.2f}".format()

def gerar_historico(unidade_edp, mes_de_consumo, inicio_leitura, final_leitura, dias_leitura, saldo_total, iluminacao_valor):
    meses = {
            "JAN": "1", "FEV": "2", "MAR": "3", "ABR": "4",
            "MAI": "5", "JUN": "6", "JUL": "7", "AGO": "8",
            "SET": "9", "OUT": "10", "NOV": "11", "DEZ": "12"
        }
    db_clientes = config['database']['dbclientes']
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()
    
    mes_split = mes_de_consumo.split('/')[0]
    ano_split = mes_de_consumo.split('/')[1]
    mes_corrigido = remove_zeros(meses[mes_split])
    mes_referencia = f"{mes_corrigido}/{ano_split}"
    
    # Verificar se tem o historico
    cursor.execute(f"SELECT COUNT(*) FROM historico WHERE UNIDADE_EDP = '{unidade_edp}' AND MES_CONSUMO = '{mes_referencia}'")
    historico = cursor.fetchone()[0] > 0
       
    if historico: # Se ja existir dados nessa data para essa unidade edp, dar update nos dados
        query = f"""
        UPDATE historico
        SET UNIDADE_EDP = '{unidade_edp}',
        MES_CONSUMO = '{remove_zeros(mes_referencia)}',
        INICIO_LEITURA = '{inicio_leitura}',
        FINAL_LEITURA = '{final_leitura}',
        DIAS_LEITURA = '{dias_leitura}',
        SALDO_TOTAL = '{saldo_total}',
        ILUMINACAO_PUBLICA = '{iluminacao_valor}'
        WHERE UNIDADE_EDP = '{unidade_edp}' AND MES_CONSUMO = '{mes_referencia}';
        """
        cursor.execute(query)
        conn.commit()
    else: # Se não existir ainda dados, inserir no banco de dados
        query = f"""
        INSERT INTO historico (
            UNIDADE_EDP,
            MES_CONSUMO,
            INICIO_LEITURA,
            FINAL_LEITURA,
            DIAS_LEITURA,
            SALDO_TOTAL,
            ILUMINACAO_PUBLICA
        ) VALUES ('{unidade_edp}','{remove_zeros(mes_referencia)}','{inicio_leitura}','{final_leitura}', '{dias_leitura}', '{saldo_total}', '{iluminacao_valor}');
        """
        cursor.execute(query)
        conn.commit()
        
    # Commit para salvar as mudanças no banco de dados
    cursor.close()
    conn.close()
    
# Guardar consumo no DB
def guardar_consumo(numero_instalacao, intervalo_bandeiras, mes_fatura, tusd, valor_fatura, dias_leitura):
    
    meses = {
            "JAN": "1", "FEV": "2", "MAR": "3", "ABR": "4",
            "MAI": "5", "JUN": "6", "JUL": "7", "AGO": "8",
            "SET": "9", "OUT": "10", "NOV": "11", "DEZ": "12"
        }
    
    db_clientes = config['database']['dbclientes']
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()

    tusd_formatada = corrigir_formatacao(tusd['quantidade'])
    valor_fatura_formatada = corrigir_formatacao(valor_fatura)

    mes_split = mes_fatura.split('/')[0]
    ano_split = mes_fatura.split('/')[1]
    mes_corrigido = remove_zeros(meses[mes_split])
    mes_referencia = f"{mes_corrigido}/{ano_split}"
    
    # Verificar se tem os consumos
    cursor.execute(f"SELECT COUNT(*) FROM consumos WHERE UNIDADE_EDP = '{numero_instalacao}' AND MES_DE_CONSUMO = '{mes_referencia}'")
    consumo = cursor.fetchone()[0] > 0
    
    cursor.execute(f"SELECT UNIDADE_EDP, MES_DE_CONSUMO, MONTANTE, VALOR_FATURA, BANDEIRA FROM consumos WHERE UNIDADE_EDP = '{numero_instalacao}' AND MES_DE_CONSUMO = '{mes_referencia}'")
    dados_antigos = cursor.fetchall()

    if len(intervalo_bandeiras) > 0: # SE EXISTIR ADICIONAL DE BANDEIRA
        if len(intervalo_bandeiras) > 1: # SE EXISTIR MAIS DE 1 ADICIONAL DE BANDEIRA
            # Tipo de bandeira e dias em vigencia
            bandeira_cor_inicial = intervalo_bandeiras[0]['TipoBandeira']
            quantidade_bandeira_inicial = corrigir_formatacao(intervalo_bandeiras[0]['Quant'])
            bandeira_dias_inicial = int((float(quantidade_bandeira_inicial)/float(tusd_formatada)) * float(dias_leitura))
            
            # Tipo de bandeira e dias em vigencia
            bandeira_cor_final = intervalo_bandeiras[1]['TipoBandeira']
            quantidade_bandeira_final = corrigir_formatacao(intervalo_bandeiras[1]['Quant'])
            bandeira_dias_final = int(float(dias_leitura) - bandeira_dias_inicial)
            
            dados = [
                (numero_instalacao, mes_referencia, tusd_formatada, valor_fatura_formatada, 'NULL', 'NULL'), # VALOR COMPLETO DO CONSUMO PARA O MES
                (numero_instalacao, mes_referencia, quantidade_bandeira_inicial, 'NULL', bandeira_cor_inicial, bandeira_dias_inicial), # VALOR PARA A PRIMEIRA BANDEIRA
                (numero_instalacao, mes_referencia, quantidade_bandeira_final, 'NULL', bandeira_cor_final, bandeira_dias_final) # VALOR PARA A SEGUNDA BANDEIRA
            ]
                        
        else: # SE EXISTIR APENAS 1 ADICIONAL DE BANDEIRA ELE PEGA O QUE JA TEM E ADICIONA O VERDE PARA OS DIAS QUE FALTAM
            # Tipo de bandeira e dias em vigencia
            bandeira_cor_inicial = intervalo_bandeiras[0]['TipoBandeira']
            quantidade_bandeira_inicial = corrigir_formatacao(intervalo_bandeiras[0]['Quant'])
            bandeira_dias_inicial = int((float(quantidade_bandeira_inicial)/float(tusd_formatada)) * float(dias_leitura))
            
            bandeira_cor_final = "Verde"
            bandeira_dias_final = int(float(dias_leitura) - bandeira_dias_inicial)
            quantidade_bandeira_final = float(tusd_formatada) - float(quantidade_bandeira_inicial)
            
            dados = [
                (numero_instalacao, mes_referencia, tusd_formatada, valor_fatura_formatada, 'NULL', 'NULL'), # VALOR COMPLETO DO CONSUMO PARA O MES
                (numero_instalacao, mes_referencia, quantidade_bandeira_inicial, 'NULL', bandeira_cor_inicial, bandeira_dias_inicial), # VALOR PARA A PRIMEIRA BANDEIRA
                (numero_instalacao, mes_referencia, quantidade_bandeira_final, 'NULL', bandeira_cor_final, bandeira_dias_final) # VALOR PARA A SEGUNDA BANDEIRA
            ]
        
        for id, linha in enumerate(dados):
            instalacao = linha[0]
            mes = remove_zeros(linha[1])
            montante = linha[2]
            vlr_fatura = linha[3]
            bandeira = linha[4]
            dias_bandeira = linha[5]

            if consumo:
                query = f"""
                UPDATE consumos
                SET UNIDADE_EDP = '{instalacao}',
                MES_DE_CONSUMO = '{mes}',
                MONTANTE = '{montante}',
                VALOR_FATURA = '{vlr_fatura}',
                BANDEIRA = '{bandeira}',
                QUANT_DIAS_BANDEIRA = '{dias_bandeira}'
                WHERE UNIDADE_EDP = '{instalacao}' AND MES_DE_CONSUMO = '{mes_referencia}' AND MONTANTE = '{dados_antigos[id][2]}' AND VALOR_FATURA = '{dados_antigos[id][3]}' AND BANDEIRA = '{dados_antigos[id][4]}';
                """
                cursor.execute(query)
                conn.commit()
            
            else:
                # Define a query para atualizar os dados
                query = f"""
                INSERT INTO consumos (
                    UNIDADE_EDP,
                    MES_DE_CONSUMO,
                    MONTANTE,
                    VALOR_FATURA,
                    BANDEIRA,
                    QUANT_DIAS_BANDEIRA
                ) VALUES ('{instalacao}', '{mes}', '{montante}', '{vlr_fatura}', '{bandeira}', '{dias_bandeira}');
                """
                # Executa a query para atualizar os dados
                cursor.execute(query)
                conn.commit()
                        
    else: # SE NÃO EXISTIR NENHUM ADICIONAL DE BANDEIRA ELE PREENCHE COM BANDEIRA VERDE
        bandeira_cor = "Verde"
        quantidade_dias_bandeira = dias_leitura

        if consumo:
            query = f"""
            UPDATE consumos
            SET UNIDADE_EDP = '{numero_instalacao}',
            MES_DE_CONSUMO = '{mes_referencia}',
            MONTANTE = '{tusd_formatada}',
            VALOR_FATURA = '{valor_fatura_formatada}',
            BANDEIRA = '{bandeira_cor}',
            QUANT_DIAS_BANDEIRA = '{quantidade_dias_bandeira}'
            WHERE UNIDADE_EDP = '{numero_instalacao}' AND MES_DE_CONSUMO = '{mes_referencia}' AND MONTANTE = '{dados_antigos[0][2]}' AND VALOR_FATURA = '{dados_antigos[0][3]}' AND BANDEIRA = '{dados_antigos[0][4]}';
            """
            cursor.execute(query)
            conn.commit()
        else:
            query = f"""
            INSERT INTO consumos (
                UNIDADE_EDP,
                MES_DE_CONSUMO,
                MONTANTE,
                VALOR_FATURA,
                BANDEIRA,
                QUANT_DIAS_BANDEIRA
            ) VALUES ('{numero_instalacao}', '{mes_referencia}', {tusd_formatada}, '{valor_fatura_formatada}', '{bandeira_cor}', '{quantidade_dias_bandeira}');
            """
            cursor.execute(query)
            conn.commit()
    cursor.close()
    conn.close()

# Guardar geracao no DB
def guardar_geracao(numero_instalacao, mes_fatura, energia_injetada, tusd_injetada, leitura_inicial, leitura_final, geradora):
    
    
    
    meses = {
            "JAN": "1", "FEV": "2", "MAR": "3", "ABR": "4",
            "MAI": "5", "JUN": "6", "JUL": "7", "AGO": "8",
            "SET": "9", "OUT": "10", "NOV": "11", "DEZ": "12"
        }
    
    db_clientes = config['database']['dbclientes']
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()
    
    mes_split = mes_fatura.split('/')[0]
    ano_split = mes_fatura.split('/')[1]
    mes_corrigido = remove_zeros(meses[mes_split])
    mes_referencia = f"{mes_corrigido}/{ano_split}"
    print(f"MES REFERENCIA: {mes_corrigido}")
    print(f"DATA REFERENCIA: {mes_referencia}")
    
    # Verificar se tem as geracoes
    if geradora == "0":
        cursor.execute(f"SELECT COUNT(*) FROM geracoes WHERE UNID_CONSUMIDORA = '{numero_instalacao}' AND FATURAMENTO = '{mes_referencia}'")
        geracoes = cursor.fetchone()[0] > 0
        cursor.execute(f"SELECT MES_PRODUCAO, CONSUMO, FATURAMENTO, UNID_CONSUMIDORA FROM geracoes WHERE UNID_CONSUMIDORA = '{numero_instalacao}' AND FATURAMENTO = '{mes_referencia}'")
        dados_antigos = cursor.fetchall()


    else:
        cursor.execute(f"SELECT COUNT(*) FROM geracoes WHERE UNIDADE_EDP = '{numero_instalacao}' AND MES_PRODUCAO = '{mes_referencia}' AND UNID_CONSUMIDORA IS NULL")
        geracoes = cursor.fetchone()[0] > 0
    
    # SE FOR UNIDADE CONSUMIDORA
    if len(tusd_injetada) > 0 and geradora == '0':
        # INJECOES
        for id, index in enumerate(tusd_injetada):
            valor = corrigir_formatacao(index['Quant'])
            if index['GD'] == "GDII":
                gdii = index['GD']
            else:
                gdii = "-"

            #  INJECOES PROPRIAS (SALVAR NA TABELA GERACOES)
            if index['Prod'] == 'mUC':
                # Define a query para atualizar os dados
                if geracoes:
                    query = f"""
                    UPDATE geracoes
                    SET UNID_CONSUMIDORA = '{numero_instalacao}',
                    FATURAMENTO = '{remove_zeros(mes_referencia)}',
                    CONSUMO = '{valor}',
                    LEITURA_FATURA = '{valor}',
                    MES_PRODUCAO = '{remove_zeros(index['data'])}',
                    UNIDADE_EDP = '{numero_instalacao}',
                    GD = '{gdii}'
                    WHERE UNID_CONSUMIDORA = '{numero_instalacao}' AND FATURAMENTO = '{mes_referencia}' AND MES_PRODUCAO ='{dados_antigos[id][0]}' AND CONSUMO = '{dados_antigos[id][1]}';
                    """
                    cursor.execute(query)
                    conn.commit()
                    
                else:
                    query = f"""
                    INSERT INTO geracoes (
                        UNID_CONSUMIDORA,
                        FATURAMENTO,
                        CONSUMO,
                        LEITURA_FATURA,
                        MES_PRODUCAO,
                        UNIDADE_EDP,
                        GD
                    ) VALUES ('{numero_instalacao}', '{remove_zeros(mes_referencia)}', '{valor}', '{valor}', '{remove_zeros(index['data'])}', '{numero_instalacao}', '{gdii}');
                    """
                    # Executa a query para atualizar os dados
                    cursor.execute(query)
                    conn.commit()

            # INJECAO DE OUTROS
            elif index['Prod'] == 'oUC':
                if geracoes:
                    query = f"""
                    UPDATE geracoes
                    SET UNID_CONSUMIDORA = '{numero_instalacao}',
                    FATURAMENTO = '{remove_zeros(mes_referencia)}',
                    CONSUMO = '{valor}',
                    MES_PRODUCAO = '{remove_zeros(index['data'])}',
                    GD = '{gdii}'
                    WHERE UNID_CONSUMIDORA = '{numero_instalacao}' AND FATURAMENTO = '{mes_referencia}' AND MES_PRODUCAO ='{dados_antigos[id][0]}' AND CONSUMO = '{dados_antigos[id][1]}';
                    """
                    cursor.execute(query)
                    conn.commit()
                else:
                    # Define a query para atualizar os dados
                    query = f"""
                    INSERT INTO geracoes (
                        UNID_CONSUMIDORA,
                        FATURAMENTO,
                        CONSUMO,
                        MES_PRODUCAO,
                        GD
                    ) VALUES ('{numero_instalacao}', '{remove_zeros(mes_referencia)}', '{valor}', '{remove_zeros(index['data'])}', '{gdii}');
                    """

                    # Executa a query para atualizar os dados
                    cursor.execute(query)
                    conn.commit()
                
    # SE FOR GERADOR
    elif geradora == '1':
        energia_injetada = energia_injetada.replace(",",".")
        # BUSCAR DADOS DO SOLAR Z DE GERAÇÃO DA USINA
        # FORMATAR A DATA DE LEITURA INICIAL DA FATURA
        data_inicio_temp = datetime.strptime(leitura_inicial, "%d/%m/%Y")
        data_inicio_formatada = data_inicio_temp.strftime("%Y-%m-%d")

        # FORMATAR A DATA DE LEITURA FINAL DA FATURA
        data_final_temp = datetime.strptime(leitura_final, "%d/%m/%Y")
        data_final_formatada = data_final_temp.strftime("%Y-%m-%d")

        query = f"SELECT NOME FROM NOMES WHERE UNIDADE_EDP = {numero_instalacao}"

        cursor.execute(query)
        resultado = cursor.fetchone()

        
        telemetria_total = buscar_geracao(data_inicio_formatada, data_final_formatada, resultado[0])
        
        # Substitui None por 0.0
        if telemetria_total is None:
            telemetria_total = 0.0

        # Formata o resultado
        telemetria_total = "{:.2f}".format(telemetria_total)

        consumo = 0
        
        if geracoes:
            query = f"""
            UPDATE geracoes
            SET UNIDADE_EDP = '{numero_instalacao}',
            CONSUMO = '{consumo}',
            LEITURA_FATURA = '{energia_injetada}',
            MES_PRODUCAO = '{remove_zeros(mes_referencia)}',
            LEITURA_TELEM = '{str(telemetria_total)}'
            WHERE UNIDADE_EDP = '{numero_instalacao}' AND MES_PRODUCAO = '{mes_referencia}' AND (UNID_CONSUMIDORA IS NULL OR UNID_CONSUMIDORA = '') AND (FATURAMENTO IS NULL OR FATURAMENTO = '');
            """
            cursor.execute(query)
            
        else:
            # Define a query para atualizar os dados
            query = f"""
            INSERT INTO geracoes (
                UNIDADE_EDP,
                CONSUMO,
                LEITURA_FATURA,
                MES_PRODUCAO,
                LEITURA_TELEM
            ) VALUES ('{numero_instalacao}','{consumo}','{energia_injetada}','{remove_zeros(mes_referencia)}', '{str(telemetria_total)}');
            """

            # Executa a query para atualizar os dados
            cursor.execute(query)

    # Commit para salvar as mudanças no banco de dados
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\r\n")
    print(f"DADOS COMPLETOS DEMONSTRATIVO: {geracoes}")
    print("\r\n")

def busca_path(path, geradora):
    
    numero_instalacao = None
    tusd_info = None
    datas_info = None
    fatura_info = None
    iluminacao_valor = None
    tusd_inj = []
    intervalo_bandeiras = []
    mes_fatura = None
    saldo_total = None

    if path is not None:
        try:
            texto_extraido = extrair_texto_pdf(path)
            
            linhas = texto_extraido.split('\n')
            
            for linha in linhas:
                # Busca numero da instalação
                instalacao_match = re.search(r'^\s*(?P<Instalacao>\d{10})\s*$', linha)
                if instalacao_match and numero_instalacao is None:
                    match_numero_instalacao = instalacao_match.group('Instalacao')
                    numero_instalacao = remove_zeros(match_numero_instalacao)
                    
                # Busca leitura anterior, leitura atual e numero de dias
                datas_match = re.search(r'(?P<data_inicial>\d{2}/\d{2}/\d{4})\s+(?P<data_leitura>\d{2}/\d{2}/\d{4})\s+(?P<dias>\d{1,2})\s+(?P<data_vencimento>\d{2}/\d{2}/\d{4})', linha)
                if datas_match:
                    datas_info = {
                        'data_inicial': datas_match.group('data_inicial'),
                        'data_leitura': datas_match.group('data_leitura'),
                        'dias': datas_match.group('dias'),
                        'data_vencimento': datas_match.group('data_vencimento')
                    }
                
                # Busca mes de referencia e valor da fatura
                fatura_match = re.search(r'(?P<mes_ano>[A-Z]{3}/\d{4})\s+(?:[*]+|\S+)\s+R\$\s*(?P<valor>[\d,.]+)', linha)

                if fatura_match:
                    fatura_info = {
                        'mes_ano': fatura_match.group('mes_ano'),
                        'valor': fatura_match.group('valor')
                    }
                
                # Busca valores de Fatura
                # Busca TUSD - Energia Ativa Fornecida
                if ("TUSD" in linha):
                    tusd_fornecida = re.search(r'TUSD\s*-?\s*(?:Energia|En\.?)\s*(?:Ativa|At\.?)\s*(?:Fornecida|Forn\.?)\s+kWh\s+(?P<quantidade>[\d\.,]+)\s+(?P<valor_unitario>[\d\.,]+)\s+(?P<valor_total>[\d\.,]+)', linha)
                    if tusd_fornecida:
                        tusd_info = {
                            'quantidade': tusd_fornecida.group('quantidade'),
                            'valor_unitario': tusd_fornecida.group('valor_unitario'),
                            'valor_total': tusd_fornecida.group('valor_total')
                        }
                
                    # Busca TUSD - Energias Injetadas
                    tusd_injetada = re.search(r'(?P<Prod>[mo]UC)\s+(?P<Pont>[mo]PT)\s+(?:(?P<GD>GDI{1,3})\s+)?(?P<data>\d{2}/\d{4})\s+(?:KWH|kWh)\s+(?P<Quant>\d*\.?\d+,\d+)-?\s*(?P<PUcTrib>\d*\.?\d+,\d+)-?\s*(?P<ValTot>\d*\.?\d+,\d+)-?\s*(?P<PISCOF>\d*\.?\d+,\d+)-?\s*(?P<BasCalc>\d*\.?\d+,\d+)-?\s*(?P<AliqICMS>\d*\.?\d+,\d+)-?\s*(?P<ICMS>\d*\.?\d+,\d+)-?\s*(?P<TarUnit>\d*\.?\d+,\d+)-?', linha)
                    if tusd_injetada:
                        tusd_inj.append(tusd_injetada.groupdict())
                                
                # Busca iluminação publica
                iluminacao_match = re.search(r'(?:Contribui[çc][ãa]o|Contrib).*?(?:Ilumina[çc][ãa]o|Ilum).*?\d+,\d+.*?(\d+,\d+)', linha)
                if iluminacao_match:
                    iluminacao_valor = iluminacao_match.group(1)
                
                # Busca adicional bandeira
                if (("Inj." not in linha or "Injetada" not in linha) and ("Adicional" in linha or "Adic" in linha or "Ad" in linha)):
                    bandeira_amarela_match = re.search(r'(?:Adicional|Adic\.|Ad\.)\s+(?:Bandeira|Band\.)\s+(?P<TipoBandeira>Amarela|Amarelo|Am\.|Amar\.)\s+kWh\s+(?P<Quant>\d*\.?\d+,\d+)-?\s*(?P<PUcTrib>\d*\.?\d+,\d+)-?\s*(?P<ValTot>\d*\.?\d+,\d+)-?\s*(?P<PISCOF>\d*\.?\d+,\d+)-?\s*(?P<BasCalc>\d*\.?\d+,\d+)-?\s*(?P<AliqICMS>\d*\.?\d+,\d+)-?\s*(?P<ICMS>\d*\.?\d+,\d+)-?\s*(?P<TarUnit>\d*\.?\d+,\d+)-?', linha)
                    bandeira_vermelha_match = re.search(r'(?:Adicional|Adic\.|Ad\.)\s+(?:Bandeira|Band\.)\s+(?P<TipoBandeira>Vermelha(?:\s+[12])?|Verm\.(?:\s+[12])?|Ver\.(?:\s+[12])?)\s+kWh\s+(?P<Quant>\d*\.?\d+,\d+)-?\s*(?P<PUcTrib>\d*\.?\d+,\d+)-?\s*(?P<ValTot>\d*\.?\d+,\d+)-?\s*(?P<PISCOF>\d*\.?\d+,\d+)-?\s*(?P<BasCalc>\d*\.?\d+,\d+)-?\s*(?P<AliqICMS>\d*\.?\d+,\d+)-?\s*(?P<ICMS>\d*\.?\d+,\d+)-?\s*(?P<TarUnit>\d*\.?\d+,\d+)-?', linha)
                    
                    if bandeira_amarela_match: # Se tiver adicional de bandeira amarela
                        intervalo_bandeiras.append(bandeira_amarela_match.groupdict())
                    elif bandeira_vermelha_match: # Se tiver adicional de bandeira vermelha
                        intervalo_bandeiras.append(bandeira_vermelha_match.groupdict())
                
                # energia_injetada_usina_match = re.search(r'(?:Energia|En\.?)\s+(?:Injetada|Inj\.?).*?(\d+(?:[.,]\d+)?)\s*$', linha)
                energia_injetada_usina_match = re.search(r'(?:Energia|En\.?)\s+(?:Injetada|Inj\.?)\s+no\s+mês.*?(\d+(?:[.,]\d+)?)\s*', linha)
                if energia_injetada_usina_match:
                    energia_injetada_usina = energia_injetada_usina_match.group(1)

                # creditos_recebidos_match = re.search(r'(?:Saldo\s+Total|Saldo\s+Tot\.?)\s+(?P<saldo_total>\d+(?:[.,]\d+)?)\s*kWh', linha)
                creditos_recebidos_match = re.search(r'(?:Saldo\s+Atualizado|Saldo\s+Atu\.?)\s+no\s+mês\s+(?P<saldo_atualizado>\d+(?:[.,]\d+)?)\s*kWh', linha)
                if creditos_recebidos_match:
                    # creditos_recebidos = creditos_recebidos_match.group('creditos')
                    saldo_total = creditos_recebidos_match.group('saldo_atualizado')
                    
                    print("Buscou os valores")

            guardar_consumo(numero_instalacao, intervalo_bandeiras, fatura_info['mes_ano'], tusd_info, fatura_info['valor'], datas_info['dias'])
            
            if geradora == "1":
                gerar_historico(numero_instalacao, fatura_info['mes_ano'], datas_info['data_inicial'], datas_info['data_leitura'], datas_info['dias'], energia_injetada_usina, iluminacao_valor)
                guardar_geracao(numero_instalacao, fatura_info['mes_ano'], energia_injetada_usina, tusd_inj, datas_info['data_inicial'], datas_info['data_leitura'], geradora)
                
            else:
                gerar_historico(numero_instalacao, fatura_info['mes_ano'], datas_info['data_inicial'], datas_info['data_leitura'], datas_info['dias'], saldo_total, iluminacao_valor)
                guardar_geracao(numero_instalacao, fatura_info['mes_ano'], tusd_info, tusd_inj, datas_info['data_inicial'], datas_info['data_leitura'], geradora)
            
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return None
        
# path = r"/media/hdfs/ULT/16 - Nova apuracao/2025/Fevereiro/Geradoras/Poleto/161171784/Fatura/245002145017.pdf"
# busca_path(path, "1")


# path = r"/media/hdfs/ULT/16 - Nova apuracao/2025/Fevereiro/Fredelino/1043813/Fatura/1043813 fev 25.pdf"
# busca_path(path, "0")