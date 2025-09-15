from typing import Any

from flask_login import LoginManager
from flask_mobility import Mobility
from flask_sqlalchemy import SQLAlchemy

# Definição das extensões
db = SQLAlchemy()
login_manager = LoginManager()
mobility = Mobility()

# Estas variáveis serão atualizadas com as sessões específicas após inicialização.
# Anotadas como Any para evitar falsos positivos do analisador estático antes da inicialização do app.
users_db: Any = None
pacientes_db: Any = None
tratamentos_db: Any = None
receitas_db: Any = None
