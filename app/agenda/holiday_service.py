"""Serviços de feriados e cache da Agenda.

Isola lógica de cache (ano e intervalo), busca externa (Invertexto)
 e operações CRUD simples, permitindo testes unitários e futura
substituição de backend (ex: Redis) sem alterar rotas.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

from app import db

from .models import Holiday

# Caches em memória (process local)
_HOLIDAYS_YEAR_CACHE: dict[int, dict[str, Any]] = {}
_HOLIDAYS_RANGE_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_HOLIDAYS_TTL_SECONDS = 3600


def utcnow() -> datetime:  # pragma: no cover - trivial
    return datetime.now(UTC)


def ensure_aware_utc(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def invalidate_cache() -> None:
    _HOLIDAYS_YEAR_CACHE.clear()
    _HOLIDAYS_RANGE_CACHE.clear()


# ================= Intervalo ==================


def get_holidays_range(start: str, end: str) -> list[dict[str, Any]]:
    if not start or not end:
        return []
    # valida formato simples
    try:
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
    except Exception:
        return []
    key = (start, end)
    now = utcnow()
    cached = _HOLIDAYS_RANGE_CACHE.get(key)
    cached_at = ensure_aware_utc(cached.get("at") if cached else None) if cached else None
    if cached and cached_at and (now - cached_at) <= timedelta(seconds=_HOLIDAYS_TTL_SECONDS):
        return cached.get("data", [])  # type: ignore[return-value]
    rows: Iterable[Holiday] = (
        Holiday.query.filter(Holiday.date >= start).filter(Holiday.date <= end).all()
    )
    data = [h.to_dict() for h in rows]
    _HOLIDAYS_RANGE_CACHE[key] = {"data": data, "at": now}
    return data


# ================= Ano ==================


def get_holidays_year(year: int) -> list[dict[str, Any]]:
    if year <= 0:
        return []
    now = utcnow()
    cached = _HOLIDAYS_YEAR_CACHE.get(year)
    cached_at = ensure_aware_utc(cached.get("at") if cached else None) if cached else None
    if cached and cached_at and (now - cached_at) <= timedelta(seconds=_HOLIDAYS_TTL_SECONDS):
        return cached.get("data", [])  # type: ignore[return-value]
    rows: Iterable[Holiday] = Holiday.query.filter(Holiday.year == year).all()
    data = [h.to_dict() for h in rows]
    _HOLIDAYS_YEAR_CACHE[year] = {"data": data, "at": now}
    return data


# ================= Refresh via API ==================


def refresh_holidays(
    year: int,
    state: str | None,
    token: str,
    requests_mod,
) -> tuple[int | None, str | None]:
    """Busca feriados na API Invertexto e substitui registros do ano.

    Retorna (count, error). Em caso de erro count=None e error descreve.
    """
    if year <= 0:
        return None, "Ano inválido"
    if not token:
        return None, "Token não configurado"
    url = f"https://api.invertexto.com/v1/holidays/{year}"
    params: dict[str, Any] = {"token": token}
    if state:
        params["state"] = state
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests_mod.get(url, params=params, headers=headers, timeout=15)
    except Exception as e:  # pragma: no cover
        return None, f"Falha de requisição: {e}"
    if r.status_code != 200:
        code = r.status_code
        msg = f"Erro {code} da API"
        if code == 401:
            msg = "Não autorizado (401)"
        elif code == 400:
            msg = "Parâmetros inválidos (400)"
        elif code == 429:
            msg = "Limite excedido (429)"
        return None, msg
    try:
        items = r.json() if r.content else []
    except Exception:  # pragma: no cover
        return None, "JSON inválido"
    if not isinstance(items, list):
        return None, "Resposta inesperada"
    # Limpa registros existentes do ano
    try:
        Holiday.query.filter(Holiday.year == year).delete(synchronize_session=False)
        db.session.commit()
    except Exception:  # pragma: no cover
        db.session.rollback()
        return None, "Falha ao limpar dados antigos"
    count = 0
    for it in items:
        try:
            date_val = str(it.get("date") or "").strip()
            name_val = (it.get("name") or "").strip()
            htype = (it.get("type") or "").strip() or None
            level = (it.get("level") or "").strip() or None
            if not date_val or not name_val:
                continue
            rec = Holiday()
            rec.date = date_val
            rec.name = name_val
            rec.type = htype
            rec.level = level
            rec.state = state
            rec.year = year
            rec.source = "invertexto"
            db.session.add(rec)
            count += 1
        except Exception:  # pragma: no cover
            continue
    db.session.commit()
    try:
        invalidate_cache()
    except Exception:  # pragma: no cover
        pass
    return count, None


# ================= CRUD local (opcional) ==================


def add_holiday_record(
    data: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    required = ["date", "name", "year"]
    if any(k not in data for k in required):
        return None, "Campos obrigatórios ausentes"
    rec = Holiday()
    rec.date = data["date"]
    rec.name = data["name"]
    rec.type = data.get("type")
    rec.level = data.get("level")
    rec.state = data.get("state")
    rec.year = data["year"]
    rec.source = data.get("source", "invertexto")
    db.session.add(rec)
    db.session.commit()
    invalidate_cache()
    return rec.to_dict(), None


def update_holiday_record(
    holiday: Holiday,
    data: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    required = ["name", "year"]
    if any(k not in data for k in required):
        return None, "Campos obrigatórios ausentes"
    holiday.name = data["name"]
    holiday.type = data.get("type")
    holiday.level = data.get("level")
    holiday.state = data.get("state")
    holiday.year = data["year"]
    holiday.source = data.get("source", "invertexto")
    db.session.commit()
    invalidate_cache()
    return holiday.to_dict(), None
