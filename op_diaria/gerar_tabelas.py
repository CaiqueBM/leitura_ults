import sqlite3
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
caminhoDB = os.path.join(parent_dir, 'dados.sqlite')
# caminhoDB = f"/media/hdfs/Softwares/leitura_ults/dados.sqlite"

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
c.close()
# Fechar a conexão
conn.close()
