import os
import sqlite3

DB_PATHS = [
    os.path.join(os.path.dirname(__file__), os.pardir, "instance", "calendario.db"),
    os.path.join(os.path.dirname(__file__), "calendario.db"),
    os.path.join(os.path.dirname(__file__), "instance", "calendario.db"),
]

for path in DB_PATHS:
    if not os.path.exists(path):
        continue
    print(f"Migrando banco: {path}")
    conn = sqlite3.connect(path)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE calendar_event ADD COLUMN notes VARCHAR(500);")
        print(" - Coluna 'notes' adicionada com sucesso.")
    except Exception as e:
        print(" - Erro ou coluna já existe:", e)
    conn.commit()
    conn.close()
