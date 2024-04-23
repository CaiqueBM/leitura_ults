import requests
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

dfdados = pd.DataFrame()
data_atual = datetime.now()
data_anterior = data_atual - timedelta(days=1)
data_anterior = data_anterior.strftime("%Y-%m-%d")

"""ids = [578496, 667618]
ult = {578496: "ULT 1", 667618: "ULT 3"}"""

ids = [578496, 667618, 686932, 767468]
ult = {578496: "ULT 1", 667618: "ULT 3", 686932: "ULT 4", 767468: "ULT 2"}

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

mensagem = (
    f"*GERAÇÃO TOTAL DIÁRIA:* \n"
    f"◉ "
    f"*{dfdados.loc[dfdados['ULT'] == 'ULT 1', 'ULT'].iloc[0]}:* {dfdados.loc[dfdados['ULT'] == 'ULT 1', 'GERACAO'].iloc[0]} kWh \n"
    f"◉ "
    f"*{dfdados.loc[dfdados['ULT'] == 'ULT 2', 'ULT'].iloc[0]}:* {dfdados.loc[dfdados['ULT'] == 'ULT 2', 'GERACAO'].iloc[0]} kWh \n"
    f"◉ "
    f"*{dfdados.loc[dfdados['ULT'] == 'ULT 3', 'ULT'].iloc[0]}:* {dfdados.loc[dfdados['ULT'] == 'ULT 3', 'GERACAO'].iloc[0]} kWh \n"
    f"◉ "
    f"*{dfdados.loc[dfdados['ULT'] == 'ULT 4', 'ULT'].iloc[0]}:* {dfdados.loc[dfdados['ULT'] == 'ULT 4', 'GERACAO'].iloc[0]} kWh"
)

print(mensagem)

# Conectar ao banco de dados e salvar o DataFrame
conn = sqlite3.connect("dados.db")
dfdados.to_sql(
    "dados_diarios", conn, index=False, if_exists="append"
)  # Use "replace" se desejar substituir a tabela existente
conn.close()

#Envio de mensagens para o whatsapp
from run import enviar_mensagem

with open('/home/caique/Documentos/leitura_ults/numeros.txt', 'r') as arquivo:
    linhas = arquivo.readlines()

for linha in linhas:
    numero = str(linha.strip())
    numero = numero + '@c.us'
    enviar_mensagem(numero, mensagem)