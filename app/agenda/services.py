"""Serviços da Agenda.

Separa lógica de domínio das rotas para facilitar testes unitários
e futuras otimizações (ex: cache, validações adicionais, regras de
negócio específicas por tipo de evento).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable, Sequence

from sqlalchemy import or_  # type: ignore

from app import db

from .models import CalendarEvent


# ===================== Utilidades de Data =====================
def _try_parse(fmt: str, s: str):  # pragma: no cover - função simples
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
    # Extra: aceitar ISO 8601 com timezone ("Z" ou offset "+HH:MM") sem depender de dateutil
    try:
        iso = s
        # fromisoformat não aceita 'Z'; converter para offset +00:00
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso)  # py3.11: aceita offsets
        # Heurística: se vier apenas data, len == 10
        is_date_only = len(s) == 10 and ("T" not in s)
        return dt, is_date_only
    except Exception:
        pass
    try:  # fallback flexível
        from dateutil.parser import parse as du_parse

        dt = du_parse(s, dayfirst=True)
        is_date_only = len(s) == 10 and s.count("/") + s.count("-") in (2,)
        return dt, is_date_only
    except Exception:  # pragma: no cover
        return None, None


def normalize_for_storage(dt: datetime, is_date_only: bool) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d") if is_date_only else dt.strftime("%Y-%m-%dT%H:%M:%S")


# ===================== Query Helpers =====================
def query_events_in_range(range_start: str, range_end: str):
    q = CalendarEvent.query
    if range_start and range_end and len(range_start) >= 10 and len(range_end) >= 10:
        try:
            q = q.filter(CalendarEvent.end >= range_start)
            q = q.filter(CalendarEvent.start < range_end)
        except Exception:  # pragma: no cover
            pass
    return q


def apply_query_filters(base_query, query_text: str):
    qtxt = (query_text or "").strip().lower()
    if not qtxt:
        return base_query
    like = f"%{qtxt}%"
    col_title = getattr(CalendarEvent, "title")
    col_notes = getattr(CalendarEvent, "notes")
    title_match = col_title.ilike(like)
    notes_match = col_notes.ilike(like)

    def color_hexes_for_query(query_text: str) -> list[str]:
        q = (query_text or "").strip().lower()
        if not q:
            return []
        color_words: dict[str, list[str]] = {
            "vermelho": ["#e11d48"],
            "rosa": ["#f43f5e", "#f472b6"],
            "laranja": ["#f59e42"],
            "amarelo": ["#fbbf24"],
            "verde": ["#22c55e"],
            "verde-agua": ["#10b981"],
            "verde agua": ["#10b981"],
            "azul": ["#2563eb"],
            "azul-claro": ["#0ea5e9"],
            "roxo": ["#6366f1"],
            "roxo-escuro": ["#a21caf"],
            "cinza": ["#64748b"],
        }
        hexes: list[str] = []
        for word, values in color_words.items():
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

    color_hexes = color_hexes_for_query(qtxt)
    if color_hexes:
        col_color = getattr(CalendarEvent, "color")
        color_match = col_color.in_(color_hexes)
        return base_query.filter(or_(title_match, notes_match, color_match))
    return base_query.filter(or_(title_match, notes_match))


# ===================== CRUD Serviços =====================
def list_events(
    range_start: str,
    range_end: str,
    query_text: str = "",
    profissional_ids: Sequence[int] | None = None,
    include_unassigned: bool = False,
    invalid_only: bool = False,
    valid_ids: set[int] | None = None,
) -> list[dict[str, Any]]:
    q = query_events_in_range(range_start, range_end)
    if profissional_ids is not None and len(profissional_ids) > 0:
        col_prof = getattr(CalendarEvent, "profissional_id")
        if include_unassigned:
            q = q.filter(or_(col_prof.in_(list(profissional_ids)), col_prof.is_(None)))
        else:
            q = q.filter(col_prof.in_(list(profissional_ids)))
    elif invalid_only:
        col_prof = getattr(CalendarEvent, "profissional_id")
        q = q.filter(CalendarEvent.profissional_id.is_not(None))
        if valid_ids:
            q = q.filter(~CalendarEvent.profissional_id.in_(list(valid_ids)))
    elif include_unassigned:
        col_prof = getattr(CalendarEvent, "profissional_id")
        q = q.filter(col_prof.is_(None))
    if query_text:
        q = apply_query_filters(q, query_text)
    try:
        events: Iterable[CalendarEvent] = q.all()
    except Exception:  # pragma: no cover
        return []
    return [e.to_dict() for e in events]


def create_event(
    data: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    raw_start = data.get("start")
    raw_end = data.get("end")
    start_dt, start_is_date_only = parse_input_datetime(raw_start)
    end_dt, end_is_date_only = parse_input_datetime(raw_end) if raw_end else (None, None)
    if not start_dt:
        return None, "Start inválido"
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
    ev = CalendarEvent()
    ev.title = str(data.get("title") or "").strip()
    ev.start = normalize_for_storage(start_dt, start_is_date_only)
    ev.end = normalize_for_storage(end_dt, end_is_date_only)
    ev.color = data.get("color")
    ev.notes = data.get("notes")
    pid_raw = data.get("profissional_id")
    ev.profissional_id = (
        int(pid_raw) if isinstance(pid_raw, (int, str)) and str(pid_raw).isdigit() else None
    )
    db.session.add(ev)
    db.session.commit()
    return ev.to_dict(), None


def update_event_fields(event: CalendarEvent, data: dict[str, Any]) -> None:
    if "title" in data:
        event.title = str(data.get("title") or "").strip()
    if "color" in data:
        event.color = data.get("color")
    if "notes" in data:
        event.notes = data.get("notes")
    if "profissional_id" in data:
        pid_raw = data.get("profissional_id")
        event.profissional_id = (
            int(pid_raw) if isinstance(pid_raw, (int, str)) and str(pid_raw).isdigit() else None
        )


def update_event_with_dates(event: CalendarEvent, data: dict[str, Any]) -> None:
    raw_start = data.get("start")
    raw_end = data.get("end")
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


def delete_event(event: CalendarEvent) -> None:
    db.session.delete(event)
    db.session.commit()


def set_event_color(event: CalendarEvent, color: str | None):
    event.color = color
    db.session.commit()


def set_event_notes(event: CalendarEvent, notes: str):
    event.notes = notes
    db.session.commit()
