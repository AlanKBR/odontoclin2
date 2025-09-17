from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .. import db
from ..auth.models import User  # type: ignore
from ..core.models import Clinica
from datetime import datetime
from ..pacientes.models import Paciente  # type: ignore
from ..utils_db import get_or_404
from .models import Medicamento, ModeloReceita
from .models import ReceitaEmitida
import json


def _get_current_user():
    """Tenta obter current_user de flask_login, com fallback neutro em testes."""
    try:
        from flask_login import current_user as _cu

        return _cu
    except Exception:

        class _Anon:
            cargo = None
            id = None

        return _Anon()


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
    # provide a small initial medicamento list so the table is visible
    meds = Medicamento.query.order_by(Medicamento.principio_ativo).limit(10).all()
    return render_template(
        "receitas/nova_receita.html",
        pacientes=pacientes,
        dentistas=dentistas,
        clinica=clinica,
        medicamentos=meds,
        now=datetime.utcnow(),
    )


@receitas_bp.route("/preview", methods=["POST"])
def preview_receita():
    # Recebe form data e retorna um fragmento HTML com o preview pronto para
    # impressão. Validação mínima.
    data = request.form or request.get_json() or {}
    paciente_id = data.get("paciente_id")
    dentista_id = data.get("dentista_id")
    itens = data.get("itens")
    texto = data.get("texto")
    if isinstance(itens, str):
        try:
            itens = json.loads(itens)
        except Exception:
            itens = []
    # allow either structured itens or a free-form texto
    if not paciente_id or not dentista_id or (not itens and not texto):
        # retorno 422 com fragmento para HTMX substituir a área do form
        return (
            render_template("receitas/_preview_receita.html", error="Dados incompletos"),
            422,
        )
    # use session.get to avoid SQLAlchemy legacy Query.get() warnings
    paciente = db.session.get(Paciente, int(paciente_id))
    dentista = db.session.get(User, int(dentista_id))
    if not paciente or not dentista:
        return (
            render_template(
                "receitas/_preview_receita.html",
                error="Paciente ou dentista não encontrado",
            ),
            422,
        )
    # If texto provided, render preview using it; otherwise use itens
    if texto:
        return render_template(
            "receitas/_preview_receita.html",
            paciente=paciente,
            dentista=dentista,
            texto=texto,
        )
    texto_render = render_template(
        "receitas/_preview_receita.html",
        paciente=paciente,
        dentista=dentista,
        itens=itens,
    )
    return texto_render


@receitas_bp.route("/emitir", methods=["POST"])
def emitir_receita():
    # Salva a receita e retorna JSON com link de impressão. Regras de permissão:
    # - se current_user.cargo == 'dentista', só pode emitir no nome dele
    # - se secretaria/admin, pode emitir em nome de qualquer dentista
    data = request.form or request.get_json() or {}
    paciente_id = data.get("paciente_id")
    dentista_id = data.get("dentista_id")
    itens = data.get("itens")
    texto = data.get("texto")
    notas = data.get("notas") or ""
    if isinstance(itens, str):
        try:
            itens = json.loads(itens)
        except Exception:
            itens = []
    # require paciente, dentista and either itens or texto
    if not paciente_id or not dentista_id or (not itens and not texto):
        return jsonify({"error": "Campos obrigatórios faltando"}), 422
    # permissões
    current_user = _get_current_user()
    if hasattr(current_user, "cargo") and current_user.cargo == "dentista":
        if int(dentista_id) != int(getattr(current_user, "id", 0)):
            return (
                jsonify({"error": "Dentista logado só pode emitir no próprio nome"}),
                403,
            )
    paciente = db.session.get(Paciente, int(paciente_id))
    dentista = db.session.get(User, int(dentista_id))
    if not paciente or not dentista:
        return jsonify({"error": "Paciente ou dentista não encontrado"}), 404
    # gerar texto simples
    if texto:
        texto_render = render_template(
            "receitas/_preview_receita.html",
            paciente=paciente,
            dentista=dentista,
            texto=texto,
            notas=notas,
        )
    else:
        texto_render = render_template(
            "receitas/_preview_receita.html",
            paciente=paciente,
            dentista=dentista,
            itens=itens,
            notas=notas,
        )
    rec = ReceitaEmitida()
    rec.paciente_id = int(paciente_id)
    rec.paciente_nome = getattr(paciente, "nome", "")
    rec.dentista_id = int(dentista_id)
    rec.dentista_nome = getattr(dentista, "nome_completo", "")
    # store itens JSON if present, else store empty list
    try:
        rec.itens_json = json.dumps(itens or [], ensure_ascii=False)
    except Exception:
        rec.itens_json = "[]"
    rec.texto_gerado = texto_render
    rec.usuario_id = getattr(current_user, "id", None)
    db.session.add(rec)
    db.session.commit()
    return jsonify({"id": rec.id, "print_url": url_for("receitas.ver_receita_imprimir", id=rec.id)})


@receitas_bp.route("/<int:id>/imprimir")
def ver_receita_imprimir(id: int):
    rec = get_or_404(ReceitaEmitida, id)
    # retorna página simples para impressão
    return render_template("receitas/visualizar_receita.html", receita=rec)


@receitas_bp.route("/item-row")
def item_row():
    # Retorna um novo item row com row_id único (timestamp ms)
    # kept for compatibility but unused in the new single-textarea UI
    row_id = int(datetime.utcnow().timestamp() * 1000)
    return render_template("receitas/_item_row.html", row_id=row_id)


@receitas_bp.route("/medicamentos/buscar-htmx")
def buscar_medicamentos_htmx():
    termo = request.args.get("q", "").strip()
    # row_id not used in the new UI but kept for compatibility
    row_id = request.args.get("row_id") or "0"
    medicamentos = []
    if termo:
        like = f"%{termo}%"
        medicamentos = (
            Medicamento.query.filter(
                (Medicamento.categoria.ilike(like))
                | (Medicamento.principio_ativo.ilike(like))
                | (Medicamento.nome_referencia.ilike(like))
            )
            .order_by(Medicamento.principio_ativo)
            .limit(50)
            .all()
        )
    return render_template(
        "receitas/_med_search_results.html", medicamentos=medicamentos, row_id=row_id
    )


@receitas_bp.route("/medicamentos/<int:med_id>/detail")
def visualizar_medicamento_htmx(med_id: int):
    med = get_or_404(Medicamento, med_id)
    # show detail in a global container in the new UI
    row_id = request.args.get("row_id") or "0"
    return render_template("receitas/_med_detail.html", medicamento=med, row_id=row_id)


@receitas_bp.route("/medicamentos/selecionar", methods=["POST"])
def selecionar_medicamento():
    # aceita JSON ou form
    data = request.get_json(silent=True)
    if not data:
        # try form or values (covers querystring and form-encoded)
        data = request.form or request.values or {}
    med_id = None
    if isinstance(data, dict):
        med_id = data.get("med_id")
    else:
        # data may be a raw string; attempt to parse
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                med_id = parsed.get("med_id")
        except Exception:
            med_id = None
    # fallback to query param or custom header
    if not med_id:
        med_id = request.args.get("med_id")
    if not med_id:
        med_id = request.headers.get("X-MED-ID")
    if not med_id:
        return (jsonify({"error": "med_id missing"}), 400)
    try:
        med = db.session.get(Medicamento, int(med_id))
    except Exception:
        return (jsonify({"error": "invalid med_id"}), 400)
    if not med:
        return (jsonify({"error": "medicamento not found"}), 404)
    primeira = f"{med.principio_ativo} ___________ {med.instrucao_compra or ''}"
    posologia = med.posologia or ""
    return jsonify(
        {
            "medicamento_id": med.id,
            "medicamento_text": primeira,
            "apresentacao": med.apresentacao or "",
            "posologia": posologia,
        }
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
