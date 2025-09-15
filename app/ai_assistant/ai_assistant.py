from flask import Blueprint, render_template

ai_assistant_bp = Blueprint(
    "ai_assistant",
    __name__,
    template_folder=".",
)


@ai_assistant_bp.route("/")
def index():  # placeholder
    return render_template("ai_assistant/index.html")
