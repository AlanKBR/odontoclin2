from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .. import db
from ..auth.models import User  # type: ignore
from ..core.models import Clinica
from ..pacientes.models import Paciente  # type: ignore
from ..utils_db import get_or_404
from .models import Medicamento, ModeloReceita

receitas_bp = Blueprint(
    "receitas",
    __name__,
    template_folder=".",
)


@receitas_bp.route("/")
def index():
    modelos = ModeloReceita.query.order_by(ModeloReceita.titulo).all()
    meds = Medicamento.query.order_by(Medicamento.principio_ativo).limit(10).all()
    clinica = Clinica.get_instance()
    return render_template(
        "receitas/index.html",
        modelos=modelos,
        medicamentos=meds,
        clinica=clinica,
    )


@receitas_bp.route("/novo", methods=["GET", "POST"])
def novo_modelo():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        conteudo = request.form.get("conteudo", "").strip()
        if not titulo or not conteudo:
            flash("Título e conteúdo obrigatórios", "danger")
        else:
            modelo = ModeloReceita()
            modelo.titulo = titulo  # type: ignore[assignment]
            modelo.conteudo = conteudo  # type: ignore[assignment]
            db.session.add(modelo)
            db.session.commit()
            flash("Modelo criado", "success")
            return redirect(url_for("receitas.index"))
    return render_template("receitas/form_modelo.html")


@receitas_bp.route("/modelos/<int:modelo_id>/editar", methods=["GET", "POST"])
def editar_modelo(modelo_id: int):
    modelo = get_or_404(ModeloReceita, modelo_id)
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        conteudo = request.form.get("conteudo", "").strip()
        if not titulo or not conteudo:
            flash("Título e conteúdo obrigatórios", "danger")
        else:
            modelo.titulo = titulo  # type: ignore[assignment]
            modelo.conteudo = conteudo  # type: ignore[assignment]
            db.session.commit()
            flash("Modelo atualizado", "success")
            return redirect(url_for("receitas.index"))
    return render_template("receitas/form_modelo.html", modelo=modelo)


@receitas_bp.route("/modelos/<int:modelo_id>/excluir", methods=["POST"])  # simples
def excluir_modelo(modelo_id: int):
    modelo = get_or_404(ModeloReceita, modelo_id)
    db.session.delete(modelo)
    db.session.commit()
    flash("Modelo excluído", "info")
    return redirect(url_for("receitas.index"))


@receitas_bp.route("/medicamentos")
def listar_medicamentos():
    meds = Medicamento.query.order_by(Medicamento.principio_ativo).all()
    return render_template(
        "receitas/lista_medicamentos.html",
        medicamentos=meds,
    )


@receitas_bp.route("/medicamentos/<int:med_id>")
def ver_medicamento(med_id: int):
    med = get_or_404(Medicamento, med_id)
    return render_template(
        "receitas/visualizar_medicamento.html",
        medicamento=med,
    )


# ------------------- Extensões avançadas (legacy parity) -------------------


@receitas_bp.route("/nova")
def nova_receita():
    pacientes = Paciente.query.order_by(Paciente.nome).all()
    dentistas = User.query.filter_by(cargo="dentista").order_by(User.nome_completo).all()
    clinica = Clinica.get_instance()
    return render_template(
        "receitas/formulario_receita.html",
        pacientes=pacientes,
        dentistas=dentistas,
        clinica=clinica,
    )


@receitas_bp.route("/medicamentos/buscar")
def buscar_medicamentos_avancado():  # busca multi-campos
    termo = request.args.get("termo", "").strip()
    medicamentos = []
    if termo:
        like = f"%{termo}%"
        medicamentos = (
            Medicamento.query.filter(
                (Medicamento.categoria.ilike(like))
                | (Medicamento.principio_ativo.ilike(like))
                | (Medicamento.nome_referencia.ilike(like))
                | (Medicamento.apresentacao.ilike(like))
                | (Medicamento.posologia.ilike(like))
                | (Medicamento.uso.ilike(like))
                | (Medicamento.indicacoes.ilike(like))
                | (Medicamento.mecanismo_acao.ilike(like))
                | (Medicamento.contraindicacoes.ilike(like))
                | (Medicamento.efeitos_colaterais.ilike(like))
                | (Medicamento.interacoes_medicamentosas.ilike(like))
                | (Medicamento.risco_gravidez.ilike(like))
                | (Medicamento.tipo_receita.ilike(like))
                | (Medicamento.alerta_principal.ilike(like))
                | (Medicamento.instrucao_compra.ilike(like))
                | (Medicamento.observacao.ilike(like))
            )
            .order_by(Medicamento.principio_ativo)
            .all()
        )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            [
                {
                    "id": m.id,
                    "principio_ativo": m.principio_ativo,
                    "apresentacao": m.apresentacao,
                    "categoria": m.categoria,
                }
                for m in medicamentos
            ]
        )
    return render_template(
        "receitas/lista_medicamentos.html",
        medicamentos=medicamentos,
        termo_busca=termo,
    )


@receitas_bp.route("/api/dentistas/<int:dentista_id>/dados")
def api_dados_dentista(dentista_id: int):
    dentista = User.query.filter_by(id=dentista_id, cargo="dentista").first()
    if not dentista:
        return jsonify({"error": "Dentista não encontrado"}), 404
    return jsonify(
        {
            "id": dentista.id,
            "nome_completo": dentista.nome_completo,
            "cro": dentista.cro or "",
            "username": dentista.username,
        }
    )


@receitas_bp.route("/api/medicamentos")
def api_medicamentos():  # basic JSON for future search UI
    termo = request.args.get("q", "").strip()
    query = Medicamento.query
    if termo:
        like = f"%{termo}%"
        query = query.filter(
            (Medicamento.principio_ativo.ilike(like))
            | (Medicamento.nome_referencia.ilike(like))
            | (Medicamento.categoria.ilike(like))
        )
    meds = query.order_by(Medicamento.principio_ativo).limit(50).all()
    return jsonify(
        [
            {
                "id": m.id,
                "principio_ativo": m.principio_ativo,
                "apresentacao": m.apresentacao,
                "categoria": m.categoria,
            }
            for m in meds
        ]
    )


@receitas_bp.route("/seed-medicamentos", methods=["POST"])  # utilitário dev
def seed_medicamentos():  # pragma: no cover - simples seed
    if Medicamento.query.first():
        flash("Já existem medicamentos", "info")
        return redirect(url_for("receitas.index"))
    exemplos = [
        {
            "categoria": "Analgesico",
            "principio_ativo": "Paracetamol",
            "apresentacao": "500mg comprimido",
            "posologia": "1 comp a cada 6-8h se dor",
        },
        {
            "categoria": "Antinflamatorio",
            "principio_ativo": "Ibuprofeno",
            "apresentacao": "600mg comprimido",
            "posologia": "1 comp 8/8h por 3 dias",
        },
    ]
    for e in exemplos:
        med = Medicamento(**e)
        db.session.add(med)
    db.session.commit()
    flash("Medicamentos seed inseridos", "success")
    return redirect(url_for("receitas.index"))
