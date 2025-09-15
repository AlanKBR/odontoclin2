import os
import sqlite3
from datetime import datetime
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request

from app import db  # reutiliza instancia global
from app import csrf

from . import services  # camada de serviços
from . import holiday_service, lookup_service
from .models import AppSetting, CalendarEvent, Holiday

agenda_bp = Blueprint(
    "agenda",
    __name__,
    template_folder=".",
    static_folder="static",
)


_HOLIDAYS_TTL_SECONDS = 3600  # manter compat


def _db_path(name: str) -> str:
    base = getattr(current_app, "instance_path", current_app.root_path)
    return os.path.join(base, name)


def get_setting(key: str, default: str | None = None) -> str | None:
    s = db.session.get(AppSetting, key)
    return s.value if s and s.value is not None else default


def set_setting(key: str, value: str | None) -> None:
    rec = db.session.get(AppSetting, key)
    if rec is None:
        rec = AppSetting()
        rec.key = key
        rec.value = value
        db.session.add(rec)
    else:
        rec.value = value
    db.session.commit()


def delete_setting(key: str) -> None:
    rec = db.session.get(AppSetting, key)
    if rec is not None:
        db.session.delete(rec)
        db.session.commit()


# ===== Rotas Principais =====
@agenda_bp.route("/")
def index():
    return render_template("agenda/calendar.html")


def _query_events_in_range(range_start: str, range_end: str):  # retrocompat
    return services.query_events_in_range(range_start, range_end)


def _try_parse(fmt: str, s: str):
    try:
        return datetime.strptime(s, fmt)
    except Exception:  # pragma: no cover
        return None


parse_input_datetime = services.parse_input_datetime


normalize_for_storage = services.normalize_for_storage


_apply_query_filters = services.apply_query_filters


@agenda_bp.route("/events")
def get_events():  # abrangente (paridade com legacy)
    range_start = (request.args.get("start") or "").strip()
    range_end = (request.args.get("end") or "").strip()
    query_text = (request.args.get("q") or "").strip()
    dentists_param = (request.args.get("dentists") or "").strip()
    include_unassigned = (request.args.get("include_unassigned") or "").strip() in (
        "1",
        "true",
        "True",
    )
    profissional_ids: list[int] | None = None
    invalid_only = False
    valid_ids: set[int] | None = None
    if dentists_param:
        try:
            profissional_ids = [int(x) for x in dentists_param.split(",") if x.strip().isdigit()]
        except Exception:  # pragma: no cover
            profissional_ids = None
    else:  # detectar invalid_only
        if not include_unassigned:
            db_path = _db_path("users.db")
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute("PRAGMA table_info(users)")
                    cols = [row[1] for row in cur.fetchall()]
                    conditions: list[str] = []
                    if "is_active" in cols:
                        conditions.append("is_active = 1")
                    if "cargo" in cols:
                        conditions.append("cargo IN ('dentista','admin')")
                    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
                    cur.execute(f"SELECT id FROM users{where}")
                    valid_ids = {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}
                    invalid_only = True
                except Exception:  # pragma: no cover
                    pass
                finally:
                    try:
                        conn.close()  # type: ignore
                    except Exception:  # pragma: no cover
                        pass
    data = services.list_events(
        range_start=range_start,
        range_end=range_end,
        query_text=query_text,
        profissional_ids=profissional_ids,
        include_unassigned=include_unassigned,
        invalid_only=invalid_only,
        valid_ids=valid_ids,
    )
    return jsonify(data)


@agenda_bp.route("/add_event", methods=["POST"])
@csrf.exempt
def add_event():  # validação e normalização igual legacy
    data = request.get_json() or {}
    created, err = services.create_event(data)  # type: ignore[assignment]
    if err:
        return jsonify({"status": "error", "message": err}), 400
    return jsonify({"status": "success", "event": created})


@agenda_bp.route("/update_event", methods=["POST"])
@csrf.exempt
def update_event():  # lógica de ajuste de intervalo baseada no legacy
    data: dict[str, Any] = request.get_json() or {}
    event_id = data.get("id")
    event = db.session.get(CalendarEvent, event_id)
    if not event:
        return jsonify({"status": "error", "message": "Event not found"}), 404
    services.update_event_with_dates(event, data)
    services.update_event_fields(event, data)
    db.session.commit()  # garantia caso serviços futuros não commit
    return jsonify({"status": "success"})


@agenda_bp.route("/update_event_color", methods=["POST"])
@csrf.exempt
def update_event_color():
    data = request.get_json() or {}
    event_id = data.get("id")
    color = data.get("color")
    event = db.session.get(CalendarEvent, event_id)
    if not event:
        return jsonify({"status": "error", "message": "Event not found"}), 404
    services.set_event_color(event, color)
    return jsonify({"status": "success", "color": color})


@agenda_bp.route("/update_event_notes", methods=["POST"])
@csrf.exempt
def update_event_notes():
    data = request.get_json() or {}
    event_id = data.get("id")
    notes = data.get("notes", "")
    event = db.session.get(CalendarEvent, event_id)
    if not event:
        return jsonify({"status": "error", "message": "Event not found"}), 404
    services.set_event_notes(event, notes)
    return jsonify({"status": "success", "notes": notes})


@agenda_bp.route("/delete_event", methods=["POST"])
@csrf.exempt
def delete_event():
    data: dict[str, Any] = request.get_json() or {}
    event_id = data.get("id")
    event = db.session.get(CalendarEvent, event_id)
    if event:
        db.session.delete(event)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Event not found"}), 404


@agenda_bp.route("/api/holidays")
def holidays():
    """Retorna os feriados cadastrados."""
    try:
        holidays_query = db.session.query(Holiday)
        holidays_list = holidays_query.all()

        holidays_data = [holiday.to_dict() for holiday in holidays_list]

        return jsonify(holidays_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==== Endpoints adicionais (migrados do legacy) =====


@agenda_bp.route("/dentists")
def listar_dentistas():
    dentists, etag = lookup_service.list_dentists()
    inm = request.headers.get("If-None-Match")
    headers = {"Cache-Control": "public, max-age=300", "ETag": etag}
    if inm and inm == etag:
        return "", 304, headers
    resp = jsonify(dentists)
    for k, v in headers.items():
        resp.headers[k] = v
    return resp


@agenda_bp.route("/pacientes")
def listar_pacientes():
    pacientes = lookup_service.list_pacientes_basic()
    return jsonify(pacientes)


@agenda_bp.route("/buscar_nomes")
def buscar_nomes():
    query = (request.args.get("q") or "").strip()
    try:
        nomes = lookup_service.search_paciente_names(query)
    except Exception as e:  # pragma: no cover
        current_app.logger.warning("Erro ao buscar pacientes: %s", e)
        nomes = []
    return jsonify(nomes)


@agenda_bp.route("/buscar_telefone")
def buscar_telefone():
    nome = (request.args.get("nome") or "").strip()
    telefone = lookup_service.find_paciente_phone(nome) if nome else None
    return jsonify({"telefone": telefone})


@agenda_bp.route("/holidays/range")
def holidays_in_range():
    start = (request.args.get("start") or "").strip()
    end = (request.args.get("end") or "").strip()
    data = holiday_service.get_holidays_range(start, end)
    resp = jsonify(data)
    resp.headers["Cache-Control"] = f"public, max-age={_HOLIDAYS_TTL_SECONDS}"
    return resp


def _cache_headers(resp, ttl: int) -> None:
    resp.headers["Cache-Control"] = f"public, max-age={ttl}"


def _get_year_param() -> int:
    try:
        return int((request.args.get("year") or "").strip())
    except Exception:  # pragma: no cover
        return 0


@agenda_bp.route("/holidays/year")
def holidays_by_year():
    year = _get_year_param()
    if year <= 0:
        return jsonify([])
    data = holiday_service.get_holidays_year(year)
    resp = jsonify(data)
    _cache_headers(resp, _HOLIDAYS_TTL_SECONDS)
    return resp


@agenda_bp.route("/cache/clear", methods=["POST"])
@csrf.exempt
def cache_clear():
    try:
        holiday_service.invalidate_cache()
    except Exception:  # pragma: no cover
        pass
    return jsonify({"status": "success"})


# ===== Invertexto Token Management & Refresh =====
@agenda_bp.route(
    "/settings/invertexto_token",
    methods=["GET", "POST", "DELETE"],
)
@csrf.exempt
def invertexto_token():
    """Gerencia o token da API Invertexto (não expõe o valor em GET)."""
    if request.method == "GET":
        tok = get_setting("invertexto_token")
        return jsonify({"hasToken": bool(tok)})
    if request.method == "DELETE":
        delete_setting("invertexto_token")
        return jsonify({"status": "success"})
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if not token:
        return jsonify({"status": "error", "message": "Token vazio"}), 400
    set_setting("invertexto_token", token)
    return jsonify({"status": "success"})


@agenda_bp.route("/holidays/refresh", methods=["POST"])
@csrf.exempt
def holidays_refresh():
    """Busca feriados via Invertexto e faz upsert no banco calendario.

    Body JSON: { year: 2025, state?: 'SP' }
    """
    try:
        import requests  # type: ignore
    except Exception:  # pragma: no cover
        requests = None  # type: ignore
    if requests is None:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Dependência 'requests' ausente",
                }
            ),
            500,
        )
    data = request.get_json(silent=True) or {}
    try:
        year = int(data.get("year") or 0)
    except Exception:
        year = 0
    state = (data.get("state") or "").strip().upper() or None
    token = get_setting("invertexto_token")
    count, error = holiday_service.refresh_holidays(
        year=year,
        state=state,
        token=token or "",
        requests_mod=requests,
    )
    if error:
        code = 400 if "Token" in error or "Ano" in error else 502
        return jsonify({"status": "error", "message": error}), code
    return jsonify({"status": "success", "count": count or 0})


@agenda_bp.route("/api/holidays", methods=["POST"])
@csrf.exempt
def add_holiday():
    """Adiciona um novo feriado."""
    data = request.get_json(silent=True) or {}
    rec, error = holiday_service.add_holiday_record(data)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(rec), 201


@agenda_bp.route("/api/holidays/<string:holiday_date>", methods=["PUT"])
@csrf.exempt
def update_holiday(holiday_date: str):
    """Atualiza um feriado existente."""
    holiday = db.session.get(Holiday, holiday_date)
    if not holiday:
        return jsonify({"error": "Feriado não encontrado"}), 404
    data = request.get_json(silent=True) or {}
    rec, error = holiday_service.update_holiday_record(holiday, data)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(rec), 200
