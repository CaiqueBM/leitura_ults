import requests
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

path_db = os.path.join(parent_dir, 'dados.sqlite')

dfdados = pd.DataFrame()
data_atual = datetime.now()
data_anterior = data_atual - timedelta(days=1)

def gerar_tabelas():
    # Conexão com o banco de dados
    conn = sqlite3.connect(path_db)
    c = conn.cursor()

    # Cria as tabelas se não existirem
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS dados_diarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ULT TEXT,
            DATA DATETIME,
            GERACAO INTEGER
        )
    """
    )

    conn.commit()
    c.close()
    # Fechar a conexão
    conn.close()

def estimar():
    # Conectar ao banco de dados
    conexao = sqlite3.connect(path_db)
    cursor = conexao.cursor()

    # Obter a data atual
    data_atual = datetime.now()
    dia_data_anterior = (datetime.now() - timedelta(days=1)).day
    data_anterior = datetime.now() - timedelta(days=1)

    # Obter o último dia do mês atual
    ultimo_dia_mes = (data_atual.replace(day=1, month=data_atual.month % 12 + 1) - timedelta(days=1)).day

    # Dicionário para armazenar os dados por ULT
    quantidade_zeros_por_ult = {}
    dados_por_ult = {}

    query_nomes = f"SELECT DISTINCT ULT FROM dados_diarios WHERE DATA = '{data_anterior.year:04d}-{data_anterior.month:02d}-{dia_data_anterior:02d}'"
    cursor.execute(query_nomes)
    nomes_ult = [row[0] for row in cursor.fetchall()]

    if data_atual.month != data_anterior.month:
        # Loop para buscar os dados por ULT
        for nome_ult in nomes_ult:
            # Query para obter os dados para a ULT atual
            query = f"""SELECT GERACAO
                FROM dados_diarios
                WHERE DATA BETWEEN '{data_anterior.year:04d}-{data_anterior.month:02d}-01'
                AND'{data_anterior.year:04d}-{data_anterior.month:02d}-{dia_data_anterior:02d}'
                AND ULT = '{nome_ult}'"""
            cursor.execute(query)
            geracoes = cursor.fetchall()
            # Armazenar os dados em uma lista para a ULT atual
            zeros = sum(1 for geracao in geracoes if geracao[0] == 0)
        
            # Armazenar a quantidade de zeros para a ULT atual
            quantidade_zeros_por_ult[f'{nome_ult}'] = zeros

            #dados_por_ult[f'ULT {ult}'] = [geracao[0] for geracao in geracoes]
            dados_por_ult[f'{nome_ult}'] = [geracao[0] for geracao in geracoes]
        # Fechar a conexão com o banco de dados
        cursor.close()
        conexao.close()
    else:
        # Loop para buscar os dados por ULT
        for nome_ult in nomes_ult:
            # Query para obter os dados para a ULT atual
            query = f"""SELECT GERACAO
                FROM dados_diarios
                WHERE DATA BETWEEN '{data_atual.year:04d}-{data_atual.month:02d}-01' AND '{data_atual.year:04d}-{data_atual.month:02d}-{dia_data_anterior:02d}'
                AND ULT = '{nome_ult}'
                AND DATA <= CURRENT_DATE
                ORDER BY DATA
                """
            cursor.execute(query)
            geracoes = cursor.fetchall()
            # Armazenar os dados em uma lista para a ULT atual
            zeros = sum(1 for geracao in geracoes if geracao[0] == 0)
        
            # Armazenar a quantidade de zeros para a ULT atual
            quantidade_zeros_por_ult[f'{nome_ult}'] = zeros

            dados_por_ult[f'{nome_ult}'] = [geracao[0] for geracao in geracoes]
        # Fechar a conexão com o banco de dados
        cursor.close()
        conexao.close()

    # Dicionário para armazenar as médias de geração por ULT
    medias_por_ult = {}

    # Loop para calcular a soma de geração para cada ULT do primeiro dia até o dia atual
    for ult, geracoes in dados_por_ult.items():
        print("SOMA GERAÇOES: ", sum(geracoes))
        print("QUANTIDADE DIAS GERADOS: ", len(geracoes))
        print("QUANTIDADE DE ZEROS: ", quantidade_zeros_por_ult[ult])
        
        # Evitar divisão por zero
        dias_nao_zero = len(geracoes) - quantidade_zeros_por_ult[ult]
        if dias_nao_zero > 0:
            media = sum(geracoes) / dias_nao_zero
        else:
            media = 0  # ou outro valor padrão que faça sentido para o seu caso
    
        medias_por_ult[ult] = media

    # Dicionário para armazenar as somas de geração por ULT
    somas_por_ult = {ult: sum(geracoes) for ult, geracoes in dados_por_ult.items()}

    # Dicionário para armazenar as projeções de geração por ULT
    projecoes_por_ult = {}

    if data_atual.day == 1:
        dias_restantes = dia_data_anterior - dia_data_anterior
    else:
        dias_restantes = ultimo_dia_mes - dia_data_anterior

    # Loop para projetar a geração para o restante do mês
    for ult, media in medias_por_ult.items():
        soma_atual = somas_por_ult[ult]
        projecao = soma_atual + (media * dias_restantes)
        projecoes_por_ult[ult] = projecao

    somas_ults = {ult: "{:.2f}".format(valor) for ult, valor in somas_por_ult.items()}
    projecoes_ults = {ult: "{:.2f}".format(valor) for ult, valor in projecoes_por_ult.items()}


    return somas_ults, projecoes_ults

def envio(numero, mensagem):
    import socketio
    import time

    # Configuração do cliente Socket.IO
    sio = socketio.Client()

    @sio.event
    def connect():
        print("Conectado ao servidor!")

    @sio.event
    def connect_error(data):
        print(f"Erro de conexão: {data}")

    @sio.event
    def disconnect():
        print("Desconectado do servidor")

    try:
        print("Tentando conectar ao servidor...")
        sio.connect('http://localhost:3006', socketio_path='/app')
        
        print("Enviando mensagem...")
        sio.emit('mensagem', {
            'numero': numero,
            'mensagem': mensagem
        })
        print(f"Mensagem enviada para {numero}")

        # Espera um pouco para garantir que a mensagem seja processada
        time.sleep(2)

    except socketio.exceptions.ConnectionError as e:
        print(f"Erro de conexão: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        if sio.connected:
            print("Desconectando...")
            sio.disconnect()
        else:
            print("Não foi possível estabelecer conexão")

def upsert_dados(df, path_db, table_name):
    conn = sqlite3.connect(path_db)
    cursor = conn.cursor()

    # Certifique-se de que a tabela existe
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            DATA TEXT,
            GERACAO REAL,
            ULT TEXT,
            PRIMARY KEY (DATA, ULT)
        )
    ''')

    # Preparar a query de upsert
    upsert_query = f'''
        INSERT OR REPLACE INTO {table_name} (DATA, GERACAO, ULT)
        VALUES (?, ?, ?)
    '''

    # Executar o upsert para cada linha do DataFrame
    for _, row in df.iterrows():
        cursor.execute(upsert_query, (row['DATA'], row['GERACAO'], row['ULT']))

    # Commit as mudanças e fechar a conexão
    conn.commit()
    conn.close()
    
if __name__ == '__main__':
    ids = [578496, 667618, 686932, 767468, 1115966, 806251]
    ult = {578496: "ULT 1", 667618: "ULT 3", 686932: "ULT 4", 767468: "ULT 2", 1115966:"Lucas Generoso", 806251:"Gilles"}

    # Conectar ao banco de dados
    conn = sqlite3.connect(path_db)
    cursor = conn.cursor()

    # Executar a consulta SQL para obter a última data adicionada
    cursor.execute("SELECT MAX(DATA) FROM dados_diarios")

    # Obter o resultado da consulta
    ultima_data = cursor.fetchone()[0]

    if not ultima_data:
        ultima_data = r"2022-01-01"

    # Fechar a conexão com o banco de dados
    cursor.close()
    conn.close()

    # Imprimir a última data
    print("A última data adicionada é:", ultima_data)

    # Converter a última data do formato string para datetime
    ultima_data = datetime.strptime(ultima_data, '%Y-%m-%d')
    print("A ultima data: ", ultima_data)

    #Verificar se a data do dia anterior é igual ou não a ultima data do banco de dados
    data_verificada = data_anterior - timedelta(days=1)

    data_anterior = data_anterior.strftime("%Y-%m-%d")

    if ultima_data != data_verificada:
        ult_data = ultima_data - timedelta(days=1)
        for usina_id in ids:

            ult_data = ultima_data + timedelta(days=1)

            while ult_data <= data_verificada:
                print(f"USINA: {usina_id}")
                print(f"DATA: {ult_data}")
                ult_data = ult_data.strftime("%Y-%m-%d")
                url = f"https://app.solarz.com.br/shareable/generation/period?usinaId={usina_id}&start={ult_data}&end={ult_data}&uniteMonths=false"

                # Realiza a requisição GET para obter os dados da página
                response = requests.get(url)

                # Verifica se a requisição foi bem-sucedida
                if response.status_code == 200:
                    # Converte a resposta para o formato JSON
                    data = response.json()
                    
                    # Obtém o valor de "totalGerado"
                    total_gerado = data.get('totalGerado')

                nome_ult = ult.get(usina_id, "Nome não encontrado ")

                df_usina = pd.DataFrame(
                    {
                        "DATA": ult_data,
                        "GERACAO": total_gerado,
                        "ULT": nome_ult,
                    },
                    index=[0]
                )
                dfdados = pd.concat([dfdados, df_usina], ignore_index=True)
                ult_data = datetime.strptime(ult_data, '%Y-%m-%d')
                ult_data = ult_data + timedelta(days=1)
                df_usina = pd.DataFrame()
        
        # Conectar ao banco de dados e salvar o DataFrame
        caminhoDB = path_db
        conn = sqlite3.connect(caminhoDB)
        dfdados.to_sql(
            "dados_diarios", conn, index=False, if_exists="append"
        )  # Use "replace" se desejar substituir a tabela existente
        conn.close()

        dfdados = pd.DataFrame()

    for usina_id in ids:
        url = f"https://app.solarz.com.br/shareable/generation/period?usinaId={usina_id}&start={data_anterior}&end={data_anterior}&uniteMonths=false"

        # Realiza a requisição GET para obter os dados da página
        response = requests.get(url)

        # Verifica se a requisição foi bem-sucedida
        if response.status_code == 200:
            # Converte a resposta para o formato JSON
            data = response.json()
            
            # Obtém o valor de "totalGerado"
            total_gerado = data.get('totalGerado')

        nome_ult = ult.get(usina_id, "Nome não encontrado ")

        df_usina = pd.DataFrame(
            {
                "DATA": data_anterior,
                "GERACAO": total_gerado,
                "ULT": nome_ult,
            },
            index=[0]
        )

        dfdados = pd.concat([dfdados, df_usina], ignore_index=True)

    upsert_dados(dfdados, path_db, "dados_diarios")

    estimativas = estimar()

    data_formatada = datetime.strptime(data_anterior, '%Y-%m-%d').strftime('%d/%m/%Y')

    # Obter o último dia do mês atual
    ultimo_dia_mes = datetime(data_atual.year, data_atual.month, 1).replace(day=1, month=data_atual.month % 12 + 1) - timedelta(days=1)
    ultimo_dia_att = ultimo_dia_mes.strftime("%Y-%m-%d")

    mensagem = (
        f"""🌞 *GERAÇÃO ULT:* 🌞
📅 *DATA:* {data_formatada} \n
⚡ *ULT 1:*
📈 *GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 1', 'GERACAO'].iloc[0] if not dfdados.loc[dfdados['ULT'] == 'ULT 1', 'GERACAO'].empty else 'N/A'} kWh
📊 *GERAÇÃO MÊS:* {estimativas[0].get('ULT 1', 'N/A')} kWh
🔮 *PROJEÇÃO MÊS:* {estimativas[1].get('ULT 1', 'N/A')} kWh\n
⚡ *ULT 2:*
📈 *GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 2', 'GERACAO'].iloc[0] if not dfdados.loc[dfdados['ULT'] == 'ULT 2', 'GERACAO'].empty else 'N/A'} kWh
📊 *GERAÇÃO MÊS:* {estimativas[0].get('ULT 2', 'N/A')} kWh
🔮 *PROJEÇÃO MÊS:* {estimativas[1].get('ULT 2', 'N/A')} kWh\n
⚡ *ULT 3:*
📈 *GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 3', 'GERACAO'].iloc[0] if not dfdados.loc[dfdados['ULT'] == 'ULT 3', 'GERACAO'].empty else 'N/A'} kWh
📊 *GERAÇÃO MÊS:* {estimativas[0].get('ULT 3', 'N/A')} kWh
🔮 *PROJEÇÃO MÊS:* {estimativas[1].get('ULT 3', 'N/A')} kWh\n
⚡ *ULT 4:*
📈 *GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 4', 'GERACAO'].iloc[0] if not dfdados.loc[dfdados['ULT'] == 'ULT 4', 'GERACAO'].empty else 'N/A'} kWh
📊 *GERAÇÃO MÊS:* {estimativas[0].get('ULT 4', 'N/A')} kWh
🔮 *PROJEÇÃO MÊS:* {estimativas[1].get('ULT 4', 'N/A')} kWh\n
⚡ *Lucas Generoso:*
📈 *GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'Lucas Generoso', 'GERACAO'].iloc[0] if not dfdados.loc[dfdados['ULT'] == 'Lucas Generoso', 'GERACAO'].empty else 'N/A'} kWh
📊 *GERAÇÃO MÊS:* {estimativas[0].get('Lucas Generoso', 'N/A')} kWh
🔮 *PROJEÇÃO MÊS:* {estimativas[1].get('Lucas Generoso', 'N/A')} kWh\n
⚡ *Gilles:*
📈 *GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'Gilles', 'GERACAO'].iloc[0] if not dfdados.loc[dfdados['ULT'] == 'Gilles', 'GERACAO'].empty else 'N/A'} kWh
📊 *GERAÇÃO MÊS:* {estimativas[0].get('Gilles', 'N/A')} kWh
🔮 *PROJEÇÃO MÊS:* {estimativas[1].get('Gilles', 'N/A')} kWh\n"""
    )

    print(mensagem)

    #Envio de mensagens para o whatsapp
    path_numeros = os.path.join(current_dir, 'numeros.txt')

    with open(path_numeros, 'r') as arquivo:
        linhas = arquivo.readlines()

    for linha in linhas:
        numero = str(linha.strip())
        numero = numero
        envio(numero, mensagem)
