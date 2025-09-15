from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class PacienteForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=100)])
    data_nascimento = StringField("Data de Nascimento", validators=[Optional(), Length(max=10)])
    sexo = SelectField(
        "Sexo",
        choices=[
            ("", "Selecione"),
            ("Masculino", "Masculino"),
            ("Feminino", "Feminino"),
        ],
    )
    cpf = StringField("CPF", validators=[Optional(), Length(max=14)])
    telefone = StringField("Telefone", validators=[Optional(), Length(max=20)])
    celular = StringField("Celular", validators=[Optional(), Length(max=20)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    submit = SubmitField("Salvar")


class FichaForm(FlaskForm):
    responsavel = StringField("Responsável", validators=[Optional(), Length(max=100)])
    contato_emergencia = StringField("Contato Emergência", validators=[Optional(), Length(max=100)])
    convenio = StringField("Convênio", validators=[Optional(), Length(max=100)])
    numero_convenio = StringField("Número Convênio", validators=[Optional(), Length(max=50)])
    alergias = TextAreaField("Alergias", validators=[Optional()])
    observacoes = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Salvar")


class AnamneseForm(FlaskForm):
    historico_medico = TextAreaField("Histórico Médico", validators=[Optional()])
    medicamentos_uso = TextAreaField("Medicamentos em Uso", validators=[Optional()])
    cirurgias_previas = TextAreaField("Cirurgias Prévias", validators=[Optional()])
    doencas_cronicas = TextAreaField("Doenças Crônicas", validators=[Optional()])
    habitos = TextAreaField("Hábitos", validators=[Optional()])
    problemas_dentarios = TextAreaField("Problemas Dentários", validators=[Optional()])
    ultima_visita_dentista = StringField("Última Visita", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Salvar")


class PlanoForm(FlaskForm):
    descricao = TextAreaField("Descrição", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[
            ("Pendente", "Pendente"),
            ("Em andamento", "Em andamento"),
            ("Concluído", "Concluído"),
            ("Cancelado", "Cancelado"),
        ],
    )
    observacoes = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Salvar")


class ProcedimentoForm(FlaskForm):
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)])
    dente = StringField("Dente", validators=[Optional(), Length(max=100)])
    valor = FloatField("Valor", validators=[Optional()])
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
    observacoes = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Salvar")


class HistoricoForm(FlaskForm):
    descricao = TextAreaField("Descrição", validators=[DataRequired()])
    procedimentos_realizados = TextAreaField("Procedimentos Realizados", validators=[Optional()])
    observacoes = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Salvar")


class FinanceiroForm(FlaskForm):
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)])
    valor = FloatField("Valor", validators=[DataRequired()])
    tipo = SelectField("Tipo", choices=[("Crédito", "Crédito"), ("Débito", "Débito")])
    forma_pagamento = SelectField(
        "Forma Pagamento",
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
    data_pagamento = DateField("Data Pagamento", validators=[Optional()])
    submit = SubmitField("Salvar")
