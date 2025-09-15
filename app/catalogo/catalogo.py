from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db
from ..auth.auth import require_roles
from ..utils_db import get_or_404
from .models import CategoriaTratamento, Tratamento

catalogo_bp = Blueprint(
    "catalogo",
    __name__,
    template_folder=".",
)


@catalogo_bp.route("/")
def listar():  # simples listagem inicial
    categorias = CategoriaTratamento.query.order_by(CategoriaTratamento.nome).all()
    return render_template("catalogo/lista.html", categorias=categorias)


# ----------------- CATEGORIAS -----------------
@catalogo_bp.route("/categorias/nova", methods=["GET", "POST"])
@require_roles("admin", "gerente")
def nova_categoria():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("Nome obrigatório", "danger")
        else:
            cat = CategoriaTratamento()
            cat.nome = nome
            cat.descricao = request.form.get("descricao")
            db.session.add(cat)
            db.session.commit()
            flash("Categoria criada", "success")
            return redirect(url_for("catalogo.listar"))
    return render_template("catalogo/form_categoria.html")


@catalogo_bp.route("/categorias/<int:cat_id>/editar", methods=["GET", "POST"])
@require_roles("admin", "gerente")
def editar_categoria(cat_id: int):
    cat = get_or_404(CategoriaTratamento, cat_id)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("Nome obrigatório", "danger")
        else:
            cat.nome = nome
            cat.descricao = request.form.get("descricao")
            db.session.commit()
            flash("Categoria atualizada", "success")
            return redirect(url_for("catalogo.listar"))
    return render_template("catalogo/form_categoria.html", cat=cat)


@catalogo_bp.route("/categorias/<int:cat_id>/excluir", methods=["POST"])
@require_roles("admin")
def excluir_categoria(cat_id: int):
    cat = get_or_404(CategoriaTratamento, cat_id)
    if cat.tratamentos.count() > 0:
        flash("Categoria com tratamentos não pode ser removida", "warning")
        return redirect(url_for("catalogo.listar"))
    db.session.delete(cat)
    db.session.commit()
    flash("Categoria excluída", "success")
    return redirect(url_for("catalogo.listar"))


# ----------------- TRATAMENTOS -----------------
@catalogo_bp.route("/categorias/<int:cat_id>/tratamentos/novo", methods=["GET", "POST"])
@require_roles("admin", "gerente", "dentista")
def novo_tratamento(cat_id: int):
    cat = get_or_404(CategoriaTratamento, cat_id)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        preco_raw = request.form.get("preco", "0").replace(",", ".")
        try:
            preco = float(preco_raw)
        except ValueError:
            preco = 0.0
        if not nome:
            flash("Nome obrigatório", "danger")
        else:
            t = Tratamento()
            t.categoria_id = cat.id
            t.nome = nome
            t.descricao = request.form.get("descricao")
            t.preco = preco
            t.duracao_estimada = request.form.get("duracao_estimada")
            db.session.add(t)
            db.session.commit()
            flash("Tratamento criado", "success")
            return redirect(url_for("catalogo.ver_categoria", cat_id=cat.id))
    return render_template("catalogo/form_tratamento.html", cat=cat)


@catalogo_bp.route("/tratamentos/<int:trat_id>/editar", methods=["GET", "POST"])
@require_roles("admin", "gerente", "dentista")
def editar_tratamento(trat_id: int):
    t = get_or_404(Tratamento, trat_id)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        preco_raw = request.form.get("preco", "0").replace(",", ".")
        try:
            preco = float(preco_raw)
        except ValueError:
            preco = 0.0
        if not nome:
            flash("Nome obrigatório", "danger")
        else:
            t.nome = nome
            t.descricao = request.form.get("descricao")
            t.preco = preco
            t.duracao_estimada = request.form.get("duracao_estimada")
            db.session.commit()
            flash("Tratamento atualizado", "success")
            return redirect(url_for("catalogo.ver_categoria", cat_id=t.categoria_id))
    return render_template("catalogo/form_tratamento.html", trat=t)


@catalogo_bp.route("/tratamentos/<int:trat_id>/excluir", methods=["POST"])
@require_roles("admin", "gerente")
def excluir_tratamento(trat_id: int):
    t = get_or_404(Tratamento, trat_id)
    cat_id = t.categoria_id
    db.session.delete(t)
    db.session.commit()
    flash("Tratamento excluído", "success")
    return redirect(url_for("catalogo.ver_categoria", cat_id=cat_id))


@catalogo_bp.route("/categorias/<int:cat_id>")
def ver_categoria(cat_id: int):
    cat = get_or_404(CategoriaTratamento, cat_id)
    tratamentos = Tratamento.query.filter_by(categoria_id=cat.id).order_by(Tratamento.nome).all()
    return render_template("catalogo/ver_categoria.html", cat=cat, tratamentos=tratamentos)
