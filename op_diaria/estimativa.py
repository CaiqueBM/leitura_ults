import sqlite3
from datetime import datetime, timedelta
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)


def estimar():
    # Conectar ao banco de dados
    path_db = os.path.join(parent_dir, 'dados.sqlite')
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

    if data_atual.month != data_anterior.month:
        # Loop para buscar os dados por ULT
        for ult in range(1, 5):
            # Query para obter os dados para a ULT atual
            query = f"SELECT GERACAO FROM dados_diarios WHERE DATA BETWEEN '{data_anterior.year:04d}-{data_anterior.month:02d}-01' AND '{data_anterior.year:04d}-{data_anterior.month:02d}-{dia_data_anterior:02d}' AND ULT = 'ULT {ult}'"
            cursor.execute(query)
            geracoes = cursor.fetchall()
            # Armazenar os dados em uma lista para a ULT atual
            zeros = sum(1 for geracao in geracoes if geracao[0] == 0)
        
            # Armazenar a quantidade de zeros para a ULT atual
            quantidade_zeros_por_ult[f'ULT {ult}'] = zeros

            #dados_por_ult[f'ULT {ult}'] = [geracao[0] for geracao in geracoes]
            dados_por_ult[f'ULT {ult}'] = [geracao[0] for geracao in geracoes]
        # Fechar a conexão com o banco de dados
        cursor.close()
        conexao.close()
    else:
        # Loop para buscar os dados por ULT
        for ult in range(1, 5):
            # Query para obter os dados para a ULT atual
            query = f"SELECT GERACAO FROM dados_diarios WHERE DATA BETWEEN '{data_atual.year:04d}-{data_atual.month:02d}-01' AND '{data_atual.year:04d}-{data_atual.month:02d}-{dia_data_anterior:02d}' AND ULT = 'ULT {ult}'"
            cursor.execute(query)
            geracoes = cursor.fetchall()
            # Armazenar os dados em uma lista para a ULT atual
            zeros = sum(1 for geracao in geracoes if geracao[0] == 0)
        
            # Armazenar a quantidade de zeros para a ULT atual
            quantidade_zeros_por_ult[f'ULT {ult}'] = zeros

            #dados_por_ult[f'ULT {ult}'] = [geracao[0] for geracao in geracoes]
            dados_por_ult[f'ULT {ult}'] = [geracao[0] for geracao in geracoes]
        # Fechar a conexão com o banco de dados
        cursor.close()
        conexao.close()

    # Dicionário para armazenar as médias de geração por ULT
    medias_por_ult = {}

    # Loop para calcular a média de geração para cada ULT
    for ult, geracoes in dados_por_ult.items():
        print("SOMA GERAÇOES: ", sum(geracoes))
        print("QUANTIDADE DIAS GERADOS: ", len(geracoes))
        print("QUANTIDADE DE ZEROS: ", quantidade_zeros_por_ult[ult])
        media = sum(geracoes) / (len(geracoes) - quantidade_zeros_por_ult[ult])
        medias_por_ult[ult] = media

    # Dicionário para armazenar as somas de geração por ULT"quantidade": 0,
    somas_por_ult = {}

    # Loop para calcular a soma de geração para cada ULT do primeiro dia até o dia atual
    for ult, geracoes in dados_por_ult.items():
        soma = sum(geracoes)
        somas_por_ult[ult] = soma

    # Dicionário para armazenar as projeções de geração por ULT
    projecoes_por_ult = {}

    if data_atual.day == 1:
        # Loop para projetar a geração para o restante do mês
        for ult, media in medias_por_ult.items():
            dias_restantes = dia_data_anterior - dia_data_anterior
            projecao = media * dias_restantes
            projecao = projecao + somas_por_ult[ult]
            projecoes_por_ult[ult] = projecao
    else:
        # Loop para projetar a geração para o restante do mês
        for ult, media in medias_por_ult.items():
            dias_restantes = ultimo_dia_mes - dia_data_anterior
            projecao = media * dias_restantes
            projecao = projecao + somas_por_ult[ult]
            projecoes_por_ult[ult] = projecao

    somas_ults = {ult: "{:.2f}".format(valor) for ult, valor in somas_por_ult.items()}
    projecoes_ults = {ult: "{:.2f}".format(valor) for ult, valor in projecoes_por_ult.items()}

    return somas_ults, projecoes_ults