from datetime import datetime

from .. import db


class Documento(db.Model):
    """Modelo completo migrado (simplificado em alguns campos).

    Mantém bind pacientes para facilitar junções futuras com paciente.
    """

    __bind_key__ = "pacientes"
    __tablename__ = "documentos"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer)
    dentista_id = db.Column(db.Integer)
    tipo_documento = db.Column(db.String(50), nullable=False)
    titulo_documento = db.Column(db.String(200), nullable=False)
    conteudo_json = db.Column(db.Text, nullable=False)
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    local_emissao = db.Column(db.String(100), default="", nullable=False)
    observacoes = db.Column(db.Text, default="")

    def __repr__(self):  # pragma: no cover
        return f"<Documento {self.id} - {self.tipo_documento}>"

    # DocumentoSimples removido após migração de testes
