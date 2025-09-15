from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, session, url_for
from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

from .. import db
from ..auth.models import User
from ..utils_db import get_or_404

users_bp = Blueprint("users", __name__, template_folder=".")


def current_user():  # simples wrapper
    uid = session.get("uid")
    if not uid:
        return None
    return db.session.get(User, uid)


def admin_required():  # pragma: no cover - pequena função
    user = current_user()
    if not user or user.cargo != "admin":  # exige admin
        abort(403)


class UserForm(FlaskForm):  # campos principais
    username = StringField("Usuário", validators=[DataRequired(), Length(min=3, max=64)])
    nome_completo = StringField("Nome completo", validators=[DataRequired(), Length(max=128)])
    cro = StringField("CRO", validators=[Optional(), Length(max=20)])
    nome_profissional = StringField("Nome profissional", validators=[Optional(), Length(max=120)])
    cargo = SelectField(
        "Cargo",
        choices=[
            ("dentista", "Dentista"),
            ("secretaria", "Secretaria"),
            ("admin", "Admin"),
        ],
    )
    password = PasswordField("Senha", validators=[Optional(), Length(min=4)])
    confirm = PasswordField(
        "Confirmar",
        validators=[EqualTo("password", message="Senhas divergentes")],
    )
    submit = SubmitField("Salvar")


@users_bp.route("/")
def listar():
    admin_required()
    usuarios = User.query.order_by(User.username).all()
    return render_template("users/lista.html", usuarios=usuarios)


@users_bp.route("/novo", methods=["GET", "POST"])
def novo():
    admin_required()
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Usuário já existe", "danger")
            return render_template("users/form.html", form=form)
        if form.cro.data and User.query.filter_by(cro=form.cro.data).first():
            flash("CRO já cadastrado", "danger")
            return render_template("users/form.html", form=form)
        u = User()
        u.username = form.username.data
        u.nome_completo = form.nome_completo.data
        u.cro = form.cro.data or None
        u.nome_profissional = form.nome_profissional.data or form.nome_completo.data
        u.cargo = form.cargo.data
        if form.password.data:
            u.set_password(form.password.data)
        else:
            u.set_password("1234")  # default simples dev
        db.session.add(u)
        db.session.commit()
        flash("Usuário criado", "success")
        return redirect(url_for("users.listar"))
    return render_template("users/form.html", form=form)


@users_bp.route("/<int:uid>/editar", methods=["GET", "POST"])
def editar(uid: int):
    admin_required()
    user = get_or_404(User, uid)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        # conflitos
        existing = User.query.filter_by(username=form.username.data).first()
        if existing and existing.id != user.id:
            flash("Usuário já existe", "danger")
            return render_template("users/form.html", form=form)
        if form.cro.data:
            existing_cro = User.query.filter_by(cro=form.cro.data).first()
            if existing_cro and existing_cro.id != user.id:
                flash("CRO já cadastrado", "danger")
                return render_template("users/form.html", form=form)
        user.username = form.username.data
        user.nome_completo = form.nome_completo.data
        user.cro = form.cro.data or None
        user.nome_profissional = form.nome_profissional.data or form.nome_completo.data
        user.cargo = form.cargo.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash("Usuário atualizado", "success")
        return redirect(url_for("users.listar"))
    return render_template("users/form.html", form=form)


@users_bp.route("/<int:uid>/toggle", methods=["POST"])
def toggle(uid: int):
    admin_required()
    user = get_or_404(User, uid)
    # Alterna is_active_db (pode ser None => True)
    user.is_active = not bool(user.is_active)
    db.session.commit()
    flash("Status alterado", "info")
    return redirect(url_for("users.listar"))


@users_bp.route("/<int:uid>/excluir", methods=["POST"])
def excluir(uid: int):
    admin_required()
    user = get_or_404(User, uid)
    db.session.delete(user)
    db.session.commit()
    flash("Usuário removido", "success")
    return redirect(url_for("users.listar"))


@users_bp.route("/perfil")
def perfil():
    u = current_user()
    if not u:
        abort(403)
    return render_template("users/perfil.html", user=u)
