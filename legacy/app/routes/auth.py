from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm

# Removed unused imports but left them commented for reference in case needed later
# from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from app import extensions  # Changed from 'from app.extensions import users_db'
from app.models.user import User

# Create a base form with CSRF disabled for all forms


class CSRFDisabledForm(FlaskForm):
    class Meta:
        csrf = False


auth = Blueprint("auth", __name__)

# Formulário de login


class LoginForm(CSRFDisabledForm):
    username = StringField("Nome de usuário", validators=[DataRequired()])
    password = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")


# Formulário de cadastro


class RegistrationForm(CSRFDisabledForm):
    username = StringField("Nome de usuário", validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    nome_completo = StringField("Nome completo", validators=[DataRequired(), Length(max=128)])
    cro = StringField(
        "CRO",
        validators=[
            Length(min=4, max=20, message="CRO deve ter entre 4 e 20 caracteres"),
            Optional(),
        ],
    )
    cargo = SelectField(
        "Cargo",
        choices=[
            ("dentista", "Dentista"),
            ("secretaria", "Secretária/Recepcionista"),
            ("admin", "Administrador"),
        ],
    )
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirmar senha", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Cadastrar")

    def validate(self, extra_validators=None) -> bool:
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False
        if self.cargo.data == "dentista" and not self.cro.data:
            self.cro.errors.append("CRO é obrigatório para dentistas.")
            return False
        return True


@auth.route("/login", methods=["GET", "POST"])
def login() -> str:
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        # Use extensions.users_db to ensure the initialized session is used
        user = extensions.users_db.query(User).filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))
        flash("Nome de usuário ou senha incorretos", "danger")

    return render_template("auth/login.html", form=form)


@auth.route("/logout")
@login_required
def logout() -> str:
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))


@auth.route("/register", methods=["GET", "POST"])
@login_required
def register() -> str:
    form = RegistrationForm()
    if form.validate_on_submit():
        # Use extensions.users_db for queries and session operations
        if extensions.users_db.query(User).filter_by(username=form.username.data).first():
            flash("Nome de usuário já existe", "danger")
            return render_template("auth/register.html", form=form)

        if extensions.users_db.query(User).filter_by(email=form.email.data).first():
            flash("Email já está cadastrado", "danger")
            return render_template("auth/register.html", form=form)

        # Cria novo usuário
        user = User(
            username=form.username.data,
            email=form.email.data,
            nome_completo=form.nome_completo.data,
            cro=form.cro.data or None,
            cargo=form.cargo.data,
        )
        user.set_password(form.password.data)

        extensions.users_db.add(user)
        extensions.users_db.commit()

        flash("Usuário cadastrado com sucesso!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html", form=form)
