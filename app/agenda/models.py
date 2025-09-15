"""Modelos da Agenda (extraídos das rotas para reduzir complexidade).

Mantém os mesmos binds e estrutura do legacy para compatibilidade com
as bases sqlite já existentes. Qualquer evolução (ex: constraints
adicionais) deve considerar migração manual pois sqlite não suporta
ALTER TABLE complexo facilmente.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app import db


class CalendarEvent(db.Model):  # type: ignore[misc]
    __bind_key__ = "calendario"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start = db.Column(db.String(30), nullable=False)
    end = db.Column(db.String(30), nullable=False)
    color = db.Column(db.String(20))
    notes = db.Column(db.String(500))
    profissional_id = db.Column(db.Integer)

    def to_dict(self) -> dict[str, Any]:
        from dateutil.parser import parse  # local import para evitar custo em import global

        try:  # detecção de allDay igual ao legacy
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
        except Exception:  # pragma: no cover - fallback simples
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


class AppSetting(db.Model):  # type: ignore[misc]
    __bind_key__ = "calendario"
    __tablename__ = "app_settings"
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(1000))


class Holiday(db.Model):  # type: ignore[misc]
    __bind_key__ = "calendario"
    __tablename__ = "holidays"
    date = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50))
    level = db.Column(db.String(50))
    state = db.Column(db.String(5))
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


# Models da agenda - migração futura (Fase 1)
