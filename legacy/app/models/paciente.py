from datetime import datetime

from app.extensions import db


class Paciente(db.Model):
    __tablename__ = "pacientes"
    __bind_key__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(10))
    cpf = db.Column(db.String(14), unique=True)
    telefone = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    email = db.Column(db.String(120))
    endereco = db.Column(db.String(200))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    profissao = db.Column(db.String(100))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relações
    ficha = db.relationship(
        "Ficha", backref="paciente", uselist=False, cascade="all, delete-orphan"
    )
    anamnese = db.relationship(
        "Anamnese", backref="paciente", uselist=False, cascade="all, delete-orphan"
    )
    planos_tratamento = db.relationship(
        "PlanoTratamento",
        backref="paciente",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    historicos = db.relationship(
        "Historico", backref="paciente", lazy="dynamic", cascade="all, delete-orphan"
    )
    financeiros = db.relationship(
        "Financeiro", backref="paciente", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Paciente {self.nome}>"


class Ficha(db.Model):
    __tablename__ = "fichas"  # Assuming table name is fichas
    __bind_key__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    responsavel = db.Column(db.String(100))
    contato_emergencia = db.Column(db.String(100))
    convenio = db.Column(db.String(100))
    numero_convenio = db.Column(db.String(50))
    alergias = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    ultima_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Anamnese(db.Model):
    __tablename__ = "anamneses"  # Assuming table name is anamneses
    __bind_key__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    historico_medico = db.Column(db.Text)
    medicamentos_uso = db.Column(db.Text)
    cirurgias_previas = db.Column(db.Text)
    doencas_cronicas = db.Column(db.Text)
    habitos = db.Column(db.Text)
    problemas_dentarios = db.Column(db.Text)
    ultima_visita_dentista = db.Column(db.String(100))
    data_preenchimento = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanoTratamento(db.Model):
    __tablename__ = "plano_tratamento"
    __bind_key__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    dentista_id = db.Column(db.Integer)  # Apenas o ID, sem relacionamento ORM
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    descricao = db.Column(db.Text, nullable=False)
    # Pendente, Em andamento, Concluído, Cancelado
    status = db.Column(db.String(20), default="Pendente")
    orcamento_total = db.Column(db.Float, default=0.0)
    observacoes = db.Column(db.Text)

    # Relação com os procedimentos do plano
    procedimentos = db.relationship(
        "Procedimento",
        backref="plano_tratamento",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class Procedimento(db.Model):
    __tablename__ = "procedimentos"
    __bind_key__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    plano_id = db.Column(db.Integer, db.ForeignKey("plano_tratamento.id"), nullable=False)
    tratamento_id = db.Column(db.Integer)  # Removed db.ForeignKey("tratamento.id")
    descricao = db.Column(db.String(200), nullable=False)
    # Now can contain multiple teeth numbers or "Boca completa"
    dente = db.Column(db.String(100))
    dentes_selecionados = db.Column(db.Text)  # JSON data of selected teeth
    # Quadrants selection (comma separated)
    quadrantes = db.Column(db.String(20))
    # If entire mouth is selected
    boca_completa = db.Column(db.Boolean, default=False)
    valor = db.Column(db.Float, default=0.0)
    # Pendente, Realizado, Cancelado
    status = db.Column(db.String(20), default="Pendente")
    data_prevista = db.Column(db.Date)
    data_realizado = db.Column(db.Date)
    observacoes = db.Column(db.Text)

    # Relação com o catálogo de tratamentos
    tratamento = db.relationship(
        "Tratamento",
        primaryjoin="foreign(Procedimento.tratamento_id) == remote(Tratamento.id)",
        backref="procedimentos_associados",  # Changed backref name
        lazy=True,
    )


class Historico(db.Model):
    __tablename__ = "historicos"
    __bind_key__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    dentista_id = db.Column(db.Integer)  # Apenas o ID, sem relacionamento ORM
    data = db.Column(db.DateTime, default=datetime.utcnow)
    descricao = db.Column(db.Text, nullable=False)
    procedimentos_realizados = db.Column(db.Text)
    observacoes = db.Column(db.Text)


class Financeiro(db.Model):
    __tablename__ = "financeiro"
    __bind_key__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    plano_id = db.Column(db.Integer, db.ForeignKey("plano_tratamento.id"))
    data_lancamento = db.Column(db.DateTime, default=datetime.utcnow)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(20))  # Crédito ou Débito
    forma_pagamento = db.Column(db.String(50))  # Dinheiro, Cartão, Pix, etc.
    # Pendente, Pago, Cancelado
    status = db.Column(db.String(20), default="Pendente")
    data_pagamento = db.Column(db.Date)
    observacoes = db.Column(db.Text)
