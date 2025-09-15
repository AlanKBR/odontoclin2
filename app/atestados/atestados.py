from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db
from ..receitas.models import Atestado  # reuse bind pacientes

atestados_bp = Blueprint(
    "atestados",
    __name__,
    template_folder=".",
)


@atestados_bp.route("/")
def lista():
    itens = Atestado.query.order_by(Atestado.data_emissao.desc()).limit(50).all()
    return render_template("atestados/gerar.html", lista=itens, contexto={})


@atestados_bp.route("/gerar", methods=["GET", "POST"])
def gerar_atestado():
    contexto = {}
    if request.method == "POST":
        paciente = request.form.get("paciente", "").strip()
        dias = request.form.get("dias", "1").strip()
        try:
            dias_int = int(dias)
        except ValueError:
            dias_int = 1
        if not paciente:
            flash("Paciente obrigatório", "danger")
        else:
            contexto = {
                "paciente": paciente,
                "dias": dias_int,
                "data": date.today().strftime("%d/%m/%Y"),
            }
            registro = Atestado()
            registro.paciente = paciente  # type: ignore[assignment]
            registro.dias = dias_int  # type: ignore[assignment]
            db.session.add(registro)
            db.session.commit()
            flash("Atestado salvo", "success")
            return redirect(url_for("atestados.lista"))
    return render_template("atestados/gerar.html", contexto=contexto)
