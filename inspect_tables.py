from sqlalchemy import create_engine, inspect

from app import create_app, db
from config import Config

app = create_app()
with app.app_context():
    from app.pacientes.models import Paciente  # ensure import  # noqa: F401

    eng_main = db.engine
    eng_pac = create_engine(Config.SQLALCHEMY_BINDS["pacientes"])
    print("Main tables BEFORE:", inspect(eng_main).get_table_names())
    print("Pacientes tables BEFORE:", inspect(eng_pac).get_table_names())
    db.create_all()
    print("Main tables AFTER:", inspect(eng_main).get_table_names())
    print("Pacientes tables AFTER:", inspect(eng_pac).get_table_names())
