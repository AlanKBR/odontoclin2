from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

# Import db from extensions.py
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __bind_key__ = "users"  # Added to route queries for this model to the 'users' bind

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    nome_completo = db.Column(db.String(128), nullable=False)
    cro = db.Column(
        db.String(20), unique=True, nullable=True
    )  # CRO agora é obrigatório para profissionais
    nome_profissional = db.Column(db.String(120), nullable=False)  # Professional name field
    password_hash = db.Column(db.String(256))  # Aumentado para 256
    cargo = db.Column(db.String(50), nullable=False, default="dentista")  # Novo campo para cargo
    # Backing column for activation state (stored as 'is_active' in DB)
    is_active_db = db.Column("is_active", db.Boolean, default=True, nullable=True)

    def __init__(
        self,
        username=None,
        nome_completo=None,
        nome_profissional=None,
        cro=None,
        cargo="dentista",
        **kwargs,
    ):
        """Initialize User instance with parameters."""
        super().__init__(**kwargs)
        if username is not None:
            self.username = username
        if nome_completo is not None:
            self.nome_completo = nome_completo
        if nome_profissional is not None:
            self.nome_profissional = nome_profissional
        if cro is not None:
            self.cro = cro
        self.cargo = cargo

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    # Flask-Login compatibility: provide read/write property
    @property
    def is_active(self) -> bool:  # type: ignore[override]
        # Treat NULL as active for backward compatibility
        return True if self.is_active_db is None else bool(self.is_active_db)

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.is_active_db = bool(value)
