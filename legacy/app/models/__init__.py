# filepath: a:\programa\prototipo\app\models\__init__.py
# This file makes Python treat the directory as a package.

# Importa todos os modelos para garantir que eles sejam carregados
# Essas importações são necessárias para que o SQLAlchemy registre os modelos
from app.models import atestado, clinica, documento, paciente, receita, tratamento, user  # noqa

# Importa as classes específicas para disponibilizá-las no __all__
from app.models.atestado import Atestado
from app.models.clinica import Clinica
from app.models.documento import Documento
from app.models.paciente import (
    Anamnese,
    Ficha,
    Financeiro,
    Historico,
    Paciente,
    PlanoTratamento,
    Procedimento,
)
from app.models.receita import Medicamento, ModeloReceita
from app.models.tratamento import CategoriaTratamento, Tratamento
from app.models.user import User

# Exportar classes principais para facilitar a importação externa
__all__ = [
    "Atestado",
    "Clinica",
    "Documento",
    "Paciente",
    "PlanoTratamento",
    "Procedimento",
    "Anamnese",
    "Ficha",
    "Financeiro",
    "Historico",
    "ModeloReceita",
    "Medicamento",
    "Tratamento",
    "CategoriaTratamento",
    "User",
]
