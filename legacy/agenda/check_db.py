import os
import sqlite3

# Verificar estrutura do users.db
try:
    users_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "instance", "users.db")
    )
    conn = sqlite3.connect(users_path)
    cursor = conn.cursor()

    # Listar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tabelas no users.db:", tables)

    # Se existe tabela users, verificar estrutura
    if ("users",) in tables:
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print("Estrutura da tabela users:", columns)

        # Mostrar alguns dados de exemplo
        cursor.execute("SELECT * FROM users LIMIT 3")
        samples = cursor.fetchall()
        print("Dados de exemplo:", samples)

    conn.close()
except Exception as e:
    print("Erro ao acessar users.db:", e)

# Verificar estrutura do pacientes.db também
try:
    pacientes_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "instance", "pacientes.db")
    )
    conn = sqlite3.connect(pacientes_path)
    cursor = conn.cursor()

    # Listar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTabelas no pacientes.db:", tables)

    # Se existe tabela pacientes, verificar estrutura
    if ("pacientes",) in tables:
        cursor.execute("PRAGMA table_info(pacientes)")
        columns = cursor.fetchall()
        print("Estrutura da tabela pacientes:", columns)

        # Mostrar alguns dados de exemplo
        cursor.execute("SELECT * FROM pacientes LIMIT 3")
        samples = cursor.fetchall()
        print("Dados de exemplo:", samples)

    conn.close()
except Exception as e:
    print("Erro ao acessar pacientes.db:", e)

# Verificar estrutura do calendario.db (raiz e instance)
for path in [
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "instance", "calendario.db")
    ),
]:
    try:
        print(f"\nVerificando {path}...")
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tabelas:", tables)
        if ("calendar_event",) in tables:
            cursor.execute("PRAGMA table_info(calendar_event)")
            columns = cursor.fetchall()
            print("Estrutura da tabela calendar_event:", columns)
            cursor.execute("SELECT * FROM calendar_event LIMIT 3")
            samples = cursor.fetchall()
            print("Dados de exemplo:", samples)
        conn.close()
    except Exception as e:
        print(f"Erro ao acessar {path}:", e)
