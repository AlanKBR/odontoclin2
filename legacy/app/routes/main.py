import os

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Email, Length, Optional

from app.decorators import debug_admin_optional, debug_login_optional
from app.extensions import db
from app.models.clinica import Clinica

main = Blueprint("main", __name__)


class ClinicaForm(FlaskForm):
    nome = StringField("Nome da Clínica", validators=[Length(max=200)])
    cro_clinica = StringField("CRO da Clínica", validators=[Optional(), Length(max=50)])
    endereco = TextAreaField("Endereço", validators=[Optional(), Length(max=300)])
    telefone = StringField("Telefone", validators=[Optional(), Length(max=20)])
    celular = StringField("Celular", validators=[Optional(), Length(max=20)])
    email = StringField("E-mail", validators=[Optional(), Email(), Length(max=100)])
    site = StringField("Site", validators=[Optional(), Length(max=100)])
    cep = StringField("CEP", validators=[Optional(), Length(max=10)])
    cidade = StringField("Cidade", validators=[Optional(), Length(max=100)])
    estado = StringField("Estado", validators=[Optional(), Length(max=2)])
    cnpj = StringField("CNPJ", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Salvar Configurações")


@main.route("/")
def index() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("agenda.index"))
    # Em modo debug, redireciona direto para a Agenda (login automático acontecerá lá)
    from flask import current_app

    if current_app.debug:
        return redirect(url_for("agenda.index"))
    return redirect(url_for("auth.login"))


@main.route("/dashboard")
@debug_login_optional
def dashboard() -> ResponseReturnValue:
    # Detecta se é um dispositivo móvel
    is_mobile = getattr(request, "MOBILE", False)

    if is_mobile:
        # Dados específicos para mobile (simplificados)
        context = {
            "pacientes_count": 125,  # Substituir por dados reais do banco
            "agendamentos_hoje": 8,
            "tratamentos_andamento": 23,
            "receitas_mes": 47,
            "ultimas_atividades": [],  # Implementar busca de atividades
            "agendamentos_hoje_lista": [],  # Implementar busca de agendamentos
        }
        return render_template("mobile/dashboard.html", **context)
    else:
        return render_template("main/dashboard.html")


@main.route("/settings", methods=["GET", "POST"])
@debug_admin_optional
def settings() -> ResponseReturnValue:
    # Obter a instância da clínica
    clinica = Clinica.get_instance()

    # Criar o formulário e preenchê-lo com os dados atuais
    form = ClinicaForm(obj=clinica)

    if form.validate_on_submit():
        # Atualizar os dados da clínica
        form.populate_obj(clinica)
        db.session.commit()
        flash("Configurações da clínica atualizadas com sucesso!", "success")
        return redirect(url_for("main.settings"))

    return render_template("main/settings.html", form=form, clinica=clinica)


@main.route("/calculadora-anestesico")
@debug_login_optional
def calculadora_anestesico():
    return render_template("main/calculadora_anestesico.html")


@main.route("/sidebar-demo")
@debug_login_optional
def sidebar_demo():
    """Demonstração das funcionalidades da nova sidebar moderna"""
    return render_template("sidebar_demo.html")


@main.route("/upload_logo", methods=["POST"])
@debug_login_optional
def upload_logo() -> ResponseReturnValue:
    if "logo" not in request.files:
        flash("Nenhum arquivo enviado.", "warning")
        return redirect(url_for("main.settings"))
    file = request.files["logo"]
    if not file.filename or file.filename == "":
        flash("Nenhum arquivo selecionado.", "warning")
        return redirect(url_for("main.settings"))
    if file and file.filename and file.filename.lower().endswith(".png"):
        filename = "clinic_logo.png"
        upload_folder = os.path.join(current_app.root_path, "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        flash("Logo da clínica enviada com sucesso!", "success")
    else:
        flash("Por favor, envie um arquivo PNG.", "danger")
    return redirect(url_for("main.settings"))


@main.route("/static/uploads/<filename>")
def uploaded_logo(filename):
    upload_folder = os.path.join(current_app.root_path, "static", "uploads")
    return send_from_directory(upload_folder, filename)


@main.route("/load-ai")
@debug_login_optional
def load_ai():
    """Redirect to AI Assistant (which will handle initialization)"""
    return redirect(url_for("ai_assistant.index"))
