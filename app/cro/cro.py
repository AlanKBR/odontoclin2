import unicodedata
from typing import Any, Iterable

from flask import (
    Blueprint,
    flash,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    make_response,
)

from .. import db
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Module-level HTTP session handle (initialized lazily in _session())
__SESSION: requests.Session | None = None


def _users_engine():

    eng = db.engines.get("users") if hasattr(db, "engines") else None
    return eng or db.engine


cro_bp = Blueprint("cro", __name__, template_folder=".")


def _get_api_key(name: str = "consultacro.com.br") -> str | None:
    """Fetch API key from users.db api_keys table.

    Returns None if absent.
    """
    engine = _users_engine()
    with engine.connect() as conn:
        row = conn.exec_driver_sql(
            'SELECT "key" FROM api_keys WHERE name = ? LIMIT 1', (name,)
        ).fetchone()
        return row[0] if row else None


def _set_api_key(key: str | None, name: str = "consultacro.com.br") -> None:
    """Insert or update API key in users.db api_keys table.

    If key is None or empty, clears the stored key.
    """
    engine = _users_engine()
    with engine.begin() as conn:  # transaction
        # Ensure table exists defensively (in case startup upgrade didn't run yet)
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                "key" TEXT
            )
            """
        )
        if key:
            conn.exec_driver_sql(
                'INSERT INTO api_keys (name, "key") VALUES (?, ?)\n'
                'ON CONFLICT(name) DO UPDATE SET "key"=excluded."key"',
                (name, key),
            )
        else:
            # Clear existing key but keep the row for future updates
            conn.exec_driver_sql(
                'INSERT INTO api_keys (name, "key") VALUES (?, NULL)\n'
                'ON CONFLICT(name) DO UPDATE SET "key"=NULL',
                (name,),
            )


@cro_bp.route("/", methods=["GET", "POST"])
def index():
    api_type = request.form.get("api_type", request.args.get("api_type", "cro"))
    uf = request.form.get("uf", request.args.get("uf", "todos"))
    # Prefill the search input from query params to allow refresh persistence
    search_term = request.args.get("q", "")

    # Handle API key submission
    if request.method == "POST" and "api_key" in request.form:
        new_key = (request.form.get("api_key") or "").strip()
        _set_api_key(new_key or None)
        flash("Chave de API atualizada", "success" if new_key else "info")
        return redirect(url_for("cro.index", api_type=api_type, uf=uf))

    # Load current API key to drive UI state
    current_api_key = _get_api_key()
    api_key_configured = bool(current_api_key)
    return render_template(
        "cro/index.html",
        api_type=api_type,
        uf=uf,
        search_term=search_term,
        api_key_configured=api_key_configured,
        current_api_key=current_api_key,
    )


# NOTE: _fold was removed because it was not used in this module.


def _sanitize_query(q: str, max_len: int = 200) -> str:
    """Sanitize user search query.

    - Normalize unicode to NFC
    - Remove control characters
    - Collapse whitespace
    - Trim and limit length
    """
    if not q:
        return ""
    # Normalize to NFC (stable composed form)
    q = unicodedata.normalize("NFC", q)
    # Remove non-printable/control characters
    q = "".join(ch for ch in q if unicodedata.category(ch)[0] != "C")
    # Collapse whitespace
    q = " ".join(q.split())
    # Truncate to max length
    if len(q) > max_len:
        q = q[:max_len]
    return q


def _call_council_api(
    api_type: str,
    q: str,
    uf: str | None,
    api_key: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Call the Consulta API and return the parsed JSON (dict).

    api_type: cro|crm|oab|crp|crea|cau|crn
    q: search term
    uf: optional UF (None or 'todos' means no filter)
    api_key: user's API key
    """
    url = f"https://www.consulta{api_type.lower()}.com.br/api/index.php"
    headers = {"Accept": "application/json"}
    params: dict[str, str] = {"tipo": api_type, "q": q, "chave": api_key, "destino": "json"}
    if uf and uf.lower() != "todos":
        params["uf"] = uf
    resp = _session().get(url, headers=headers, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()  # type: ignore[return-value]


@cro_bp.get("/search")
def search_htmx():
    api_type = request.args.get("api_type", "cro").lower()
    q = _sanitize_query((request.args.get("q") or request.args.get("search_term") or ""))
    uf = (request.args.get("uf", "todos") or "todos").upper()
    if uf != "TODOS" and uf not in _ALLOWED_UFS:
        uf = "TODOS"
    if not q:
        resp = make_response(
            render_template("cro/_results.html", results=[], raw={"erro": "Informe termo de busca"})
        )
        resp.headers["Cache-Control"] = "no-store"
        return resp

    api_key = _get_api_key()
    if not api_key:
        resp = make_response(
            render_template(
                "cro/_results.html",
                results=[],
                raw={"erro": "Chave de API n\u00e3o configurada"},
            )
        )
        resp.headers["Cache-Control"] = "no-store"
        return resp

    try:
        data = _call_council_api(api_type, q, uf, api_key)
        items: list[dict[str, Any]] = []
        if isinstance(data, dict) and data.get("status") == "true" and "item" in data:
            items = data.get("item") or []
        # Stripped fields by default; if ``strip=0`` passed, return raw items.
        strip_param = (request.args.get("strip") or "").strip()
        strip = not (strip_param == "0")
        shaped_items = _shape_items(items, _DEFAULT_FIELDS) if strip else items
        # JSON output path: return JSON if Accept header asks or format=json
        wants_json = (
            request.headers.get("Accept") == "application/json"
            or request.args.get("format") == "json"
        )
        if wants_json:
            resp = jsonify(shaped_items if strip else data)
            resp.headers["Cache-Control"] = "private, max-age=60"
            # Push the index URL with query params so refresh returns the full page
            uf_param = "todos" if uf == "TODOS" else uf
            resp.headers["HX-Push-Url"] = url_for("cro.index", api_type=api_type, uf=uf_param, q=q)
            return resp
        # HTML partial: render table by default with shaped items
        resp = make_response(
            render_template("cro/_results_table.html", results=shaped_items, raw=data)
        )
        resp.headers["Cache-Control"] = "private, max-age=60"
        uf_param = "todos" if uf == "TODOS" else uf
        resp.headers["HX-Push-Url"] = url_for("cro.index", api_type=api_type, uf=uf_param, q=q)
        return resp
    except requests.exceptions.HTTPError as e:  # pragma: no cover - depends on API
        resp = make_response(
            render_template(
                "cro/_results.html",
                results=[],
                raw={"erro": f"HTTP {e.response.status_code if e.response else ''}"},
            )
        )
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except requests.exceptions.RequestException as e:  # pragma: no cover
        resp = make_response(render_template("cro/_results.html", results=[], raw={"erro": str(e)}))
        resp.headers["Cache-Control"] = "no-store"
        return resp


# --- Utilities ---
_ALLOWED_UFS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}


def _shape_items(items: Iterable[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    shaped: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        shaped.append({k: it.get(k) for k in fields})
    return shaped


def _session() -> requests.Session:
    # Lazily create a module-level session with keep-alive and light retries
    global __SESSION
    if "__SESSION" in globals() and isinstance(__SESSION, requests.Session):
        return __SESSION
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    __SESSION = s
    return s


_DEFAULT_FIELDS: tuple[str, ...] = ("nome", "numero", "uf", "situacao", "profissao")

# Expose public constants for templates/tests
API_TYPES = ("cro", "crm", "oab", "crp", "crea", "cau", "crn")
