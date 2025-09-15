from datetime import datetime

from app.extensions import db


class CategoriaTratamento(db.Model):
    __tablename__ = "categoria_tratamento"
    __bind_key__ = "tratamentos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.Text)

    # Relacionamento com tratamentos
    tratamentos = db.relationship("Tratamento", backref="categoria", lazy=True)

    def __repr__(self):
        return f"<CategoriaTratamento {self.nome}>"


class Tratamento(db.Model):
    __tablename__ = "tratamento"
    __bind_key__ = "tratamentos"

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categoria_tratamento.id"), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Float, nullable=False)
    duracao_estimada = db.Column(db.String(50))  # Em minutos ou formato hh:mm
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Tratamento {self.nome}>"
