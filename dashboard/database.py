import sqlite3

# Conectar ao banco de dados (cria o arquivo ult.db se não existir)
conexao = sqlite3.connect('./dashboard/ult.sqlite')
cursor = conexao.cursor()

# Criar a tabela "HISTORICO"
cursor.execute('''
CREATE TABLE IF NOT EXISTS historico (
    UNIDADE_EDP TEXT,
    MES_DE_CONSUMO TEXT,
    MONTANTE REAL,
    VALOR_FATURA REAL,
    VALOR_CONTRATADO REAL,
    MONTANTE_CONT REAL,
    ECONOMIA REAL,
    VALOR_KWH REAL
);
''')

# Criar a tabela "GERACOES"
cursor.execute('''
CREATE TABLE IF NOT EXISTS geracoes (
    UNIDADE_EDP TEXT,
    MES_PRODUCAO TEXT,
    LEITURA_TELEM REAL,
    LEITURA_FATURA TEXT,
    CONSUMO REAL,
    FATURAMENTO REAL,
    UNID_CONSUMIDORA TEXT,
    ALUGUEL_PAGO BLOB
);
''')

# Criar a tabela "CONSUMOS"
cursor.execute('''
CREATE TABLE IF NOT EXISTS consumos (
    UNIDADE_EDP TEXT,
    MES_DE_CONSUMO TEXT,
    MONTANTE REAL,
    VALOR_FATURA REAL,
    BANDEIRA TEXT,
    QUANT_DIAS_BANDEIRA
);
''')


# Criar a tabela "NOMES" com a primary key em UNIDADE_EDP
cursor.execute('''
CREATE TABLE IF NOT EXISTS nomes (
    UNIDADE_EDP TEXT PRIMARY KEY,
    GERADORA TEXT,
    PROPRIETARIO TEXT,
    NOME TEXT,
    PLANILHA TEXT,
    URL_DASHBOARD TEXT,
    CRITERIO_PROC TEXT,
    DESC_GERAR BLOB,
    RECEBE_ENERGIA_DE TEXT,
    VALOR_ALUGUEL REAL    
);
''')

# Confirmar as alterações e fechar a conexão
conexao.commit()
cursor.close()
conexao.close()

print("Banco de dados e tabelas criados com sucesso!")
