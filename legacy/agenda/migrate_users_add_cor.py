import os
import sqlite3

USERS_DB = os.path.join(os.path.dirname(__file__), os.pardir, "instance", "users.db")
USERS_DB = os.path.abspath(USERS_DB)

if os.path.exists(USERS_DB):
    print(f"Migrando banco de usuários: {USERS_DB}")
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE users ADD COLUMN cor VARCHAR(20) NULL;")
        print(" - Coluna 'cor' adicionada na tabela users.")
    except Exception as e:
        print(" - Erro ou coluna já existe:", e)
    conn.commit()
    conn.close()
else:
    print("users.db não encontrado; nenhuma alteração realizada.")
