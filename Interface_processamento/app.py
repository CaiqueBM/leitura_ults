from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash, jsonify
import sqlite3
from datetime import datetime, timedelta
import configparser
import os
from fuzzywuzzy import process
import gspread
import requests
import pandas as pd
import math

config = configparser.ConfigParser()
config.read(r"./config.ini")

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
    fatura_encontrada = False
    arquivos = os.listdir(caminho_instalacao)
    if len(arquivos) == 1:  # Só há um arquivo na pasta
        return arquivos[0]  # Retorna o nome do arquivo
    return None  # Não encontrou ou há mais de um arquivo

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

def gerar_dashboard(unidade_edp, data_referencia):
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
                "folderId": 4
            }
            update_dashboard_url = f"{grafana_url}/api/dashboards/db"

            data_mod = sanitize_json(data)

            response = requests.post(update_dashboard_url, headers=headers, json=data_mod)

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

# def update_status(db_clientes):
#     hoje = datetime.now().day
#     conn = sqlite3.connect(db_clientes)
#     cursor = conn.cursor()

#     # Atualizar status com base na data
#     if hoje < 2:
#         cursor.execute('UPDATE dados SET status_analise = "Coletando dados" WHERE status_analise != "Enviado" AND status_analise != "Revisar"')
#     else:
#         cursor.execute('UPDATE dados SET status_analise = "Em análise" WHERE status_analise != "Enviado" AND status_analise != "Revisar"')

#     conn.commit()
#     conn.close()

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

# Rota das unidades (Nao vai ser o '/')
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # update_status(db_clientes)  # Atualizar os status antes de carregar a página inicial
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()
    # cursor.execute('SELECT NOME FROM nomes WHERE GERADORA = 0')
    cursor.execute('SELECT NOME FROM nomes ORDER BY NOME ASC')
    clients = cursor.fetchall()
    conn.close()
    return render_template('index.html', clients=clients)

@app.route('/client/<string:client_id>', methods=['GET', 'POST'])
def client_detail(client_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))  

    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    # Obter a data de referência (ano e mês) da sessão
    ano = session.get('ano')
    mes = session.get('mes')
    data = f"{mes}/{ano}"

    mes_formatado = meses[int(mes)]

    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()

    # Recuperar detalhes do cliente usando o identificador como string
    cursor.execute('SELECT UNIDADE_EDP, NOME, PROPRIETARIO, DESC_GERAR, PATH_FATURA, GERADORA FROM nomes WHERE NOME = ?', (client_id,))
    cliente = cursor.fetchone()

    dados_cliente = (cliente[0], cliente[1])

    # Recuperar detalhes do cliente usando o identificador como string
    cursor.execute(f"SELECT UNIDADE_EDP, MES_PRODUCAO, CONSUMO, FATURAMENTO FROM geracoes WHERE FATURAMENTO = '{data}' AND CAST(UNID_CONSUMIDORA AS UNSIGNED) = {cliente[0]}")
    geracoes = cursor.fetchall()

    # Buscar unidades de geração (GERADORA = 1)
    cursor.execute('SELECT DISTINCT UNIDADE_EDP, NOME FROM nomes WHERE GERADORA = 1')
    geradoras = cursor.fetchall()

    # Buscar nome da pasta do cliente
    if cliente[5] == '1':
        path_busca = f"""{cliente[4]}{ano}/{mes_formatado}/00 - Geradoras/"""
    else:
        path_busca = f"""{cliente[4]}{ano}/{mes_formatado}/"""

    # Procurar o nome mais aproximado na pasta
    nomes_pasta = os.listdir(path_busca)
    melhor_correspondencia = encontrar_mais_proximo(cliente[2], nomes_pasta)

    path = f"{path_busca}{melhor_correspondencia}/{cliente[0]}/Fatura"

    if os.path.isdir(path):
        # Verificar fatura na instalação
        nome_fatura = verificar_arquivo(path)

    path_completo = f"{cliente[4]}{ano}/{mes_formatado}/{melhor_correspondencia}/{cliente[0]}/Fatura/{nome_fatura}"

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
)

    # Status para indicar se ainda esta a fazer ou finalizado
    # if request.method == 'POST':
    #     acao = request.form.get('action')
    #     if acao == 'confirmar':
    #         cursor.execute('UPDATE dados SET status_analise = "Enviado" WHERE SiglaCCEE = ?', (client_id,)) #status_analise = 1 - Preparando Dados, 2 - Em analise, 3 - Enviado, 4 - Revisar
    #     elif acao == 'revisar':
    #         cursor.execute('UPDATE dados SET status_analise = "Revisar" WHERE SiglaCCEE = ?', (client_id,))
    #     conn.commit()
    #     conn.close()
    #     return redirect(url_for('index'))

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

    path_mod = path.split("/")

    path_busca = f"{path_mod[0]}/{path_mod[1]}/{path_mod[2]}/{path_mod[3]}/{path_mod[4]}/{path_mod[5]}/{path_mod[6]}/{path_mod[7]}/{path_mod[8]}/{selected_option}"

    if os.path.isdir(path_busca):
        # Verificar fatura na instalação
        nome_fatura = verificar_arquivo(path_busca)

    path_completo = f"{path_busca}/{nome_fatura}"

    if selected_option == 'Fatura':
        new_src = url_for('download_fatura', filename=nome_fatura, path=path_busca)
    elif selected_option == 'Demonstrativo':
        new_src = url_for('download_fatura', filename=nome_fatura, path=path_busca, cliente=client_id)
    else:
        new_src = url_for('download_fatura', filename=nome_fatura, path=path_busca)  # Padrão para Fatura
    
    return jsonify({'newSrc': new_src})



# if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3004)

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

            worksheet = spreadsheet.worksheet("V1")
            worksheet.update_acell('X21', f'{novo_status}')
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
    
    # Obter a data de referência (ano e mês) da sessão
    ano = session.get('ano')
    mes = session.get('mes')
    data = f"{mes}/{ano}"

    cred_recebido_ouc = 0
    cred_recebido_muc = 0
    bandeira_1 = ""
    adicional_bandeira_1 = ""
    bandeira_2 = ""
    adicional_bandeira_2 = ""
    
    service_acc = config['auth']['service_acc']

    unid_consumidora = request.form.get('unid_consumidora')
    client_id = request.form.get('client_id')  # Ou outra lógica para obtê-lo

    # Conectar ao banco de dados
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()
    # Recuperar detalhes do cliente
    cursor.execute('SELECT UNIDADE_EDP, PROPRIETARIO, PLANILHA, DESC_GERAR FROM nomes WHERE UNIDADE_EDP = ?', (unid_consumidora,))
    cliente = cursor.fetchone()

    # Recuperar detalhes do cliente usando o identificador como string
    cursor.execute(f"SELECT UNIDADE_EDP, MES_PRODUCAO, CONSUMO, FATURAMENTO FROM geracoes WHERE FATURAMENTO = '{data}' AND CAST(UNID_CONSUMIDORA AS UNSIGNED) = {cliente[0]}")
    geracoes = cursor.fetchall()

    # Recuperar detalhes do cliente usando o identificador como string
    cursor.execute(f"SELECT MES_DE_CONSUMO, MONTANTE, BANDEIRA, QUANT_DIAS_BANDEIRA FROM consumos WHERE MES_DE_CONSUMO = '{data}' AND CAST(UNIDADE_EDP AS UNSIGNED) = {cliente[0]}")
    consumos = cursor.fetchall()

    for geracao in geracoes:
        if try_int(geracao[0]) == try_int(cliente[0]):
            print(geracao[0])
            cred_recebido_muc = try_int(geracao[2])

        if geracao[0] == "None":
            print("") # ERRO
        elif geracao[0] != "EXTERNO":
            print(geracao[2])
            cred_recebido_ouc = try_int(cred_recebido_ouc) + try_int(geracao[2])
            print(cred_recebido_ouc)

    for consumo in consumos:
        if consumo[2] == 'NULL':
            montante = int(consumo[1])
        else:
            if adicional_bandeira_1 == "":
                bandeira_1 = consumo[2]
                adicional_bandeira_1 = consumo[3]
            else:
                if consumo[2] != "":
                    bandeira_2 = consumo[2]
                    adicional_bandeira_2 = consumo[3]
                else:
                    bandeira_2 = ""
                    adicional_bandeira_2 = 0

    # Conectar ao Google Sheets
    try:
        gc = gspread.service_account(filename=service_acc)
        spreadsheet = gc.open_by_key(cliente[2])

        worksheet = spreadsheet.worksheet("V1")
        worksheet.update_acell('Z31', f'{montante}') # TUSD
        worksheet.update_acell('AA32', f'{bandeira_1}') # Bandeira 1
        worksheet.update_acell('AA33', f'{bandeira_2}') # Bandeira 2
        worksheet.update_acell('Z32', f'{adicional_bandeira_1}') # Adicional Bandeira 1
        worksheet.update_acell('Z33', f'{adicional_bandeira_2}') # Adicional Bandeira 2
        worksheet.update_acell('Z34', f'{cred_recebido_muc}') # Credito Recebido mUC
        worksheet.update_acell('Z35', f'{cred_recebido_ouc}') # Credito Recebido oUC

        montante = adequacao(worksheet.acell('Z36').value)
        valor_fatura = adequacao(worksheet.acell('Z37').value)
        valor_contratado = adequacao(worksheet.acell('Z38').value)
        montante_contratado = adequacao(worksheet.acell('Z39').value)
        economia = adequacao(worksheet.acell('Z40').value)*100
        economia_valor = adequacao(worksheet.acell('Z41').value)
        valor_kwh = adequacao(worksheet.acell('Z42').value)

        # Conectar ao banco de dados
        conn = sqlite3.connect(db_clientes)
        cursor = conn.cursor()
        # Exemplo de query para atualizar o banco
        query = f"""UPDATE historico SET MONTANTE = {montante},
        VALOR_FATURA = '{valor_fatura}',
        VALOR_CONTRATADO = '{valor_contratado}',
        MONTANTE_CONT = '{montante_contratado}',
        ECONOMIA = '{economia}',
        ECONOMIA_VALOR = '{economia_valor}',
        VALOR_KWH = '{valor_kwh}'
        WHERE CAST(UNIDADE_EDP AS UNSIGNED) = '{unid_consumidora}' AND MES_DE_CONSUMO = '{data}'"""
        cursor.execute(query)
        conn.commit()
        # Fechar conexão com o banco de dados
        cursor.close()
        conn.close()


        # Chamar função pra gerar o dashboard
        # from dashboard import gerar_dashboard
        # gerar_dashboard(unid_consumidora, data)

        gerar_dashboard(unid_consumidora, data)

        # Chamar função para gerar a fatura


        # Chamar função para juntar os PDF





    except Exception as e:
        app.logger.error(f'Erro ao atualizar Google Sheets: {str(e)}')
    return redirect(url_for('client_detail', client_id=client_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3004)
