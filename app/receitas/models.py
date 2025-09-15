from datetime import datetime

from .. import db


class Medicamento(db.Model):
    """Modelo simplificado migrado do legacy.

    Campos principais preservados; alguns campos longos de texto mantidos para
    futura interface de busca/detalhe. Bind dedicado 'receitas'.
    """

    __bind_key__ = "receitas"
    __tablename__ = "medicamentos"
    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(100), nullable=False)
    principio_ativo = db.Column(db.String(100), nullable=False)
    nome_referencia = db.Column(db.String(100))
    apresentacao = db.Column(db.String(100), nullable=False)
    posologia = db.Column(db.Text, nullable=False)
    uso = db.Column(db.String(50))
    indicacoes = db.Column(db.Text)
    mecanismo_acao = db.Column(db.Text)
    contraindicacoes = db.Column(db.Text)
    efeitos_colaterais = db.Column(db.Text)
    interacoes_medicamentosas = db.Column(db.Text)
    risco_gravidez = db.Column(db.String(20))
    tipo_receita = db.Column(db.String(50))
    alerta_principal = db.Column(db.Text)
    instrucao_compra = db.Column(db.Text)
    observacao = db.Column(db.Text)

    def __repr__(self):  # pragma: no cover - representação simples
        return f"<Medicamento {self.principio_ativo}>"


class ModeloReceita(db.Model):
    """Modelos de texto de receitas vinculados a (futuro) usuário.

    Usuário ainda não obrigatório; campo usuario_id opcional por enquanto para
    permitir criação anônima nos testes até integração com auth.
    """

    __bind_key__ = "receitas"
    __tablename__ = "modelos_receita"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    usuario_id = db.Column(db.Integer)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):  # pragma: no cover
        return f"<ModeloReceita {self.titulo}>"


class Atestado(db.Model):
    """Registro simples de atestados gerados."""

    __bind_key__ = "pacientes"
    __tablename__ = "atestados"
    id = db.Column(db.Integer, primary_key=True)
    paciente = db.Column(db.String(150), nullable=False)
    dias = db.Column(db.Integer, nullable=False, default=1)
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)


# Alias retro-compatível com versão inicial simplificada
# Alias removido: ReceitaModelo
