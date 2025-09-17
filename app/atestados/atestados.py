from datetime import date, datetime, timedelta
import json
import os
import unicodedata

from flask import Blueprint, flash, render_template, request
from flask import send_from_directory

from .. import db
from ..receitas.models import Atestado  # reuse bind pacientes
from ..pacientes.models import Paciente
from ..core.models import Clinica

atestados_bp = Blueprint(
    "atestados",
    __name__,
    template_folder=".",
)


@atestados_bp.route("/gerar.js")
def gerar_js():
    """Serve the gerar.js script located next to the templates in this package."""
    root = os.path.dirname(__file__)
    return send_from_directory(root, "gerar.js")


# Module-level cache for precomputed CID JSON entries (lazy-loaded)
_CID_CACHE = None


@atestados_bp.route("/")
def lista():
    try:
        itens = Atestado.query.order_by(Atestado.data_emissao.desc()).limit(50).all()
    except Exception:
        # If the DB schema is incompatible or DB missing, return empty list
        itens = []
    return render_template("atestados/gerar.html", lista=itens, contexto={})


@atestados_bp.route("/gerar", methods=["GET", "POST"])
def gerar_atestado():
    contexto = {}
    if request.method == "POST":
        paciente_id = request.form.get("paciente_id", "").strip()
        paciente_name = request.form.get("paciente", "").strip()
        dias = request.form.get("dias", "1").strip()
        tipo = request.form.get("tipo", "repouso").strip()  # 'repouso' or 'comparecimento'
        # The form now uses a select named 'fins' (legacy used free-text 'motivo').
        # Keep DB column named `motivo` for backwards compatibility but read
        # the value from the 'fins' field and store it into registro.motivo.
        fins = request.form.get("fins", "").strip()
        cid_codigo = request.form.get("cid_codigo", "").strip()
        cid_descricao = request.form.get("cid_descricao", "").strip()
        # local_emissao should come from the clinic configuration (users DB)
        # do not accept arbitrary free-text from the form for this field
        # local_emissao variable not needed here; we set registro.local_emissao below

        try:
            dias_int = int(dias)
        except ValueError:
            dias_int = 1

        # Resolve patient name if id provided
        paciente_obj = None
        if paciente_id:
            try:
                paciente_obj = db.session.get(Paciente, int(paciente_id))
            except Exception:
                paciente_obj = None

        if not paciente_obj and not paciente_name:
            flash("Paciente obrigatório", "danger")
        else:
            nome_para_salvar = paciente_name or (paciente_obj.nome if paciente_obj else "")
            contexto = {
                "paciente": nome_para_salvar,
                "dias": dias_int,
                "data": date.today().strftime("%d/%m/%Y"),
                "fins": fins,
                "cid_codigo": cid_codigo,
                "cid_descricao": cid_descricao,
                "tipo": tipo,
            }
            # If user requested an attendance certificate, compute time range
            if tipo == "comparecimento":
                now = datetime.now()
                # round now to nearest 30 minutes
                minute = now.minute
                remainder = minute % 30
                if remainder < 15:
                    rounded_min = minute - remainder
                else:
                    rounded_min = minute + (30 - remainder)
                # handle hour overflow
                end_dt = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                    minutes=rounded_min
                )
                # if rounding pushed minutes to 60, end_dt will be next hour correctly
                start_dt = end_dt - timedelta(hours=1)
                contexto["start_time"] = start_dt.strftime("%H:%M")
                contexto["end_time"] = end_dt.strftime("%H:%M")
                contexto["data"] = end_dt.strftime("%d/%m/%Y")
            # Do not persist atestados in the DB. Build preview/contexto only.
            try:
                clinica = Clinica.get_instance()
                cidade = (clinica.cidade or "").strip()
                estado = (clinica.estado or "").strip()
                if cidade and estado:
                    local_emissao = f"{cidade} - {estado}"
                elif cidade:
                    local_emissao = cidade
                elif estado:
                    local_emissao = estado
                else:
                    local_emissao = clinica.nome or ""
            except Exception:
                local_emissao = ""

            contexto["local_emissao"] = local_emissao
            # render the same template with contexto filled for preview/printing
            pacientes = Paciente.query.order_by(Paciente.nome).limit(50).all()
            return render_template("atestados/gerar.html", contexto=contexto, pacientes=pacientes)

    # On GET show patients for selection
    pacientes = Paciente.query.order_by(Paciente.nome).limit(50).all()
    return render_template("atestados/gerar.html", contexto=contexto, pacientes=pacientes)


@atestados_bp.route("/buscar_pacientes")
def buscar_pacientes():
    """Search patients by term and return an HTML fragment for HTMX.

    Query param: q - search term (partial name or cpf)
    Returns: fragment with list of checkbox rows (can be inserted into the form)
    """
    termo = request.args.get("q", "").strip()
    resultados = []
    if termo:
        # simple case-insensitive partial match on name or cpf
        filtro = Paciente.nome.ilike(f"%{termo}%")
        # include cpf match if term looks like numbers/punct
        if any(c.isdigit() for c in termo):
            filtro = filtro | Paciente.cpf.ilike(f"%{termo}%")
        resultados = Paciente.query.filter(filtro).order_by(Paciente.nome).limit(50).all()

    # Render a minimal fragment (no layout) suitable for HTMX insertion
    return render_template("atestados/_pacientes_fragment.html", resultados=resultados)


@atestados_bp.route("/api/pacientes")
def api_pacientes():
    """Return JSON list of patients matching query param `q` (autocomplete)."""
    q = request.args.get("q", "").strip()
    if not q:
        return {"results": []}
    filtro = Paciente.nome.ilike(f"%{q}%")
    if any(c.isdigit() for c in q):
        filtro = filtro | Paciente.cpf.ilike(f"%{q}%")
    rows = Paciente.query.filter(filtro).order_by(Paciente.nome).limit(50).all()
    return {"results": [{"id": r.id, "nome": r.nome, "cpf": r.cpf or ""} for r in rows]}


@atestados_bp.route("/api/buscar_cid")
def api_buscar_cid():
    """Search CID10.xml for matching codes or descriptions and return JSON results.

    Uses the copied `app/atestados/CID10.xml` file.
    Query param: q
    """
    q = request.args.get("q", "").strip()
    results = []
    if not q:
        return {"results": results}

    # Load precomputed JSON of CID entries (lazy, cached in module-level _CID_CACHE)
    CID_JSON_PATH = os.path.join(os.path.dirname(__file__), "cid10_filtered.json")

    global _CID_CACHE
    if _CID_CACHE is None:
        try:
            with open(CID_JSON_PATH, "r", encoding="utf-8") as fh:
                entries = json.load(fh)
        except Exception:
            entries = []
        # precompute normalized searchable fields
        for e in entries:
            desc = e.get("descricao", "") or ""
            code = e.get("codigo", "") or ""
            norm_desc = unicodedata.normalize("NFD", desc)
            norm_desc = "".join(c for c in norm_desc if not unicodedata.combining(c)).lower()
            norm_code = unicodedata.normalize("NFD", code)
            norm_code = (
                "".join(c for c in norm_code if not unicodedata.combining(c))
                .lower()
                .replace(".", "")
            )
            e["_search_desc"] = norm_desc
            e["_search_code"] = norm_code
        _CID_CACHE = entries

    qnorm = unicodedata.normalize("NFD", q)
    qnorm = "".join(c for c in qnorm if not unicodedata.combining(c)).lower()
    qnorm = qnorm.replace(".", "").strip()

    seen_codes = set()
    for e in _CID_CACHE:
        if qnorm in e.get("_search_code", "") or qnorm in e.get("_search_desc", ""):
            code = e.get("codigo")
            if code in seen_codes:
                continue
            seen_codes.add(code)
            results.append({"codigo": code, "descricao": e.get("descricao", "")})
            if len(results) >= 50:
                break

    return {"results": results}
