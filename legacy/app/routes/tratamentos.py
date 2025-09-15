from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.decorators import debug_login_optional
from app.extensions import db
from app.models.tratamento import CategoriaTratamento, Tratamento


class CSRFDisabledForm(FlaskForm):
    class Meta:
        csrf = False


tratamentos = Blueprint("tratamentos", __name__)


class CategoriaForm(CSRFDisabledForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=100)])
    descricao = TextAreaField("Descrição", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Salvar")


class TratamentoForm(CSRFDisabledForm):
    categoria_id = SelectField("Categoria", coerce=int, validators=[DataRequired()])
    nome = StringField("Nome do Procedimento", validators=[DataRequired(), Length(max=200)])
    descricao = TextAreaField("Descrição", validators=[Optional()])
    preco = FloatField("Preço (R$)", validators=[DataRequired(), NumberRange(min=0)])
    duracao_estimada = StringField("Duração Estimada", validators=[Optional(), Length(max=50)])
    ativo = BooleanField("Ativo")
    submit = SubmitField("Salvar")


@tratamentos.route("/")
@debug_login_optional
def lista_categorias():
    categorias = CategoriaTratamento.query.all()
    return render_template("tratamentos/lista_categorias.html", categorias=categorias)


@tratamentos.route("/categoria/nova", methods=["GET", "POST"])
@debug_login_optional
def nova_categoria():
    form = CategoriaForm()
    if form.validate_on_submit():
        categoria = CategoriaTratamento(nome=form.nome.data, descricao=form.descricao.data)
        db.session.add(categoria)
        db.session.commit()
        flash("Categoria criada com sucesso!", "success")
        return redirect(url_for("tratamentos.lista_categorias"))

    if request.method == "POST" and not form.validate_on_submit():
        flash("Erro ao criar categoria. Verifique os dados informados.", "danger")

    return render_template(
        "tratamentos/formulario_categoria.html", form=form, titulo="Nova Categoria"
    )


@tratamentos.route("/categoria/<int:categoria_id>/editar", methods=["GET", "POST"])
@debug_login_optional
def editar_categoria(categoria_id):
    categoria = CategoriaTratamento.query.get_or_404(categoria_id)
    form = CategoriaForm()

    if form.validate_on_submit():
        categoria.nome = form.nome.data
        categoria.descricao = form.descricao.data
        db.session.commit()
        flash("Categoria atualizada com sucesso!", "success")
        return redirect(url_for("tratamentos.lista_categorias"))

    if request.method == "GET":
        form.nome.data = categoria.nome
        form.descricao.data = categoria.descricao

    return render_template(
        "tratamentos/formulario_categoria.html", form=form, titulo="Editar Categoria"
    )


@tratamentos.route("/categoria/<int:categoria_id>/excluir", methods=["POST"])
@debug_login_optional
def excluir_categoria(categoria_id):
    categoria = CategoriaTratamento.query.get_or_404(categoria_id)

    # Verificar se há tratamentos vinculados a esta categoria
    if categoria.tratamentos:
        flash("Não é possível excluir uma categoria com tratamentos vinculados.", "danger")
        return redirect(url_for("tratamentos.lista_categorias"))

    db.session.delete(categoria)
    db.session.commit()
    flash("Categoria excluída com sucesso!", "success")
    return redirect(url_for("tratamentos.lista_categorias"))


@tratamentos.route("/categoria/<int:categoria_id>")
@debug_login_optional
def visualizar_categoria(categoria_id):
    categoria = CategoriaTratamento.query.get_or_404(categoria_id)
    tratamentos = (
        Tratamento.query.filter_by(categoria_id=categoria_id).order_by(Tratamento.nome).all()
    )
    return render_template(
        "tratamentos/visualizar_categoria.html",
        categoria=categoria,
        tratamentos=tratamentos,
    )


@tratamentos.route("/tratamento/novo", methods=["GET", "POST"])
@debug_login_optional
def novo_tratamento():
    form = TratamentoForm()

    # Carregar as opções de categorias
    form.categoria_id.choices = [
        (c.id, c.nome) for c in CategoriaTratamento.query.order_by(CategoriaTratamento.nome).all()
    ]

    if form.validate_on_submit():
        tratamento = Tratamento(
            categoria_id=form.categoria_id.data,
            nome=form.nome.data,
            descricao=form.descricao.data,
            preco=form.preco.data,
            duracao_estimada=form.duracao_estimada.data,
            ativo=form.ativo.data,
        )
        db.session.add(tratamento)
        db.session.commit()
        flash("Tratamento criado com sucesso!", "success")
        return redirect(
            url_for("tratamentos.visualizar_categoria", categoria_id=form.categoria_id.data)
        )

    if request.method == "POST" and not form.validate_on_submit():
        flash("Erro ao criar tratamento. Verifique os dados informados.", "danger")

    return render_template(
        "tratamentos/formulario_tratamento.html", form=form, titulo="Novo Tratamento"
    )


@tratamentos.route("/tratamento/<int:tratamento_id>/editar", methods=["GET", "POST"])
@debug_login_optional
def editar_tratamento(tratamento_id):
    tratamento = Tratamento.query.get_or_404(tratamento_id)
    form = TratamentoForm()

    # Carregar as opções de categorias
    form.categoria_id.choices = [
        (c.id, c.nome) for c in CategoriaTratamento.query.order_by(CategoriaTratamento.nome).all()
    ]

    if form.validate_on_submit():
        tratamento.categoria_id = form.categoria_id.data
        tratamento.nome = form.nome.data
        tratamento.descricao = form.descricao.data
        tratamento.preco = form.preco.data
        tratamento.duracao_estimada = form.duracao_estimada.data
        tratamento.ativo = form.ativo.data
        db.session.commit()
        flash("Tratamento atualizado com sucesso!", "success")
        return redirect(
            url_for("tratamentos.visualizar_categoria", categoria_id=tratamento.categoria_id)
        )

    if request.method == "GET":
        form.categoria_id.data = tratamento.categoria_id
        form.nome.data = tratamento.nome
        form.descricao.data = tratamento.descricao
        form.preco.data = tratamento.preco
        form.duracao_estimada.data = tratamento.duracao_estimada
        form.ativo.data = tratamento.ativo

    return render_template(
        "tratamentos/formulario_tratamento.html", form=form, titulo="Editar Tratamento"
    )


@tratamentos.route("/tratamento/<int:tratamento_id>/excluir", methods=["POST"])
@debug_login_optional
def excluir_tratamento(tratamento_id):
    tratamento = Tratamento.query.get_or_404(tratamento_id)
    categoria_id = tratamento.categoria_id

    db.session.delete(tratamento)
    db.session.commit()
    flash("Tratamento excluído com sucesso!", "success")
    return redirect(url_for("tratamentos.visualizar_categoria", categoria_id=categoria_id))


@tratamentos.route("/lista")
@debug_login_optional
def lista_completa():
    # Buscar todas as categorias e seus respectivos tratamentos
    categorias = CategoriaTratamento.query.order_by(CategoriaTratamento.nome).all()
    return render_template("tratamentos/lista_completa.html", categorias=categorias)
