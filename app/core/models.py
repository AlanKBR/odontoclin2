"""Modelos centrais / globais.

Inclui migração incremental do modelo Clinica (do legacy) para suportar
documentos avançados (cabeçalho, assinatura institucional etc.). Mantém
bind em 'users' para armazenar configuração administrativa única.

Simplificado: apenas campos usados atualmente em geração de documentos.
Pode ser expandido conforme necessidade (email, site etc.).
"""

from datetime import datetime

from .. import db


class Clinica(db.Model):  # pragma: no cover - acesso indireto em runtime
    __tablename__ = "clinica"
    __bind_key__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False, default="OdontoClinic")
    endereco = db.Column(db.String(300))
    telefone = db.Column(db.String(20))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cnpj = db.Column(db.String(20))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_instance(cls):  # pragma: no cover - simples
        inst = cls.query.first()
        if not inst:
            inst = cls()
            db.session.add(inst)
            db.session.commit()
        return inst

    def __repr__(self):  # pragma: no cover
        return f"<Clinica {self.nome}>"
