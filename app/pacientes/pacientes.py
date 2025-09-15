from datetime import date, datetime

from flask import (
    Blueprint,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from .. import db
from ..auth.auth import require_roles
from ..utils_db import get_or_404
from .forms import (
    AnamneseForm,
    FichaForm,
    FinanceiroForm,
    HistoricoForm,
    PacienteForm,
    PlanoForm,
    ProcedimentoForm,
)
from .models import Anamnese, Ficha, Financeiro, Historico, Paciente, PlanoTratamento, Procedimento
from .services import (
    add_procedimento,
    calcular_totais_financeiro,
    cpf_existe,
    normalizar_cpf,
    recompute_orcamento_total,
    remove_procedimento,
)

pacientes_bp = Blueprint("pacientes", __name__, template_folder=".")


@pacientes_bp.route("/")
def listar():
    page = request.args.get("page", 1, type=int)
    busca = request.args.get("busca", "")
    query = Paciente.query.filter_by(deleted_at=None)
    if busca:
        like = f"%{busca}%"
        query = query.filter(Paciente.nome.ilike(like))
    pacientes = query.order_by(Paciente.nome).paginate(
        page=page,
        per_page=10,
    )
    return render_template(
        "pacientes/lista.html",
        pacientes=pacientes,
        busca=busca,
    )


@pacientes_bp.route("/novo", methods=["GET", "POST"])
@require_roles("admin", "gerente", "atendimento")
def novo():
    form = PacienteForm()
    if form.validate_on_submit():
        data_nasc = None
        if form.data_nascimento.data:
            try:
                data_nasc = datetime.strptime(
                    form.data_nascimento.data,
                    "%d/%m/%Y",
                ).date()
            except ValueError:
                flash("Data inválida, use dd/mm/aaaa", "danger")
                return render_template(
                    "pacientes/form.html",
                    form=form,
                    titulo="Novo Paciente",
                )
        paciente = Paciente()
        paciente.nome = form.nome.data
        paciente.data_nascimento = data_nasc
        paciente.sexo = form.sexo.data
        if form.cpf.data:
            try:
                cpf_norm = normalizar_cpf(form.cpf.data, validar=True)
                # cpf_norm garantido não None aqui
                if cpf_existe(cpf_norm):  # type: ignore[arg-type]
                    flash("CPF já cadastrado", "danger")
                    return render_template(
                        "form.html",
                        form=form,
                        titulo="Novo Paciente",
                    )
                paciente.cpf = cpf_norm
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template(
                    "pacientes/form.html",
                    form=form,
                    titulo="Novo Paciente",
                )
        paciente.telefone = form.telefone.data
        paciente.celular = form.celular.data
        paciente.email = form.email.data
        db.session.add(paciente)
        db.session.commit()
        flash("Paciente cadastrado", "success")
        return redirect(url_for("pacientes.listar"))
    return render_template(
        "pacientes/form.html",
        form=form,
        titulo="Novo Paciente",
    )


@pacientes_bp.route("/<int:paciente_id>")
def visualizar(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if paciente.deleted_at:
        flash("Paciente removido", "warning")
        return redirect(url_for("pacientes.listar"))
    # Relationship é dynamic; .all() já retorna apenas lançamentos
    # pertencentes ao paciente
    lancs = paciente.financeiros.all()
    saldo = None
    if lancs:
        _, _, saldo = calcular_totais_financeiro(lancs)
    return render_template(
        "pacientes/visualizar.html",
        paciente=paciente,
        saldo=saldo,
    )


@pacientes_bp.route("/<int:paciente_id>/ficha", methods=["GET", "POST"])
def ficha(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    ficha = Ficha.query.filter_by(paciente_id=paciente.id).first()
    if not ficha:
        ficha = Ficha()
        ficha.paciente_id = paciente.id
        db.session.add(ficha)
        db.session.commit()
    form = FichaForm(obj=ficha)
    if form.validate_on_submit():
        form.populate_obj(ficha)
        db.session.commit()
        flash("Ficha atualizada", "success")
        return redirect(url_for("pacientes.ficha", paciente_id=paciente.id))
    return render_template(
        "pacientes/ficha.html",
        paciente=paciente,
        form=form,
    )


@pacientes_bp.route("/<int:paciente_id>/anamnese", methods=["GET", "POST"])
def anamnese(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    an = Anamnese.query.filter_by(paciente_id=paciente.id).first()
    if not an:
        an = Anamnese()
        an.paciente_id = paciente.id
        db.session.add(an)
        db.session.commit()
    form = AnamneseForm(obj=an)
    if form.validate_on_submit():
        form.populate_obj(an)
        an.ultima_atualizacao = datetime.utcnow()
        db.session.commit()
        flash("Anamnese atualizada", "success")
        return redirect(url_for("pacientes.anamnese", paciente_id=paciente.id))
    return render_template(
        "pacientes/anamnese.html",
        paciente=paciente,
        form=form,
    )


@pacientes_bp.route("/<int:paciente_id>/planos")
def planos(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    planos = (
        PlanoTratamento.query.filter_by(paciente_id=paciente.id)
        .order_by(PlanoTratamento.data_criacao.desc())
        .all()
    )
    return render_template(
        "pacientes/planos.html",
        paciente=paciente,
        planos=planos,
    )


@pacientes_bp.route("/<int:paciente_id>/planos/novo", methods=["GET", "POST"])
@require_roles("admin", "gerente")
def novo_plano(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    form = PlanoForm()
    if form.validate_on_submit():
        plano = PlanoTratamento()
        plano.paciente_id = paciente.id
        plano.descricao = form.descricao.data
        plano.status = form.status.data
        plano.observacoes = form.observacoes.data
        db.session.add(plano)
        db.session.commit()
        flash("Plano criado", "success")
        return redirect(
            url_for(
                "pacientes.visualizar_plano",
                paciente_id=paciente.id,
                plano_id=plano.id,
            )
        )
    return render_template(
        "pacientes/form_plano.html",
        paciente=paciente,
        form=form,
    )


@pacientes_bp.route("/<int:paciente_id>/planos/<int:plano_id>")
def visualizar_plano(paciente_id: int, plano_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    plano = get_or_404(PlanoTratamento, plano_id)
    if plano.paciente_id != paciente.id:
        return redirect(url_for("pacientes.planos", paciente_id=paciente.id))
    procedimentos = Procedimento.query.filter_by(plano_id=plano.id).all()
    # Resumo financeiro agregado (créditos/débitos) para o plano
    fin_query = Financeiro.query.filter_by(plano_id=plano.id)
    total_creditos = 0.0
    total_debitos = 0.0
    creditos_pagos = 0.0
    for f in fin_query.all():
        if f.status == "Cancelado":  # ignora cancelados em totais
            continue
        valor = float(f.valor or 0)
        if f.tipo == "Crédito":
            total_creditos += valor
            if f.status == "Pago":
                creditos_pagos += valor
        elif f.tipo == "Débito":
            total_debitos += valor
    resumo_financeiro_plano = {
        "total_creditos": total_creditos,
        "total_debitos": total_debitos,
        "saldo": creditos_pagos - total_debitos,
        "creditos_pagos": creditos_pagos,
    }
    return render_template(
        "pacientes/visualizar_plano.html",
        paciente=paciente,
        plano=plano,
        procedimentos=procedimentos,
        resumo_financeiro_plano=resumo_financeiro_plano,
    )


@pacientes_bp.route(
    "/<int:paciente_id>/planos/<int:plano_id>/procedimentos/novo",
    methods=["GET", "POST"],
)
@require_roles("clinico")
def novo_procedimento(paciente_id: int, plano_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    plano = get_or_404(PlanoTratamento, plano_id)
    if plano.paciente_id != paciente.id:
        flash("Plano inválido", "danger")
        return redirect(url_for("pacientes.planos", paciente_id=paciente.id))
    form = ProcedimentoForm()
    if form.validate_on_submit():
        try:
            add_procedimento(
                plano,
                descricao=form.descricao.data or "",
                valor=form.valor.data or 0,
                dente=form.dente.data,
                status=form.status.data,
                data_prevista=form.data_prevista.data,
                data_realizado=form.data_realizado.data,
                observacoes=form.observacoes.data,
            )
            db.session.commit()
            flash("Procedimento adicionado", "success")
        except ValueError as exc:  # valor negativo, etc.
            flash(str(exc), "danger")
            return render_template(
                "pacientes/form_procedimento.html",
                paciente=paciente,
                plano=plano,
                form=form,
            )
        return redirect(
            url_for(
                "pacientes.visualizar_plano",
                paciente_id=paciente.id,
                plano_id=plano.id,
            )
        )
    return render_template(
        "pacientes/form_procedimento.html",
        paciente=paciente,
        plano=plano,
        form=form,
    )


@pacientes_bp.route(
    "/<int:paciente_id>/planos/<int:plano_id>/procedimentos/" "<int:proc_id>/excluir",
    methods=["POST"],
)
@require_roles("admin", "gerente")
def excluir_procedimento(paciente_id: int, plano_id: int, proc_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    plano = get_or_404(PlanoTratamento, plano_id)
    proc = get_or_404(Procedimento, proc_id)
    if plano.paciente_id != paciente.id or proc.plano_id != plano.id:
        flash("Procedimento inválido", "danger")
        return redirect(url_for("pacientes.planos", paciente_id=paciente.id))
    remove_procedimento(proc)
    db.session.commit()
    flash("Procedimento removido", "success")
    return redirect(
        url_for(
            "pacientes.visualizar_plano",
            paciente_id=paciente.id,
            plano_id=plano.id,
        )
    )


@pacientes_bp.route(
    "/<int:paciente_id>/planos/<int:plano_id>/procedimentos/" "<int:proc_id>/realizar",
    methods=["POST"],
)
@require_roles("clinico")
def realizar_procedimento(paciente_id: int, plano_id: int, proc_id: int):
    """Marca procedimento como realizado atribuindo data_realizado."""
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    plano = get_or_404(PlanoTratamento, plano_id)
    proc = get_or_404(Procedimento, proc_id)
    if proc.plano_id != plano.id or plano.paciente_id != paciente.id:
        flash("Procedimento inválido", "danger")
        return redirect(
            url_for(
                "pacientes.visualizar_plano",
                paciente_id=paciente.id,
                plano_id=plano.id,
            )
        )
    proc.status = "Realizado"
    if not proc.data_realizado:
        proc.data_realizado = date.today()
    db.session.commit()
    flash("Procedimento marcado como realizado", "success")
    return redirect(
        url_for(
            "pacientes.visualizar_plano",
            paciente_id=paciente.id,
            plano_id=plano.id,
        )
    )


# --- HTMX Procedimentos ---


@pacientes_bp.route(
    "/<int:paciente_id>/planos/<int:plano_id>/procedimentos/" "<int:proc_id>/realizar/htmx",
    methods=["POST"],
)
@require_roles("clinico")
def realizar_procedimento_htmx(paciente_id: int, plano_id: int, proc_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return make_response("", 410)
    plano = get_or_404(PlanoTratamento, plano_id)
    proc = get_or_404(Procedimento, proc_id)
    if proc.plano_id != plano.id or plano.paciente_id != paciente.id:
        resp = make_response("", 400)
        return resp
    proc.status = "Realizado"
    if not proc.data_realizado:
        proc.data_realizado = date.today()
    db.session.commit()
    return render_template(
        "pacientes/partials/_procedimento_row.html",
        p=proc,
        paciente=paciente,
        plano=plano,
    )


@pacientes_bp.route(
    "/<int:paciente_id>/planos/<int:plano_id>/procedimentos/" "<int:proc_id>/excluir/htmx",
    methods=["POST"],
)
@require_roles("admin", "gerente")
def excluir_procedimento_htmx(paciente_id: int, plano_id: int, proc_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return make_response("", 410)
    plano = get_or_404(PlanoTratamento, plano_id)
    proc = get_or_404(Procedimento, proc_id)
    if plano.paciente_id != paciente.id or proc.plano_id != plano.id:
        return make_response("", 400)
    remove_procedimento(proc)
    db.session.commit()
    # Retornamos linha vazia para remoção via hx-swap="outerHTML"
    return make_response("", 204)


@pacientes_bp.route(
    "/<int:paciente_id>/planos/<int:plano_id>/procedimentos/htmx",
    methods=["GET"],
)
def listar_procedimentos_htmx(paciente_id: int, plano_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return make_response("", 410)
    plano = get_or_404(PlanoTratamento, plano_id)
    if plano.paciente_id != paciente.id:
        return make_response("", 400)
    procedimentos = Procedimento.query.filter_by(plano_id=plano.id).all()
    return render_template(
        "pacientes/partials/_procedimentos_table.html",
        paciente=paciente,
        plano=plano,
        procedimentos=procedimentos,
    )


@pacientes_bp.route(
    "/<int:paciente_id>/planos/<int:plano_id>/recompute",
    methods=["POST"],
)
@require_roles("admin", "gerente")
def recompute_plano(paciente_id: int, plano_id: int):
    """Recalcula orçamento total do plano (manutenção)."""
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    plano = get_or_404(PlanoTratamento, plano_id)
    if plano.paciente_id != paciente.id:
        flash("Plano inválido", "danger")
        return redirect(url_for("pacientes.planos", paciente_id=paciente.id))
    recompute_orcamento_total(plano)
    db.session.commit()
    flash("Orçamento recalculado", "info")
    return redirect(
        url_for(
            "pacientes.visualizar_plano",
            paciente_id=paciente.id,
            plano_id=plano.id,
        )
    )


# --- HTMX Financeiro Totais ---
@pacientes_bp.route(
    "/<int:paciente_id>/financeiro/totais/htmx",
    methods=["GET"],
)
def financeiros_totais_htmx(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return make_response("", 410)
    lancamentos = (
        Financeiro.query.filter_by(paciente_id=paciente.id)
        .order_by(Financeiro.data_lancamento.desc())
        .all()
    )
    total_credito, total_debito, saldo = calcular_totais_financeiro(
        lancamentos,
    )
    return render_template(
        "pacientes/partials/_financeiro_totais.html",
        total_credito=total_credito,
        total_debito=total_debito,
        saldo=saldo,
        paciente=paciente,
    )


@pacientes_bp.route("/<int:paciente_id>/historico")
def historico(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    page = request.args.get("page", 1, type=int)
    per_page = 20
    base_q = Historico.query.filter_by(paciente_id=paciente.id).order_by(Historico.data.desc())
    total = base_q.count()
    registros = base_q.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    return render_template(
        "pacientes/historico.html",
        paciente=paciente,
        historicos=registros,
        page=page,
        pages=pages,
        total=total,
    )


@pacientes_bp.route(
    "/<int:paciente_id>/historico/novo",
    methods=["GET", "POST"],
)
@require_roles("admin", "gerente", "dentista")
def novo_historico(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    form = HistoricoForm()
    if form.validate_on_submit():
        h = Historico()
        h.paciente_id = paciente.id
        h.descricao = form.descricao.data
        h.procedimentos_realizados = form.procedimentos_realizados.data
        h.observacoes = form.observacoes.data
        db.session.add(h)
        db.session.commit()
        flash("Histórico adicionado", "success")
        return redirect(
            url_for("pacientes.historico", paciente_id=paciente.id),
        )
    return render_template(
        "pacientes/form_historico.html",
        paciente=paciente,
        form=form,
    )


@pacientes_bp.route("/<int:paciente_id>/financeiro")
def financeiro(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    page = request.args.get("page", 1, type=int)
    per_page = 20
    base_q = Financeiro.query.filter_by(paciente_id=paciente.id).order_by(
        Financeiro.data_lancamento.desc()
    )
    all_for_totals = base_q.all()
    total_credito, total_debito, saldo = calcular_totais_financeiro(
        all_for_totals,
    )
    lancamentos = base_q.offset((page - 1) * per_page).limit(per_page).all()
    total = len(all_for_totals)
    pages = (total + per_page - 1) // per_page
    # Inline form para criação rápida via HTMX
    form_inline = FinanceiroForm()
    return render_template(
        "pacientes/financeiro.html",
        paciente=paciente,
        lancamentos=lancamentos,
        total_credito=total_credito,
        total_debito=total_debito,
        saldo=saldo,
        form_inline=form_inline,
        page=page,
        pages=pages,
        total=total,
    )


@pacientes_bp.route(
    "/<int:paciente_id>/financeiro/novo",
    methods=["GET", "POST"],
)
@require_roles("admin", "gerente", "financeiro")
def novo_financeiro(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    form = FinanceiroForm()
    if form.validate_on_submit():
        fin = Financeiro()
        fin.paciente_id = paciente.id
        fin.descricao = form.descricao.data
        # WTForms FloatField -> coerção implícita para Numeric (SQLAlchemy)
        fin.valor = form.valor.data
        fin.tipo = form.tipo.data
        fin.forma_pagamento = form.forma_pagamento.data
        fin.status = form.status.data
        fin.data_pagamento = form.data_pagamento.data
        proc_id = request.form.get("procedimento_id")
        if proc_id and proc_id.isdigit():
            fin.procedimento_id = int(proc_id)
            # Propaga plano_id se procedimento tiver plano
            proc_obj = db.session.get(Procedimento, fin.procedimento_id)
            if proc_obj is not None:
                fin.plano_id = proc_obj.plano_id
        db.session.add(fin)
        db.session.commit()
        flash("Lançamento registrado", "success")
        return redirect(
            url_for("pacientes.financeiro", paciente_id=paciente.id),
        )
    return render_template(
        "pacientes/form_financeiro.html",
        paciente=paciente,
        form=form,
    )


@pacientes_bp.route(
    "/<int:paciente_id>/financeiro/novo/htmx",
    methods=["POST"],
)
@require_roles("admin", "gerente", "financeiro")
def novo_financeiro_htmx(paciente_id: int):
    """Cria lançamento financeiro via HTMX e retorna linha parcial.

    Retorna 422 com fragmento de erros se validação falhar.
    Dispara evento 'financeiroUpdated' para atualização dos totais.
    """
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return make_response("", 410)
    form = FinanceiroForm()
    if form.validate_on_submit():
        fin = Financeiro()
        fin.paciente_id = paciente.id
        fin.descricao = form.descricao.data
        fin.valor = form.valor.data
        fin.tipo = form.tipo.data
        fin.forma_pagamento = form.forma_pagamento.data
        fin.status = form.status.data
        fin.data_pagamento = form.data_pagamento.data
        proc_id = request.form.get("procedimento_id")
        if proc_id and proc_id.isdigit():
            fin.procedimento_id = int(proc_id)
            proc_obj = db.session.get(Procedimento, fin.procedimento_id)
            if proc_obj is not None:
                fin.plano_id = proc_obj.plano_id
        db.session.add(fin)
        db.session.commit()
        # Recarregar linha recém criada (ordenação na view principal)
        return (
            render_template(
                "pacientes/partials/_financeiro_row.html",
                f=fin,
                paciente=paciente,
            ),
            200,
            {"HX-Trigger": "financeiroUpdated"},
        )
    # Erros: retornar pequeno bloco com mensagens
    erros = []
    for field, msgs in form.errors.items():
        for m in msgs:
            erros.append(f"{field}: {m}")
    html = "<div class='form-errors'>" + "<br>".join(erros) + "</div>"
    resp = make_response(html, 422)
    # Direciona erros para o box de mensagens do formulário inline
    resp.headers["HX-Retarget"] = "#inline-financeiro-messages"
    resp.headers["HX-Reswap"] = "innerHTML"
    return resp


@pacientes_bp.route(
    "/<int:paciente_id>/financeiro/<int:fin_id>/excluir/htmx",
    methods=["POST", "DELETE"],
)
@require_roles("admin", "gerente", "financeiro")
def excluir_financeiro_htmx(paciente_id: int, fin_id: int):
    """Exclui um lançamento financeiro via HTMX e remove a linha.

    Retorna 204 (No Content) para remoção via hx-swap="outerHTML" e
    dispara 'financeiroUpdated' para atualizar totais.
    """
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return make_response("", 410)
    fin = db.session.get(Financeiro, fin_id)
    if fin is None or fin.paciente_id != paciente.id:
        return make_response("", 404)
    db.session.delete(fin)
    db.session.commit()
    return ("", 204, {"HX-Trigger": "financeiroUpdated"})


@pacientes_bp.route("/<int:paciente_id>/editar", methods=["GET", "POST"])
@require_roles("admin", "gerente", "atendimento")
def editar(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        return redirect(url_for("pacientes.listar"))
    form = PacienteForm(obj=paciente)
    if request.method == "GET" and paciente.data_nascimento:
        form.data_nascimento.data = paciente.data_nascimento.strftime(
            "%d/%m/%Y",
        )
    if form.validate_on_submit():
        if form.data_nascimento.data:
            try:
                paciente.data_nascimento = datetime.strptime(
                    form.data_nascimento.data,
                    "%d/%m/%Y",
                ).date()
            except ValueError:
                flash("Data inválida, use dd/mm/aaaa", "danger")
                return render_template(
                    "pacientes/form.html",
                    form=form,
                    titulo="Editar Paciente",
                )
        paciente.nome = form.nome.data
        paciente.sexo = form.sexo.data
        if form.cpf.data:
            try:
                cpf_norm = normalizar_cpf(form.cpf.data, validar=True)
                # se alterou e já existe em outro
                if cpf_norm != paciente.cpf and cpf_norm and cpf_existe(cpf_norm):
                    flash("CPF já cadastrado", "danger")
                    return render_template(
                        "pacientes/form.html",
                        form=form,
                        titulo="Editar Paciente",
                    )
                paciente.cpf = cpf_norm
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template(
                    "pacientes/form.html",
                    form=form,
                    titulo="Editar Paciente",
                )
        else:
            paciente.cpf = None
        paciente.telefone = form.telefone.data
        paciente.celular = form.celular.data
        paciente.email = form.email.data
        db.session.commit()
        flash("Paciente atualizado", "success")
        return redirect(
            url_for("pacientes.visualizar", paciente_id=paciente.id),
        )
    return render_template(
        "pacientes/form.html",
        form=form,
        titulo="Editar Paciente",
    )


@pacientes_bp.route("/<int:paciente_id>/excluir", methods=["POST"])
@require_roles("admin")
def excluir(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if getattr(paciente, "deleted_at", None):
        flash("Já removido", "info")
        return redirect(url_for("pacientes.listar"))
    paciente.deleted_at = datetime.utcnow()
    db.session.commit()
    flash("Paciente removido", "success")
    return redirect(url_for("pacientes.listar"))


@pacientes_bp.route("/<int:paciente_id>/restaurar", methods=["POST"])
@require_roles("admin")
def restaurar(paciente_id: int):
    paciente = get_or_404(Paciente, paciente_id)
    if not getattr(paciente, "deleted_at", None):
        flash("Paciente não está removido", "info")
        return redirect(
            url_for("pacientes.visualizar", paciente_id=paciente.id),
        )
    paciente.deleted_at = None
    db.session.commit()
    flash("Paciente restaurado", "success")
    return redirect(url_for("pacientes.visualizar", paciente_id=paciente.id))


@pacientes_bp.route("/aniversarios")
def aniversarios():
    mes = datetime.utcnow().month
    pacientes = Paciente.query.filter(
        db.extract("month", Paciente.data_nascimento) == mes,
    ).all()
    return render_template(
        "pacientes/aniversarios.html",
        pacientes=pacientes,
        mes=mes,
    )


@pacientes_bp.route("/api/<int:paciente_id>/dados")
def api_dados(paciente_id: int):
    p = get_or_404(Paciente, paciente_id)
    data_nasc_fmt = p.data_nascimento.strftime("%d/%m/%Y") if p.data_nascimento else ""
    return jsonify(
        {
            "id": p.id,
            "nome": p.nome,
            "data_nascimento": data_nasc_fmt,
            "idade": p.idade(),
            "telefone": p.telefone or "",
            "email": p.email or "",
        }
    )


@pacientes_bp.route("/search")
def search():
    term = request.args.get("term", "")
    if len(term) < 2:
        return jsonify([])
    like = f"%{term}%"
    results = Paciente.query.filter(Paciente.nome.ilike(like)).limit(10).all()
    return jsonify([p.nome for p in results])


@pacientes_bp.route("/dashboard")
def dashboard():
    """Painel simples de métricas clínicas e financeiras.

    Métricas:
    - total_pacientes (exclui soft-deleted)
    - procedimentos_pendentes/realizados (exclui pacientes removidos)
    - saldo_global conforme política: créditos pagos - débitos não cancelados
    """
    # Pacientes ativos
    total_pacientes = Paciente.query.filter_by(deleted_at=None).count()
    # Contagem de procedimentos por status, apenas de pacientes ativos
    from sqlalchemy import func  # import local para evitar topo muito longo

    base_join = (
        db.session.query(func.count(Procedimento.id))
        .join(PlanoTratamento, Procedimento.plano_id == PlanoTratamento.id)
        .join(Paciente, PlanoTratamento.paciente_id == Paciente.id)
        .filter(Paciente.deleted_at.is_(None))
    )
    procedimentos_pendentes = base_join.filter(Procedimento.status == "Pendente").scalar() or 0
    procedimentos_realizados = base_join.filter(Procedimento.status == "Realizado").scalar() or 0

    # Saldo global (pacientes ativos)
    lancs = (
        Financeiro.query.join(Paciente, Financeiro.paciente_id == Paciente.id)
        .filter(Paciente.deleted_at.is_(None))
        .all()
    )
    _tc, _td, saldo_global = calcular_totais_financeiro(lancs)

    # Filtro opcional por período (dd/mm/aaaa)
    inicio_raw = request.args.get("inicio", "").strip()
    fim_raw = request.args.get("fim", "").strip()
    saldo_global_filtrado = None
    inicio_dt = None
    fim_dt = None
    if inicio_raw and fim_raw:
        try:
            inicio_dt = datetime.strptime(inicio_raw, "%d/%m/%Y")
            fim_dt = datetime.strptime(fim_raw, "%d/%m/%Y")
            # incluir fim do dia
            fim_dt = fim_dt.replace(hour=23, minute=59, second=59)
            lancs_f = (
                Financeiro.query.join(Paciente, Financeiro.paciente_id == Paciente.id)
                .filter(Paciente.deleted_at.is_(None))
                .filter(Financeiro.data_lancamento >= inicio_dt)
                .filter(Financeiro.data_lancamento <= fim_dt)
                .all()
            )
            _tc2, _td2, saldo_global_filtrado = calcular_totais_financeiro(lancs_f)
        except ValueError:
            # Datas inválidas: ignorar filtro e seguir sem saldo filtrado
            saldo_global_filtrado = None
    return render_template(
        "pacientes/dashboard.html",
        total_pacientes=total_pacientes,
        procedimentos_pendentes=procedimentos_pendentes,
        procedimentos_realizados=procedimentos_realizados,
        saldo_global=saldo_global,
        inicio=inicio_raw,
        fim=fim_raw,
        saldo_global_filtrado=saldo_global_filtrado,
    )
