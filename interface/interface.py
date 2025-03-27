from flask import Flask, render_template, jsonify, request, make_response
import sqlite3
from flask_weasyprint import HTML, render_pdf
from datetime import datetime
import os

app = Flask(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)


# Rota para a página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Rota para obter os dados do banco de dados e enviá-los como JSON
@app.route('/data')
def get_data():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    ult_type = request.args.get('ult_type')  # Novo parâmetro para o tipo de ULT selecionado

    # Conectar ao banco de dados
    caminhoDB = os.path.join(parent_dir, 'dados.sqlite')
    conn = sqlite3.connect(caminhoDB)
    c = conn.cursor()
    c.execute("SELECT DATA, GERACAO, ULT FROM dados_diarios WHERE ULT = ? AND DATA BETWEEN ? AND ?", (ult_type, start_date, end_date))
    data = c.fetchall()

    quant_zeros = sum(1 for row in data if row[1] == 0)
    conn.close()

    # Formatar os dados para o formato adequado (exemplo)
    formatted_data = [{'data': row[0], 'geracao': row[1], 'ult': row[2]} for row in data]

    return jsonify(formatted_data)

@app.route('/ult_pdf', methods=['GET'])
def ult_pdf():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    ult_type = request.args.get('ult_type')

    # Conectar-se ao banco de dados
    caminhoDB = os.path.join(parent_dir, 'dados.sqlite')
    conn = sqlite3.connect(caminhoDB)
    cursor = conn.cursor()

    # Executar consulta SQL para obter os dados
    cursor.execute("SELECT DATA, GERACAO FROM dados_diarios WHERE ULT = ? AND DATA BETWEEN ? AND ?", (ult_type, start_date, end_date))
    data = cursor.fetchall()

    # Contar quantas gerações são iguais a zero
    quant_zeros = sum(1 for row in data if row[1] == 0)

    # Calcular total de geração e média de geração
    total_geracao = sum(row[1] for row in data)
    media_geracao = total_geracao / (len(data) - quant_zeros) if data else 0

    start_date_formatted = datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y')
    end_date_formatted = datetime.strptime(end_date, '%Y-%m-%d').strftime('%d/%m/%Y')

    # Modifique o loop de formatação dos dados
    formatted_data = []

    for row in data:
        formatted_date = datetime.strptime(row[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        geracao = str(row[1]).replace('.', ',')  # Substitui os pontos por vírgulas
        formatted_data.append({'data': formatted_date, 'geracao': geracao})


    # Fechar conexão com o banco de dados
    conn.close()

    # Renderizar a página HTML com Jinja2 e passar os dados para a tabela
    rendered = render_template('ult_pdf.html', data=formatted_data, total_geracao=total_geracao, media_geracao=media_geracao, start_date=start_date_formatted, end_date=end_date_formatted, ult_type=ult_type)

    # Gerar PDF a partir do HTML
    pdf = render_pdf(HTML(string=rendered))

    # Enviar PDF como resposta
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=ult_data.pdf'

    return response

if __name__ == '__main__':
    port = 5004
    app.run(debug=True, host='0.0.0.0', port=port)
