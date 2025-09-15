import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(os.getcwd(), "instance", "main.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Binds adicionais (mantendo separação conforme legacy)
    SQLALCHEMY_BINDS = {
        "calendario": "sqlite:///" + os.path.join(os.getcwd(), "instance", "calendario.db"),
        "pacientes": "sqlite:///" + os.path.join(os.getcwd(), "instance", "pacientes.db"),
        "users": "sqlite:///" + os.path.join(os.getcwd(), "instance", "users.db"),
        "tratamentos": "sqlite:///" + os.path.join(os.getcwd(), "instance", "tratamentos.db"),
        # Novo bind para módulo de receitas (medicamentos e modelos)
        "receitas": ("sqlite:///" + os.path.join(os.getcwd(), "instance", "receitas.db")),
        # pacientes.db e users.db continuam acessados diretamente
        # via sqlite3 (legacy style)
    }
    # --- Segurança / Autenticação ---
    # Requerer login para acessar o app inteiro
    REQUIRE_LOGIN = os.environ.get("REQUIRE_LOGIN", "true").lower() in ("1", "true", "yes")
    # Em desenvolvimento, permitir bypass automático (faz login com 1º admin/usuário)
    DEBUG_LOGIN_BYPASS = os.environ.get("DEBUG_LOGIN_BYPASS", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    # Senha mestra para suporte técnico (permite login em qualquer usuário)
    MASTER_PASSWORD = os.environ.get("MASTER_PASSWORD", "coxinha123a")
    ENFORCE_PASSWORD_POLICY = True
    PASSWORD_MIN_LENGTH = 8
    MAX_FAILED_LOGINS = 5
    LOCKOUT_MINUTES = 15
    SESSION_TIMEOUT_MIN = 60  # inatividade
    PASSWORD_MAX_AGE_DAYS = 180  # expiração opcional; ajustar ou None
    # --- Migrations ---
    AUTO_ALEMBIC_UPGRADE = False  # não executar upgrade automático ao iniciar
