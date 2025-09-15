import requests
from flask import (
    Blueprint,
    flash,
    get_flashed_messages,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

# Changed url_prefix for generality
cro_bp = Blueprint("cro", __name__, url_prefix="/professional-lookup")

API_KEY = None


@cro_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    global API_KEY
    results = None
    api_limite = None
    api_consultas = None
    remaining_queries = None
    total_results_api = None  # Initialize total_results_api
    search_term_processed = request.form.get("search_term", "")
    api_type_processed = request.args.get("api_type", request.form.get("api_type", "cro"))
    uf_processed = request.args.get("uf", request.form.get("uf", "todos"))  # Default to 'todos'

    if request.method == "POST":
        if "api_key" in request.form:  # API Key submission
            new_api_key = request.form.get("api_key")
            if new_api_key:
                API_KEY = new_api_key
                flash("Chave de API atualizada com sucesso!", "success")
            else:
                API_KEY = None
                flash("Chave de API removida.", "info")
            return redirect(url_for("cro.index", api_type=api_type_processed, uf=uf_processed))

        elif "search_term" in request.form and "api_type" in request.form and "uf" in request.form:
            if not API_KEY:
                flash("Por favor, configure sua Chave de API primeiro.", "warning")
                return redirect(url_for("cro.index", api_type=api_type_processed, uf=uf_processed))

            search_term = request.form.get("search_term")
            api_type = request.form.get("api_type")
            uf = request.form.get("uf")

            search_term_processed = search_term
            api_type_processed = api_type
            uf_processed = uf

            # Dynamically construct the API URL
            if not api_type:  # Should not happen with dropdown, but as a safeguard
                flash("Tipo de conselho não especificado.", "danger")
                return redirect(url_for("cro.index", api_type=api_type_processed, uf=uf_processed))

            dynamic_api_url = f"https://www.consulta{api_type.lower()}.com.br/api/index.php"

            headers = {"Accept": "application/json"}
            params = {
                "tipo": api_type,  # tipo is still sent as a parameter as per example
                "q": search_term,
                "chave": API_KEY,
                "destino": "json",
            }
            if uf and uf.lower() != "todos":
                params["uf"] = uf

            try:
                response = requests.get(dynamic_api_url, headers=headers, params=params, timeout=15)
                response.raise_for_status()
                results_data = response.json()

                # Extract API limit and usage information
                api_limite_raw = results_data.get("api_limite")
                api_consultas_raw = results_data.get("api_consultas")

                if api_limite_raw is not None and api_consultas_raw is not None:
                    try:
                        api_limite = int(api_limite_raw)
                        api_consultas = int(api_consultas_raw)
                        remaining_queries = api_limite - api_consultas
                    except (ValueError, TypeError):
                        flash(
                            "Não foi possível processar as informações de limite de API (formato inesperado).",
                            "warning",
                        )

                # Extract total results from API if available
                total_results_api_raw = results_data.get("total")
                if total_results_api_raw is not None:
                    try:
                        total_results_api = int(total_results_api_raw)
                    except (ValueError, TypeError):
                        flash(
                            "Não foi possível processar o número total de resultados da API (formato inesperado).",
                            "warning",
                        )
                        total_results_api = None  # Reset if conversion fails

                current_uf_display = f" em {uf.upper()}" if uf and uf.lower() != "todos" else ""

                if (
                    isinstance(results_data, dict)
                    and results_data.get("status") == "true"
                    and "item" in results_data
                ):
                    results = results_data["item"]
                    if not results and search_term:
                        flash(
                            f'Nenhum resultado encontrado para "{search_term}" em '
                            f"{api_type.upper()}{current_uf_display}. "
                            f'(API: {results_data.get("mensagem", "Sem detalhes")})',
                            "info",
                        )
                elif isinstance(results_data, dict) and results_data.get("status") == "false":
                    flash(
                        f"API ({api_type.upper()}{current_uf_display}) retornou erro: "
                        f'{results_data.get("mensagem", "Erro da API")}',
                        "warning",
                    )
                    results = []
                else:
                    results = []
                    if search_term:
                        flash(
                            f'Resposta inesperada da API ({api_type.upper()}{current_uf_display}) para "{search_term}".',
                            "warning",
                        )

                if results is None:
                    results = []

                if (
                    not results
                    and search_term
                    and not get_flashed_messages(category_filter=["info", "warning"])
                ):
                    flash(
                        f'Nenhum resultado encontrado para "{search_term}" em {api_type.upper()}{current_uf_display}.',
                        "info",
                    )

            except requests.exceptions.HTTPError as errh:
                status_code = errh.response.status_code
                reason = errh.response.reason
                error_details = f" (API: {api_type.upper()}, UF: {uf.upper() if uf and uf != 'todos' else 'Todos'})"
                try:
                    error_body = errh.response.json()
                    if isinstance(error_body, dict) and "erro" in error_body:
                        error_details += f" Detalhe: {error_body['erro']}"
                except ValueError:
                    pass  # Keep pass if no specific action is needed for non-JSON error bodies
                flash(f"Erro HTTP: {status_code} - {reason}.{error_details}", "danger")
                if status_code in [401, 403]:
                    flash("Chave de API inválida/não autorizada.", "warning")
            except requests.exceptions.ConnectionError:
                flash(
                    f"Erro de conexão com API em {dynamic_api_url}.", "danger"
                )  # Use dynamic_api_url
            except requests.exceptions.Timeout:
                flash(
                    f"Timeout ao consultar API ({api_type.upper()}, UF: {uf.upper() if uf and uf != 'todos' else 'Todos'}) em {dynamic_api_url}.",
                    "danger",
                )  # Use dynamic_api_url
            except requests.exceptions.RequestException as err:
                flash(
                    f"Erro na requisição ({api_type.upper()}, UF: {uf.upper() if uf and uf != 'todos' else 'Todos'}) API: {err}",
                    "danger",
                )
            except ValueError:
                flash(
                    f"Erro ao processar JSON da API ({api_type.upper()}, UF: {uf.upper() if uf and uf != 'todos' else 'Todos'}).",
                    "danger",
                )

    if request.method == "GET":
        api_type_from_args = request.args.get("api_type")
        if api_type_from_args:
            api_type_processed = api_type_from_args
        uf_from_args = request.args.get("uf")
        if uf_from_args:
            uf_processed = uf_from_args

    return render_template(
        "cro/index.html",
        api_key_configured=bool(API_KEY),
        current_api_key=API_KEY,
        results=results,
        search_term=search_term_processed,
        api_type_selected=api_type_processed,
        uf_selected=uf_processed,
        should_focus_api_key=not bool(API_KEY),
        api_limite=api_limite,
        api_consultas=api_consultas,
        remaining_queries=remaining_queries,
        total_results_api=total_results_api,  # Pass total_results_api to template
    )


# Consider renaming the blueprint in __init__.py as well if cro_bp name is changed here.
# e.g., from app.routes.cro import cro_bp as professional_lookup_bp
# and then app.register_blueprint(professional_lookup_bp)
