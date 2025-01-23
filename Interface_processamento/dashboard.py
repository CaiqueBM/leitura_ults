import sqlite3
import configparser
import requests
import pandas as pd

config = configparser.ConfigParser()
config.read(r"./config.ini")

# def sanitize_json(obj):
#     if isinstance(obj, dict):
#         return {k: sanitize_json(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [sanitize_json(v) for v in obj]
#     elif isinstance(obj, float):
#         return obj if math.isfinite(obj) else None  # Substitui valores inválidos
#     return obj


# query = f"SELECT MONTANTE
#         FROM historico
#         WHERE CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND MES_DE_CONSUMO = '{mes_consumo}';"

def gerar_dashboard(unidade_edp, data_referencia):
    # Caminho para o banco de dados SQLite
    db_clientes = config['database']['dbclientes']

    # Guardar dados de siglas no dataframe
    conexao = sqlite3.connect(db_clientes)
    query = "SELECT PROPRIETARIO, NOME, URL_DASHBOARD, TOKEN_DASH FROM nomes WHERE UNIDADE_EDP = {unidade_edp}"
    df_dados = pd.read_sql_query(query, conexao)
    conexao.close()

    # Iterar sobre cada valor da coluna SiglaCCEE
    for index, row in df_dados.iterrows():
        token = row['TOKEN_DASH']
        ur_dash = row['URL_DASHBOARD']
        proprietario = row['PROPRIETARIO']
        query = ""

    # URL e configurações de conexão com o Grafana
        grafana_url = "http://localhost:3002"

        headers = {
            "Authorization": f"Bearer {token}",  # Substitua pelo seu token
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Passo 1: Obter o dashboard atual
        get_dashboard_url = f"{grafana_url}/api/dashboards/uid/{ur_dash}"
        
        response = requests.get(get_dashboard_url, headers=headers)
        
        if response.status_code == 200:
            dashboard_data = response.json()
            dashboard = dashboard_data['dashboard'] if dashboard_data['dashboard'] is not None else {}
            
            # Incrementar a versão do dashboard para forçar a atualização
            dashboard['version'] += 1
            
            # Passo 2: Encontrar o painel de texto e substituir a mensagem
            for panel in dashboard['panels']:
                if panel['id'] == 2: # CONSUMO DE ENERGIA
                    query = f"""SELECT VALOR_FATURA
                                FROM historico
                                WHERE
                                    CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                    MES_DE_CONSUMO = '{data_referencia}'"""
                    
                    panel['targets'][0]['queryText'] = query
                    panel['targets'][0]['rawQueryText'] = query

                if panel['id'] == 3: # HISTORICO MENSAL
                    ano = data_referencia.split("/")[1]
                    data_inicio = f"01/{ano}"
                    data_final = f"12/{ano}"
                    
                    query = f"""SELECT MES_DE_CONSUMO,
                                    VALOR_FATURA
                                FROM historico
                                WHERE
                                    UNIDADE_EDP = '{unidade_edp}' AND
                                    MES_DE_CONSUMO BETWEEN '{data_inicio}' AND '{data_final}'
                                ORDER BY MES_DE_CONSUMO ASC"""
                    
                    panel['targets'][0]['queryText'] = query
                    panel['targets'][0]['rawQueryText'] = query
                    
                if panel['id'] == 4: # ECONOMIA ACUMULADA
                    ano = data_referencia.split("/")[1]
                    data_inicio = f"01/{ano}"
                    data_final = f"12/{ano}"

                    query = f"""SELECT 
                                    MES_DE_CONSUMO,
                                    ECONOMIA_VALOR,
                                    SUM(ECONOMIA_VALOR) OVER (
                                        PARTITION BY UNIDADE_EDP
                                        ORDER BY CAST(SUBSTR(MES_DE_CONSUMO, 4, 4) || '-' || SUBSTR(MES_DE_CONSUMO, 1, 2) AS TEXT)
                                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                                    ) AS ECONOMIA_ACUMULADA
                                FROM historico
                                WHERE
                                    UNIDADE_EDP = '{unidade_edp}' AND 
                                    MES_DE_CONSUMO BETWEEN '{data_inicio}' AND '{data_final}'
                                ORDER BY 
                                    CAST(SUBSTR(MES_DE_CONSUMO, 4, 4) || '-' || SUBSTR(MES_DE_CONSUMO, 1, 2) AS TEXT);
                                """
                    panel['targets'][0]['queryText'] = query
                    panel['targets'][0]['rawQueryText'] = query

                if panel['id'] == 5: # ENERGIA CONTRATADA
                    query = f"""SELECT MONTANTE_CONT
                                FROM historico
                                WHERE
                                    CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                    MES_DE_CONSUMO = '{data_referencia}';"""
                    
                    panel['targets'][0]['queryText'] = query
                    panel['targets'][0]['rawQueryText'] = query
                
                if panel['id'] == 6: # IDENTIFICAÇÃO
                    query = f'<h1 style="text-align: center; color: black;">FATURA DE ENERGIA | {proprietario} - {unidade_edp} | MÊS: {data_referencia}</h1>'
                    
                    panel['options']['content'] = query
                    
                if panel['id'] == 7:  # ECONOMIA
                    query = f"""SELECT ECONOMIA
                                FROM historico
                                WHERE
                                    CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                    MES_DE_CONSUMO = '{data_referencia}';"""
                    
                    panel['targets'][0]['queryText'] = query
                    panel['targets'][0]['rawQueryText'] = query

            # Passo 3: Atualizar o dashboard com o painel de texto modificado
            data = {
                "dashboard": dashboard,
                "message": "Conteúdo do painel de alertas substituído",
                "overwrite": True,
                "folderId": 2
            }
            update_dashboard_url = f"{grafana_url}/api/dashboards/db"

            # sanitize_json(data)

            response = requests.post(update_dashboard_url, headers=headers, json=data)