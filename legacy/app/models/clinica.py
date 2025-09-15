from datetime import datetime

from app.extensions import db


class Clinica(db.Model):
    __tablename__ = "clinica"
    __bind_key__ = "users"  # Usando o bind do users para configurações do sistema

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False, default="OdontoClinic")
    cro_clinica = db.Column(db.String(50), nullable=True)
    endereco = db.Column(db.String(300), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    celular = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    site = db.Column(db.String(100), nullable=True)
    cep = db.Column(db.String(10), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    cnpj = db.Column(db.String(20), nullable=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Clinica {self.nome}>"

    @classmethod
    def get_instance(cls):
        """Retorna a única instância de configuração da clínica ou cria uma nova"""
        clinica = cls.query.first()
        if not clinica:
            clinica = cls()
            clinica.nome = "OdontoClinic"
            db.session.add(clinica)
            db.session.commit()
        return clinica
