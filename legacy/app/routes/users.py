from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import HiddenField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

from app import extensions
from app.decorators import debug_login_optional
from app.models.user import User

users = Blueprint("users", __name__)


# Formulário base com CSRF desabilitado
class CSRFDisabledForm(FlaskForm):
    class Meta(FlaskForm.Meta):  # type: ignore[misc]
        # Pylance might expect a cached_property; for runtime, WTForms reads a simple flag.
        csrf = False  # type: ignore[assignment]


# Formulário para criar/editar usuário
class UserForm(CSRFDisabledForm):
    username = StringField("Nome de usuário", validators=[DataRequired(), Length(min=3, max=64)])
    nome_completo = StringField("Nome completo", validators=[DataRequired(), Length(max=128)])
    cro = StringField(
        "CRO",
        validators=[
            Length(min=4, max=20, message="CRO deve ter entre 4 e 20 caracteres"),
            Optional(),
        ],
    )
    nome_profissional = StringField(
        "Nome profissional", validators=[DataRequired(), Length(max=120)]
    )
    password = PasswordField("Senha", validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField("Confirmar senha", validators=[EqualTo("password")])
    cargo = SelectField(
        "Cargo",
        choices=[
            ("dentista", "Dentista"),
            ("secretaria", "Secretária/Recepcionista"),
            ("admin", "Administrador"),
        ],
        validators=[DataRequired()],
    )
    id = HiddenField("ID")
    submit = SubmitField("Salvar")


# Formulário para edição de perfil (sem o campo cargo)
class UserProfileForm(CSRFDisabledForm):
    username = StringField("Nome de usuário", validators=[DataRequired(), Length(min=3, max=64)])
    nome_completo = StringField("Nome completo", validators=[DataRequired(), Length(max=128)])
    cro = StringField(
        "CRO",
        validators=[
            Length(min=4, max=20, message="CRO deve ter entre 4 e 20 caracteres"),
            Optional(),
        ],
    )
    nome_profissional = StringField(
        "Nome profissional", validators=[DataRequired(), Length(max=120)]
    )
    password = PasswordField("Senha", validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField("Confirmar senha", validators=[EqualTo("password")])
    id = HiddenField("ID")
    submit = SubmitField("Salvar")


def admin_required() -> None:
    if not current_user.is_authenticated or current_user.cargo != "admin":
        abort(403)


@users.route("/")
@debug_login_optional
def listar_usuarios():
    # Lista todos os usuários
    usuarios = extensions.users_db.query(User).all()
    return render_template("users/lista_usuarios.html", usuarios=usuarios)


@users.route("/novo", methods=["GET", "POST"])
@debug_login_optional
def novo_usuario():
    admin_required()
    form = UserForm()

    if form.validate_on_submit():
        # Verifica se o nome de usuário já existe
        if extensions.users_db.query(User).filter_by(username=form.username.data).first():
            flash("Nome de usuário já existe", "danger")
            return render_template(
                "users/formulario_usuario.html", form=form, titulo="Novo Usuário"
            )

        # Verifica se o CRO já existe (se informado)
        if form.cro.data:
            if extensions.users_db.query(User).filter_by(cro=form.cro.data).first():
                flash("CRO já está cadastrado", "danger")
                return render_template(
                    "users/formulario_usuario.html", form=form, titulo="Novo Usuário"
                )

        # Cria novo usuário
        novo_usuario = User(
            username=form.username.data,
            nome_completo=form.nome_completo.data,
            cro=form.cro.data or None,
            nome_profissional=form.nome_profissional.data,
            cargo=form.cargo.data,  # Salvar o cargo
            is_active=True,
        )

        # Definir a senha apenas se for fornecida
        if form.password.data:
            novo_usuario.set_password(form.password.data)
        else:
            flash("A senha é obrigatória para novos usuários", "danger")
            return render_template(
                "users/formulario_usuario.html", form=form, titulo="Novo Usuário"
            )

        extensions.users_db.add(novo_usuario)
        extensions.users_db.commit()

        flash("Usuário criado com sucesso!", "success")
        return redirect(url_for("users.listar_usuarios"))

    return render_template("users/formulario_usuario.html", form=form, titulo="Novo Usuário")


@users.route("/editar/<int:id>", methods=["GET", "POST"])
@debug_login_optional
def editar_usuario(id: int):
    admin_required()
    usuario = extensions.users_db.query(User).get(id)
    if usuario is None:
        abort(404)

    # Inicializa o formulário com os dados do usuário
    if request.method == "GET":
        form = UserForm(
            id=usuario.id,
            username=usuario.username,
            nome_completo=usuario.nome_completo,
            cro=usuario.cro,
            nome_profissional=usuario.nome_profissional,
            cargo=usuario.cargo,  # Usa o campo cargo diretamente
        )
    else:
        form = UserForm()

    if form.validate_on_submit():
        # Verifica se o username já existe para outro usuário
        existing_user = (
            extensions.users_db.query(User).filter_by(username=form.username.data).first()
        )
        if existing_user and existing_user.id != usuario.id:
            flash("Nome de usuário já existe", "danger")
            return render_template(
                "users/formulario_usuario.html", form=form, titulo="Editar Usuário"
            )

        # Verifica se o CRO já existe para outro usuário (se informado)
        if form.cro.data:
            existing_cro = extensions.users_db.query(User).filter_by(cro=form.cro.data).first()
            if existing_cro and existing_cro.id != usuario.id:
                flash("CRO já está cadastrado", "danger")
                return render_template(
                    "users/formulario_usuario.html", form=form, titulo="Editar Usuário"
                )

        # Atualiza os dados do usuário
        usuario.username = form.username.data
        usuario.nome_completo = form.nome_completo.data
        usuario.cro = form.cro.data or None
        usuario.nome_profissional = form.nome_profissional.data
        usuario.cargo = form.cargo.data  # Salvar o cargo
        # Removido is_admin, pois agora usamos apenas o campo cargo
        usuario.is_active = True

        # Atualiza a senha apenas se for fornecida
        if form.password.data:
            usuario.set_password(form.password.data)

        extensions.users_db.commit()
        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for("users.listar_usuarios"))

    return render_template("users/formulario_usuario.html", form=form, titulo="Editar Usuário")


@users.route("/toggle/<int:user_id>", methods=["POST"])
@debug_login_optional
def toggle_user(user_id: int):
    # Somente admin pode ativar/desativar
    if not current_user.is_authenticated or current_user.cargo != "admin":
        abort(403)
    usuario = extensions.users_db.query(User).get(user_id)
    if usuario is None:
        abort(404)
    # Evitar desativar a si mesmo, opcional
    if usuario.id == getattr(current_user, "id", None):
        flash("Você não pode desativar seu próprio usuário.", "warning")
        return redirect(url_for("users.listar_usuarios"))
    try:
        usuario.is_active = not bool(usuario.is_active)
        extensions.users_db.commit()
        flash(
            ("Usuário ativado." if usuario.is_active else "Usuário desativado."),
            "success",
        )
    except Exception:
        extensions.users_db.rollback()
        flash("Falha ao alterar status do usuário.", "danger")
    return redirect(url_for("users.listar_usuarios"))


@users.route("/excluir/<int:user_id>", methods=["POST"])
@debug_login_optional
def delete_user(user_id: int):
    admin_required()
    user_to_delete = extensions.users_db.query(User).get(user_id)
    if user_to_delete is None:
        abort(404)

    if user_to_delete.id == current_user.id:
        flash("Você não pode excluir seu próprio usuário.", "danger")
        return redirect(url_for("users.listar_usuarios"))

    # Exclui apenas o usuário do banco users.db
    extensions.users_db.delete(user_to_delete)
    extensions.users_db.commit()
    flash("Usuário excluído com sucesso!", "success")
    return redirect(url_for("users.listar_usuarios"))


@users.route("/perfil", methods=["GET", "POST"])
@debug_login_optional
def meu_perfil():
    usuario = extensions.users_db.query(User).get(current_user.id)

    # Inicializa o formulário com os dados do usuário
    if request.method == "GET":
        form = UserProfileForm(
            id=usuario.id,
            username=usuario.username,
            nome_completo=usuario.nome_completo,
            cro=usuario.cro,
            nome_profissional=usuario.nome_profissional,
        )
    else:
        form = UserProfileForm()

    if form.validate_on_submit():
        # Verifica se o username já existe para outro usuário
        existing_user = (
            extensions.users_db.query(User).filter_by(username=form.username.data).first()
        )
        if existing_user and existing_user.id != usuario.id:
            flash("Nome de usuário já existe", "danger")
            return render_template("users/meu_perfil.html", form=form)

        # Verifica se o CRO já existe para outro usuário (se informado)
        if form.cro.data:
            existing_cro = extensions.users_db.query(User).filter_by(cro=form.cro.data).first()
            if existing_cro and existing_cro.id != usuario.id:
                flash("CRO já está cadastrado", "danger")
                return render_template("users/meu_perfil.html", form=form)

        # Atualiza os dados do usuário
        usuario.username = form.username.data
        usuario.nome_completo = form.nome_completo.data
        usuario.cro = form.cro.data or None
        usuario.nome_profissional = form.nome_profissional.data

        # Atualiza a senha apenas se for fornecida
        if form.password.data:
            usuario.set_password(form.password.data)

        extensions.users_db.commit()
        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("users.meu_perfil"))

    return render_template("users/meu_perfil.html", form=form)
