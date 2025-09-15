from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from .. import db


class User(db.Model):
    __bind_key__ = "users"
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    nome_completo = db.Column(db.String(128), nullable=False)
    cro = db.Column(db.String(20))  # opcional
    nome_profissional = db.Column(db.String(120))  # exibição profissional
    password_hash = db.Column(db.String(256))
    # Cargos: admin, gerente, dentista, atendimento, financeiro
    cargo = db.Column(db.String(50), default="dentista")
    # Alinha com legacy: coluna física 'is_active'
    is_active_db = db.Column("is_active", db.Boolean, default=True, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    # Segurança adicional
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_password_change = db.Column(db.DateTime)

    def _validate_password_policy(self, password: str) -> None:
        """Valida regras básicas de senha (configuráveis via app.config).

        Regras padrão (ativadas apenas se ENFORCE_PASSWORD_POLICY=True):
        - mín. 8 caracteres
        - deve conter pelo menos um dígito e uma letra
        - não pode conter o username em lowercase
        """
        from flask import current_app

        if not current_app:  # pragma: no cover - proteção defensiva
            return
        if not current_app.config.get("ENFORCE_PASSWORD_POLICY"):
            return
        min_len = current_app.config.get("PASSWORD_MIN_LENGTH", 8)
        if len(password) < min_len:
            raise ValueError("Senha curta demais")
        if password.lower().count(self.username.lower()) > 0:
            raise ValueError("Senha não pode conter o usuário")
        if not any(c.isdigit() for c in password):
            raise ValueError("Senha precisa de dígito")
        if not any(c.isalpha() for c in password):
            raise ValueError("Senha precisa de letra")

    def set_password(self, password: str) -> None:
        self._validate_password_policy(password)
        self.password_hash = generate_password_hash(password)
        self.last_password_change = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # Propriedade compatível com Flask-Login (sem dependência direta)
    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return True if self.is_active_db is None else bool(self.is_active_db)

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.is_active_db = bool(value)

    # --- Controle de tentativas de login ---
    def register_failed_login(self, max_attempts: int, lock_minutes: int) -> None:
        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lock_minutes)
            self.failed_login_count = 0  # reinicia após bloqueio

    def reset_failed_login(self) -> None:
        self.failed_login_count = 0
        self.locked_until = None
