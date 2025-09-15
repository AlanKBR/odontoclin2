from datetime import date, datetime

from sqlalchemy import CheckConstraint, event, text

from .. import db


class Paciente(db.Model):
    __bind_key__ = "pacientes"
    __tablename__ = "pacientes"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_nascimento = db.Column(db.Date)
    sexo = db.Column(db.String(15))
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
    deleted_at = db.Column(db.DateTime)  # soft delete
    # Relacionamentos (lazy simples)
    fichas = db.relationship("Ficha", backref="paciente", lazy="dynamic")
    anamneses = db.relationship("Anamnese", backref="paciente", lazy="dynamic")
    planos = db.relationship("PlanoTratamento", backref="paciente", lazy="dynamic")
    historicos = db.relationship("Historico", backref="paciente", lazy="dynamic")
    financeiros = db.relationship("Financeiro", backref="paciente", lazy="dynamic")

    def idade(self) -> int | None:
        if not self.data_nascimento:
            return None
        hoje = date.today()
        anos = hoje.year - self.data_nascimento.year
        if (hoje.month, hoje.day) < (
            self.data_nascimento.month,
            self.data_nascimento.day,
        ):
            anos -= 1
        return anos


class Ficha(db.Model):
    __bind_key__ = "pacientes"
    __tablename__ = "fichas"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    responsavel = db.Column(db.String(100))
    contato_emergencia = db.Column(db.String(100))
    convenio = db.Column(db.String(100))
    numero_convenio = db.Column(db.String(50))
    alergias = db.Column(db.Text)
    observacoes = db.Column(db.Text)


class Anamnese(db.Model):
    __bind_key__ = "pacientes"
    __tablename__ = "anamneses"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    historico_medico = db.Column(db.Text)
    medicamentos_uso = db.Column(db.Text)
    cirurgias_previas = db.Column(db.Text)
    doencas_cronicas = db.Column(db.Text)
    habitos = db.Column(db.Text)
    problemas_dentarios = db.Column(db.Text)
    ultima_visita_dentista = db.Column(db.String(100))
    ultima_atualizacao = db.Column(db.DateTime, default=datetime.utcnow)


class PlanoTratamento(db.Model):
    __bind_key__ = "pacientes"
    __tablename__ = "plano_tratamento"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Pendente")
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    # Precisão financeira usando Numeric (Decimal) para evitar erros de
    # ponto flutuante. 12 dígitos totais, 2 casas decimais.
    orcamento_total = db.Column(db.Numeric(12, 2), default=0)
    procedimentos = db.relationship("Procedimento", backref="plano", lazy="dynamic")


class Procedimento(db.Model):
    __bind_key__ = "pacientes"
    __tablename__ = "procedimentos"
    id = db.Column(db.Integer, primary_key=True)
    plano_id = db.Column(db.Integer, db.ForeignKey("plano_tratamento.id"), nullable=False)
    # Campos adicionais (legacy) sem FK cross-bind para catálogo
    tratamento_id = db.Column(db.Integer)
    descricao = db.Column(db.String(200), nullable=False)
    dente = db.Column(db.String(100))
    dentes_selecionados = db.Column(db.Text)  # JSON (lista) opcional
    quadrantes = db.Column(db.String(20))  # ex: "Q1,Q2"
    boca_completa = db.Column(db.Boolean, default=False)
    valor = db.Column(db.Numeric(12, 2), default=0)
    status = db.Column(db.String(30), default="Pendente")
    data_prevista = db.Column(db.Date)
    data_realizado = db.Column(db.Date)
    observacoes = db.Column(db.Text)


class Historico(db.Model):
    __bind_key__ = "pacientes"
    __tablename__ = "historicos"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    procedimentos_realizados = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)


class Financeiro(db.Model):
    __bind_key__ = "pacientes"
    __tablename__ = "financeiro"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    plano_id = db.Column(db.Integer, db.ForeignKey("plano_tratamento.id"))
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    tipo = db.Column(db.String(10), default="Crédito")  # Crédito | Débito
    forma_pagamento = db.Column(db.String(30))
    status = db.Column(db.String(20), default="Pendente")  # Pendente | Pago | Cancelado
    data_pagamento = db.Column(db.Date)
    data_lancamento = db.Column(db.DateTime, default=datetime.utcnow)
    procedimento_id = db.Column(
        db.Integer,
        db.ForeignKey("procedimentos.id"),
        nullable=True,
    )  # vinculo opcional p/ rastreabilidade

    __table_args__ = (
        # Constraints simples (compatível com SQLite) para integridade.
        CheckConstraint("tipo in ('Crédito','Débito')", name="ck_financeiro_tipo"),
        CheckConstraint(
            "status in ('Pendente','Pago','Cancelado')",
            name="ck_financeiro_status",
        ),
    )


# --- Eventos para manter orcamento_total consistente automaticamente ---


def _recompute_plano(connection, plano_id: int) -> None:
    """Recalcula orçamento via SQL agregando procedimentos persistidos.

    Usar SQL direto evita carregar objetos em memória e funciona em eventos
    before/after mesmo fora de um contexto de sessão completo.
    """
    if plano_id is None:
        return
    connection.execute(
        text(
            """
            UPDATE plano_tratamento
               SET orcamento_total = (
                   SELECT COALESCE(SUM(valor), 0)
                     FROM procedimentos
                    WHERE plano_id = :pid
               )
             WHERE id = :pid
            """
        ),
        {"pid": plano_id},
    )


@event.listens_for(Procedimento, "after_insert")
@event.listens_for(Procedimento, "after_update")
def _proc_after_upsert(mapper, connection, target):  # pragma: no cover - infra
    _recompute_plano(connection, target.plano_id)


@event.listens_for(Procedimento, "after_delete")
def _proc_after_delete(mapper, connection, target):  # pragma: no cover - infra
    _recompute_plano(connection, target.plano_id)
