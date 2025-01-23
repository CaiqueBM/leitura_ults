import sqlite3
import csv

# Conectar ao banco de dados
conexao = sqlite3.connect('./dashboard/ult.sqlite')
cursor = conexao.cursor()

# Caminho para o arquivo CSV
caminho_csv = r'/media/hdfs/Softwares/leitura_ults/dashboard/nomes.csv'  # Substitua pelo caminho correto do seu arquivo CSV

# Inserir dados na tabela NOMES
with open(caminho_csv, 'r', encoding='utf-8') as arquivo_csv:
    leitor = csv.reader(arquivo_csv, delimiter=';')  # Usar ';' como delimitador
    next(leitor)  # Pular o cabeçalho
    for linha in leitor:
        cursor.execute('''
        INSERT INTO nomes (UNIDADE_EDP, GERADORA, PROPRIETARIO, NOME, PLANILHA, CRITERIO_PROC, RECEBE_ENERGIA_DE)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', linha)

# Confirmar as alterações e fechar a conexão
conexao.commit()
cursor.close()
conexao.close()

print("Dados inseridos na tabela NOMES com sucesso!")
