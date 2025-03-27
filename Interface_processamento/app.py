from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash, jsonify, current_app, render_template_string
import sqlite3
from datetime import datetime, timedelta
import os
from fuzzywuzzy import process
import gspread
import requests
import pandas as pd
import math
from datetime import datetime
import subprocess
import sys
import barcode
from barcode.writer import ImageWriter
import json
from dateutil.relativedelta import relativedelta


import shutil
import webbrowser
import time
import http.server
import socketserver
import threading

# Adiciona o diretório pai ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))

from dados_fatura import busca_path
from dados_demonstrativo import busca_demonstrativo

parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import configparser

config = configparser.ConfigParser()
config.read(os.path.join(parent_dir, 'config.ini'))

# Função para normalizar nomes
def normalizar_nome(nome):
    return nome.strip().lower()

# Função para encontrar o nome da pasta mais próximo do nome do banco de dados
def encontrar_mais_proximo(nome_banco, nomes_pasta):
    # Normalizar o nome do banco de dados
    nome_banco_normalizado = normalizar_nome(nome_banco)
    
    # Criar um dicionário para mapear nomes normalizados aos nomes originais das pastas
    mapa_normalizado_para_original = {
        normalizar_nome(nome_pasta): nome_pasta
        for nome_pasta in nomes_pasta
    }
    
    # Obter o nome normalizado mais próximo
    nome_normalizado_mais_proximo = process.extractOne(
        nome_banco_normalizado, 
        list(mapa_normalizado_para_original.keys())
    )[0]
    
    # Retornar o nome original da pasta correspondente
    return mapa_normalizado_para_original[nome_normalizado_mais_proximo]

# Função para verificar se existe a fatura em uma instalação
def verificar_arquivo(caminho_instalacao):
    try:
        # Verifica se o diretório existe
        if not os.path.exists(caminho_instalacao):
            return None
            
        # Lista os arquivos do diretório
        arquivos = os.listdir(caminho_instalacao)
        
        # Verifica se há exatamente um arquivo
        if len(arquivos) == 1:
            return arquivos[0]  # Retorna o nome do arquivo
        else:
            return None
            
    except Exception as e:
        print(f"Erro ao buscar fatura: {str(e)}")
        return None

# Função auxiliar para tentar converter para inteiro
def try_int(value):
    try:
        return int(value)
    except ValueError:
        return None
    
def adequacao(valor):
    try:
        valor_att = valor.replace(",", ".")
        return float(valor_att)

    except ValueError:
        return valor

def sanitize_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json(v) for v in obj]
    elif isinstance(obj, float):
        return obj if math.isfinite(obj) else None  # Substitui valores inválidos
    return obj

def gerar_dashboard(unidade_edp, data_referencia, output, linha_digitavel):
    
    if output == "":
        # Caminho para o banco de dados SQLite
        db_clientes = config['database']['dbclientes']

        # Guardar dados de siglas no dataframe
        conexao = sqlite3.connect(db_clientes)
        query = f"""SELECT PROPRIETARIO, NOME, URL_DASHBOARD, TOKEN_DASH FROM nomes WHERE UNIDADE_EDP = {unidade_edp}"""
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
                    print(panel['id'])
                    if panel['id'] == 2: # CONSUMO DE ENERGIA
                        ano = data_referencia.split("/")[1]
                        data_inicio = f"01/{ano}"
                        data_final = f"12/{ano}"

                        conn = sqlite3.connect(db_clientes)
                        cursor = conn.cursor()

                        # Recuperar detalhes do cliente
                        cursor.execute(f'''SELECT 
                                                MAX(VALOR_FATURA) AS MAIOR_VALOR_EDP
                                            FROM (
                                                SELECT 
                                                    MES_CONSUMO,
                                                    VALOR_FATURA
                                                FROM 
                                                    historico
                                                WHERE 
                                                    CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND 
                                                    MES_CONSUMO BETWEEN '{data_inicio}' AND '{data_final}'
                                                GROUP BY 
                                                    MES_CONSUMO
                                            ) AS subquery;'''
                                            )
                        max_valor = cursor.fetchone()
                        
                        
                        query = f"""SELECT VALOR_FATURA
                                    FROM historico
                                    WHERE
                                        CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                        MES_CONSUMO = '{data_referencia}'"""
                        cursor.execute(query)
                        max_valor_alt = cursor.fetchone()
                        cursor.close()
                        conn.close()
                        
                        if max_valor == "" or max_valor == None:
                            panel['fieldConfig']['defaults']['max'] = max_valor
                        else:
                            panel['fieldConfig']['defaults']['max'] = max_valor_alt

                        panel['title'] = "Consumo de energia EDP"
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
                        data4 = data_ref - relativedelta(months=3)
                        data5 = data_ref - relativedelta(months=4)
                        data6 = data_ref - relativedelta(months=5)
                        data7 = data_ref - relativedelta(months=6)
                        data8 = data_ref - relativedelta(months=7)
                        data9 = data_ref - relativedelta(months=8)
                        data10 = data_ref - relativedelta(months=9)
                        data11 = data_ref - relativedelta(months=10)
                        data12 = data_ref - relativedelta(months=11) # Mês mais antigo
                        
                        # Formatar as datas sem zero à esquerda
                        mes1 = f"{data1.month}/{data1.year}"  # Mais recente
                        mes2 = f"{data2.month}/{data2.year}"
                        mes3 = f"{data3.month}/{data3.year}"
                        mes4 = f"{data4.month}/{data4.year}"
                        mes5 = f"{data5.month}/{data5.year}"  
                        mes6 = f"{data6.month}/{data6.year}"
                        mes7 = f"{data7.month}/{data7.year}"
                        mes8 = f"{data8.month}/{data8.year}"
                        mes9 = f"{data9.month}/{data9.year}"
                        mes10 = f"{data10.month}/{data10.year}"
                        mes11 = f"{data11.month}/{data11.year}"
                        mes12 = f"{data12.month}/{data12.year}"  # Mais antigo
                        
                        # Criar as cláusulas CASE separadamente
                        case1 = f"WHEN '{mes1}' THEN 12"  # Valor 12 para o mais recente
                        case2 = f"WHEN '{mes2}' THEN 11"
                        case3 = f"WHEN '{mes3}' THEN 10"
                        case4 = f"WHEN '{mes4}' THEN 9"
                        case5 = f"WHEN '{mes5}' THEN 8"
                        case6 = f"WHEN '{mes6}' THEN 7"
                        case7 = f"WHEN '{mes7}' THEN 6"
                        case8 = f"WHEN '{mes8}' THEN 5"
                        case9 = f"WHEN '{mes9}' THEN 4"
                        case10 = f"WHEN '{mes10}' THEN 3"
                        case11 = f"WHEN '{mes11}' THEN 2"
                        case12 = f"WHEN '{mes12}' THEN 1"
                        
                        query = f"""SELECT MES_CONSUMO, VALOR_FATURA
                                    FROM historico
                                    WHERE
                                        UNIDADE_EDP = '{unidade_edp}' AND
                                        MES_CONSUMO IN ('{mes1}', '{mes2}', '{mes3}', '{mes4}', '{mes5}', '{mes6}', '{mes7}', '{mes8}', '{mes9}', '{mes10}', '{mes11}', '{mes12}')
                                    ORDER BY CASE MES_CONSUMO
                                        {case1}
                                        {case2}
                                        {case3}
                                        {case4}
                                        {case5}
                                        {case6}
                                        {case7}
                                        {case8}
                                        {case9}
                                        {case10}
                                        {case11}
                                        {case12}
                                        ELSE 0 END
                                    """
                                               
                        conn = sqlite3.connect(db_clientes)
                        cursor = conn.cursor()

                        # Sua query original
                        query_busca = f"""SELECT MAX(VALOR_FATURA) as maior_valor
                                    FROM historico
                                    WHERE
                                        UNIDADE_EDP = '{unidade_edp}' AND
                                        MES_CONSUMO IN ('{mes1}', '{mes2}', '{mes3}', '{mes4}', '{mes5}', '{mes6}', '{mes7}', '{mes8}', '{mes9}', '{mes10}', '{mes11}', '{mes12}')
                                    """

                        cursor.execute(query_busca)
                        maior_valor = cursor.fetchone()[0]
                        cursor.close()
                        conn.close()
                        
                        # tam_correto = economia_acumulada.replace(',', '.').split('.')[0]
                        
                        qtd_caracteres = len(str(int(maior_valor)))
                        if qtd_caracteres < 4:
                            maximo_field = (((maior_valor + 49) // 50) * 50) + 50
                        elif qtd_caracteres < 5:
                            maximo_field = (((maior_valor + 49) // 50) * 50) + 500
                        else:
                            maximo_field = (((maior_valor + 499) // 500) * 500) + 1000
                        
                        panel['fieldConfig']['defaults']['max'] = int(maximo_field)
                        panel['options']['xTickLabelRotation'] = "-45"
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
                                    
                        conn = sqlite3.connect(db_clientes)
                        cursor = conn.cursor()

                        # Sua query original
                        query_busca = f"""SELECT MAX(ECONOMIA_ACUMULADA)
                                    FROM (
                                        SELECT
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
                                    ) subquery
                                    """

                        cursor.execute(query_busca)
                        economia_acumulada = cursor.fetchone()[0]
                        cursor.close()
                        conn.close()
                        
                        # tam_correto = economia_acumulada.replace(',', '.').split('.')[0]
                            
                        qtd_caracteres = len(str(int(economia_acumulada)))
                        if qtd_caracteres < 4:
                            maximo_field = (((economia_acumulada + 49) // 50) * 50) + 50
                        elif qtd_caracteres < 5:
                            maximo_field = (((economia_acumulada + 49) // 50) * 50) + 500
                        else:
                            maximo_field = (((economia_acumulada + 499) // 500) * 500) + 1000

                        panel['fieldConfig']['defaults']['max'] = int(maximo_field)
                        panel['options']['xTickLabelRotation'] = "-45"
                        panel['targets'][0]['queryText'] = query
                        panel['targets'][0]['rawQueryText'] = query

                    if panel['id'] == 5: # ENERGIA CONTRATADA
                        query = f"""SELECT MONTANTE_CONT
                                    FROM historico
                                    WHERE
                                        CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                        MES_CONSUMO = '{data_referencia}';"""
                        
                        panel['title'] = "Montante Contratado"
                        panel['targets'][0]['queryText'] = query
                        panel['targets'][0]['rawQueryText'] = query
                        # panel['options']['text']['valueSize'] = 25

                    if panel['id'] == 7:  # ECONOMIA
                        query = f"""SELECT CAST(ECONOMIA_VALOR AS DECIMAL(10,2)) AS ECONOMIA_VALOR
                                    FROM historico
                                    WHERE
                                        CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                        MES_CONSUMO = '{data_referencia}';"""
                        
                        panel['targets'][0]['queryText'] = query
                        panel['targets'][0]['rawQueryText'] = query

                    if panel['id'] == 8:  # IDENTIFICAÇÃO DE FATURA
                        ano = data_referencia.split("/")[1]
                        mes = data_referencia.split("/")[0]
                        data_atual = datetime.now()
                        data_hoje = data_atual.day 
                        mes_atual = data_atual.month # Mês
                        ano_atual = data_atual.year
                        data_mod = f"{mes}-{ano}"
                        data_fatura = f"{data_hoje}/{mes_atual}/{ano_atual}"

                        numero_fatura = f"{unidade_edp}-{data_mod}"

                        vencimento_fatura = f"20/{mes_atual}/{ano_atual}"

                        conn = sqlite3.connect(db_clientes)
                        cursor = conn.cursor()

                        # Recuperar detalhes do cliente
                        cursor.execute(f"""SELECT VALOR_CONTRATADO
                                            FROM historico
                                                WHERE
                                                    CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                                    MES_CONSUMO = '{data_referencia}'"""
                                                    )
                        busca = cursor.fetchone()
                        cursor.close()
                        conn.close()

                        conn = sqlite3.connect(db_clientes)
                        cursor = conn.cursor()

                        # Recuperar detalhes do cliente
                        cursor.execute(f"""SELECT UNIDADE_EDP, NOME
                                            FROM nomes
                                            WHERE CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}'"""
                                        )
                        cliente = cursor.fetchone()
                        cursor.close()
                        conn.close()

                        valor_fatura = f"R$ {busca[0]}"

                        query = f'''<h1 style="text-align: center; color: rgb(0, 111, 192); text-decoration: underline;">FATURA DE EFICIÊNCIA ENERGÉTICA</h1>
                                    <h2 style="text-align: center; color: rgb(0, 111, 192);">{cliente[1]}</h2>

                                    <table style="text-align: center; border: 1px solid white; width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed;">
                                    <thead>
                                        <tr>
                                        <th style="text-align: center; background-color: rgb(0, 111, 192); color: white; padding: 5px; width: 50%;">Nº da fatura</th>
                                        <th style="text-align: center; background-color: rgb(0, 111, 192); color: white; padding: 5px; width: 50%;">Data de Emissão</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                        <td style="text-align: center; padding: 5px;">{numero_fatura}</td>
                                        <td style="text-align: center; padding: 5px;">{data_fatura}</td>
                                        </tr>
                                    </tbody>
                                    </table>

                                    <table style="text-align: center; border: 1px solid white; width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed;">
                                    <thead>
                                        <tr>
                                        <th style="text-align: center; background-color: rgb(0, 111, 192); color: white; padding: 5px; width: 50%;">Valor Fatura</th>
                                        <th style="text-align: center; background-color: rgb(0, 111, 192); color: white; padding: 5px; width: 50%;">Data de Vencimento</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                        <td style="text-align: center; padding: 5px;">{valor_fatura}</td>
                                        <td style="text-align: center; padding: 5px;">{vencimento_fatura}</td>
                                        </tr>
                                    </tbody>
                                    </table>
                                    '''
                        
                        # panel['options']['text']['valueSize'] = 25
                        panel['options']['content'] = query

                    if panel['id'] == 9: # DIVISAO DE VALORES (PIZZA)
                        query = f"""SELECT VALOR_FATURA,VALOR_CONTRATADO,ECONOMIA_VALOR
                                    FROM historico
                                    WHERE
                                        CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                        MES_CONSUMO = '{data_referencia}'"""

                        panel['targets'][0]['queryText'] = query
                        panel['targets'][0]['rawQueryText'] = query

                    if panel['id'] == 10: # LEGENDA DO ID 9

                        conn = sqlite3.connect(db_clientes)
                        cursor = conn.cursor()

                        # Recuperar detalhes do cliente
                        cursor.execute(f"""SELECT ECONOMIA_VALOR, VALOR_CONTRATADO, VALOR_FATURA
                                            FROM historico
                                            WHERE
                                                CAST(UNIDADE_EDP AS UNSIGNED) = '{unidade_edp}' AND
                                                MES_CONSUMO = '{data_referencia}'"""
                                                    )
                        busca = cursor.fetchone()
                        cursor.close()
                        conn.close()

                        economia_valor = f"{float(busca[0]):.2f}"  # Primeiro valor de 'busca'
                        fatura_valor = f"{float(busca[1]):.2f}"      # Segundo valor de 'busca'
                        fatura_edp = f"{float(busca[2]):.2f}"    # Terceiro valor de 'busca'

                        query = f'''<div style="width: 165px; padding: 10px; font-family: Arial, sans-serif; font-size: 10px; margin-top: 30px;">
                                        <h3 style="text-align: center; color: rgb(0, 111, 192);  margin-bottom: 20px;">LEGENDA</h3>
                                        <div style="text-align: center; margin-bottom: 20px;">
                                            <span style="font-size: 12px;">Economia: R$ {economia_valor}</span>
                                            <div style="height: 5px; background-color: #1cac14; margin-top: 5px; width: auto; margin-left: auto;"></div>
                                        </div>
                                        <div style="text-align: center; margin-bottom: 20px;">
                                            <span style="font-size: 12px;">Fatura EDP: R$ {fatura_edp}</span>
                                            <div style="height: 5px; background-color: #f4e44c; margin-top: 5px; width: auto; margin-left: auto;"></div>
                                        </div>
                                        <div style="text-align: center; margin-bottom: 20px;">
                                            <span style="font-size: 12px;">Valor Fatura: R$ {fatura_valor}</span>
                                            <div style="height: 5px; background-color: #6494e4; margin-top: 5px; width: auto; margin: auto;"></div>
                                        </div>
                                    </div>
                                    '''


                                    
                        
                        panel['options']['content'] = query
                        
                    if panel['id'] == 11:
                        query = f"""
                        <h2 style="text-align: center; padding: 0px 15px; font-size:17px; margin-top:20px;">PAGAMENTO VIA CÓDIGO DE BARRAS</h2>
                        <div style="display: grid; place-items: center; text-align: center; padding: 0px 15px; height: 100px; margin-top:70px;">
                        <h4 style="text-align: center; padding: 0px 15px; font-size:13px; margin-top: 50px">Simulação de Fatura</h4>
                        </div>
                        """
                        panel['options']['content'] = query 

    else:
        output_img = output.split("/grafana")[1]
        output_img = f"{output_img}.png"
        # Caminho para o banco de dados SQLite
        db_clientes = config['database']['dbclientes']

        # Guardar dados de siglas no dataframe
        conexao = sqlite3.connect(db_clientes)
        query = f"""SELECT PROPRIETARIO, NOME, URL_DASHBOARD, TOKEN_DASH FROM nomes WHERE UNIDADE_EDP = {unidade_edp}"""
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
                                
                # Passo 2: Encontrar o painel de texto e substituir a mensagem
                for panel in dashboard['panels']:
                    if panel['id'] == 11:
                        query = f"""<div style="width: 500px; padding: 10px; font-family: Arial, sans-serif; font-size: 10px; margin-top: 30px;">
                                <h2 style="text-align: center; padding: 0px 15px; font-size:17px; margin-top:10px;">PAGAMENTO VIA CÓDIGO DE BARRAS</h2>
                                <img src="{output_img}" alt="Codigo de Barras" style="margin-top: 20px; width: auto; height: 100px;">
                                <h3 style="text-align: center; padding: 0px 15px; font-size:16px;margin-top: 10px;">{linha_digitavel}</h3>
                                <h5 style="text-align: center; padding: 0px 15px; font-size:12px; margin-top: 40px">*Pagamento pode ser efetuado até a data de vencimento</h5>
                            </div>"""
                        
                        panel['options']['content'] = query   

    # Passo 3: Atualizar o dashboard com o painel de texto modificado
    data = {
        "dashboard": dashboard,
        "message": "Conteúdo do painel de alertas substituído",
        "overwrite": True,
        "folderId": 4
    }
    update_dashboard_url = f"{grafana_url}/api/dashboards/db"

    data_mod = sanitize_json(data)

    response = requests.post(update_dashboard_url, headers=headers, json=data_mod)
    return dashboard

def gerar_cod_barras(codigo_itf, output_file):
    # Configurações personalizadas do ImageWriter
    options = {
        "write_text": False,
        "module_width": 0.25,  # Largura de cada módulo/barra (padrão é 0.2)
        "module_height": 15.0,  # Altura das barras (ajuste conforme necessário)
        "quiet_zone": 10,  # Margem em branco nas laterais (aumente se os números cortarem)
        "font_size": 10,  # Tamanho da fonte para os números
        "text_distance": 5.0,  # Distância entre os números e as barras
    }

    # Gerar o código de barras ITF
    barcode_format = "itf"  # Especifica o formato ITF
    barcode_obj = barcode.get(barcode_format, codigo_itf, writer=ImageWriter())
    barcode_obj.save(output_file, options=options)
    print(f"Imagem ITF gerada com sucesso: {output_file}")

def criar_snapshot(unidade_edp, grafana_url, dashboard_json):

    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()
    query = f"""SELECT NOME, TOKEN_DASH FROM nomes WHERE UNIDADE_EDP = {unidade_edp}"""
    cursor.execute(query)
    cliente = cursor.fetchone()
    cursor.close()
    conn.close()

    # Endpoint para criar snapshots
    snapshot_url = f"{grafana_url}/api/snapshots"

    # Cabeçalhos para a solicitação
    headers = {
        "Authorization": f"Bearer {cliente[1]}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Configuração do snapshot
    snapshot_payload = {
        "dashboard": dashboard_json,
        "expires": 3600,  # Tempo para o snapshot expirar (em segundos), ajuste conforme necessário
        "name": f"{cliente[0]} - Snapshot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "external": False,
        "public": True,
        "enable": True
    }

    user = config['auth']['user']
    password = config['auth']['password']

    # Cabeçalhos de autenticação (usando autenticação básica)
    auth = (user, password)  # Usando nome de usuário e senha

    try:
        # Enviando a solicitação para criar o snapshot
        response = requests.post(snapshot_url, headers=headers, data=json.dumps(snapshot_payload), auth=auth)
        response.raise_for_status()  # Levanta uma exceção para erros HTTP

        # Resultado
        snapshot = response.json()

        # Obtém o diretório do próprio script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Caminho do arquivo dentro da mesma pasta do script
        temp_snapshot_path = os.path.join(script_dir, "temp_snapshot.txt")

        print("PATH PARA O SNAPSHOT: ", temp_snapshot_path)

        # Abre o arquivo e escreve nele
        with open(temp_snapshot_path, 'w') as temp_file:
            temp_file.write(f"{unidade_edp}:{snapshot.get('key')}\n")

            print(f"Arquivo criado/modificado em: {temp_snapshot_path}")

        if not snapshot_url:
            print("Falha ao criar o snapshot.")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao criar snapshot: {e}")
        return None

def gerar_snapshot_pdf(path_output):
    try:
        # Obtém o caminho absoluto do script Node.js
        node_script_path = os.path.abspath(os.path.join(
            current_app.root_path, 
            'topdf.js'
        ))

        # Copia o ambiente atual
        env = os.environ.copy()
        env['NODE_DEBUG'] = 'puppeteer'  # Adiciona debug para Node.js

        # Monta o comando
        command = [
            "node",
            node_script_path,
            path_output
        ]

        # Executa o script e captura a saída
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            env=env
        )

        print("Saída do Node.js:", result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print("Erro detalhado:")
        print(f"Comando que falhou: {e.cmd}")
        print(f"Código de saída: {e.returncode}")
        print(f"Saída de erro: {e.stderr}")
        print(f"Saída padrão: {e.stdout}")
        return False
    
def mod_metadados(path_output):
    try:
        
        chmod_command = ["sudo", "chmod", "g+rw", path_output]
        chmod_result = subprocess.run(chmod_command, capture_output=True, text=True)
        
        # Obtém o caminho absoluto do script Node.js
        node_script_path = os.path.abspath(os.path.join(
            current_app.root_path,
            'metadados_mod.js'
        ))
        
        # Monta o comando
        command = [
            "node",
            node_script_path,
            path_output
        ]
        
        # Executa o script e captura a saída
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        print("Saída do Node.js:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("Erro ao executar o script Node.js:")
        print(f"Comando que falhou: {e.cmd}")
        print(f"Código de saída: {e.returncode}")
        print(f"Saída de erro: {e.stderr}")
        print(f"Saída padrão: {e.stdout}")
        return False
    except FileNotFoundError as e:
        print(f"Erro: {e}")
        return False
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return False

def apagar_snapshot(unidade_edp):
      # Obtém o diretório do próprio script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Caminho do arquivo dentro da mesma pasta do script
    temp_snapshot_path = os.path.join(script_dir, "temp_snapshot.txt")

    grafana_url = "http://192.168.33.234:3002"

    # Caminho para o banco de dados SQLite
    db_clientes = config['database']['dbclientes']

    conn = sqlite3.connect(db_clientes)
    query = f"""SELECT NOME, URL_DASHBOARD, TOKEN_DASH FROM nomes WHERE UNIDADE_EDP = {unidade_edp}"""
    df_dados = pd.read_sql_query(query, conn)
    conn.close()

    # Ler o arquivo
    with open(temp_snapshot_path, 'r') as temp_file:
        lines = temp_file.readlines()  # Lê todas as linhas do arquivo

        # Iterar sobre cada valor da coluna SiglaCCEE
    for index, row in df_dados.iterrows():
        token = row['TOKEN_DASH']

        if lines:

            linha_1 = lines[0].strip()

            key = linha_1.split(':')[1]
        # key = lines[index].split("\n")[0].split(":")[1].strip()

        headers = {
        "Authorization": f"Bearer {token}",  # Substitua pelo seu token
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

        url = f"{grafana_url}/api/snapshots/{key}"
    
        # Enviar a requisição DELETE
        response = requests.delete(url, headers=headers)
        if not response.status_code == 200:
            print(f"Erro ao deletar snapshot: {response.status_code} - {response.text}")
            return False
        else:
            return True
    
# Criação do aplicativo Flask
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'secret'

# Credenciais de login
USERNAME = config['auth_system']['username']
PASSWORD = config['auth_system']['password']

# Caminho para o banco de dados SQLite
db_clientes = config['database']['dbclientes']

# Função para gerar o nome do pdf do dashboard, juntando a sigla com o mes de referencia
def filename_dashboard(sigla_ccee):
    mes_referencia = (datetime.now() - timedelta(days=30)).strftime('%m-%Y')
    return f"{sigla_ccee}_{mes_referencia}.pdf"

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('select_date'))
        else:
            return render_template('login.html', error="Credenciais inválidas.")
    return render_template('login.html')

# Rota para logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# # Rota para escolher a data de referencia
@app.route('/select_date', methods=['GET', 'POST'])
def select_date():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        ano = request.form['ano']
        mes = request.form['mes']
        # Armazenando o ano e mês na sessão
        session['ano'] = ano
        session['mes'] = mes
        return redirect(url_for('index'))  # Redireciona de volta para a página inicial ou outra

    return render_template('select_date.html')  # Renderiza a página de seleção

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    ano = session.get('ano')
    mes = session.get('mes').lstrip('0')
    data = f"{mes}/{ano}"

    meses = {
            1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }

    mes_formatado = meses[int(mes)]

    # update_status(db_clientes)  # Atualizar os status antes de carregar a página inicial
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()
    cursor.execute("""SELECT NOME, UNIDADE_EDP, PROPRIETARIO, PATH_FATURA, GERADORA 
    FROM nomes 
    ORDER BY GERADORA ASC, NOME ASC
    """)
    clients = cursor.fetchall()
    cursor.close()
    conn.close()

    clients_with_class = []  # Lista precisa ser definida antes do loop

    for client in clients:
        path_fatura = client[3]
        
        if client[4] == "1":
            path_pasta_fatura = f"{path_fatura}{ano}/{mes_formatado}/Geradoras/{client[2]}/{client[1]}/Fatura"
            nome_fatura = verificar_arquivo(path_pasta_fatura)
            tem_arquivo_fatura = bool(nome_fatura)
            valor_cor = "geradora-verde"
        else:
            path_pasta_fatura = f"{path_fatura}{ano}/{mes_formatado}/{client[2]}/{client[1]}/Fatura"
            path_pasta_dashboard = f"{path_fatura}{ano}/{mes_formatado}/{client[2]}/{client[1]}/Dashboard"
            nome_fatura = verificar_arquivo(path_pasta_fatura)
            nome_dashboard = verificar_arquivo(path_pasta_dashboard)
            tem_arquivo_fatura = bool(nome_fatura)
            tem_arquivo_dashboard = bool(nome_dashboard)
               

            if not tem_arquivo_fatura:
                valor_cor = "consumidora-faltando"
            elif tem_arquivo_fatura and not tem_arquivo_dashboard:
                valor_cor = "consumidora-fatura"
            elif tem_arquivo_fatura and tem_arquivo_dashboard:
                valor_cor = "consumidora-concluida"
            
        clients_with_class.append(client + (valor_cor,))
        
    return render_template('index.html',
                           clients=clients_with_class,
                           data=data)

@app.route('/client/<string:client_id>', methods=['GET', 'POST'])
def client_detail(client_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        meses = {
            1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        # Obter a data de referência (ano e mês) da sessão
        ano = session.get('ano')
        mes = session.get('mes').lstrip('0')
        data = f"{mes}/{ano}"
        data_referencia = f"{mes}/{ano}"

        link = config['sheet']['link']
        link_dash = "http://" + link 
        mes_formatado = meses[int(mes)]

        conn = sqlite3.connect(db_clientes)
        cursor = conn.cursor()

        # Recuperar detalhes do cliente usando o identificador como string
        cursor.execute('SELECT UNIDADE_EDP, NOME, PROPRIETARIO, DESC_GERAR, PATH_FATURA, GERADORA FROM nomes WHERE NOME = ?', (client_id,))
        cliente = cursor.fetchone()

        dados_cliente = (cliente[0], cliente[1])

        if cliente[5] == "0":
            # Recuperar detalhes do cliente usando o identificador como string
            cursor.execute(f"SELECT UNIDADE_EDP, MES_PRODUCAO, CONSUMO, FATURAMENTO, GD FROM geracoes WHERE FATURAMENTO = '{data}' AND CAST(UNID_CONSUMIDORA AS UNSIGNED) = {cliente[0]}")
            geracoes = cursor.fetchall()
        else:
            # Recuperar detalhes do cliente usando o identificador como string
            cursor.execute(f"""SELECT UNIDADE_EDP, MES_PRODUCAO, LEITURA_TELEM, LEITURA_FATURA, GD 
                                FROM geracoes 
                                WHERE MES_PRODUCAO = '{data}' 
                                AND CAST(UNIDADE_EDP AS UNSIGNED) = {cliente[0]}
                                AND (UNID_CONSUMIDORA IS NULL OR UNID_CONSUMIDORA = '')
                            """)
            geracoes = cursor.fetchall()
            
        print("\n\n")
        print(f"Valor de geração = {geracoes}")
        print("\n\n")
        session['unidade_edp'] = cliente[0]
        
        # -----------------------------------------------
        
        # Buscar unidades de geração (GERADORA = 1)
        cursor.execute('SELECT DISTINCT UNIDADE_EDP, NOME FROM nomes WHERE GERADORA = 1')
        geradoras = cursor.fetchall()
        
        max_meses_regressivos = 24
        # # CALCULO DE SALDOS / CRÉDITOS
        data_saldo = f"{mes}/{ano}"
        mes_consulta = mes
        ano_consulta = ano
        
        consumos_consulta = []
        montante_consulta = []
        meses_saldo = []

        for i in range(max_meses_regressivos):            
            for geradora in geradoras:
                cursor.execute(f"select MES_PRODUCAO, RECEPTORA, MONTANTE, PERCENTUAL_ALOCADO, GERADORA from demonstrativo where (MES_PRODUCAO = '{mes_consulta}/{ano_consulta}') and (RECEPTORA = '{cliente[0]}') and (GERADORA = '{geradora[0]}')")
                valor_consulta = cursor.fetchall()
                if valor_consulta:
                    montante_consulta.append(valor_consulta[0])
            
                # Buscar os dados na tabela gerações
                cursor.execute(f"""select MES_PRODUCAO, UNID_CONSUMIDORA, UNIDADE_EDP, sum(CONSUMO) as gastos from geracoes where (UNIDADE_EDP = '{geradora[0]}') and (MES_PRODUCAO = '{mes_consulta}/{ano_consulta}') and (UNID_CONSUMIDORA = '{cliente[0]}')""")
                geracao_consulta = cursor.fetchone()
                if geracao_consulta and geracao_consulta[0] is not None and geracao_consulta[1] is not None:
                    consumos_consulta.append(geracao_consulta)
            data = f'{mes_consulta}/{ano_consulta}'
            if data not in meses_saldo:
                meses_saldo.append(data)
                
            if (mes_consulta == '1'):
                mes_consulta = '12'
                ano_consulta = str(int(ano_consulta) - 1)

            else:
                mes_consulta = str(int(mes_consulta) - 1)
        

        # Criar um dicionário para os montantes
        montantes_dict = {}
        for item in montante_consulta:
                key = (item[0], item[1], item[4])  # MES_PRODUCAO, RECEPTORA
                montantes_dict[key] = float(item[2])  # MONTANTE

        # Criar um dicionário para os consumos
        consumos_dict = {(c[0], c[1], c[2]): float(c[3]) for c in consumos_consulta}

        # Calcular as diferenças
        resultados = []
        for key in montantes_dict:
            if key in consumos_dict:
                mes_producao, receptora, geradora = key
                montante = montantes_dict[key]
                consumo = consumos_dict[key]
                valor_sub = montante - consumo
                diferenca = "{:.3f}".format(valor_sub)
                classe = 'valor-zero-diferenca' if float(valor_sub) == 0 else 'valor-negativo-diferenca' if float(valor_sub) < 0 else 'valor-positivo-diferenca'
                resultados.append((mes_producao, receptora, geradora, diferenca, classe))

            else:
                mes_producao, receptora, geradora = key
                montante = "{:.3f}".format(montantes_dict[key])
                classe = 'valor-zero-diferenca' if float(montante) == 0 else 'valor-negativo-diferenca' if float(montante) < 0 else 'valor-positivo-diferenca'
                resultados.append((mes_producao, receptora, geradora, montante, classe))
                
        # -----------------------------------------------
        
        # Buscar nome da pasta do cliente
        if cliente[5] == '1':
            path_busca = f"""{cliente[4]}{ano}/{mes_formatado}/Geradoras/"""
        else:
            path_busca = f"""{cliente[4]}{ano}/{mes_formatado}/"""

        # Procurar o nome mais aproximado na pasta
        nomes_pasta = os.listdir(path_busca)

        if cliente[2] in nomes_pasta:
            for nome in nomes_pasta:
                if nome == cliente[2]:
                    caminho_cliente = os.path.join(path_busca, nome)

        # melhor_correspondencia = encontrar_mais_proximo(cliente[2], nomes_pasta)

        path_completo = f"{caminho_cliente}/{cliente[0]}/Fatura"
        # path_completo = f"{caminho_cliente}/{cliente[0]}/Dashboard"
              
        if os.path.isdir(path_completo):
            # Verificar fatura na instalação
            nome_fatura = verificar_arquivo(path_completo)
            path_fatura = f"{path_completo}/{nome_fatura}"
            
        # Separar os valores em duas listas
        valores_geracao_propria = [row for row in geracoes if row[0] is not None and try_int(row[0]) == try_int(cliente[0])]
        valores_com_edp = [row for row in geracoes if row[0] is not None and try_int(row[0]) != try_int(cliente[0])]
        valores_sem_edp = [row for row in geracoes if row[0] is None]

        if cliente is None:
            return "Cliente não encontrado", 404

        filename = filename_dashboard(cliente[0])
              
        if request.method == 'POST':
            # Processar o formulário submetido
            atualizacoes = request.form.to_dict()
            for key, unidade_edp in atualizacoes.items():
                if key.startswith('relacionar_') and unidade_edp.strip():  # Verifica se há valor escrito
                    idx = int(key.split('_')[-1])  # Pega o índice do item relacionado
                    selecionado = valores_sem_edp[idx]

                    # Atualizar o banco de dados apenas para os valores preenchidos
                    query = f"""
                        UPDATE geracoes
                        SET UNIDADE_EDP = '{unidade_edp}'
                        WHERE MES_PRODUCAO = '{selecionado[1]}' AND CONSUMO = {selecionado[2]} AND FATURAMENTO = '{selecionado[3]}'
                    """
                    cursor.execute(query)
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('client_detail', client_id=client_id))  # Redireciona para a mesma página
    
        # Preparar dados para o template
        return render_template(
        'client_detail.html',
        client=(cliente[0], cliente[1], cliente[2], cliente[3], filename),
        valores_geracao_propria=valores_geracao_propria,
        valores_com_edp=valores_com_edp,
        valores_sem_edp=valores_sem_edp,
        geradoras=geradoras,
        path_completo=path_completo,
        dados_cliente=dados_cliente,
        link_dash=link_dash,
        path_fatura=path_fatura,
        egeradora=cliente[5],
        resultados=resultados,
        meses_saldo= meses_saldo,
        data_referencia=data_referencia,
        )
    # except Exception as e:
    #     return render_template(
    #     'client_detail.html',
    #     client=(cliente[0], cliente[1], cliente[2], cliente[3], filename),
    #     valores_geracao_propria=valores_geracao_propria,
    #     valores_com_edp=valores_com_edp,
    #     valores_sem_edp=valores_sem_edp,
    #     geradoras=geradoras,
    #     path_completo=path_completo,
    #     dados_cliente=dados_cliente,
    #     link_dash=link_dash,
    #     path_fatura=path_fatura,
    #     egeradora=cliente[5],
    #     resultados=resultados,
    #     meses_saldo= meses_saldo,
    #     data_referencia=data_referencia,
    #     )
    except Exception as e:
        print(f"Erro: {str(e)}")
        # Em caso de outros erros, redirecione para a index
        flash('Cliente sem pasta no diretorio', 'danger')
        return redirect(url_for('index'))

@app.route("/uploads/fatura/<string:filename>")
def download_fatura(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Captura o diretório completo
    path_completo = request.args.get("path")
    cliente = request.args.get("cliente")
    
    # Lógica para split caso necessário
    diretorio = os.path.dirname(path_completo)  # Diretório sem o nome do arquivo
    # nome_arquivo = os.path.basename(path_completo)  # Nome do arquivo

    # Retorna o arquivo do diretório correto
    return send_from_directory(path_completo, filename)

@app.route('/atualizar_iframe', methods=['POST'])
def atualizar_iframe():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    data = request.json
    selected_option = data.get('option')
    client_id = data.get('clientId')
    filename = data.get('filename')
    path = data.get('path')
    
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()

    # Recuperar detalhes do cliente usando o identificador como string
    cursor.execute('SELECT UNIDADE_EDP, NOME, PROPRIETARIO, DESC_GERAR, PATH_FATURA, GERADORA FROM nomes WHERE UNIDADE_EDP = ?', (client_id,))
    cliente = cursor.fetchone()
    
    cursor.close()
    conn.close()
        
    if selected_option == "Fatura ULT":
        selected_option = "Dashboard"

    path_mod = path.split("/")

    if cliente[5] =="0":
        path_busca = f"{path_mod[0]}/{path_mod[1]}/{path_mod[2]}/{path_mod[3]}/{path_mod[4]}/{path_mod[5]}/{path_mod[6]}/{path_mod[7]}/{path_mod[8]}/{selected_option}"
    else:
        path_busca = f"{path_mod[0]}/{path_mod[1]}/{path_mod[2]}/{path_mod[3]}/{path_mod[4]}/{path_mod[5]}/{path_mod[6]}/{path_mod[7]}/{path_mod[8]}/{path_mod[9]}/{selected_option}"

    if os.path.isdir(path_busca):
        # Verificar fatura na instalação
        nome_fatura = verificar_arquivo(path_busca)

    path_completo = f"{path_busca}/{nome_fatura}"

    if selected_option == 'Fatura':
        new_src = url_for('download_fatura', filename=nome_fatura, path=path_busca)
    elif selected_option == 'Demonstrativo':
        new_src = url_for('download_fatura', filename=nome_fatura, path=path_busca, cliente=client_id)
    elif selected_option == 'Fatura ULT':
        new_src = url_for('download_fatura', filename=nome_fatura, path=path_busca, cliente=client_id)
    else:
        new_src = url_for('download_fatura', filename=nome_fatura, path=path_busca)  # Padrão para Fatura
    
    return jsonify({'newSrc': new_src})

@app.route('/atualizar_status', methods=['POST'])
def atualizar_status():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        data = request.json
        client_id = data.get('clientId')

        service_acc = config['auth']['service_acc']

        if not client_id:
            raise ValueError('ClientId não fornecido')

        # Conectar ao banco de dados
        conn = sqlite3.connect(db_clientes)
        cursor = conn.cursor()

        # Recuperar detalhes do cliente
        cursor.execute('SELECT UNIDADE_EDP, PROPRIETARIO, PLANILHA, DESC_GERAR FROM nomes WHERE UNIDADE_EDP = ?', (client_id,))
        cliente = cursor.fetchone()
        
        if not cliente:
            raise ValueError(f'Cliente não encontrado para o ID: {client_id}')

        # Atualizar o status no banco de dados
        novo_status = "TRUE" if cliente[3] == "FALSE" else "FALSE"
        cursor.execute('UPDATE nomes SET DESC_GERAR = ? WHERE UNIDADE_EDP = ?', (novo_status, client_id))
        conn.commit()
        # Fechar conexão com o banco de dados
        cursor.close()
        conn.close()

        # Conectar ao Google Sheets
        try:
            gc = gspread.service_account(filename=service_acc)
            spreadsheet = gc.open_by_key(cliente[2])

            worksheet = spreadsheet.worksheet("Fatura")
            worksheet.update_acell('O28', f'{novo_status}')
        except Exception as e:
            app.logger.error(f'Erro ao atualizar Google Sheets: {str(e)}')
            # Não levantamos a exceção aqui para permitir que a atualização do banco de dados seja concluída

        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso',
            'newStatus': novo_status
        })

    except Exception as e:
        app.logger.error(f'Erro ao atualizar status: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar status: {str(e)}'
        }), 500

@app.route('/excluir_geracao', methods=['POST'])
def excluir_geracao():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    unidade_edp = request.form.get('unidade_edp')
    mes_producao = request.form.get('mes_producao')
    montante = request.form.get('montante')
    faturamento = request.form.get('faturamento')
    client_id = request.form.get('client_id')  # Ou outra lógica para obtê-lo
    unid_consumidora = request.form.get('unid_consumidora')

    if unidade_edp:
        try:
            # Conectar ao banco de dados
            conn = sqlite3.connect(db_clientes)
            cursor = conn.cursor()
            # Exemplo de query para atualizar o banco
            query = f"UPDATE geracoes SET UNIDADE_EDP = NULL WHERE  CAST(UNID_CONSUMIDORA AS UNSIGNED) = '{unid_consumidora}' AND MES_PRODUCAO = '{mes_producao}' AND CONSUMO = '{montante}' AND FATURAMENTO = '{faturamento}'"
            cursor.execute(query)
            conn.commit()
            flash('Valor atualizado com sucesso!', 'success')
            # Fechar conexão com o banco de dados
            cursor.close()
            conn.close()
        except Exception as e:
            flash(f'Erro ao atualizar valor: {e}', 'danger')
    return redirect(url_for('client_detail', client_id=client_id))

@app.route('/calculo_economia', methods=['POST'])
def calculo_economia():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    dados = request.json
    
    meses = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }

    # Obter a data de referência (ano e mês) da sessão
    ano = session.get('ano')
    mes = session.get('mes').lstrip('0')
    data = f"{mes}/{ano}"

    cred_recebido_ouc = 0
    cred_recebido_muc = 0
    cred_recebido_muc_gdii = 0
    cred_recebido_ouc_gdii = 0
    cred_recebido_ouc_ext = 0
    cred_recebido_ouc_ext_gdii = 0

    service_acc = config['auth']['service_acc']

    unid_consumidora = dados.get('unid_consumidora')
    client_id = dados.get('client_id')  # Ou outra lógica para obtê-lo
    observacao  = dados.get('observacao')
    valor_outro = dados.get('valor_outro')

    # Conectar ao banco de dados
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()

    # Recuperar detalhes do cliente
    cursor.execute('SELECT UNIDADE_EDP, PROPRIETARIO, PLANILHA, DESC_GERAR FROM nomes WHERE UNIDADE_EDP = ?', (unid_consumidora,))
    cliente = cursor.fetchone()

    # Recuperar detalhes do cliente usando o identificador como string
    cursor.execute(f"SELECT UNIDADE_EDP, MES_PRODUCAO, CONSUMO, FATURAMENTO, GD FROM geracoes WHERE FATURAMENTO = '{data}' AND CAST(UNID_CONSUMIDORA AS UNSIGNED) = {cliente[0]}")
    geracoes = cursor.fetchall()

    # Recuperar detalhes do cliente usando o identificador como string
    cursor.execute(f"SELECT MES_DE_CONSUMO, MONTANTE, BANDEIRA, QUANT_DIAS_BANDEIRA FROM consumos WHERE MES_DE_CONSUMO = '{data}' AND CAST(UNIDADE_EDP AS UNSIGNED) = {cliente[0]}")
    consumos = cursor.fetchall()

    cursor.execute(f"SELECT UNIDADE_EDP, MES_CONSUMO, DIAS_LEITURA, ILUMINACAO_PUBLICA FROM historico WHERE MES_CONSUMO = '{data}' AND CAST(UNIDADE_EDP AS UNSIGNED) = {cliente[0]}")
    quant_dias_leitura = cursor.fetchall()
    
    iluminacao_publica = quant_dias_leitura[0][3]

    for geracao in geracoes:
        if (geracao[0].lstrip('0') == cliente[0].lstrip('0') and geracao[4] == "GDII"): # Geração propria e GDII [mUC GDII]
            cred_recebido_muc_gdii += geracao[2]
        elif (geracao[0].lstrip('0') == cliente[0].lstrip('0') and geracao[4] != "GDII"): # Geração propria mas não GDII [mUC]
            cred_recebido_muc += geracao[2]
        elif (geracao[0].lstrip('0') == "EXTERNO" and geracao[4] == "GDII"): # Geração externa e GDII [Externa GDII]
            cred_recebido_ouc_ext_gdii += geracao[2]
        elif (geracao[0].lstrip('0') == "EXTERNO" and geracao[4] != "GDII"): # Geração externa mas não GDII [Externa]
            cred_recebido_ouc_ext += geracao[2]
        elif (geracao[0].lstrip('0') != cliente[0].lstrip('0') and geracao[4] == "GDII"): # Geração recebida de outra unidade GDII [oUC GDII]
            cred_recebido_ouc_gdii += geracao[2]
        elif geracao[0].lstrip('0') != cliente[0].lstrip('0') and geracao[4] != "GDII": # Geração recebida de outra unidade mas não GDII [oUC]
            cred_recebido_ouc += geracao[2]

    if len(consumos) < 2:
        if consumos[0][2] != "Verde":
                tusd = consumos[0][1]
                bandeira_verde = int(quant_dias_leitura[0][2]) - int(consumos[0][3]) #Diminuir pelo valor dos dias da outra bandeira
                
                
                bandeira = [
                {0: f'{data}', 1: f'{consumos[0][1]}', 2: f'{consumos[0][2]}', 3: f'{consumos[0][3]}'},
                {0: f'{data}', 1: f'{consumos[0][1]}', 2: 'Verde', 3: f'{bandeira_verde}'}
                ]

        else:
            tusd = consumos[0][1]   
            bandeira = consumos
                
    else:
        bandeira = []
        for consumo in consumos:
            if consumo[2] != "NULL":
                bandeira.append(consumo)
            else:
                tusd = consumo[1]

    # Conectar ao Google Sheets
    try:
        gc = gspread.service_account(filename=service_acc)
        spreadsheet = gc.open_by_key(cliente[2])

        worksheet = spreadsheet.worksheet("Fatura")

        imposto_path = os.path.join(parent_dir, 'imposto.json')
        
        with open(imposto_path, 'r') as arquivo:
            imposto = json.load(arquivo)
            mes_formatado = meses[int(mes)]
            dados_mes = None
            for item in imposto:
                if item['mes'] == mes_formatado:
                    pis = item['pis_pasep']
                    cofins = item['cofins']
                    break
                else:
                    pis = '0'
                    cofins = '0'
            
            worksheet.update_acell('M5', f"{pis}") # PIS
            worksheet.update_acell('M6', f"{cofins}") # COFINS
            
        worksheet.update_acell('P28', f'{cliente[3]}') # Bandeira 1

        # Guardar as bandeiras no sheets
        if len(bandeira) > 1:
            worksheet.update_acell('P11', f'{bandeira[0][2]}') # Bandeira 1
            worksheet.update_acell('P12', f'{str(bandeira[0][3])}') # Adicional Bandeira 1
            worksheet.update_acell('P13', f'{bandeira[1][2]}') # Bandeira 2
            worksheet.update_acell('P14', f'{str(bandeira[1][3])}') # Adicional Bandeira 2
        else:
            worksheet.update_acell('P11', f'{bandeira[0][2]}') # Bandeira 1
            worksheet.update_acell('P12', f'{bandeira[0][3]}') # Adicional Bandeira 1
            worksheet.update_acell('P13', f'-') # Bandeira 2
            worksheet.update_acell('P14', f'0') # Adicional Bandeira 2

        # Guardar credito gerado pelo proprio cliente [mUC]
        worksheet.update_acell('P15', f"{str(cred_recebido_muc).replace('.',',')}")
        # Guardar credito gerado pelo proprio cliente com GDII [mUC GDII]
        worksheet.update_acell('P22', f"{str(cred_recebido_muc_gdii).replace('.',',')}")
        # Guardar credito gerado por oUC [oUC]
        worksheet.update_acell('P16', f"{str(cred_recebido_ouc).replace('.',',')}")
        # Guardar credito gerado por oUC com GDII [oUC GDII]
        worksheet.update_acell('P21', f"{str(cred_recebido_ouc_gdii).replace('.',',')}")
        # Guardar credito gerado por Externo [Externo]
        worksheet.update_acell('P19', f"{str(cred_recebido_ouc_ext).replace('.',',')}")
        # Guardar credito gerado por Externo com GDII [Externo GDII]
        worksheet.update_acell('P20', f"{str(cred_recebido_ouc_ext_gdii).replace('.',',')}")

        # Guardar o TUSD
        worksheet.update_acell('P10', f"{str(tusd).replace('.',',')}")
        
         # Guardar a iluminacao publica
        worksheet.update_acell('P17', f"{str(iluminacao_publica)}")
        

        # Guardar os outros valores
        worksheet.update_acell('P29', f'{valor_outro}')
        worksheet.update_acell('P30', f'{unid_consumidora}')
        
        if not all([unid_consumidora, client_id, observacao]):
                return jsonify({"success": False, "message": "Dados incompletos"}), 400

        # Após todo o processamento, em vez de redirecionar:
        return jsonify({
            "success": True,
            "message": "Cálculo de economia realizado com sucesso",
            "data": {
                "unid_consumidora": unid_consumidora,
                "client_id": client_id,
            }
        }), 200
    
    except Exception as e:
        app.logger.error(f'Erro ao atualizar Google Sheets: {str(e)}')
    return redirect(url_for('client_detail', client_id=client_id))

@app.route('/gerar_fat_simulacao', methods=['POST'])
def gerar_fat_simulacao():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        # Obter a data de referência (ano e mês) da sessão
    ano = session.get('ano')
    mes = session.get('mes').lstrip('0')
    data_modificada = f"{mes}/{ano}"

    data = request.json
    observacao = data.get('observacao')
    unid_consumidora = data.get('unid_consumidora')
    client_id = data.get('client_id')

    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_clientes)
        cursor = conn.cursor()
        # Recuperar detalhes do cliente
        cursor.execute('SELECT UNIDADE_EDP, PROPRIETARIO, PLANILHA, DESC_GERAR FROM nomes WHERE UNIDADE_EDP = ?', (unid_consumidora,))
        cliente = cursor.fetchone()
    
        service_acc = config['auth']['service_acc']

        gc = gspread.service_account(filename=service_acc)
        spreadsheet = gc.open_by_key(cliente[2])

        worksheet = spreadsheet.worksheet("Fatura")

        # Buscar a TUSD
        tusd = adequacao(worksheet.acell('P10').value)
        # Buscar Montante Contratado
        montante_contratado_mod = adequacao(worksheet.acell('P18').value)
        montante_contratado = float(str(montante_contratado_mod).replace(" ", ""))
        # Buscar o valor da Fatura
        valor_fatura_edp_mod = adequacao(worksheet.acell('P23').value)
        valor_fatura_edp = float(str(valor_fatura_edp_mod).replace(" ", ""))
        # Buscar o valor Contratado
        valor_fatura_ult_mod = adequacao(worksheet.acell('P24').value)
        valor_fatura_ult = float(str(valor_fatura_ult_mod).replace(" ", ""))
        # Buscar a economia [%]
        economia_mod = adequacao(worksheet.acell('P25').value)*100
        economia = float(str(economia_mod).replace(" ", ""))
        # Buscar a economia [R$]
        economia_valor_mod = adequacao(worksheet.acell('P26').value)
        economia_valor = float(str(economia_valor_mod).replace(" ", ""))
        # Buscar o valor do kWh
        valor_kwh_mod = adequacao(worksheet.acell('P27').value)
        valor_kwh = float(str(valor_kwh_mod).replace(" ", ""))

        # Conectar ao banco de dados
        conn = sqlite3.connect(db_clientes)
        cursor = conn.cursor()
        # Exemplo de query para atualizar o banco
        query = f"""UPDATE historico SET MONTANTE = '{tusd}',
        VALOR_FATURA = '{valor_fatura_edp}',
        VALOR_CONTRATADO = '{valor_fatura_ult}',
        MONTANTE_CONT = '{montante_contratado}',
        ECONOMIA = '{economia}',
        ECONOMIA_VALOR = '{economia_valor}',
        VALOR_KWH = '{valor_kwh}',
        OBSERVACOES = '{observacao}'
        WHERE CAST(UNIDADE_EDP AS UNSIGNED) = '{unid_consumidora}' AND MES_CONSUMO = '{data_modificada}'"""
        cursor.execute(query)
        conn.commit()
        # Fechar conexão com o banco de dados
        cursor.close()
        conn.close()

        output = ""
        linha_digitavel = "1111111111111111"
        dashboard = gerar_dashboard(unid_consumidora, data_modificada, output, linha_digitavel)

        grafana_url = "http://localhost:3002"
        criar_snapshot(unid_consumidora, grafana_url, dashboard)
        print("Criei snapshot")

        # Obtém o diretório do próprio script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Caminho do arquivo dentro da mesma pasta do script
        temp_snapshot_path = os.path.join(script_dir, "temp_snapshot.txt")

        # Lê o arquivo temporário
        with open(temp_snapshot_path, 'r') as file:
            lines = file.readlines()
            snapshotKey = lines[0].split(':')[1].split('\n')[0]
        
        grafana_url = f"http://absserver:3002/dashboard/snapshot/{snapshotKey}?orgId=0&kiosk"

        # Armazena o snapshotKey em uma variável de sessão
        # session['current_snapshot'] = snapshotKey

        return jsonify({
            'success': True,
            'message': 'Fatura de simulação gerada com sucesso',
            'grafana_url': grafana_url
        })        

    except Exception as e:
        app.logger.error(f'Erro ao atualizar Google Sheets: {str(e)}')
    return redirect(url_for('client_detail', client_id=client_id))

@app.route('/gerar_fatura', methods=['POST'])
def gerar_fatura():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        # Obtém o diretório do script atual
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Caminho correto para temp.txt
        temp_file_path = os.path.join(script_dir, "temp.txt")

        # Caminho do arquivo dentro da mesma pasta do script
        temp_snapshot_path = os.path.join(script_dir, "temp_snapshot.txt")
        
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_snapshot_path):
            os.remove(temp_snapshot_path)
        
        # Obter a data de referência (ano e mês) da sessão
        ano = session.get('ano')
        mes = session.get('mes').lstrip('0')
        data_referencia = f"{mes}/{ano}"

        dados = request.json
        unid_consumidora = dados.get('unid_consumidora')
        cliente_inicial = dados.get('cliente')
        cliente = cliente_inicial.replace(" ", "_")
        client_id = dados.get('client_id')

        data = ""

        conn = sqlite3.connect(db_clientes)
        cursor = conn.cursor()
        # Recuperar detalhes do cliente
        cursor.execute('SELECT UNIDADE_EDP, VALOR_CONTRATADO FROM historico WHERE UNIDADE_EDP = ? AND MES_CONSUMO = ?', (unid_consumidora, data_referencia))
        valor_fatura = cursor.fetchone()
        cursor.close()
        conn.close()
        
        conn = sqlite3.connect(db_clientes)
        cursor = conn.cursor()
        cursor.execute('SELECT UNIDADE_EDP, PROPRIETARIO, PATH_FATURA FROM nomes WHERE UNIDADE_EDP = ?', (unid_consumidora,))
        path_dashboard = cursor.fetchone()
        cursor.close()
        conn.close()

        # Caminho absoluto para o script PHP
        if not valor_fatura:
            return jsonify({
                "success": False,
                "message": "Valor da fatura não encontrado no histórico"
            }), 404

        # Gera o código de barras
        php_script_path = os.path.abspath(os.path.join(
            current_app.root_path, 
            'auth.php'
        ))

        output_dir = f"/usr/share/grafana/public/img/barcode_{cliente}.png"

        command = [
            "php", 
            php_script_path, 
            str(unid_consumidora), 
            cliente, 
            str(valor_fatura[1]), 
            output_dir
        ]
        print("\n---------------------------------------------------\n")
        print("DADOS ENVIADOS PELO PYTHON: ")
        print("UNIDADE CONSUMIDORA: ", unid_consumidora)
        print("VALOR FATURA: ", valor_fatura[1])
        print("\n---------------------------------------------------\n")
        
        subprocess.run(command, check=True)

        # Lê o arquivo temporário
        with open(temp_file_path, 'r') as file:
            lines = file.readlines()
            codigo_barras = lines[0].strip()
            linha_digitavel = lines[1].strip()

        # Mudar permissões para um arquivo
        permissao_barcode = f"{output_dir}.png"
        # subprocess.run(['sudo', 'chmod', '755', permissao_barcode], check=True)
        
        # Chamar a função para gerar o codigo de barraswWW
        gerar_cod_barras(codigo_barras, output_dir)

        # Chama a função para gerar o dashboard
        dashboard = gerar_dashboard(unid_consumidora, data_referencia, output_dir, linha_digitavel)

        # Criar o snapshot
        grafana_url = "http://localhost:3002"
        criar_snapshot(unid_consumidora, grafana_url, dashboard)

        meses = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        mes_formatado = meses[int(mes)]

        path_busca = f"""{path_dashboard[2]}{ano}/{mes_formatado}"""

        # Procurar o nome mais aproximado na pasta
        nomes_pasta = os.listdir(path_busca)

        if path_dashboard[1] in nomes_pasta:
            for nome in nomes_pasta:
                if nome == path_dashboard[1]:
                    caminho_cliente = os.path.join(path_busca, nome)

        path_output = f"{caminho_cliente}/{unid_consumidora}/Dashboard/{unid_consumidora}-{mes}-{ano}.pdf"
        
        # Tirar print do snapshot
        gerar_snapshot_pdf(path_output)
        
        mod_metadados(path_output)
        
        # Apagar o snapshot
        apagar_snapshot(unid_consumidora)
        print("\APAGOU SNAPSHOT \n")
        
        # Remove o arquivo temporário
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            os.remove(temp_snapshot_path)

        redirect_url = url_for('client_detail', client_id=client_id)

        return jsonify({
            "success": True,
            "message": "Fatura gerada com sucesso",
            "redirect_url": redirect_url
        }), 200

    except subprocess.CalledProcessError as e:
        app.logger.error(f"Erro no script PHP: {e.stderr}")
        return jsonify({
            "success": False,
            "message": "Falha ao gerar código de barras"
        }), 500

    except sqlite3.Error as e:
        app.logger.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Erro interno ao acessar dados"
        }), 500

    except Exception as e:
        app.logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Erro inesperado ao processar a fatura"
        }), 500

@app.route('/apagar_snapshot_route', methods=['POST'])
def apagar_snapshot_route():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Não autorizado'}), 401
    
    data = request.get_json()
    

    if not data or 'client' not in data:
        return jsonify({'success': False, 'message': 'Parâmetro client não enviado'}), 400
    
    unidade_edp = data['client']  # Pegando o valor enviado
    print("UNIDADE EDP: ", unidade_edp)
    
    # unidade_edp = session.get('unidade_edp')
    if unidade_edp:
        apagar_snapshot(unidade_edp)
        # session.pop('current_snapshot', None)

        # Obtém o diretório do próprio script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Caminho do arquivo dentro da mesma pasta do script
        temp_snapshot_path = os.path.join(script_dir, "temp_snapshot.txt")

        os.remove(temp_snapshot_path)
        return jsonify({'success': True, 'message': 'Snapshot apagado com sucesso'})
    else:
        return jsonify({'success': False, 'message': 'Nenhum snapshot para apagar'})

@app.route('/atualizar_db', methods=['POST'])
def atualizar_db():
    data = request.json
    path = data.get('path')
    geradora = data.get('geradora')
    
    print("Chegou na rota atualizar DB")
    
    if path and geradora:
        try:
            resultado = busca_path(path, geradora)
            
            if geradora == "1":
                path_split= path.split("/")
                path_demonstrativo = f"""/{path_split[1]}/{path_split[2]}/{path_split[3]}/{path_split[4]}/{path_split[5]}/{path_split[6]}/{path_split[7]}/{path_split[8]}/{path_split[9]}/Demonstrativo"""
                nome_demonstrativo = verificar_arquivo(path_demonstrativo)
                path_completo = f"""{path_demonstrativo}/{nome_demonstrativo}"""
                busca_demonstrativo(path_completo)
                
            return jsonify({"message": "Sucesso", "resultado": resultado}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Por favor, forneça path e geradora."}), 400




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3004)