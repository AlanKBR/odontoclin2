"""
Este módulo define os modelos relacionados a receitas médicas.
"""

from sqlalchemy import Column, Integer, String, Text

from app.extensions import db


class Medicamento(db.Model):
    """
    Modelo para representar medicamentos conforme a estrutura da tabela SQL.

    Atributos:
        id (int): Identificador único do medicamento
        categoria (str): Categoria do medicamento
        principio_ativo (str): Princípio ativo do medicamento
        nome_referencia (str): Nome de referência do medicamento
        apresentacao (str): Apresentação do medicamento
        posologia (str): Instruções de posologia
        uso (str): Indicação de uso
        indicacoes (str): Indicações comuns para o medicamento
        mecanismo_acao (str): Mecanismo de ação do medicamento
        contraindicacoes (str): Contraindicações do medicamento
        efeitos_colaterais (str): Efeitos colaterais comuns
        interacoes_medicamentosas (str): Interações medicamentosas
        risco_gravidez (str): Risco na gravidez
        tipo_receita (str): Tipo de receita necessária
        alerta_principal (str): Alerta principal sobre o medicamento
        instrucao_compra (str): Instruções para compra
        observacao (str): Observações adicionais
    """

    __tablename__ = "medicamentos"
    __bind_key__ = "receitas"

    id = Column(Integer, primary_key=True)
    categoria = Column(String(100), nullable=False)
    principio_ativo = Column(String(100), nullable=False)
    nome_referencia = Column(String(100))
    apresentacao = Column(String(100), nullable=False)
    posologia = Column(Text, nullable=False)
    uso = Column(String(50))
    indicacoes = Column(Text)
    mecanismo_acao = Column(Text)
    contraindicacoes = Column(Text)
    efeitos_colaterais = Column(Text)
    interacoes_medicamentosas = Column(Text)
    risco_gravidez = Column(String(20))
    tipo_receita = Column(String(50))
    alerta_principal = Column(Text)
    instrucao_compra = Column(Text)
    observacao = Column(Text)

    def __repr__(self):
        return f"<Medicamento {self.principio_ativo}>"


class ModeloReceita(db.Model):
    """
    Modelo para representar modelos de texto de receitas salvas pelo usuário.

    Atributos:
        id (int): Identificador único do modelo
        titulo (str): Título do modelo de receita
        conteudo (str): Conteúdo do modelo de receita
        usuario_id (int): ID do usuário que criou o modelo
    """

    __tablename__ = "modelos_receita"
    __bind_key__ = "receitas"

    id = Column(Integer, primary_key=True)
    titulo = Column(String(100), nullable=False)
    conteudo = Column(Text, nullable=False)
    usuario_id = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<ModeloReceita {self.titulo}>"
