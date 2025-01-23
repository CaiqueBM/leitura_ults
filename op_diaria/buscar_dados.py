import requests
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

dfdados = pd.DataFrame()
data_atual = datetime.now()
data_anterior = data_atual - timedelta(days=1)

ids = [578496, 667618, 686932, 767468]
ult = 


# Conectar ao banco de dados
conn = sqlite3.connect('dados.db')
cursor = conn.cursor()

# Executar a consulta SQL para obter a última data adicionada
cursor.execute("SELECT MAX(DATA) FROM dados_diarios")

# Obter o resultado da consulta
ultima_data = cursor.fetchone()[0]

# Fechar a conexão com o banco de dados
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
    for usina_id in ids:

        ult_data = ultima_data + timedelta(days=1)

        while ult_data <= data_verificada:
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
    caminhoDB = f"/home/abs/Aplicativos/leitura_ults/dados.db"
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

# Conectar ao banco de dados e salvar o DataFrame
caminhoDB = f"/home/abs/Aplicativos/leitura_ults/dados.db"
conn = sqlite3.connect(caminhoDB)
dfdados.to_sql(
    "dados_diarios", conn, index=False, if_exists="append"
)  # Use "replace" se desejar substituir a tabela existente
conn.close()

#Buscar os dados de estimativa
from estimativa import estimar

estimativas = estimar()

data_formatada = datetime.strptime(data_anterior, '%Y-%m-%d').strftime('%d/%m/%Y')

# Obter o último dia do mês atual
ultimo_dia_mes = datetime(data_atual.year, data_atual.month, 1).replace(day=1, month=data_atual.month % 12 + 1) - timedelta(days=1)
ultimo_dia_att = ultimo_dia_mes.strftime("%Y-%m-%d")


mensagem = (
    f"*GERAÇÃO ULT:* \n\n"
    f"*DATA:* {data_formatada} \n\n"
    f"◉ *{dfdados.loc[dfdados['ULT'] == 'ULT 1', 'ULT'].iloc[0]}:*\n"
    f"*GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 1', 'GERACAO'].iloc[0]} kWh \n"
    f"*GERAÇÃO MÊS:* {estimativas[0]['ULT 1']} kWh\n"
    f"*PROJEÇÃO MÊS:* {estimativas[1]['ULT 1']} kWh\n\n"
    f"◉ *{dfdados.loc[dfdados['ULT'] == 'ULT 2', 'ULT'].iloc[0]}:*\n"
    f"*GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 2', 'GERACAO'].iloc[0]} kWh \n"
    f"*GERAÇÃO MÊS:* {estimativas[0]['ULT 2']} kWh\n"
    f"*PROJEÇÃO MÊS:* {estimativas[1]['ULT 2']} kWh\n\n"
    f"◉ *{dfdados.loc[dfdados['ULT'] == 'ULT 3', 'ULT'].iloc[0]}:*\n"
    f"*GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 3', 'GERACAO'].iloc[0]} kWh \n"
    f"*GERAÇÃO MÊS:* {estimativas[0]['ULT 3']} kWh\n"
    f"*PROJEÇÃO MÊS:* {estimativas[1]['ULT 3']} kWh\n\n"
    f"◉ *{dfdados.loc[dfdados['ULT'] == 'ULT 4', 'ULT'].iloc[0]}:*\n"
    f"*GERAÇÃO DIÁRIA:* {dfdados.loc[dfdados['ULT'] == 'ULT 4', 'GERACAO'].iloc[0]} kWh \n"
    f"*GERAÇÃO MÊS:* {estimativas[0]['ULT 4']} kWh\n"
    f"*PROJEÇÃO MÊS:* {estimativas[1]['ULT 4']} kWh\n\n"
)

print(mensagem)

# #Envio de mensagens para o whatsapp
# from run import enviar_mensagem

# with open('/home/abs/Aplicativos/leitura_ults/numeros.txt', 'r') as arquivo:
#     linhas = arquivo.readlines()

# for linha in linhas:
#     numero = str(linha.strip())
#     numero = numero + '@c.us'
#     enviar_mensagem(numero, mensagem)
