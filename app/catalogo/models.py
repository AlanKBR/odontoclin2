from datetime import datetime

from .. import db


class CategoriaTratamento(db.Model):
    __bind_key__ = "tratamentos"
    __tablename__ = "categoria_tratamento"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    tratamentos = db.relationship("Tratamento", backref="categoria", lazy="dynamic")


class Tratamento(db.Model):
    __bind_key__ = "tratamentos"
    __tablename__ = "tratamento"
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categoria_tratamento.id"), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Float, nullable=False, default=0.0)
    duracao_estimada = db.Column(db.String(50))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
