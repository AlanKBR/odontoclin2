from flask import Blueprint, jsonify, render_template

from ..documentos.models import Documento
from ..pacientes.models import Paciente
from ..receitas.models import ModeloReceita

reports_bp = Blueprint(
    "reports",
    __name__,
    template_folder=".",
)


@reports_bp.route("/")
def index():  # placeholder
    return render_template("reports/index.html")


@reports_bp.route("/api/resumo")
def api_resumo():  # pequeno agregado
    return jsonify(
        {
            "pacientes": Paciente.query.count(),
            "modelos_receita": ModeloReceita.query.count(),
            "documentos": Documento.query.count(),
        }
    )
