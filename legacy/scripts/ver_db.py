"""
Script para mostrar uma visão detalhada das estruturas dos bancos de dados SQLite na pasta instance.
Uso:
  python ver_db.py           # Mostra todos os bancos
  python ver_db.py nome.db  # Mostra apenas o banco especificado
"""

import os
import sqlite3
import sys

from tabulate import tabulate

INSTANCE_DIR = os.path.join(os.path.dirname(__file__), "instance")


def listar_bancos():
    return [f for f in os.listdir(INSTANCE_DIR) if f.endswith(".db")]


def mostrar_estrutura(db_path):
    print(f"\nBanco: {os.path.basename(db_path)}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tabelas = [row[0] for row in cursor.fetchall()]
        if not tabelas:
            print("  (Sem tabelas)")
            return
        for tabela in tabelas:
            print(f"\n  Tabela: {tabela}")
            cursor.execute(f"PRAGMA table_info({tabela})")
            colunas = cursor.fetchall()
            if colunas:
                print(
                    tabulate(
                        colunas,
                        headers=["cid", "nome", "tipo", "notnull", "default", "pk"],
                        tablefmt="grid",
                    )
                )
            else:
                print("    (Sem colunas)")
            # Mostra índices
            cursor.execute(f"PRAGMA index_list({tabela})")
            indices = cursor.fetchall()
            if indices:
                print("    Índices:")
                for idx in indices:
                    print(f"      {idx}")
            # Mostra 1 registro exemplo
            cursor.execute(f"SELECT * FROM {tabela} LIMIT 1")
            row = cursor.fetchone()
            if row:
                print("    Exemplo de registro:")
                print("      ", row)
        conn.close()
    except Exception as e:
        print(f"  ERRO ao acessar {db_path}: {e}")


def main():
    bancos = listar_bancos()
    if len(sys.argv) > 1:
        db_nome = sys.argv[1]
        if db_nome not in bancos:
            print(f"Banco '{db_nome}' não encontrado na pasta instance.")
            print("Bancos disponíveis:", bancos)
            sys.exit(1)
        mostrar_estrutura(os.path.join(INSTANCE_DIR, db_nome))
    else:
        for db in bancos:
            mostrar_estrutura(os.path.join(INSTANCE_DIR, db))


if __name__ == "__main__":
    main()
