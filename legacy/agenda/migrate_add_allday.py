import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), os.pardir, "instance", "calendario.db")
db_path = os.path.abspath(db_path)
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path)
c = conn.cursor()
try:
    c.execute("ALTER TABLE calendar_event ADD COLUMN " "all_day BOOLEAN NOT NULL DEFAULT 0;")
    print("Coluna all_day adicionada com sucesso.")
except Exception as e:
    print("Erro ou coluna já existe:", e)
conn.commit()
conn.close()
