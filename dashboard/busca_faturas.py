import os
from fuzzywuzzy import process
import sqlite3
from datetime import datetime
from dados_fatura import busca_path

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
def verificar_fatura(caminho_instalacao):
    fatura_encontrada = False
    arquivos = os.listdir(caminho_instalacao)
    if len(arquivos) == 1:  # Só há um arquivo na pasta
        return arquivos[0]  # Retorna o nome do arquivo
    return None  # Não encontrou ou há mais de um arquivo

# Processo principal
def processar_faturas():
    # Dicionário para traduzir número do mês para nome em português
    meses_em_portugues = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    # Ano e mês corrente
    hoje = datetime.now()
    mes_anterior_corrente = 8
    ano_corrente = 2024
    # mes_anterior_corrente = hoje.month - 1 if hoje.month > 1 else 12
    # ano_corrente = hoje.year if mes_anterior_corrente >= 1 and mes_anterior_corrente < 12 else hoje.year - 1
    
    # mes_anterior_corrente = 9
    mes_anterior = meses_em_portugues[mes_anterior_corrente]

    conexao = sqlite3.connect("./dashboard/ult.sqlite")  # Ajuste o nome do banco de dados
    cursor = conexao.cursor()

    cursor.execute("SELECT PROPRIETARIO, UNIDADE_EDP, PATH_FATURA, GERADORA FROM nomes GROUP BY PROPRIETARIO")
    clientes = cursor.fetchall()

    for nome_cliente, unidade_edp, path_fatura, geradora in clientes:
        if geradora == '1':
            path_busca = f"""{path_fatura}{ano_corrente}/{mes_anterior}/00 - Geradoras/"""
        else:
            path_busca = f"""{path_fatura}{ano_corrente}/{mes_anterior}"""

        # Procurar o nome mais aproximado na pasta
        nomes_pasta = os.listdir(path_busca)
        melhor_correspondencia = encontrar_mais_proximo(nome_cliente, nomes_pasta)

        if melhor_correspondencia:
            caminho_cliente = os.path.join(path_busca, melhor_correspondencia)
            
            if os.path.isdir(caminho_cliente):
                # Iterar sobre as pastas das instalações
                pastas_instalacoes = [p for p in os.listdir(caminho_cliente) if os.path.isdir(os.path.join(caminho_cliente, p))]
                for pasta_instalacao in pastas_instalacoes:

                    caminho_instalacao = os.path.join(caminho_cliente, pasta_instalacao, "Fatura")

                    # Verificar fatura na instalação
                    nome_fatura = verificar_fatura(caminho_instalacao)
                    tem_fatura_valor = 1 if nome_fatura else 0

                    # Rodar função secundária se houver fatura
                    if nome_fatura:
                        caminho_fatura = os.path.join(caminho_instalacao, nome_fatura)
                        busca_path(caminho_fatura, tem_fatura_valor, geradora)
        else:
            print(f"Nenhuma correspondência encontrada para: {nome_cliente}")

# Exemplo de uso
if __name__ == "__main__":
    conexao = sqlite3.connect("./dashboard/ult.sqlite")  # Ajuste o nome do banco de dados

    processar_faturas()

    conexao.close()
