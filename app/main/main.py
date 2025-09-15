from flask import Blueprint, render_template

main_bp = Blueprint(
    "main",
    __name__,
    template_folder=".",
)


@main_bp.route("/")
def dashboard():  # simples painel
    return render_template("main/dashboard.html")


@main_bp.route("/settings")
def settings():  # placeholder
    return render_template("main/settings.html")


@main_bp.route("/calculadora-anestesico")
def calculadora_anestesico():  # placeholder minimal
    return render_template("main/calculadora_anestesico.html")
