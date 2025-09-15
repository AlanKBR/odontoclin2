from sqlalchemy import create_engine, text

from config import Config

eng = create_engine(Config.SQLALCHEMY_BINDS["pacientes"])
with eng.connect() as conn:
    rows = conn.execute(text("PRAGMA table_info(pacientes)")).fetchall()
    print("Colunas pacientes:")
    for r in rows:
        print(r)
