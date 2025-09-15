"""
Este módulo oferece suporte a múltiplos bancos de dados SQLite para a aplicação.
Contém classes personalizadas para trabalhar com múltiplos bancos de dados SQLAlchemy.
"""

from typing import Optional

from flask import Flask
from flask_sqlalchemy import SQLAlchemy  # Assuming db_instance is SQLAlchemy
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker


class MultiDB:
    """
    Classe para gerenciar múltiplas instâncias de banco de dados SQLite.
    Permite separar as tabelas em diferentes arquivos de banco de dados,
    mas mantém a mesma interface de programação para o restante da aplicação.
    """

    def __init__(
        self, app: Optional[Flask] = None, db_instance: Optional[SQLAlchemy] = None
    ) -> None:
        self.app: Optional[Flask] = app
        self.db_instance: Optional[SQLAlchemy] = db_instance
        self.engines: dict[str, Engine] = {}
        self.sessions: dict[str, scoped_session[Session]] = {}

        if app is not None and db_instance is not None:
            self.init_app(app, db_instance)

    def init_app(self, app: Flask, db_instance: SQLAlchemy) -> None:
        """
        Inicializa os bancos de dados SQLite.

        Args:
            app: A instância do Flask app
            db_instance: The main SQLAlchemy instance from app.extensions
        """
        self.app = app
        self.db_instance = db_instance

        # Configurar bancos de dados separados
        self.configure_db("users", app.config.get("USERS_DATABASE_URI", "sqlite:///users.db"))
        self.configure_db(
            "pacientes",
            app.config.get("PACIENTES_DATABASE_URI", "sqlite:///pacientes.db"),
        )
        self.configure_db(
            "tratamentos",
            app.config.get("TRATAMENTOS_DATABASE_URI", "sqlite:///tratamentos.db"),
        )
        self.configure_db(
            "receitas", app.config.get("RECEITAS_DATABASE_URI", "sqlite:///receitas.db")
        )

    def configure_db(self, name: str, uri: str) -> None:
        """
        Configura um banco de dados individual.

        Args:
            name: Nome do banco de dados
            uri: URI de conexão SQLAlchemy
        """
        self.engines[name] = create_engine(uri)
        self.sessions[name] = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engines[name])
        )

    def create_all(self) -> None:
        """Cria todas as tabelas em todos os bancos de dados."""
        if not self.db_instance:
            raise RuntimeError(
                "SQLAlchemy instance not provided to MultiDB. " "Call init_app with db_instance."
            )

        from app.models.paciente import (
            Anamnese,
            Ficha,
            Financeiro,
            Historico,
            Paciente,
            PlanoTratamento,
            Procedimento,
        )
        from app.models.receita import Medicamento, ModeloReceita
        from app.models.tratamento import CategoriaTratamento, Tratamento
        from app.models.user import User

        # Cria tabelas no banco de dados de usuários
        self.db_instance.Model.metadata.create_all(
            bind=self.engines["users"], tables=[t.__table__ for t in [User]]
        )

        # Cria tabelas no banco de dados de pacientes
        self.db_instance.Model.metadata.create_all(
            bind=self.engines["pacientes"],
            tables=[
                t.__table__
                for t in [
                    Paciente,
                    Ficha,
                    Anamnese,
                    PlanoTratamento,
                    Procedimento,
                    Historico,
                    Financeiro,
                ]
            ],
        )

        # Cria tabelas no banco de dados de tratamentos
        self.db_instance.Model.metadata.create_all(
            bind=self.engines["tratamentos"],
            tables=[t.__table__ for t in [CategoriaTratamento, Tratamento]],
        )

        # Cria tabelas no banco de dados de receitas
        self.db_instance.Model.metadata.create_all(
            bind=self.engines["receitas"],
            tables=[t.__table__ for t in [Medicamento, ModeloReceita]],
        )

    def get_engine(self, name: str) -> Optional[Engine]:
        """Retorna o engine para o banco de dados especificado."""
        return self.engines.get(name)

    def get_session(self, name: str) -> Optional[scoped_session[Session]]:
        """Retorna a sessão para o banco de dados especificado."""
        return self.sessions.get(name)


# Variáveis globais para acesso às sessões
users_session: Optional[scoped_session[Session]] = None
pacientes_session = None
tratamentos_session = None

# Instância global para ser importada pelos demais módulos
multidb = MultiDB()
