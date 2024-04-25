import sqlite3

caminhoDB = f"/home/abs/Aplicativos/leitura_ults/dados.db"

# Conexão com o banco de dados
conn = sqlite3.connect(caminhoDB)
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
