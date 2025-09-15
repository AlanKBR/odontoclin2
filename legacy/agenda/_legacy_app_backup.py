import datetime as dt
import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, or_, text

try:
    import requests  # type: ignore
except Exception:
    requests = None  # will be validated at runtime

app = Flask(__name__)
# Usar caminho absoluto para o banco dentro de instance/
# (evita problemas de path no Windows)
basedir = os.path.abspath(os.path.dirname(__file__))
db_file = os.path.join(basedir, "instance", "calendario.db")
db_uri = "sqlite:///" + db_file.replace("\\", "/")
app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Helpers: timezone-aware UTC now and coercion for cached values
# UTC constant from datetime module (Python 3.11+)
UTC = dt.UTC


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _ensure_aware_utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    try:
        if d.tzinfo is None:
            return d.replace(tzinfo=UTC)
        return d.astimezone(UTC)
    except Exception:
        return d


# SQLAlchemy model for events


class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start = db.Column(db.String(30), nullable=False)
    end = db.Column(db.String(30), nullable=False)
    color = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    # Novo: vínculo opcional ao dentista (users.id em instance/users.db)
    profissional_id = db.Column(db.Integer, nullable=True)

    def __init__(
        self,
        title,
        start,
        end,
        color=None,
        notes=None,
        profissional_id=None,
    ):
        self.title = title
        self.start = start
        self.end = end
        self.color = color
        self.notes = notes
        self.profissional_id = profissional_id

    def to_dict(self):
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
            # Para filtragem no cliente
            "profissional_id": self.profissional_id,
        }


# Simple key-value settings table (e.g., to store Invertexto token)
class AppSetting(db.Model):
    __tablename__ = "app_settings"
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(1000), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Holidays table to cache Invertexto results (not treated as events)
class Holiday(db.Model):
    __tablename__ = "holidays"
    date = db.Column(db.String(10), primary_key=True)  # YYYY-MM-DD
    name = db.Column(db.String(200), nullable=False)
    # feriado | facultativo | ...
    type = db.Column(db.String(50), nullable=True)
    # nacional | estadual | ...
    level = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(5), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(50), nullable=False, default="invertexto")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "date": self.date,
            "name": self.name,
            "type": self.type,
            "level": self.level,
            "state": self.state,
            "year": self.year,
            "source": self.source,
        }


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


def _load_valid_dentist_ids() -> set[int]:
    """Carrega os IDs válidos de dentistas a partir de instance/users.db.
    Em caso de erro ou arquivo inexistente, retorna set() (nenhum válido
    conhecido).
    """
    # Cache em memória (TTL + mtime do arquivo)
    # Evita reabrir o DB a cada requisição de /events sem seleção de dentistas
    try:
        db_path = os.path.join(basedir, "instance", "users.db")
        if not os.path.exists(db_path):
            return set()
        # atributos de cache
        now = _utcnow()
        ttl = timedelta(seconds=60)
        mtime = os.path.getmtime(db_path)
        cache = getattr(_load_valid_dentist_ids, "_cache", None)
        if cache and isinstance(cache, dict):
            last_mtime = cache.get("mtime")
            cached_at = _ensure_aware_utc(cache.get("at"))
            cached_ids = cache.get("ids")
            if (
                cached_ids is not None
                and last_mtime == mtime
                and cached_at
                and (now - cached_at) <= ttl
            ):
                return cached_ids  # type: ignore[return-value]
        # recarregar do DB
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cur.fetchall()]
            if "id" not in cols:
                ids: set[int] = set()
            else:
                cur.execute("SELECT id FROM users")
                ids = {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}
        finally:
            try:
                conn.close()
            except Exception:
                pass
        # salvar cache
        setattr(
            _load_valid_dentist_ids,
            "_cache",
            {"ids": ids, "mtime": mtime, "at": now},
        )
        return ids
    except Exception:
        return set()


# ===== Server-side caches (in-memory) =====
# Dentists list cache: avoid hitting users.db repeatedly.
def _load_dentists_list_cached(
    ttl_seconds: int = 300,
) -> tuple[list[dict], float]:
    """Return (dentists_list, users_db_mtime).

    Caches by users.db mtime and a TTL. If users.db is missing or the table is
    incompatible, returns empty list with mtime=0.
    """
    try:
        db_path = os.path.join(basedir, "instance", "users.db")
        if not os.path.exists(db_path):
            return [], 0.0
        now = _utcnow()
        mtime = os.path.getmtime(db_path)
        cache = getattr(_load_dentists_list_cached, "_cache", None)
        if cache and isinstance(cache, dict):
            last_mtime = cache.get("mtime")
            cached_at = _ensure_aware_utc(cache.get("at"))
            dentists = cache.get("dentists") or []
            if (
                dentists is not None
                and last_mtime == mtime
                and cached_at
                and (now - cached_at) <= timedelta(seconds=ttl_seconds)
            ):
                return dentists, mtime  # type: ignore[return-value]

        # Recompute from DB
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cur.fetchall()]
            if "id" not in cols:
                dentists: list[dict] = []
            else:
                name_candidates = [
                    "nome_profissional",
                    "nome",
                    "name",
                    "full_name",
                    "username",
                ]
                name_col = next((c for c in name_candidates if c in cols), None)
                if not name_col:
                    name_col = "id"
                color_col = "color" if "color" in cols else ("cor" if "cor" in cols else None)
                sel_cols = [
                    "id",
                    name_col,
                ] + ([color_col] if color_col else [])
                q = f"SELECT {', '.join(sel_cols)} FROM users " f"ORDER BY {name_col}"
                cur.execute(q)
                rows = cur.fetchall()
                dentists = []
                for r in rows:
                    did = r["id"]
                    name = r[name_col]
                    color_val = r[color_col] if color_col else None
                    dentists.append({"id": did, "nome": name, "color": color_val})
        finally:
            try:
                conn.close()
            except Exception:
                pass
        setattr(
            _load_dentists_list_cached,
            "_cache",
            {"dentists": dentists, "mtime": mtime, "at": now},
        )
        return dentists, mtime
    except Exception:
        return [], 0.0


# Holidays caches
_HOLIDAYS_YEAR_CACHE: dict[int, dict] = {}
_HOLIDAYS_RANGE_CACHE: dict[tuple[str, str], dict] = {}
_HOLIDAYS_TTL_SECONDS = 3600  # 1h


def _invalidate_holidays_cache() -> None:
    _HOLIDAYS_YEAR_CACHE.clear()
    _HOLIDAYS_RANGE_CACHE.clear()


def _invalidate_dentists_caches() -> None:
    """Invalidate dentists-related in-memory caches."""
    try:
        if hasattr(_load_dentists_list_cached, "_cache"):
            delattr(_load_dentists_list_cached, "_cache")
    except Exception:
        pass
    try:
        if hasattr(_load_valid_dentist_ids, "_cache"):
            delattr(_load_valid_dentist_ids, "_cache")
    except Exception:
        pass


@app.route("/cache/clear", methods=["POST"])
def clear_all_caches():
    """Clear server-side in-memory caches (holidays, dentists)."""
    try:
        _invalidate_holidays_cache()
    except Exception:
        pass
    try:
        _invalidate_dentists_caches()
    except Exception:
        pass
    return jsonify({"status": "success"})


# Utilitários de data/hora: aceitar BR (dd/mm/aaaa[ HH:MM[:SS]])
# e ISO (YYYY-MM-DD[THH:MM[:SS]])
def _try_parse(fmt: str, s: str):
    try:
        return datetime.strptime(s, fmt)
    except Exception:
        return None


def parse_input_datetime(raw: str):
    """Aceita valores em pt-BR e ISO.
    Retorna (dt, is_date_only) ou (None, None).
    """
    if not raw:
        return None, None
    s = str(raw).strip()
    # pt-BR com hora
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        dt = _try_parse(fmt, s)
        if dt:
            return dt, False
    # pt-BR só data
    dt = _try_parse("%d/%m/%Y", s)
    if dt:
        return dt, True
    # ISO com hora
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
    ):
        dt = _try_parse(fmt, s)
        if dt:
            return dt, False
    # ISO só data
    dt = _try_parse("%Y-%m-%d", s)
    if dt:
        return dt, True
    # Fallback: dateutil com dayfirst
    try:
        from dateutil.parser import parse as du_parse

        dt = du_parse(s, dayfirst=True)
        # Heurística: se string tem apenas dígitos/sep e tamanho 10,
        # considerar date-only
        is_date_only = len(s) == 10 and s.count("/") + s.count("-") in (2,)
        return dt, is_date_only
    except Exception:
        return None, None


def normalize_for_storage(dt: datetime, is_date_only: bool) -> str:
    """Normaliza para armazenamento: ISO (YYYY-MM-DD)
    ou (YYYY-MM-DDTHH:MM:SS).
    """
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d") if is_date_only else dt.strftime("%Y-%m-%dT%H:%M:%S")


def _color_hexes_for_query(query_text: str) -> list[str]:
    q = (query_text or "").strip().lower()
    if not q:
        return []
    # Mapeamento de palavras -> hex (paleta do menu de cores)
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
    # aceitar busca por hex direto (#rrggbb)
    if q.startswith("#") and len(q) in (4, 7):
        hexes.append(q)
    # normalizar únicos
    seen = set()
    uniq = []
    for h in hexes:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def _apply_query_filters(base_query, query_text: str):
    qtxt = (query_text or "").strip().lower()
    if not qtxt:
        return base_query
    like = f"%{qtxt}%"
    col_title = getattr(CalendarEvent, "title")
    col_notes = getattr(CalendarEvent, "notes")
    title_match = col_title.ilike(like)
    notes_match = col_notes.ilike(like)
    color_hexes = _color_hexes_for_query(qtxt)
    if color_hexes:
        col_color = getattr(CalendarEvent, "color")
        color_match = col_color.in_(color_hexes)
        return base_query.filter(or_(title_match, notes_match, color_match))
    return base_query.filter(or_(title_match, notes_match))


@app.route("/events")
def get_events():
    # Optional range filtering from FullCalendar: start/end (ISO).
    # End is exclusive.
    range_start = (request.args.get("start") or "").strip()
    range_end = (request.args.get("end") or "").strip()
    q = CalendarEvent.query
    # Server-side search (title, notes, color by word)
    query_text = (request.args.get("q") or "").strip()
    # Filtrar por dentistas selecionados (CSV de ids inteiros)
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
        # Sem ids selecionados
        try:
            col_prof = getattr(CalendarEvent, "profissional_id")
            if include_unassigned:
                # Somente "Todos (sem dentista)" selecionado:
                # retornar apenas sem dentista
                q = q.filter(col_prof.is_(None))
            else:
                # Nenhuma opção marcada:
                # apenas inválidos (ignora sem dentista)
                valid_ids = _load_valid_dentist_ids()
                q = q.filter(col_prof.is_not(None))
                if valid_ids:
                    q = q.filter(~col_prof.in_(list(valid_ids)))
        except Exception:
            # Se a coluna não existir, manter comportamento padrão (sem filtro)
            pass
    # When both start and end present, restrict to events that
    # intersect the range: event.end >= start AND event.start < end
    # Se houver busca (q), ignore range para retornar todos os resultados
    if range_start and range_end and not query_text:
        try:
            # basic sanity check on formats
            # accept YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS]
            if len(range_start) >= 10 and len(range_end) >= 10:
                col_end = getattr(CalendarEvent, "end")
                col_start = getattr(CalendarEvent, "start")
                q = q.filter(col_end >= range_start)
                q = q.filter(col_start < range_end)
        except Exception:
            # fallback to full list if parsing fails
            pass
    # Aplicar busca por título/notas/cor
    if query_text:
        q = _apply_query_filters(q, query_text)
    try:
        events = q.all()
        return jsonify([event.to_dict() for event in events])
    except Exception as e:
        # Fallback: se a coluna 'profissional_id' não existe,
        # refazer sem filtro
        msg = str(e).lower()
        if "no such column" in msg and "profissional_id" in msg:
            try:
                q2 = CalendarEvent.query
                # manter apenas o filtro de data, se houver
                if range_start and range_end:
                    try:
                        if len(range_start) >= 10 and len(range_end) >= 10:
                            col_end = getattr(CalendarEvent, "end")
                            col_start = getattr(CalendarEvent, "start")
                            q2 = q2.filter(col_end >= range_start)
                            q2 = q2.filter(col_start < range_end)
                    except Exception:
                        pass
                events = q2.all()
                return jsonify([event.to_dict() for event in events])
            except Exception:
                return jsonify([])
        # Outro erro inesperado
        return jsonify([])


@app.route("/events/search_range")
def events_search_range():
    """Retorna o intervalo e a contagem dos eventos que casam a busca e
    filtros atuais, ignorando o range da visão.
    Params: q, dentists, include_unassigned.
    """
    q = CalendarEvent.query
    # filtros de dentista
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
        # Sem ids selecionados
        try:
            col_prof = getattr(CalendarEvent, "profissional_id")
            if include_unassigned:
                # Somente "Todos (sem dentista)" selecionado:
                # somente sem dentista
                q = q.filter(col_prof.is_(None))
            else:
                # Nenhuma opção marcada => apenas inválidos
                valid_ids = _load_valid_dentist_ids()
                q = q.filter(col_prof.is_not(None))
                if valid_ids:
                    q = q.filter(~col_prof.in_(list(valid_ids)))
        except Exception:
            pass
    # aplicar q
    query_text = (request.args.get("q") or "").strip()
    if query_text:
        q = _apply_query_filters(q, query_text)
    try:
        events = q.all()
        if not events:
            return jsonify({"min": None, "max": None, "count": 0})
        # Como usamos formato ISO no armazenamento, comparação lexical funciona
        starts = [e.start for e in events if e.start]
        ends = [e.end for e in events if e.end]
        min_start = min(starts) if starts else None
        max_end = max(ends) if ends else None
        return jsonify(
            {
                "min": min_start,
                "max": max_end,
                "count": len(events),
            }
        )
    except Exception:
        return jsonify({"min": None, "max": None, "count": 0})


@app.route("/add_event", methods=["POST"])
def add_event():
    data = request.get_json()
    raw_start = data.get("start")
    raw_end = data.get("end")
    start_dt, start_is_date_only = parse_input_datetime(raw_start)
    end_dt, end_is_date_only = parse_input_datetime(raw_end) if raw_end else (None, None)

    if not start_dt:
        return jsonify({"status": "error", "message": "Start inválido"}), 400

    # Caso all-day (data pura): end = start + 1 dia, se ausente ou inválido
    if start_is_date_only:
        if not end_dt or not end_is_date_only:
            end_dt = start_dt + timedelta(days=1)
            end_is_date_only = True
        elif end_dt <= start_dt:
            end_dt = start_dt + timedelta(days=1)
    else:
        # Caso com hora: se end ausente, padrão = +1h
        if not end_dt:
            end_dt = start_dt + timedelta(hours=1)
            end_is_date_only = False
        elif end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)
            end_is_date_only = False

    # Garantir tipos booleanos (para linters) –
    # aqui nunca serão None se dt válido
    start_is_date_only = bool(start_is_date_only)
    end_is_date_only = bool(end_is_date_only)
    new_start = normalize_for_storage(start_dt, start_is_date_only)
    new_end = normalize_for_storage(end_dt, end_is_date_only)
    new_event = CalendarEvent(
        title=data["title"],
        start=new_start,
        end=new_end,
        color=data.get("color"),
        notes=data.get("notes"),
        profissional_id=(
            int(data.get("profissional_id"))
            if str(data.get("profissional_id" or "")).isdigit()
            else None
        ),
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify({"status": "success", "event": new_event.to_dict()})


# Endpoint to delete an event by id
@app.route("/delete_event", methods=["POST"])
def delete_event():
    data = request.get_json()
    event_id = data.get("id")
    event = db.session.get(CalendarEvent, event_id)
    if event:
        db.session.delete(event)
        db.session.commit()
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Event not found"}), 404


# Endpoint to update event (date/time)
@app.route("/update_event", methods=["POST"])
def update_event():
    data = request.get_json()
    event_id = data.get("id")
    raw_start = data.get("start")
    raw_end = data.get("end")

    event = db.session.get(CalendarEvent, event_id)
    if event:
        start_dt, start_is_date_only = (
            parse_input_datetime(raw_start) if raw_start else (None, None)
        )
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
            # Garantir tipos booleanos
            start_is_date_only = bool(start_is_date_only)
            end_is_date_only = bool(end_is_date_only)
            event.start = normalize_for_storage(start_dt, start_is_date_only)
            if end_dt:
                event.end = normalize_for_storage(end_dt, end_is_date_only)
            else:
                event.end = None
        # Atualização opcional do dentista
        try:
            if "profissional_id" in data:
                pid = data.get("profissional_id")
                event.profissional_id = int(pid) if str(pid).isdigit() else None
        except Exception:
            pass
        db.session.commit()
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Event not found"}), 404


# Endpoint to update event color
@app.route("/update_event_color", methods=["POST"])
def update_event_color():
    data = request.get_json()
    event_id = data.get("id")
    color = data.get("color")
    event = db.session.get(CalendarEvent, event_id)
    if event:
        event.color = color
        db.session.commit()
        return jsonify({"status": "success", "color": color})
    else:
        return jsonify({"status": "error", "message": "Event not found"}), 404


# Endpoint to update event notes (description)
@app.route("/update_event_notes", methods=["POST"])
def update_event_notes():
    data = request.get_json()
    event_id = data.get("id")
    notes = data.get("notes", "")
    event = db.session.get(CalendarEvent, event_id)
    if event:
        event.notes = notes
        db.session.commit()
        return jsonify({"status": "success", "notes": notes})
    else:
        return jsonify({"status": "error", "message": "Event not found"}), 404


# ===== Dentists (users.db) =====
@app.route("/dentists")
def listar_dentistas():
    """Retorna lista de dentistas a partir de instance/users.db
    com id, nome e cor (pode ser None). Se cor for None, o cliente usa padrão.
    """
    dentists, mtime = _load_dentists_list_cached()
    # ETag simples com base em mtime e tamanho da lista
    etag = f"{int(mtime)}:{len(dentists)}"
    inm = request.headers.get("If-None-Match")
    headers = {
        "Cache-Control": "public, max-age=300",
        "ETag": etag,
    }
    if inm and inm == etag:
        # curto-circuito 304
        return "", 304, headers
    resp = jsonify(dentists)
    for k, v in headers.items():
        resp.headers[k] = v
    return resp


# Endpoint para listar nomes de pacientes
@app.route("/pacientes")
def listar_pacientes():
    """Retorna lista de pacientes do banco pacientes.db"""
    engine = create_engine("sqlite:///instance/pacientes.db")
    with engine.connect() as conn:
        query = "SELECT id, nome FROM pacientes ORDER BY nome"
        result = conn.execute(text(query))
        pacientes = [{"id": row[0], "nome": row[1]} for row in result]
    return jsonify(pacientes)


# Endpoint para buscar nomes de pacientes para autocompletar
@app.route("/buscar_nomes")
def buscar_nomes():
    """Retorna lista de nomes de pacientes contendo o trecho buscado"""
    query = request.args.get("q", "").strip()
    nomes = []

    # Busca a partir de 1 caractere (case-insensitive),
    # mas apenas nomes/sobrenomes que começam com o trecho
    if query and len(query) >= 1:
        # Padrões: início do nome (q%) OU após espaço (" q%")
        # Utiliza NOCASE para ignorar maiúsculas/minúsculas
        try:
            conn = sqlite3.connect("instance/pacientes.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nome FROM pacientes "
                "WHERE (nome LIKE ? COLLATE NOCASE) "
                "   OR (nome LIKE ? COLLATE NOCASE) "
                "ORDER BY nome LIMIT 20",
                (f"{query}%", f"% {query}%"),
            )
            for row in cursor.fetchall():
                if row[0]:
                    nomes.append(row[0])
            conn.close()
        except Exception as e:
            print(f"Erro ao buscar pacientes: {e}")

    # Limitar o total de resultados
    return jsonify(nomes[:20])


# Endpoint para buscar telefone do paciente pelo nome
@app.route("/buscar_telefone")
def buscar_telefone():
    """Retorna o telefone de um paciente baseado no nome"""
    nome = request.args.get("nome", "").strip()

    if not nome:
        return jsonify({"telefone": None})

    try:
        conn = sqlite3.connect("instance/pacientes.db")
        cursor = conn.cursor()

        # Buscar primeiro por nome exato
        cursor.execute(
            ("SELECT celular FROM pacientes " "WHERE LOWER(nome) = LOWER(?) LIMIT 1"),
            (nome,),
        )
        result = cursor.fetchone()

        # Se não encontrou, buscar por nome que contenha o termo
        if not result:
            cursor.execute(
                "SELECT celular FROM pacientes WHERE LOWER(nome) LIKE " "LOWER(?) LIMIT 1",
                (f"%{nome}%",),
            )
            result = cursor.fetchone()

        conn.close()

        if result and result[0]:
            return jsonify({"telefone": result[0]})
        else:
            return jsonify({"telefone": None})

    except Exception as e:
        print(f"Erro ao buscar telefone: {e}")
        return jsonify({"telefone": None})


@app.route("/")
def index():
    return render_template("calendar.html")


# ===== Invertexto Holidays integration =====


@app.route("/settings/invertexto_token", methods=["GET", "POST", "DELETE"])
def invertexto_token():
    """GET: returns whether a token is configured (does not return the token).
    POST: sets/updates the token. Body: { token: '...' }.
    DELETE: clears the stored token.
    """
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


@app.route("/holidays/refresh", methods=["POST"])
def holidays_refresh():
    """Fetch holidays from Invertexto for a given year and optional state (UF),
    then upsert into local DB. Body: { year: 2025, state?: 'SP' }"""
    if requests is None:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": ("Dependência 'requests' ausente"),
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
            jsonify(
                {
                    "status": "error",
                    "message": "Token não configurado",
                }
            ),
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
                jsonify(
                    {
                        "status": "error",
                        "message": ("Resposta inesperada da API"),
                    }
                ),
                502,
            )
        # Replace holidays for this year/UF: delete old, then insert fresh
        try:
            # Remove todos os feriados do ano informado (independente de UF)
            # para evitar conflito de PK (date) entre estados diferentes.
            q = Holiday.query.filter(Holiday.year == year)
            q.delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": ("Falha ao limpar dados antigos"),
                    }
                ),
                500,
            )

        # Insert fresh rows
        count = 0
        for it in items:
            try:
                date = str(it.get("date") or "").strip()  # YYYY-MM-DD
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
        # invalidate server-side caches
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


@app.route("/holidays/range")
def holidays_in_range():
    """Return holidays between start and end (inclusive).
    Query params: start=YYYY-MM-DD&end=YYYY-MM-DD
    """
    start = (request.args.get("start") or "").strip()
    end = (request.args.get("end") or "").strip()
    if not start or not end:
        return jsonify([])
    try:
        # normalize and validate
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
    except Exception:
        return jsonify([])
    # SQLite string compare works for ISO dates
    # Try in-memory cache
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


@app.route("/holidays/year")
def holidays_by_year():
    """Return all holidays for a given year.
    Query param: year=YYYY
    """
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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Add a sample event if DB is empty
        if CalendarEvent.query.count() == 0:
            sample = CalendarEvent(
                title="Consulta Exemplo",
                start="2025-07-21T10:00:00",
                end="2025-07-21T11:00:00",
                color=None,
            )
            db.session.add(sample)
            db.session.commit()
    app.run(debug=True)
