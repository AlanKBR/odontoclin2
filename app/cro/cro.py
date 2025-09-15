import unicodedata

from flask import Blueprint, flash, jsonify, render_template, request

cro_bp = Blueprint(
    "cro",
    __name__,
    template_folder=".",
)


# Modo offline: evita chamadas externas em testes. Placeholder
OFFLINE = True


@cro_bp.route("/", methods=["GET", "POST"])
def index():
    results = []
    api_type = request.form.get("api_type", request.args.get("api_type", "cro"))
    uf = request.form.get("uf", request.args.get("uf", "todos"))
    search_term = request.form.get("search_term", "").strip()
    if request.method == "POST":
        if not search_term:
            flash("Informe termo de busca", "warning")
        else:
            if OFFLINE:
                # Simula pequeno dataset local
                dummy = [
                    {
                        "nome": "Dr. João Silva",
                        "registro": "12345",
                        "uf": "SP",
                    },
                    {
                        "nome": "Dra. Ana Souza",
                        "registro": "67890",
                        "uf": "RJ",
                    },
                ]

                def _fold(s: str) -> str:
                    return "".join(
                        c
                        for c in unicodedata.normalize("NFD", s)
                        if unicodedata.category(c) != "Mn"
                    ).lower()

                folded_term = _fold(search_term)
                for d in dummy:
                    if folded_term in _fold(d["nome"]):
                        if uf == "todos" or d["uf"].lower() == uf.lower():
                            results.append(d)
                if not results:
                    flash("Nenhum resultado (offline)", "info")
            else:  # pragma: no cover - futura integração real
                flash("Integração externa desativada", "info")
    if request.headers.get("Accept") == "application/json":
        return jsonify(results)
    return render_template(
        "cro/index.html",
        results=results,
        api_type=api_type,
        uf=uf,
        search_term=search_term,
    )
