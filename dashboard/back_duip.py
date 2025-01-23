import sqlite3

# Tenta conectar ao banco corrompido
try:
    conn = sqlite3.connect("./dashboard/ult.sqlite")
    cursor = conn.cursor()

    # Exporta os dados
    with open("dump.sql", "w") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")

    print("Dump gerado com sucesso!")
except sqlite3.DatabaseError as e:
    print(f"Erro: {e}")
finally:
    conn.close()