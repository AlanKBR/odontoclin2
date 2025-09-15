from datetime import datetime

from app.extensions import db


class Documento(db.Model):
    __tablename__ = "documentos"
    __bind_key__ = "pacientes"  # Usando o mesmo bind do paciente para simplificar

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, nullable=False)
    dentista_id = db.Column(db.Integer, nullable=False)
    tipo_documento = db.Column(
        db.String(50), nullable=False
    )  # Ex: 'autorizacao_imagem', 'interrupcao_tratamento'
    titulo_documento = db.Column(db.String(200), nullable=False)  # Nome amigável do documento
    conteudo_json = db.Column(db.Text, nullable=False)  # Dados específicos em JSON
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    local_emissao = db.Column(db.String(100), default="", nullable=False)
    observacoes = db.Column(db.Text, default="")  # Campo opcional para observações

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Documento {self.id} - {self.tipo_documento} - Paciente {self.paciente_id}>"

    @property
    def nome_paciente(self):
        """Retorna o nome do paciente (necessário relacionamento)"""
        from app.models.paciente import Paciente

        paciente = Paciente.query.get(self.paciente_id)
        return paciente.nome if paciente else "Paciente não encontrado"

    @property
    def nome_dentista(self):
        """Retorna o nome do dentista (necessário relacionamento)"""
        from app.models.user import User

        dentista = User.query.get(self.dentista_id)
        return dentista.nome_completo if dentista else "Dentista não encontrado"
