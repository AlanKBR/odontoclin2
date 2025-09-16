from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from flask import Blueprint, render_template, request, make_response


calc_anestesico_bp = Blueprint("calc_anestesico", __name__, template_folder=".")


@dataclass(frozen=True)
class AnestesicoParams:
    mg_kg: float
    mg_max: float


ANESTESICOS: dict[str, AnestesicoParams] = {
    "lidocaina": AnestesicoParams(mg_kg=4.4, mg_max=300),
    "mepivacaina": AnestesicoParams(mg_kg=4.4, mg_max=300),
    "articaina": AnestesicoParams(mg_kg=7.0, mg_max=500),
    "prilocaina": AnestesicoParams(mg_kg=6.0, mg_max=400),
    "bupivacaina": AnestesicoParams(mg_kg=1.3, mg_max=90),
}


VASO_MAX = {
    # mg totals (adulto saudável). Cardiopata 0,04 mg não aplicado aqui.
    "epinefrina": {"dose_max_mg": 0.2},
    "norepinefrina": {"dose_max_mg": 0.34},
    "fenilefrina": {"dose_max_mg": 5.0},
    # felipressina é em UI: 0,27 UI/kg (máx. 5,4 UI)
    "felypressina": {"dose_max_ui_kg": 0.27, "dose_max_ui_total": 5.4},
}


DEFAULTS = {
    "peso": 70.0,
    "anestesico": "lidocaina",
    "concentracao": 2.0,  # %
    "vaso": "epinefrina",
    "conc_vaso": 0.01,  # mg/ml (1:100.000) | felipressina usa UI/ml 0,03
}


def _parse_float(val: Optional[str]) -> Optional[float]:
    try:
        if val is None or val == "":
            return None
        return float(val.replace(",", "."))
    except Exception:
        return None


@calc_anestesico_bp.get("/")
def index():
    # Renderiza a página com valores padrão
    return render_template(
        "calculadora_anestesico/index.html",
        defaults=DEFAULTS,
    )


@calc_anestesico_bp.get("/conc-vaso-options")
def conc_vaso_options():
    """Retorna <option> para o seletor de concentração do vasoconstrictor (HTMX)."""
    vaso = (request.args.get("vaso") or "").strip().lower()
    opts: list[tuple[str, str]] = []
    if vaso == "epinefrina":
        opts = [("0.01", "1:100.000 (0,01 mg/ml)"), ("0.005", "1:200.000 (0,005 mg/ml)")]
    elif vaso == "norepinefrina":
        opts = [("0.033", "1:30.000 (0,033 mg/ml)")]
    elif vaso == "fenilefrina":
        opts = [("0.4", "1:2.500 (0,4 mg/ml)")]
    elif vaso == "felypressina":
        opts = [("0.03", "0,03 UI/ml")]
    # Caso nenhum, retorna placeholder
    return render_template("calculadora_anestesico/_conc_vaso_options.html", options=opts)


@calc_anestesico_bp.post("/calcular")
def calcular_htmx():
    """Processa o formulário e retorna parcial HTML com o resultado."""
    peso = _parse_float(request.form.get("peso")) or 0.0
    anest = (request.form.get("anestesico") or "").strip().lower()
    conc_percent = _parse_float(request.form.get("concentracao")) or 0.0
    vaso = (request.form.get("vaso") or "nenhum").strip().lower()
    conc_vaso_val = _parse_float(request.form.get("conc_vaso"))

    errors: list[str] = []
    if peso <= 0:
        errors.append("Informe um peso válido.")
    if anest not in ANESTESICOS:
        errors.append("Tipo de anestésico inválido.")
    if conc_percent <= 0:
        errors.append("Informe a concentração do anestésico (%).")
    if vaso != "nenhum" and conc_vaso_val is None:
        errors.append("Selecione a concentração do vasoconstrictor.")

    if errors:
        resp = make_response(
            render_template("calculadora_anestesico/_resultado.html", erro=" ".join(errors))
        )
        resp.headers["Cache-Control"] = "no-store"
        return resp

    ml_tubete = 1.8
    # Anestésico local
    params = ANESTESICOS[anest]
    dose_max_mg = min(peso * params.mg_kg, params.mg_max)
    mg_por_ml_anest = conc_percent * 10.0
    mg_por_tubete_anest = mg_por_ml_anest * ml_tubete
    tubetes_max_anest = dose_max_mg / mg_por_tubete_anest if mg_por_tubete_anest > 0 else 0.0

    # Vasoconstrictor (opcional)
    tubetes_max_vaso: Optional[float] = None
    if vaso in VASO_MAX:
        if vaso == "felypressina":
            ui_max = min(
                VASO_MAX[vaso]["dose_max_ui_kg"] * peso,
                VASO_MAX[vaso]["dose_max_ui_total"],
            )
            ui_por_ml = conc_vaso_val or 0.0
            ui_por_tubete = ui_por_ml * ml_tubete
            tubetes_max_vaso = ui_max / ui_por_tubete if ui_por_tubete > 0 else None
        else:
            mg_max = VASO_MAX[vaso]["dose_max_mg"]
            mg_por_ml_vaso = conc_vaso_val or 0.0
            mg_por_tubete_vaso = mg_por_ml_vaso * ml_tubete
            tubetes_max_vaso = mg_max / mg_por_tubete_vaso if mg_por_tubete_vaso > 0 else None

    # Menor valor prevalece
    criterio = "anestésico local"
    tubetes_final = tubetes_max_anest
    if tubetes_max_vaso is not None and tubetes_max_vaso < tubetes_max_anest:
        tubetes_final = tubetes_max_vaso
        criterio = "vasoconstrictor"

    contexto = {
        "peso": peso,
        "anestesico": anest,
        "concentracao": conc_percent,
        "vaso": vaso,
        "conc_vaso": conc_vaso_val,
        "tubetes_max_anest": tubetes_max_anest,
        "tubetes_max_vaso": tubetes_max_vaso,
        "tubetes_final": tubetes_final,
        "criterio": criterio,
        "dose_max_mg": dose_max_mg,
        "mg_por_tubete_anest": mg_por_tubete_anest,
        "ml_tubete": ml_tubete,
    }

    resp = make_response(render_template("calculadora_anestesico/_resultado.html", **contexto))
    resp.headers["Cache-Control"] = "no-store"
    return resp
