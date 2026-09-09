import hmac
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .. import db
from .models import User


auth_bp = Blueprint(
    "auth",
    __name__,
    template_folder=".",
)


# Grupos compostos (futuro: poderia vir de config/DB)
ROLE_GROUPS = {
    "clinico": {"admin", "gerente", "dentista"},
    "financeiro_all": {"admin", "gerente", "financeiro"},
}


def _ordered_users():
    """Return users in the stable order expected by the login screen."""

    return User.query.order_by(
        (User.nome_profissional.is_(None)).asc(),
        User.nome_profissional.asc(),
        (User.nome_completo.is_(None)).asc(),
        User.nome_completo.asc(),
        User.username.asc(),
    ).all()


def _master_password_matches(candidate: str) -> bool:
    """Match the optional support override without providing a default secret."""

    configured = current_app.config.get("MASTER_PASSWORD")
    return (
        isinstance(configured, str)
        and bool(configured)
        and hmac.compare_digest(candidate, configured)
    )


def require_roles(*roles):
    """Decorator para exigir um dos cargos ou grupos definidos.

    Aceita nomes diretos (admin, gerente, dentista, atendimento, financeiro)
    ou grupos em ROLE_GROUPS. Sem argumentos => apenas exige login.
    """

    def decorator(fn):
        from functools import wraps

        @wraps(fn)
        def wrapper(*args, **kwargs):
            if getattr(g, "user", None) is None:
                flash("Login necessário", "warning")
                return redirect(url_for("auth.login"))
            if roles:
                allowed = set()
                for role in roles:
                    allowed.update(ROLE_GROUPS.get(role, {role}))
                if g.user.cargo not in allowed:  # type: ignore[attr-defined]
                    # Para chamadas HTMX ou API podemos retornar 403 direto;
                    # aqui optamos por flash + redirect.
                    flash("Sem permissão", "danger")
                    return redirect(url_for("core.index"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@auth_bp.before_app_request
def load_user():  # carrega usuário simples da sessão
    uid = session.get("uid")
    g.user = None
    if uid:
        # Substitui Query.get (deprecated) por Session.get
        g.user = db.session.get(User, uid)

    # Expiração de sessão (inatividade)
    now = datetime.utcnow()
    timeout_min = current_app.config.get("SESSION_TIMEOUT_MIN", 60)
    last = session.get("_last_activity")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if (now - last_dt) > timedelta(minutes=timeout_min):
                session.clear()
                g.user = None
                flash("Sessão expirada por inatividade", "warning")
        except ValueError:  # pragma: no cover - formatação inesperada
            session.pop("_last_activity", None)
    session["_last_activity"] = now.isoformat()


@auth_bp.before_app_request
def enforce_login_globally():
    """Enforce authentication for every non-exempt path when configured.

    Exemptions: static assets, authentication routes, and the health endpoint.
    The development bypass must be enabled explicitly and never relies on a
    built-in password.
    """

    if not current_app.config.get("REQUIRE_LOGIN", True):
        return

    path = request.path or "/"
    if (
        path.startswith("/auth/")
        or path == "/auth/login"
        or path == "/health"
        or path.startswith("/static/")
    ):
        return

    if getattr(g, "user", None):
        return

    if current_app.config.get("DEBUG_LOGIN_BYPASS"):
        admin = User.query.filter_by(cargo="admin").first()
        user = admin or User.query.first()

        # Bootstrap only when a password was explicitly supplied.
        if not user:
            dev_password = current_app.config.get("DEV_ADMIN_PASSWORD")
            if isinstance(dev_password, str) and dev_password:
                try:
                    user = User()
                    user.username = "dev"
                    user.nome_completo = "Dev Admin"
                    user.cargo = "admin"
                    user.set_password(dev_password)
                    db.session.add(user)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    user = User.query.first()

        if user:
            session["uid"] = user.id
            flash("Login automático (bypass debug)", "info")
            return

    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        master_matches = _master_password_matches(password)
        user = User.query.filter_by(username=username).first()

        if (
            user
            and user.locked_until
            and user.locked_until > datetime.utcnow()
            and not master_matches
        ):
            restante = int(
                (user.locked_until - datetime.utcnow()).total_seconds() / 60
            ) + 1
            flash(
                f"Usuário bloqueado. Tente novamente em ~{restante} min.",
                "danger",
            )
            return render_template("auth/login.html", users=_ordered_users())

        if not user:
            flash("Credenciais inválidas", "danger")
            return render_template("auth/login.html", users=_ordered_users())

        if not (user.check_password(password) or master_matches):
            user.register_failed_login(
                current_app.config.get("MAX_FAILED_LOGINS", 5),
                current_app.config.get("LOCKOUT_MINUTES", 15),
            )
            db.session.commit()
            flash("Credenciais inválidas", "danger")
            return render_template("auth/login.html", users=_ordered_users())

        # The optional, explicitly configured support override can access an
        # inactive account for troubleshooting; normal credentials cannot.
        if not user.is_active and not master_matches:
            flash("Usuário inativo", "warning")
            return render_template("auth/login.html", users=_ordered_users())

        max_age_days = current_app.config.get("PASSWORD_MAX_AGE_DAYS")
        if max_age_days and user.last_password_change:
            delta = datetime.utcnow() - user.last_password_change
            if delta > timedelta(days=max_age_days):
                flash("Senha expirada, redefina a senha", "warning")

        user.reset_failed_login()
        db.session.commit()
        session["uid"] = user.id
        flash("Sessão iniciada", "success")
        return redirect(url_for("core.index"))

    return render_template("auth/login.html", users=_ordered_users())


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("uid", None)
    flash("Sessão encerrada", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/seed-admin", methods=["POST"])
def seed_admin():  # pragma: no cover - utilitária de desenvolvimento
    """Create a development admin only under an explicit, local-safe setup."""

    if not (
        current_app.debug
        and current_app.config.get("DEBUG_LOGIN_BYPASS")
    ):
        abort(404)

    dev_password = current_app.config.get("DEV_ADMIN_PASSWORD")
    if not isinstance(dev_password, str) or not dev_password:
        abort(503, description="DEV_ADMIN_PASSWORD must be configured")

    if User.query.filter_by(username="admin").first():
        flash("Admin já existe", "info")
        return redirect(url_for("auth.login"))

    user = User()
    user.username = "admin"
    user.nome_completo = "Administrador"
    user.cargo = "admin"
    user.set_password(dev_password)
    db.session.add(user)
    db.session.commit()
    flash("Usuário admin de desenvolvimento criado", "success")
    return redirect(url_for("auth.login"))
