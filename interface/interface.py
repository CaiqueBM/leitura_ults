from flask import Flask, render_template, jsonify, request, make_response
import sqlite3
from flask_weasyprint import HTML, render_pdf


app = Flask(__name__)

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
    conn = sqlite3.connect('dados.db')
    c = conn.cursor()
    c.execute("SELECT DATA, GERACAO, ULT FROM dados_diarios WHERE ULT = ? AND DATA BETWEEN ? AND ?", (ult_type, start_date, end_date))
    data = c.fetchall()
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
    conn = sqlite3.connect('dados.db')
    cursor = conn.cursor()

    # Executar consulta SQL para obter os dados
    cursor.execute("SELECT DATA, GERACAO FROM dados_diarios WHERE ULT = ? AND DATA BETWEEN ? AND ?", (ult_type, start_date, end_date))
    data = cursor.fetchall()

    # Fechar conexão com o banco de dados
    conn.close()

    # Renderizar a página HTML com Jinja2 e passar os dados para a tabela
    rendered = render_template('ult_pdf.html', data=data)

    # Gerar PDF a partir do HTML
    pdf = render_pdf(HTML(string=rendered))

    # Enviar PDF como resposta
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=ult_data.pdf'

    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
