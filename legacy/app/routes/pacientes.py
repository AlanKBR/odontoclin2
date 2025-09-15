import json
from calendar import month_name
from datetime import datetime

from flask import (  # current_app,  # Unused import; session,  # Unused import
    Blueprint,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import or_  # Add this import
from sqlalchemy.exc import SQLAlchemyError  # Added import
from wtforms import (
    DateField,
    EmailField,
    FloatField,
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    ValidationError,
)
from wtforms.validators import DataRequired, Email, Length, Optional

from app.decorators import debug_login_optional
from app.extensions import db  # Changed from \\\'from app import db\\\'
from app.models.paciente import Paciente  # Ensure Paciente is imported
from app.models.paciente import (
    Anamnese,
    Ficha,
    Financeiro,
    Historico,
    PlanoTratamento,
    Procedimento,
)
from app.models.tratamento import CategoriaTratamento, Tratamento
from app.models.user import User

# Create a base form with CSRF disabled for all forms


class CSRFDisabledForm(FlaskForm):
    class Meta:
        csrf = False


pacientes = Blueprint("pacientes", __name__)

# Formulário de paciente


class PacienteForm(CSRFDisabledForm):
    nome = StringField("Nome Completo", validators=[DataRequired(), Length(max=100)])
    data_nascimento = StringField("Data de Nascimento", validators=[DataRequired()])
    sexo = SelectField(
        "Sexo",
        choices=[
            ("", "Selecione..."),
            ("Masculino", "Masculino"),
            ("Feminino", "Feminino"),
        ],
    )
    cpf = StringField("CPF", validators=[DataRequired(), Length(max=14)])
    telefone = StringField("Telefone", validators=[Length(max=20)])
    celular = StringField("Celular", validators=[DataRequired(), Length(max=20)])
    email = EmailField("Email", validators=[Optional(), Email(), Length(max=120)])
    endereco = StringField("Endereço", validators=[Length(max=200)])
    bairro = StringField("Bairro", validators=[Length(max=100)])
    cidade = StringField("Cidade", validators=[Length(max=100)])
    estado = SelectField(
        "Estado",
        choices=[
            ("", "Selecione..."),
            ("AC", "AC"),
            ("AL", "AL"),
            ("AP", "AP"),
            ("AM", "AM"),
            ("BA", "BA"),
            ("CE", "CE"),
            ("DF", "DF"),
            ("ES", "ES"),
            ("GO", "GO"),
            ("MA", "MA"),
            ("MT", "MT"),
            ("MS", "MS"),
            ("MG", "MG"),
            ("PA", "PA"),
            ("PB", "PB"),
            ("PR", "PR"),
            ("PE", "PE"),
            ("PI", "PI"),
            ("RJ", "RJ"),
            ("RN", "RN"),
            ("RS", "RS"),
            ("RO", "RO"),
            ("RR", "RR"),
            ("SC", "SC"),
            ("SP", "SP"),
            ("SE", "SE"),
            ("TO", "TO"),
        ],
    )
    cep = StringField("CEP", validators=[Length(max=10)])
    profissao = StringField("Profissão", validators=[Length(max=100)])
    submit = SubmitField("Salvar")

    def validate_data_nascimento(self, field: StringField) -> None:
        try:
            datetime.strptime(field.data, "%d/%m/%Y")
        except (ValueError, TypeError) as exc:
            raise ValidationError("Data de nascimento deve estar no formato dd/mm/aaaa") from exc

    def validate_cpf(self, field: StringField) -> None:
        cpf = field.data
        if not cpf:
            raise ValidationError("CPF é obrigatório.")
        cpf = "".join(filter(str.isdigit, cpf))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            raise ValidationError("CPF inválido.")
        for i in range(9, 11):
            soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
            digito = ((soma * 10) % 11) % 10
            if int(cpf[i]) != digito:
                raise ValidationError("CPF inválido.")


# Formulário de ficha do paciente


class FichaForm(CSRFDisabledForm):
    responsavel = StringField("Responsável", validators=[Length(max=100)])
    contato_emergencia = StringField("Contato de Emergência", validators=[Length(max=100)])
    convenio = StringField("Convênio", validators=[Length(max=100)])
    numero_convenio = StringField("Número do Convênio", validators=[Length(max=50)])
    alergias = TextAreaField("Alergias")
    observacoes = TextAreaField("Observações")
    submit = SubmitField("Salvar")


# Formulário de anamnese


class AnamneseForm(CSRFDisabledForm):
    historico_medico = TextAreaField("Histórico Médico")
    medicamentos_uso = TextAreaField("Medicamentos em Uso")
    cirurgias_previas = TextAreaField("Cirurgias Prévias")
    doencas_cronicas = TextAreaField("Doenças Crônicas")
    habitos = TextAreaField("Hábitos (Fumo, álcool, etc)")
    problemas_dentarios = TextAreaField("Problemas Dentários")
    ultima_visita_dentista = StringField("Última Visita ao Dentista", validators=[Length(max=100)])
    submit = SubmitField("Salvar")


# Formulário de plano de tratamento


class PlanoTratamentoForm(CSRFDisabledForm):
    descricao = TextAreaField("Descrição do Plano", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[
            ("Pendente", "Pendente"),
            ("Em andamento", "Em andamento"),
            ("Concluído", "Concluído"),
            ("Cancelado", "Cancelado"),
        ],
    )
    observacoes = TextAreaField("Observações")
    submit = SubmitField("Salvar")


# Formulário de procedimento


class ProcedimentoForm(CSRFDisabledForm):
    tratamento_id = SelectField("Procedimento do Catálogo", coerce=int, validators=[Optional()])
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)])
    # Changed max length to accommodate multiple teeth
    dente = StringField("Dente", validators=[Length(max=100)])
    # Hidden field for teeth selection JSON
    teeth_selection = StringField("Seleção de Dentes", widget=HiddenField())
    valor = FloatField("Valor (R$)")
    status = SelectField(
        "Status",
        choices=[
            ("Pendente", "Pendente"),
            ("Realizado", "Realizado"),
            ("Cancelado", "Cancelado"),
        ],
    )
    data_prevista = DateField("Data Prevista", validators=[Optional()])
    data_realizado = DateField("Data Realizado", validators=[Optional()])
    observacoes = TextAreaField("Observações")
    submit = SubmitField("Salvar")


# Formulário de histórico


class HistoricoForm(CSRFDisabledForm):
    descricao = TextAreaField("Descrição", validators=[DataRequired()])
    procedimentos_realizados = TextAreaField("Procedimentos Realizados")
    observacoes = TextAreaField("Observações")
    submit = SubmitField("Salvar")


# Formulário financeiro


class FinanceiroForm(CSRFDisabledForm):
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)])
    valor = FloatField("Valor (R$)", validators=[DataRequired()])
    tipo = SelectField("Tipo", choices=[("Crédito", "Crédito"), ("Débito", "Débito")])
    forma_pagamento = SelectField(
        "Forma de Pagamento",
        choices=[
            ("Dinheiro", "Dinheiro"),
            ("Cartão de Crédito", "Cartão de Crédito"),
            ("Cartão de Débito", "Cartão de Débito"),
            ("Pix", "Pix"),
            ("Transferência", "Transferência"),
            ("Boleto", "Boleto"),
        ],
    )
    status = SelectField(
        "Status",
        choices=[
            ("Pendente", "Pendente"),
            ("Pago", "Pago"),
            ("Cancelado", "Cancelado"),
        ],
    )
    data_pagamento = DateField("Data de Pagamento", validators=[Optional()])
    plano_id = SelectField("Plano de Tratamento", coerce=int)
    observacoes = TextAreaField("Observações")
    submit = SubmitField("Salvar")


class ExcluirPacienteForm(CSRFDisabledForm):
    submit = SubmitField("Excluir")


@pacientes.route("/pacientes/<int:paciente_id>/financeiro/novo", methods=["GET", "POST"])
@debug_login_optional
def novo_financeiro(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    form = FinanceiroForm()

    # Preencher opções de planos de tratamento
    planos = PlanoTratamento.query.filter_by(paciente_id=paciente.id).all()
    plano_choices = [(0, "Nenhum")] + [
        (p.id, f'Plano #{p.id} - {p.data_criacao.strftime("%d/%m/%Y")}') for p in planos
    ]
    # Configurar as choices do campo definido na classe
    form.plano_id.choices = plano_choices

    if form.validate_on_submit():
        financeiro = Financeiro(
            paciente_id=paciente.id,
            plano_id=form.plano_id.data if form.plano_id.data > 0 else None,
            descricao=form.descricao.data,
            valor=form.valor.data,
            tipo=form.tipo.data,
            forma_pagamento=form.forma_pagamento.data,
            status=form.status.data,
            data_pagamento=form.data_pagamento.data,
            observacoes=form.observacoes.data,
        )
        db.session.add(financeiro)
        db.session.commit()

        flash("Lançamento financeiro registrado com sucesso!", "success")
        return redirect(url_for("pacientes.listar_financeiro", paciente_id=paciente.id))

    return render_template(
        "pacientes/formulario_financeiro.html",
        form=form,
        paciente=paciente,
        aba_ativa="financeiro",
    )


@pacientes.route("/pacientes")
@debug_login_optional
def listar_pacientes() -> str:  # Add return type annotation
    page = request.args.get("page", 1, type=int)
    query = Paciente.query.order_by(Paciente.nome)  # Filtro de busca
    busca = request.args.get("busca", "")
    if busca:
        # Adaptação para buscar em múltiplos campos
        busca_termo = f"%{busca}%"
        query = query.filter(
            or_(
                Paciente.nome.ilike(busca_termo),
                Paciente.cpf.ilike(busca_termo),
                Paciente.telefone.ilike(busca_termo),
                Paciente.email.ilike(busca_termo),
            )
        )

    # Ordenar por nome por padrão
    query = query.order_by(Paciente.nome)

    pacientes_pagination = query.paginate(page=page, per_page=10)

    # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)

    if is_mobile:
        # Para mobile, usar template específico
        return render_template(
            "mobile/lista_pacientes.html",
            pacientes=pacientes_pagination.items,
            pagination=pacientes_pagination,
            busca=busca,
        )
    else:
        # Para desktop, usar template original
        return render_template(
            "pacientes/lista_pacientes.html",
            pacientes=pacientes_pagination,
            busca=busca,
        )


@pacientes.route("/pacientes/novo", methods=["GET", "POST"])
@debug_login_optional
def novo_paciente() -> str:  # Add return type annotation
    form = PacienteForm()
    if form.validate_on_submit():
        data_nascimento = datetime.strptime(form.data_nascimento.data, "%d/%m/%Y").date()
        paciente = Paciente(
            nome=form.nome.data,
            data_nascimento=data_nascimento,
            sexo=form.sexo.data,
            cpf=form.cpf.data,
            telefone=form.telefone.data,
            celular=form.celular.data,
            email=form.email.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            estado=form.estado.data,
            cep=form.cep.data,
            profissao=form.profissao.data,
        )

        # Verificar se CPF já existe (se foi fornecido)
        if form.cpf.data and Paciente.query.filter_by(cpf=form.cpf.data).first():
            flash("CPF já cadastrado em outro paciente", "danger")
            # Detectar se é dispositivo móvel
            is_mobile = getattr(request, "MOBILE", False)
            template = (
                "mobile/formulario_paciente.html"
                if is_mobile
                else "pacientes/formulario_paciente.html"
            )
            return render_template(template, form=form, titulo="Novo Paciente")

        db.session.add(paciente)
        db.session.commit()

        # Criar Ficha e Anamnese vazios para o paciente
        ficha = Ficha(paciente_id=paciente.id)
        anamnese = Anamnese(paciente_id=paciente.id)

        db.session.add(ficha)
        db.session.add(anamnese)
        db.session.commit()

        flash("Paciente cadastrado com sucesso!", "success")
        return redirect(url_for("pacientes.visualizar_paciente", paciente_id=paciente.id))

    # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)
    template = (
        "mobile/formulario_paciente.html" if is_mobile else "pacientes/formulario_paciente.html"
    )
    return render_template(template, form=form, titulo="Novo Paciente")


@pacientes.route("/pacientes/<int:paciente_id>")
@debug_login_optional
def visualizar_paciente(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)

    # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)

    if is_mobile:
        # Para mobile, usar template específico
        return render_template("mobile/visualizar_paciente.html", paciente=paciente)
    else:
        # Para desktop, usar template original
        return render_template(
            "pacientes/visualizar_paciente.html", paciente=paciente, aba_ativa="ficha"
        )


@pacientes.route("/pacientes/<int:paciente_id>/editar", methods=["GET", "POST"])
@debug_login_optional
def editar_paciente(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    form = PacienteForm(obj=paciente)
    if request.method == "GET" and paciente.data_nascimento:
        form.data_nascimento.data = paciente.data_nascimento.strftime("%d/%m/%Y")

    if form.validate_on_submit():
        # Verificar se CPF já existe em outro paciente
        if form.cpf.data and form.cpf.data != paciente.cpf:
            existe_cpf = Paciente.query.filter(
                Paciente.cpf == form.cpf.data, Paciente.id != paciente_id
            ).first()
            if existe_cpf:
                flash("CPF já cadastrado em outro paciente", "danger")
                # Detectar se é dispositivo móvel
                is_mobile = getattr(request, "MOBILE", False)
                template = (
                    "mobile/formulario_paciente.html"
                    if is_mobile
                    else "pacientes/formulario_paciente.html"
                )
                return render_template(template, form=form, titulo="Editar Paciente")

        # Atualizar dados
        paciente.data_nascimento = datetime.strptime(form.data_nascimento.data, "%d/%m/%Y").date()
        form.populate_obj(paciente)
        db.session.commit()

        flash("Dados do paciente atualizados com sucesso!", "success")
        return redirect(url_for("pacientes.visualizar_paciente", paciente_id=paciente.id))

    # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)
    template = (
        "mobile/formulario_paciente.html" if is_mobile else "pacientes/formulario_paciente.html"
    )
    return render_template(template, form=form, titulo="Editar Paciente")


@pacientes.route("/pacientes/<int:paciente_id>/financeiro")
@debug_login_optional
def listar_financeiro(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    lancamentos = (
        Financeiro.query.filter_by(paciente_id=paciente.id)
        .order_by(Financeiro.data_lancamento.desc())
        .all()
    )  # Calcular totais
    total_credito = sum(
        lancamento.valor
        for lancamento in lancamentos
        if lancamento.tipo == "Crédito" and lancamento.status != "Cancelado"
    )
    total_debito = sum(
        lancamento.valor
        for lancamento in lancamentos
        if lancamento.tipo == "Débito" and lancamento.status != "Cancelado"
    )  # Saldo agora representa tudo que foi pago pelo paciente (somente créditos com status "Pago")
    saldo = sum(
        lancamento.valor
        for lancamento in lancamentos
        if lancamento.tipo == "Crédito" and lancamento.status == "Pago"
    )

    # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)

    if is_mobile:
        # Para mobile, usar template específico
        return render_template(
            "mobile/financeiro.html",
            paciente=paciente,
            lancamentos=lancamentos,
            total_credito=total_credito,
            total_debito=total_debito,
            saldo=saldo,
        )
    else:
        # Para desktop, usar template original
        return render_template(
            "pacientes/financeiro.html",
            paciente=paciente,
            lancamentos=lancamentos,
            total_credito=total_credito,
            total_debito=total_debito,
            saldo=saldo,
            aba_ativa="financeiro",
        )


@pacientes.route("/pacientes/<int:paciente_id>/excluir", methods=["POST"])
@debug_login_optional
def excluir_paciente(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    try:
        db.session.delete(paciente)
        db.session.commit()
        flash("Paciente excluído com sucesso!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Erro ao excluir paciente: {str(e)}", "danger")
        return redirect(url_for("pacientes.visualizar_paciente", paciente_id=paciente_id))
    return redirect(url_for("pacientes.listar_pacientes"))


@pacientes.route("/pacientes/<int:paciente_id>/ficha", methods=["GET", "POST"])
@debug_login_optional
def editar_ficha(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)

    # Criar ficha se não existir
    if not paciente.ficha:
        ficha = Ficha(paciente_id=paciente.id)
        db.session.add(ficha)
        db.session.commit()
        paciente.ficha = ficha

    form = FichaForm(obj=paciente.ficha)

    if form.validate_on_submit():
        form.populate_obj(paciente.ficha)
        db.session.commit()
        flash("Ficha atualizada com sucesso!", "success")
        return redirect(url_for("pacientes.visualizar_paciente", paciente_id=paciente.id))

    return render_template("pacientes/ficha.html", form=form, paciente=paciente, aba_ativa="ficha")


@pacientes.route("/pacientes/<int:paciente_id>/anamnese", methods=["GET", "POST"])
@debug_login_optional
def editar_anamnese(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)

    # Criar anamnese se não existir
    if not paciente.anamnese:
        anamnese = Anamnese(paciente_id=paciente.id)
        db.session.add(anamnese)
        db.session.commit()
        paciente.anamnese = anamnese

    form = AnamneseForm(obj=paciente.anamnese)

    if form.validate_on_submit():
        form.populate_obj(paciente.anamnese)
        paciente.anamnese.ultima_atualizacao = datetime.utcnow()
        db.session.commit()
        flash("Anamnese atualizada com sucesso!", "success")
        return redirect(url_for("pacientes.visualizar_paciente", paciente_id=paciente.id))

    return render_template(
        "pacientes/anamnese.html", form=form, paciente=paciente, aba_ativa="anamnese"
    )


@pacientes.route("/pacientes/<int:paciente_id>/planos")
@debug_login_optional
def listar_planos(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    planos = (
        PlanoTratamento.query.filter_by(paciente_id=paciente.id)
        .order_by(PlanoTratamento.data_criacao.desc())
        .all()
    )

    # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)

    if is_mobile:
        # Para mobile, usar template específico
        return render_template("mobile/planos.html", paciente=paciente, planos=planos)
    else:
        # Para desktop, usar template original
        return render_template(
            "pacientes/planos.html", paciente=paciente, planos=planos, aba_ativa="plano"
        )


@pacientes.route("/pacientes/<int:paciente_id>/planos/novo", methods=["GET", "POST"])
@debug_login_optional
def novo_plano(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    form = PlanoTratamentoForm()

    if form.validate_on_submit():
        plano = PlanoTratamento(
            paciente_id=paciente.id,
            dentista_id=current_user.id,
            descricao=form.descricao.data,
            status=form.status.data,
            observacoes=form.observacoes.data,
        )
        db.session.add(plano)
        db.session.commit()

        flash("Plano de tratamento criado com sucesso!", "success")
        return redirect(
            url_for("pacientes.visualizar_plano", paciente_id=paciente.id, plano_id=plano.id)
        )  # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)
    template = "mobile/formulario_plano.html" if is_mobile else "pacientes/formulario_plano.html"

    return render_template(
        template,
        form=form,
        paciente=paciente,
        aba_ativa="plano" if not is_mobile else None,
    )


@pacientes.route("/pacientes/<int:paciente_id>/planos/<int:plano_id>")
@debug_login_optional
def visualizar_plano(paciente_id: int, plano_id: int):  # Add type hints
    paciente = Paciente.query.get_or_404(paciente_id)
    plano = PlanoTratamento.query.get_or_404(plano_id)

    # Verificar se o plano pertence ao paciente
    if plano.paciente_id != paciente.id:
        abort(404)

    procedimentos = Procedimento.query.filter_by(plano_id=plano.id).all()
    dentista = None
    if plano.dentista_id:
        dentista = User.query.get(
            plano.dentista_id
        )  # Buscar categorias de tratamento para o modal de novo procedimento
    categorias = CategoriaTratamento.query.order_by(CategoriaTratamento.nome).all()
    # Carregamento ansioso dos tratamentos
    for categoria in categorias:
        tratamentos = Tratamento.query.filter_by(categoria_id=categoria.id, ativo=True).all()
        categoria.tratamentos = tratamentos

    # Detectar se é dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)

    if is_mobile:
        # Para mobile, usar template específico
        return render_template(
            "mobile/visualizar_plano.html",
            paciente=paciente,
            plano=plano,
            procedimentos=procedimentos,
            dentista=dentista,
            categorias=categorias,
            now=datetime.now(),
        )
    else:
        # Para desktop, usar template original
        return render_template(
            "pacientes/visualizar_plano.html",
            paciente=paciente,
            plano=plano,
            procedimentos=procedimentos,
            dentista=dentista,
            categorias=categorias,
            now=datetime.now(),
            aba_ativa="plano",
        )


@pacientes.route(
    "/pacientes/<int:paciente_id>/planos/<int:plano_id>/editar", methods=["GET", "POST"]
)
@debug_login_optional
def editar_plano(paciente_id: int, plano_id: int):  # Add type hints
    paciente = Paciente.query.get_or_404(paciente_id)
    plano = PlanoTratamento.query.get_or_404(plano_id)

    if plano.paciente_id != paciente.id:
        abort(404)

    form = PlanoTratamentoForm(obj=plano)

    if form.validate_on_submit():
        form.populate_obj(plano)
        plano.dentista_id = current_user.id  # Update dentist if it changed or wasn't set
        db.session.commit()
        flash("Plano de tratamento atualizado com sucesso!", "success")
        return redirect(
            url_for("pacientes.visualizar_plano", paciente_id=paciente.id, plano_id=plano.id)
        )

    return render_template(
        "pacientes/formulario_plano.html",
        form=form,
        paciente=paciente,
        plano=plano,  # Pass the plan object to the template
        titulo="Editar Plano de Tratamento",  # Add a title for clarity
        aba_ativa="plano",
    )


@pacientes.route(
    "/pacientes/<int:paciente_id>/planos/<int:plano_id>/procedimentos/novo",
    methods=["GET", "POST"],
)
@debug_login_optional
def novo_procedimento(paciente_id: int, plano_id: int):  # Add type hints
    paciente = Paciente.query.get_or_404(paciente_id)
    plano = PlanoTratamento.query.get_or_404(plano_id)

    # Verificar se o plano pertence ao paciente
    if plano.paciente_id != paciente.id:
        abort(404)

    # Buscar categorias com seus tratamentos para o formulário
    categorias = CategoriaTratamento.query.order_by(CategoriaTratamento.nome).all()

    # Carregamento ansioso dos tratamentos
    for categoria in categorias:
        tratamentos = Tratamento.query.filter_by(categoria_id=categoria.id, ativo=True).all()
        categoria.tratamentos = tratamentos

    form = ProcedimentoForm()

    if form.validate_on_submit():
        # Processar os dados da seleção de dentes
        teeth_data = {}
        selected_teeth = []
        selected_quadrants = []
        entire_mouth = False

        # Parse teeth selection data if available
        if form.teeth_selection.data:
            try:
                teeth_data = json.loads(form.teeth_selection.data)
                selected_teeth = teeth_data.get("teeth", [])
                selected_quadrants = teeth_data.get("quadrants", [])
                entire_mouth = teeth_data.get("entireMouth", False)
            except json.JSONDecodeError:
                pass

        # Format teeth string for display
        dente_str = ""
        if entire_mouth:
            dente_str = "Boca completa"
        elif selected_quadrants:
            quadrant_names = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
            dente_str = ", ".join([quadrant_names.get(q, str(q)) for q in selected_quadrants])
        elif selected_teeth:
            dente_str = ", ".join([str(tooth) for tooth in sorted(selected_teeth)])
        else:
            dente_str = form.dente.data

        # Criar novo procedimento
        procedimento = Procedimento(
            plano_id=plano.id,
            tratamento_id=form.tratamento_id.data if form.tratamento_id.data else None,
            descricao=(
                form.descricao.data
                if form.descricao.data
                else Tratamento.query.get(form.tratamento_id.data).nome
            ),
            dente=dente_str,
            dentes_selecionados=json.dumps(selected_teeth) if selected_teeth else None,
            quadrantes=(
                ",".join([str(q) for q in selected_quadrants]) if selected_quadrants else None
            ),
            boca_completa=entire_mouth,
            valor=form.valor.data,
            status=form.status.data,
            data_prevista=form.data_prevista.data,
            data_realizado=form.data_realizado.data,
            observacoes=form.observacoes.data,
        )
        db.session.add(procedimento)
        # Atualizar o orçamento total do plano
        plano.orcamento_total += procedimento.valor

        db.session.commit()
        flash("Procedimento adicionado com sucesso!", "success")
        return redirect(
            url_for("pacientes.visualizar_plano", paciente_id=paciente.id, plano_id=plano.id)
        )

    return render_template(
        "pacientes/formulario_procedimento.html",
        form=form,
        paciente=paciente,
        plano=plano,
        categorias=categorias,
        proc=None,
        aba_ativa="plano",
    )


@pacientes.route(
    "/pacientes/<int:paciente_id>/planos/<int:plano_id>/procedimentos/<int:proc_id>/editar",
    methods=["GET", "POST"],
)
@debug_login_optional
def editar_procedimento(paciente_id: int, plano_id: int, proc_id: int):  # Add type hints
    paciente = Paciente.query.get_or_404(paciente_id)
    plano = PlanoTratamento.query.get_or_404(plano_id)
    procedimento = Procedimento.query.get_or_404(proc_id)

    # Verificar se o plano pertence ao paciente e se o procedimento pertence ao plano
    if plano.paciente_id != paciente.id or procedimento.plano_id != plano.id:
        abort(404)

    # Buscar categorias com seus tratamentos para o formulário
    categorias = CategoriaTratamento.query.order_by(CategoriaTratamento.nome).all()

    # Carregamento ansioso dos tratamentos
    for categoria in categorias:
        tratamentos = Tratamento.query.filter_by(categoria_id=categoria.id, ativo=True).all()
        categoria.tratamentos = tratamentos

    # Prepare form with existing data
    form = ProcedimentoForm(obj=procedimento)

    # Prepare teeth selection data for the form
    if procedimento.boca_completa:
        initial_teeth_selection = json.dumps({"teeth": [], "quadrants": [], "entireMouth": True})
    elif procedimento.quadrantes:
        quadrants = [int(q) for q in procedimento.quadrantes.split(",") if q]
        initial_teeth_selection = json.dumps(
            {"teeth": [], "quadrants": quadrants, "entireMouth": False}
        )
    elif procedimento.dentes_selecionados:
        try:
            selected_teeth = json.loads(procedimento.dentes_selecionados)
            initial_teeth_selection = json.dumps(
                {"teeth": selected_teeth, "quadrants": [], "entireMouth": False}
            )
        except json.JSONDecodeError:
            # Handle case where dentes_selecionados is not valid JSON
            initial_teeth_selection = json.dumps(
                {"teeth": [], "quadrants": [], "entireMouth": False}
            )
    else:
        initial_teeth_selection = None

    # Set initial value for the hidden field
    form.teeth_selection.data = initial_teeth_selection

    if form.validate_on_submit():
        # Guardar o valor antigo para ajustar o orçamento total do plano
        valor_antigo = procedimento.valor

        # Process teeth selection data
        teeth_data = {}
        selected_teeth = []
        selected_quadrants = []
        entire_mouth = False

        # Parse teeth selection data if available
        if form.teeth_selection.data:
            try:
                teeth_data = json.loads(form.teeth_selection.data)
                selected_teeth = teeth_data.get("teeth", [])
                selected_quadrants = teeth_data.get("quadrants", [])
                entire_mouth = teeth_data.get("entireMouth", False)
            except json.JSONDecodeError:
                pass

        # Format teeth string for display
        dente_str = ""
        if entire_mouth:
            dente_str = "Boca completa"
        elif selected_quadrants:
            quadrant_names = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
            dente_str = ", ".join([quadrant_names.get(q, str(q)) for q in selected_quadrants])
        elif selected_teeth:
            dente_str = ", ".join([str(tooth) for tooth in sorted(selected_teeth)])
        else:
            dente_str = form.dente.data

        # Update procedimento fields first
        form.populate_obj(procedimento)

        # Update the teeth selection fields
        procedimento.dente = dente_str
        procedimento.dentes_selecionados = json.dumps(selected_teeth) if selected_teeth else None
        procedimento.quadrantes = (
            ",".join([str(q) for q in selected_quadrants]) if selected_quadrants else None
        )
        procedimento.boca_completa = entire_mouth

        # Se um tratamento do catálogo foi selecionado mas a descrição não foi preenchida,
        # usa o nome do tratamento do catálogo como descrição.
        if not form.descricao.data and form.tratamento_id.data:
            tratamento_obj = Tratamento.query.get(form.tratamento_id.data)
            if tratamento_obj:  # Ensure treatment object exists
                procedimento.descricao = tratamento_obj.nome

        # Atualizar o orçamento total do plano
        plano.orcamento_total = plano.orcamento_total - valor_antigo + procedimento.valor

        db.session.commit()

        flash("Procedimento atualizado com sucesso!", "success")
        return redirect(
            url_for("pacientes.visualizar_plano", paciente_id=paciente.id, plano_id=plano.id)
        )

    return render_template(
        "pacientes/formulario_procedimento.html",
        form=form,
        paciente=paciente,
        plano=plano,
        categorias=categorias,
        proc=procedimento,
        aba_ativa="plano",
    )


@pacientes.route(
    "/pacientes/<int:paciente_id>/planos/<int:plano_id>/procedimentos/<int:proc_id>/excluir",
    methods=["POST"],
)
@debug_login_optional
def excluir_procedimento(paciente_id: int, plano_id: int, proc_id: int):  # Add type hints
    paciente = Paciente.query.get_or_404(paciente_id)
    plano = PlanoTratamento.query.get_or_404(plano_id)
    procedimento = Procedimento.query.get_or_404(proc_id)

    # Verificar se o plano pertence ao paciente e se o procedimento pertence ao plano
    if plano.paciente_id != paciente.id or procedimento.plano_id != plano.id:
        abort(404)

    # Atualizar o orçamento total do plano
    plano.orcamento_total -= procedimento.valor

    try:
        db.session.delete(procedimento)
        db.session.commit()
        flash("Procedimento excluído com sucesso!", "success")
    except SQLAlchemyError as e:  # Changed from Exception to SQLAlchemyError
        db.session.rollback()
        flash(f"Erro ao excluir procedimento: {e}", "danger")

    return redirect(
        url_for("pacientes.visualizar_plano", paciente_id=paciente.id, plano_id=plano.id)
    )


@pacientes.route(
    "/pacientes/<int:paciente_id>/planos/<int:plano_id>/procedimentos/adicionar",
    methods=["POST"],
)
@debug_login_optional
def adicionar_procedimento(paciente_id: int, plano_id: int):  # Add type hints
    """Endpoint para adicionar procedimento via formulário ajax"""
    paciente = Paciente.query.get_or_404(paciente_id)
    plano = PlanoTratamento.query.get_or_404(plano_id)

    # Verificar se o plano pertence ao paciente
    if plano.paciente_id != paciente.id:
        abort(404)

    # Verificar se veio do catálogo ou é personalizado
    tratamento_id = request.form.get("tratamento_id", type=int)
    descricao = request.form.get("descricao", "")

    # Se selecionou tratamento do catálogo, mas não especificou descrição
    if tratamento_id and not descricao:
        tratamento = Tratamento.query.get_or_404(tratamento_id)
        descricao = tratamento.nome

    # Verificar se a descrição foi fornecida
    if not descricao:
        flash("A descrição do procedimento é obrigatória.", "danger")
        return redirect(
            url_for("pacientes.visualizar_plano", paciente_id=paciente.id, plano_id=plano.id)
        )

    # Criar novo procedimento
    procedimento = Procedimento(
        plano_id=plano.id,
        tratamento_id=tratamento_id,
        descricao=descricao,
        dente=request.form.get("dente", ""),
        valor=request.form.get("valor", type=float) or 0.0,
        status=request.form.get("status", "Pendente"),
        data_prevista=(
            datetime.strptime(request.form.get("data_prevista"), "%Y-%m-%d").date()
            if request.form.get("data_prevista")
            else None
        ),
        data_realizado=(
            datetime.strptime(request.form.get("data_realizado"), "%Y-%m-%d").date()
            if request.form.get("data_realizado")
            else None
        ),
        observacoes=request.form.get("observacoes", ""),
    )

    db.session.add(procedimento)

    # Atualizar o orçamento total do plano
    plano.orcamento_total += procedimento.valor

    db.session.commit()

    flash("Procedimento adicionado com sucesso!", "success")
    return redirect(
        url_for("pacientes.visualizar_plano", paciente_id=paciente.id, plano_id=plano.id)
    )


@pacientes.route("/api/tratamentos/por-categoria/<int:categoria_id>")
@debug_login_optional
def tratamentos_por_categoria(categoria_id: int):  # Add type hint
    """Endpoint AJAX para buscar tratamentos de uma categoria"""
    tratamentos = Tratamento.query.filter_by(categoria_id=categoria_id, ativo=True).all()
    return jsonify(
        [
            {
                "id": t.id,
                "nome": t.nome,
                "preco": t.preco,
                "duracao": t.duracao_estimada,
            }
            for t in tratamentos
        ]
    )


@pacientes.route("/pacientes/<int:paciente_id>/historico")
@debug_login_optional
def listar_historico(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    historicos = (
        Historico.query.filter_by(paciente_id=paciente.id).order_by(Historico.data.desc()).all()
    )

    return render_template(
        "pacientes/historico.html",
        paciente=paciente,
        historicos=historicos,
        aba_ativa="historico",
    )


@pacientes.route("/pacientes/<int:paciente_id>/historico/novo", methods=["GET", "POST"])
@debug_login_optional
def novo_historico(paciente_id: int):  # Add type hint
    paciente = Paciente.query.get_or_404(paciente_id)
    form = HistoricoForm()

    if form.validate_on_submit():
        historico = Historico(
            paciente_id=paciente.id,
            dentista_id=current_user.id,
            descricao=form.descricao.data,
            procedimentos_realizados=form.procedimentos_realizados.data,
            observacoes=form.observacoes.data,
        )
        db.session.add(historico)
        db.session.commit()

        flash("Histórico adicionado com sucesso!", "success")
        return redirect(url_for("pacientes.listar_historico", paciente_id=paciente.id))

    return render_template(
        "pacientes/formulario_historico.html",
        form=form,
        paciente=paciente,
        aba_ativa="historico",
    )


@pacientes.route("/pacientes/aniversarios")
@debug_login_optional
def aniversarios():
    """
    Exibe os pacientes que fazem aniversário no mês atual.
    """
    mes_atual = datetime.now().month
    pacientes_mes = (
        Paciente.query.filter(db.extract("month", Paciente.data_nascimento) == mes_atual)
        .order_by(db.extract("day", Paciente.data_nascimento))
        .all()
    )
    nome_mes = month_name[mes_atual].capitalize()
    is_mobile = getattr(request, "MOBILE", False)
    if is_mobile:
        return render_template(
            "mobile/aniversarios.html",
            pacientes=pacientes_mes,
            nome_mes=nome_mes,
        )
    else:
        return render_template(
            "pacientes/aniversarios.html",
            pacientes=pacientes_mes,
            nome_mes=nome_mes,
        )


# Rota para buscar pacientes por nome (para autocomplete)
@pacientes.route("/search_pacientes", methods=["GET"])
@debug_login_optional
def search_pacientes() -> Response:
    search_term = request.args.get("term", "")
    if len(search_term) < 2:  # Minimum characters to search
        return jsonify([])

    pacientes_encontrados = (
        Paciente.query.filter(Paciente.nome.ilike(f"%{search_term}%"))
        .limit(10)  # Limit results for performance
        .all()
    )
    nomes_pacientes = [paciente.nome for paciente in pacientes_encontrados]
    return jsonify(nomes_pacientes)


@pacientes.route("/api/pacientes/<int:paciente_id>/dados-receita")
@debug_login_optional
def obter_dados_paciente_receita(paciente_id: int):
    """API para obter dados básicos do paciente para uso em receitas."""
    try:
        paciente = Paciente.query.get_or_404(paciente_id)  # Formatar data de nascimento
        data_nascimento = ""
        if paciente.data_nascimento:
            data_nascimento = paciente.data_nascimento.strftime("%d/%m/%Y")

        dados = {
            "id": paciente.id,
            "nome": paciente.nome,
            "data_nascimento": data_nascimento,
            "cpf": paciente.cpf or "",
            "telefone": paciente.telefone or "",
            "email": paciente.email or "",
        }

        return jsonify(dados)
    except Exception:
        return jsonify({"error": "Paciente não encontrado"}), 404
