from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request
from sqlalchemy import create_engine, or_, text

try:
    # Prefer the host application's SQLAlchemy instance
    from app.extensions import db  # type: ignore
except Exception:  # fallback to local if running standalone
    from .db import db

bp = Blueprint(
    "agenda",
    __name__,
    template_folder="templates",
    static_folder="static",
)


# Models colocados aqui para manter o módulo autocontido
class CalendarEvent(db.Model):
    __bind_key__ = "calendario"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start = db.Column(db.String(30), nullable=False)
    end = db.Column(db.String(30), nullable=False)
    color = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    profissional_id = db.Column(db.Integer, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        from dateutil.parser import parse

        try:
            start_dt = parse(self.start)
            end_dt = parse(self.end)
            if len(self.start) == 10 and len(self.end) == 10:
                all_day = True
            elif (
                start_dt.hour == 0
                and start_dt.minute == 0
                and start_dt.second == 0
                and end_dt.hour == 0
                and end_dt.minute == 0
                and end_dt.second == 0
                and (end_dt - start_dt).total_seconds() % 86400 == 0
            ):
                all_day = True
            else:
                all_day = False
        except Exception:
            all_day = False
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "color": self.color,
            "notes": self.notes,
            "allDay": all_day,
            "profissional_id": self.profissional_id,
        }


class AppSetting(db.Model):
    __tablename__ = "app_settings"
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(1000), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Holiday(db.Model):
    __bind_key__ = "calendario"
    __tablename__ = "holidays"
    date = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=True)
    level = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(5), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(50), nullable=False, default="invertexto")
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "name": self.name,
            "type": self.type,
            "level": self.level,
            "state": self.state,
            "year": self.year,
            "source": self.source,
        }


# ===== Holidays settings and caches =====
try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - optional dep defensive
    requests = None  # type: ignore

_HOLIDAYS_YEAR_CACHE: dict[int, dict] = {}
_HOLIDAYS_RANGE_CACHE: dict[tuple[str, str], dict] = {}
_HOLIDAYS_TTL_SECONDS = 3600  # 1h


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _ensure_aware_utc(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _invalidate_holidays_cache() -> None:
    _HOLIDAYS_YEAR_CACHE.clear()
    _HOLIDAYS_RANGE_CACHE.clear()


def _db_path(name: str) -> str:
    # Use app.instance_path (outside package), set by create_app/init_agenda
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


@bp.route("/")
def index():
    return render_template("calendar.html")


def _try_parse(fmt: str, s: str):
    try:
        return datetime.strptime(s, fmt)
    except Exception:
        return None


def parse_input_datetime(raw: Any):
    if not raw:
        return None, None
    s = str(raw).strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        dt = _try_parse(fmt, s)
        if dt:
            return dt, False
    dt = _try_parse("%d/%m/%Y", s)
    if dt:
        return dt, True
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
    ):
        dt = _try_parse(fmt, s)
        if dt:
            return dt, False
    dt = _try_parse("%Y-%m-%d", s)
    if dt:
        return dt, True
    try:
        from dateutil.parser import parse as du_parse

        dt = du_parse(s, dayfirst=True)
        is_date_only = len(s) == 10 and s.count("/") + s.count("-") in (2,)
        return dt, is_date_only
    except Exception:
        return None, None


def normalize_for_storage(dt: datetime, is_date_only: bool) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d") if is_date_only else dt.strftime("%Y-%m-%dT%H:%M:%S")


def _apply_query_filters(base_query, query_text: str):
    qtxt = (query_text or "").strip().lower()
    if not qtxt:
        return base_query
    like = f"%{qtxt}%"
    col_title = getattr(CalendarEvent, "title")
    col_notes = getattr(CalendarEvent, "notes")
    title_match = col_title.ilike(like)
    notes_match = col_notes.ilike(like)
    # Optional: match color by words (e.g., "vermelho") or hex (e.g., "#ff0000")

    def _color_hexes_for_query(query_text: str) -> list[str]:
        q = (query_text or "").strip().lower()
        if not q:
            return []
        COLOR_WORDS: dict[str, list[str]] = {
            "vermelho": ["#e11d48"],
            "rosa": ["#f43f5e", "#f472b6"],
            "rosa-claro": ["#f472b6"],
            "laranja": ["#f59e42"],
            "amarelo": ["#fbbf24"],
            "verde": ["#22c55e"],
            "verde-agua": ["#10b981"],
            "verde agua": ["#10b981"],
            "azul": ["#2563eb"],
            "azul-escuro": ["#2563eb"],
            "azul escuro": ["#2563eb"],
            "azul-claro": ["#0ea5e9"],
            "azul claro": ["#0ea5e9"],
            "roxo": ["#6366f1"],
            "lilás": ["#6366f1"],
            "lilas": ["#6366f1"],
            "roxo-escuro": ["#a21caf"],
            "roxo escuro": ["#a21caf"],
            "púrpura": ["#a21caf"],
            "purpura": ["#a21caf"],
            "cinza": ["#64748b"],
            "grey": ["#64748b"],
            "grafite": ["#64748b"],
        }
        hexes: list[str] = []
        for word, values in COLOR_WORDS.items():
            if q == word or word in q:
                hexes.extend(values)
        if q.startswith("#") and len(q) in (4, 7):
            hexes.append(q)
        # unique
        seen: set[str] = set()
        uniq: list[str] = []
        for h in hexes:
            if h not in seen:
                seen.add(h)
                uniq.append(h)
        return uniq

    color_hexes = _color_hexes_for_query(qtxt)
    if color_hexes:
        col_color = getattr(CalendarEvent, "color")
        color_match = col_color.in_(color_hexes)
        return base_query.filter(or_(title_match, notes_match, color_match))
    return base_query.filter(or_(title_match, notes_match))


@bp.route("/settings/invertexto_token", methods=["GET", "POST", "DELETE"])
def invertexto_token():
    """Manage Invertexto API token (does not expose the token on GET)."""
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


@bp.route("/events")
def get_events():
    range_start = (request.args.get("start") or "").strip()
    range_end = (request.args.get("end") or "").strip()
    q = CalendarEvent.query
    query_text = (request.args.get("q") or "").strip()
    dentists_param = (request.args.get("dentists") or "").strip()
    include_unassigned = (request.args.get("include_unassigned") or "").strip() in (
        "1",
        "true",
        "True",
    )
    if dentists_param:
        try:
            ids = [int(x) for x in dentists_param.split(",") if x.strip().isdigit()]
            col_prof = getattr(CalendarEvent, "profissional_id")
            if ids and include_unassigned:
                q = q.filter(or_(col_prof.in_(ids), col_prof.is_(None)))
            elif ids:
                q = q.filter(col_prof.in_(ids))
        except Exception:
            pass
    else:
        try:
            col_prof = getattr(CalendarEvent, "profissional_id")
            if include_unassigned:
                q = q.filter(col_prof.is_(None))
            else:
                # invalid-only: ids not in the set of currently selectable dentists (active + role), and not null
                db_path = _db_path("users.db")
                valid_ids: set[int] = set()
                if os.path.exists(db_path):
                    conn: sqlite3.Connection | None = None
                    try:
                        conn = sqlite3.connect(db_path)
                        cur = conn.cursor()
                        # Determine available columns to apply same filter as /dentists
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
                    finally:
                        try:
                            if conn is not None:
                                conn.close()
                        except Exception:
                            pass
                q = q.filter(CalendarEvent.profissional_id.is_not(None))
                if valid_ids:
                    q = q.filter(~CalendarEvent.profissional_id.in_(list(valid_ids)))
        except Exception:
            pass
    if range_start and range_end and not query_text:
        try:
            if len(range_start) >= 10 and len(range_end) >= 10:
                col_end = getattr(CalendarEvent, "end")
                col_start = getattr(CalendarEvent, "start")
                q = q.filter(col_end >= range_start)
                q = q.filter(col_start < range_end)
        except Exception:
            pass
    if query_text:
        q = _apply_query_filters(q, query_text)
    try:
        events = q.all()
        return jsonify([e.to_dict() for e in events])
    except Exception:
        return jsonify([])


@bp.route("/events/search_range")
def events_search_range():
    q = CalendarEvent.query
    dentists_param = (request.args.get("dentists") or "").strip()
    include_unassigned = (request.args.get("include_unassigned") or "").strip() in (
        "1",
        "true",
        "True",
    )
    if dentists_param:
        try:
            ids = [int(x) for x in dentists_param.split(",") if x.strip().isdigit()]
            col_prof = getattr(CalendarEvent, "profissional_id")
            if ids and include_unassigned:
                q = q.filter(or_(col_prof.in_(ids), col_prof.is_(None)))
            elif ids:
                q = q.filter(col_prof.in_(ids))
        except Exception:
            pass
    else:
        try:
            col_prof = getattr(CalendarEvent, "profissional_id")
            if include_unassigned:
                q = q.filter(col_prof.is_(None))
            else:
                # invalid-only based on active dentists/admins as valid
                db_path = _db_path("users.db")
                valid_ids: set[int] = set()
                if os.path.exists(db_path):
                    conn: sqlite3.Connection | None = None
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
                    finally:
                        try:
                            if conn is not None:
                                conn.close()
                        except Exception:
                            pass
                q = q.filter(CalendarEvent.profissional_id.is_not(None))
                if valid_ids:
                    q = q.filter(~CalendarEvent.profissional_id.in_(list(valid_ids)))
        except Exception:
            pass
    query_text = (request.args.get("q") or "").strip()
    if query_text:
        q = _apply_query_filters(q, query_text)
    try:
        events = q.all()
        if not events:
            return jsonify({"min": None, "max": None, "count": 0})
        starts = [e.start for e in events if e.start]
        ends = [e.end for e in events if e.end]
        min_start = min(starts) if starts else None
        max_end = max(ends) if ends else None
        return jsonify({"min": min_start, "max": max_end, "count": len(events)})
    except Exception:
        return jsonify({"min": None, "max": None, "count": 0})


@bp.route("/add_event", methods=["POST"])
def add_event():
    data: dict[str, Any] = request.get_json() or {}
    raw_start = data.get("start")
    raw_end = data.get("end")
    start_dt, start_is_date_only = parse_input_datetime(raw_start)
    end_dt, end_is_date_only = parse_input_datetime(raw_end) if raw_end else (None, None)
    if not start_dt:
        return jsonify({"status": "error", "message": "Start inválido"}), 400
    if start_is_date_only:
        if not end_dt or not end_is_date_only:
            end_dt = start_dt + timedelta(days=1)
            end_is_date_only = True
        elif end_dt <= start_dt:
            end_dt = start_dt + timedelta(days=1)
    else:
        if not end_dt:
            end_dt = start_dt + timedelta(hours=1)
            end_is_date_only = False
        elif end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)
            end_is_date_only = False
    start_is_date_only = bool(start_is_date_only)
    end_is_date_only = bool(end_is_date_only)
    new_event = CalendarEvent()
    new_event.title = str(data.get("title") or "").strip()
    new_event.start = normalize_for_storage(start_dt, start_is_date_only)
    new_event.end = normalize_for_storage(end_dt, end_is_date_only)
    new_event.color = data.get("color")
    new_event.notes = data.get("notes")
    pid_raw = data.get("profissional_id")
    new_event.profissional_id = (
        int(pid_raw) if isinstance(pid_raw, int | str) and str(pid_raw).isdigit() else None
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify({"status": "success", "event": new_event.to_dict()})


@bp.route("/delete_event", methods=["POST"])
def delete_event():
    data: dict[str, Any] = request.get_json() or {}
    event_id = data.get("id")
    event = db.session.get(CalendarEvent, event_id)
    if event:
        db.session.delete(event)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Event not found"}), 404


@bp.route("/update_event", methods=["POST"])
def update_event():
    data: dict[str, Any] = request.get_json() or {}
    event_id = data.get("id")
    raw_start = data.get("start")
    raw_end = data.get("end")
    event = db.session.get(CalendarEvent, event_id)
    if not event:
        return jsonify({"status": "error", "message": "Event not found"}), 404
    start_dt, start_is_date_only = parse_input_datetime(raw_start) if raw_start else (None, None)
    end_dt, end_is_date_only = parse_input_datetime(raw_end) if raw_end else (None, None)
    if start_dt:
        if start_is_date_only:
            if not end_dt or not end_is_date_only or end_dt <= start_dt:
                end_dt = start_dt + timedelta(days=1)
                end_is_date_only = True
        else:
            if not end_dt or end_dt <= start_dt:
                end_dt = start_dt + timedelta(hours=1)
                end_is_date_only = False
        start_is_date_only = bool(start_is_date_only)
        end_is_date_only = bool(end_is_date_only)
        event.start = normalize_for_storage(start_dt, start_is_date_only)
        event.end = normalize_for_storage(end_dt, end_is_date_only) if end_dt else None
    if "profissional_id" in data:
        pid = data.get("profissional_id")
        event.profissional_id = (
            int(pid) if isinstance(pid, int | str) and str(pid).isdigit() else None
        )
    db.session.commit()
    return jsonify({"status": "success"})


@bp.route("/update_event_color", methods=["POST"])
def update_event_color():
    data = request.get_json() or {}
    event_id = data.get("id")
    color = data.get("color")
    event = db.session.get(CalendarEvent, event_id)
    if not event:
        return jsonify({"status": "error", "message": "Event not found"}), 404
    event.color = color
    db.session.commit()
    return jsonify({"status": "success", "color": color})


@bp.route("/update_event_notes", methods=["POST"])
def update_event_notes():
    data = request.get_json() or {}
    event_id = data.get("id")
    notes = data.get("notes", "")
    event = db.session.get(CalendarEvent, event_id)
    if not event:
        return jsonify({"status": "error", "message": "Event not found"}), 404
    event.notes = notes
    db.session.commit()
    return jsonify({"status": "success", "notes": notes})


@bp.route("/dentists")
def listar_dentistas():
    db_path = _db_path("users.db")
    dentists = []
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cur.fetchall()]
            if "id" in cols:
                name_candidates = [
                    "nome_profissional",
                    "nome",
                    "name",
                    "full_name",
                    "username",
                ]
                name_col = (
                    next(
                        (c for c in name_candidates if c in cols),
                        None,
                    )
                    or "id"
                )
                color_col = "color" if "color" in cols else ("cor" if "cor" in cols else None)
                sel_cols = ["id", name_col] + ([color_col] if color_col else [])
                conditions: list[str] = []
                if "is_active" in cols:
                    conditions.append("is_active = 1")
                if "cargo" in cols:
                    conditions.append("cargo IN ('dentista','admin')")
                where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
                q = "SELECT " f"{', '.join(sel_cols)} " f"FROM users{where} ORDER BY {name_col}"
                cur.execute(q)
                for r in cur.fetchall():
                    did = r[0]
                    name = r[1]
                    color_val = r[2] if color_col else None
                    dentists.append(
                        {
                            "id": did,
                            "nome": name,
                            "color": color_val,
                        }
                    )
        finally:
            try:
                conn.close()
            except Exception:
                pass
    etag = f"{int(os.path.getmtime(db_path)) if os.path.exists(db_path) else 0}" f":{len(dentists)}"
    inm = request.headers.get("If-None-Match")
    headers = {"Cache-Control": "public, max-age=300", "ETag": etag}
    if inm and inm == etag:
        return "", 304, headers
    resp = jsonify(dentists)
    for k, v in headers.items():
        resp.headers[k] = v
    return resp


@bp.route("/pacientes")
def listar_pacientes():
    engine = create_engine(f"sqlite:///{_db_path('pacientes.db')}")
    with engine.connect() as conn:
        query = "SELECT id, nome FROM pacientes ORDER BY nome"
        result = conn.execute(text(query))
        pacientes = [{"id": row[0], "nome": row[1]} for row in result]
    return jsonify(pacientes)


@bp.route("/buscar_nomes")
def buscar_nomes():
    query = request.args.get("q", "").strip()
    nomes: list[str] = []
    if query and len(query) >= 1:
        try:
            conn = sqlite3.connect(_db_path("pacientes.db"))
            cursor = conn.cursor()
            cursor.execute(
                (
                    "SELECT nome FROM pacientes "
                    "WHERE (nome LIKE ? COLLATE NOCASE) "
                    "OR (nome LIKE ? COLLATE NOCASE) "
                    "ORDER BY nome LIMIT 20"
                ),
                (f"{query}%", f"% {query}%"),
            )
            for row in cursor.fetchall():
                if row[0]:
                    nomes.append(row[0])
            conn.close()
        except Exception as e:
            current_app.logger.warning("Erro ao buscar pacientes: %s", e)
    return jsonify(nomes[:20])


@bp.route("/buscar_telefone")
def buscar_telefone():
    nome = request.args.get("nome", "").strip()
    if not nome:
        return jsonify({"telefone": None})
    try:
        conn = sqlite3.connect(_db_path("pacientes.db"))
        cursor = conn.cursor()
        cursor.execute(
            ("SELECT celular FROM pacientes WHERE LOWER(nome) = LOWER(?) " "LIMIT 1"),
            (nome,),
        )
        result = cursor.fetchone()
        if not result:
            cursor.execute(
                ("SELECT celular FROM pacientes " "WHERE LOWER(nome) LIKE LOWER(?) " "LIMIT 1"),
                (f"%{nome}%",),
            )
            result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return jsonify({"telefone": result[0]})
        return jsonify({"telefone": None})
    except Exception as e:
        current_app.logger.warning("Erro ao buscar telefone: %s", e)
        return jsonify({"telefone": None})


# ===== Invertexto Holidays integration =====


@bp.route("/holidays/refresh", methods=["POST"])
def holidays_refresh():
    """Fetch holidays from Invertexto and upsert into local DB.

    Body: { year: 2025, state?: 'SP' }
    """
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
    year = int(data.get("year") or 0)
    state = (data.get("state") or "").strip().upper() or None
    if year <= 0:
        return jsonify({"status": "error", "message": "Ano inválido"}), 400
    token = get_setting("invertexto_token")
    if not token:
        return (
            jsonify({"status": "error", "message": "Token não configurado"}),
            400,
        )
    url = f"https://api.invertexto.com/v1/holidays/{year}"
    params = {"token": token}
    if state:
        params["state"] = state
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            msg = f"Erro {r.status_code} da API Invertexto"
            if r.status_code == 401:
                msg = "Não autorizado (401): verifique o token"
            elif r.status_code == 400:
                msg = "Parâmetros inválidos (400): ano/UF"
            elif r.status_code == 429:
                msg = "Limite de requisições excedido (429)"
            return jsonify({"status": "error", "message": msg}), 502
        items = r.json() if r.content else []
        if not isinstance(items, list):
            return (
                jsonify({"status": "error", "message": "Resposta inesperada"}),
                502,
            )
        # Replace holidays for this year (any state) to avoid PK conflicts
        try:
            q = Holiday.query.filter(Holiday.year == year)
            q.delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Falha ao limpar dados antigos",
                    }
                ),
                500,
            )
        count = 0
        for it in items:
            try:
                date = str(it.get("date") or "").strip()
                name = (it.get("name") or "").strip()
                htype = (it.get("type") or "").strip() or None
                level = (it.get("level") or "").strip() or None
                if not date or not name:
                    continue
                rec = Holiday()
                rec.date = date
                rec.name = name
                rec.type = htype
                rec.level = level
                rec.state = state
                rec.year = year
                rec.source = "invertexto"
                db.session.add(rec)
                count += 1
            except Exception:
                continue
        db.session.commit()
        try:
            _invalidate_holidays_cache()
        except Exception:
            pass
        return jsonify({"status": "success", "count": count})
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Falha ao consultar API: {e}",
                }
            ),
            502,
        )


@bp.route("/holidays/range")
def holidays_in_range():
    """Return holidays between start and end (inclusive)."""
    start = (request.args.get("start") or "").strip()
    end = (request.args.get("end") or "").strip()
    if not start or not end:
        return jsonify([])
    try:
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
    except Exception:
        return jsonify([])
    key = (start, end)
    now = _utcnow()
    cached = _HOLIDAYS_RANGE_CACHE.get(key)
    cached_at = _ensure_aware_utc(cached.get("at") if cached else None) if cached else None
    if cached and cached_at and (now - cached_at) <= timedelta(seconds=_HOLIDAYS_TTL_SECONDS):
        resp = jsonify(cached.get("data", []))
        resp.headers["Cache-Control"] = f"public, max-age={_HOLIDAYS_TTL_SECONDS}"
        return resp
    rows = Holiday.query.filter(Holiday.date >= start).filter(Holiday.date <= end).all()
    data = [h.to_dict() for h in rows]
    _HOLIDAYS_RANGE_CACHE[key] = {"data": data, "at": now}
    resp = jsonify(data)
    resp.headers["Cache-Control"] = f"public, max-age={_HOLIDAYS_TTL_SECONDS}"
    return resp


@bp.route("/holidays/year")
def holidays_by_year():
    """Return all holidays for a given year. Query param: year=YYYY"""
    year_raw = (request.args.get("year") or "").strip()
    try:
        year = int(year_raw)
    except Exception:
        year = 0
    if year <= 0:
        return jsonify([])
    now = _utcnow()
    cached = _HOLIDAYS_YEAR_CACHE.get(year)
    cached_at = _ensure_aware_utc(cached.get("at") if cached else None) if cached else None
    if cached and cached_at and (now - cached_at) <= timedelta(seconds=_HOLIDAYS_TTL_SECONDS):
        resp = jsonify(cached.get("data", []))
        resp.headers["Cache-Control"] = f"public, max-age={_HOLIDAYS_TTL_SECONDS}"
        return resp
    rows = Holiday.query.filter(Holiday.year == year).all()
    data = [h.to_dict() for h in rows]
    _HOLIDAYS_YEAR_CACHE[year] = {"data": data, "at": now}
    resp = jsonify(data)
    resp.headers["Cache-Control"] = f"public, max-age={_HOLIDAYS_TTL_SECONDS}"
    return resp


@bp.route("/cache/clear", methods=["POST"])  # lightweight noop for client hard refresh
def cache_clear():
    try:
        _invalidate_holidays_cache()
    except Exception:
        pass
    # No server-wide caches besides holidays; respond OK
    return jsonify({"status": "success"})
