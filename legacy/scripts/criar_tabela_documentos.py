#!/usr/bin/env python3
"""Script para criar a tabela de documentos no banco de dados."""

import os
import sys

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

# Adicionar o diretório do projeto ao Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def criar_tabela_documentos():
    """Cria a tabela de documentos no banco de dados."""
    app = create_app()

    with app.app_context():
        try:
            # Criar todas as tabelas (se não existirem)
            db.create_all()
            print("✅ Tabela de documentos criada com sucesso!")

            # Verificar se a tabela foi criada
            inspector = db.inspect(db.get_engine(bind_key="pacientes"))
            if "documentos" in inspector.get_table_names():
                print("✅ Tabela 'documentos' confirmada no banco 'pacientes'")
            else:
                print("❌ Tabela 'documentos' não encontrada")

        except Exception as e:
            print(f"❌ Erro ao criar tabela: {e}")


if __name__ == "__main__":
    criar_tabela_documentos()
