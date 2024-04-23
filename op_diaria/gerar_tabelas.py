import sqlite3

# Conexão com o banco de dados
conn = sqlite3.connect("dados.db")
c = conn.cursor()

# Cria as tabelas se não existirem
c.execute(
    """
    CREATE TABLE IF NOT EXISTS dados_diarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ULT TEXT,
        DATA DATETIME,
        GERACAO INTEGER
    )
"""
)

conn.commit()

# Fechar a conexão
conn.close()