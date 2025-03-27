import sqlite3
import configparser
import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

config = configparser.ConfigParser()
config.read(r"./config.ini")

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
                    partes = data_referencia.split("/")
                    mes = int(partes[0])
                    ano = int(partes[1])
                    
                    # Criar objeto datetime para a data de referência
                    data_ref = datetime(year=ano, month=mes, day=1)
                    
                    # Gerar os 4 meses separadamente
                    data1 = data_ref  # Mês mais recente (mês de referência)
                    data2 = data_ref - relativedelta(months=1)
                    data3 = data_ref - relativedelta(months=2)
                    data4 = data_ref - relativedelta(months=3)  # Mês mais antigo
                    
                    # Formatar as datas sem zero à esquerda
                    mes1 = f"{data1.month}/{data1.year}"  # Mais recente
                    mes2 = f"{data2.month}/{data2.year}"
                    mes3 = f"{data3.month}/{data3.year}"
                    mes4 = f"{data4.month}/{data4.year}"  # Mais antigo
                    
                    # Criar as cláusulas CASE separadamente
                    case1 = f"WHEN '{mes1}' THEN 4"  # Valor 4 para o mais recente
                    case2 = f"WHEN '{mes2}' THEN 3"
                    case3 = f"WHEN '{mes3}' THEN 2"
                    case4 = f"WHEN '{mes4}' THEN 1"  # Valor 1 para o mais antigo
                    
                    query = f"""SELECT MES_CONSUMO, VALOR_FATURA
                                FROM historico
                                WHERE
                                    UNIDADE_EDP = '{unidade_edp}' AND
                                    MES_CONSUMO IN ('{mes1}', '{mes2}', '{mes3}', '{mes4}')
                                ORDER BY CASE MES_CONSUMO
                                    {case1}
                                    {case2}
                                    {case3}
                                    {case4}
                                    ELSE 0 END
                                """
                    
                    panel['targets'][0]['queryText'] = query
                    panel['targets'][0]['rawQueryText'] = query
                    
                if panel['id'] == 4: # ECONOMIA ACUMULADA
                    partes = data_referencia.split("/")
                    mes = int(partes[0])
                    ano = int(partes[1])
                    
                    # Criar objeto datetime para a data de referência
                    data_ref = datetime(year=ano, month=mes, day=1)
                    
                    # Gerar os 4 meses separadamente
                    data1 = data_ref  # Mês mais recente (mês de referência)
                    data2 = data_ref - relativedelta(months=1)
                    data3 = data_ref - relativedelta(months=2)
                    data4 = data_ref - relativedelta(months=3)  # Mês mais antigo
                    
                    # Formatar as datas sem zero à esquerda
                    mes1 = f"{data1.month}/{data1.year}"  # Mais recente
                    mes2 = f"{data2.month}/{data2.year}"
                    mes3 = f"{data3.month}/{data3.year}"
                    mes4 = f"{data4.month}/{data4.year}"  # Mais antigo
                    
                    # Criar as cláusulas CASE separadamente
                    case1 = f"WHEN '{mes1}' THEN 4"  # Valor 4 para o mais recente
                    case2 = f"WHEN '{mes2}' THEN 3"
                    case3 = f"WHEN '{mes3}' THEN 2"
                    case4 = f"WHEN '{mes4}' THEN 1"  # Valor 1 para o mais antigo

                    query = f"""SELECT
                                MES_CONSUMO,
                                ECONOMIA_VALOR,
                                SUM(ECONOMIA_VALOR) OVER (
                                    PARTITION BY UNIDADE_EDP
                                    ORDER BY CASE MES_CONSUMO
                                        {case4}
                                        {case3}
                                        {case2}
                                        {case1}
                                        ELSE 0 END
                                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                                ) AS ECONOMIA_ACUMULADA
                                FROM historico
                                WHERE
                                    UNIDADE_EDP = '{unidade_edp}' AND
                                    MES_CONSUMO IN ('{mes1}', '{mes2}', '{mes3}', '{mes4}')
                                ORDER BY CASE MES_CONSUMO
                                    {case4}
                                    {case3}
                                    {case2}
                                    {case1}
                                    ELSE 0 END
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