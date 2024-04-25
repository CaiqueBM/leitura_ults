import sqlite3
from datetime import datetime, timedelta


def estimar():
    # Conectar ao banco de dados
    conexao = sqlite3.connect('/home/abs/Aplicativos/leitura_ults/dados.db')
    cursor = conexao.cursor()

    # Obter a data atual
    data_atual = datetime.now()
    data_anterior = (datetime.now() - timedelta(days=1)).day

    # Obter o último dia do mês atual
    ultimo_dia_mes = (data_atual.replace(day=1, month=data_atual.month % 12 + 1) - timedelta(days=1)).day

    # Dicionário para armazenar os dados por ULT
    dados_por_ult = {}

    # Loop para buscar os dados por ULT
    for ult in range(1, 5):
        # Query para obter os dados para a ULT atual
        query = f"SELECT GERACAO FROM dados_diarios WHERE DATA BETWEEN '{data_atual.year:04d}-{data_atual.month:02d}-01' AND '{data_atual.year:04d}-{data_atual.month:02d}-{data_anterior:02d}' AND ULT = 'ULT {ult}'"
        cursor.execute(query)
        geracoes = cursor.fetchall()
        # Armazenar os dados em uma lista para a ULT atual
        dados_por_ult[f'ULT {ult}'] = [geracao[0] for geracao in geracoes]

    # Fechar a conexão com o banco de dados
    conexao.close()

    # Salvar os dados por ULT em variáveis separadas
    """for ult, geracoes in dados_por_ult.items():
        globals()[f'dados_{ult}'] = geracoes"""

    # Dicionário para armazenar as médias de geração por ULT
    medias_por_ult = {}

    # Loop para calcular a média de geração para cada ULT
    for ult, geracoes in dados_por_ult.items():
        media = sum(geracoes) / len(geracoes)
        medias_por_ult[ult] = media

    # Dicionário para armazenar as somas de geração por ULT
    somas_por_ult = {}

    # Loop para calcular a soma de geração para cada ULT do primeiro dia até o dia atual
    for ult, geracoes in dados_por_ult.items():
        soma = sum(geracoes[:data_atual.day])
        somas_por_ult[ult] = soma

    # Dicionário para armazenar as projeções de geração por ULT
    projecoes_por_ult = {}

    # Loop para projetar a geração para o restante do mês
    for ult, media in medias_por_ult.items():
        dias_restantes = ultimo_dia_mes - data_atual.day
        projecao = media * dias_restantes
        projecao = projecao + somas_por_ult[ult]
        projecoes_por_ult[ult] = projecao

    somas_ults = {ult: "{:.2f}".format(valor) for ult, valor in somas_por_ult.items()}
    projecoes_ults = {ult: "{:.2f}".format(valor) for ult, valor in projecoes_por_ult.items()}

    return somas_ults, projecoes_ults