from datetime import datetime, timedelta

from flask import (
    Blueprint,
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
                for r in roles:
                    allowed.update(ROLE_GROUPS.get(r, {r}))
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
    """If REQUIRE_LOGIN is True, enforce authentication for all non-exempt paths.

    Exemptions: static, auth routes, health, and explicitly allowed GET assets.
    Includes a debug bypass that auto-logs into first admin/any user when enabled.
    """
    if not current_app.config.get("REQUIRE_LOGIN", True):
        return  # disabled

    path = request.path or "/"
    # Whitelist basic routes
    if (
        path.startswith("/auth/")
        or path == "/auth/login"
        or path == "/health"
        or path.startswith("/static/")
    ):
        return

    # If already logged, allow
    if getattr(g, "user", None):
        return

    # No support token path

    # Debug bypass: only when enabled
    if current_app.debug or current_app.config.get("DEBUG_LOGIN_BYPASS"):
        if current_app.config.get("DEBUG_LOGIN_BYPASS"):
            # Try auto login with first admin, else any user
            admin = User.query.filter_by(cargo="admin").first()
            user = admin or User.query.first()
            if not user:
                # Seed a fallback admin user in dev/test bypass
                try:
                    user = User()
                    user.username = "dev"
                    user.nome_completo = "Dev Admin"
                    user.cargo = "admin"
                    user.set_password("dev")
                    db.session.add(user)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    user = User.query.first()
            if user:
                session["uid"] = user.id
                flash("Login automático (bypass debug)", "info")
                return

    # Not logged -> redirect to login
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        # Master password override
        master = current_app.config.get("MASTER_PASSWORD", "coxinha123a")
        user = User.query.filter_by(username=username).first()
        # Verifica bloqueio
        if (
            user
            and user.locked_until
            and user.locked_until > datetime.utcnow()
            and password != master
        ):
            restante = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            flash(
                f"Usuário bloqueado. Tente novamente em ~{restante} min.",
                "danger",
            )
            # Order by fields with NULLs last (SQLite-friendly): IS NULL asc then value asc
            users = User.query.order_by(
                (User.nome_profissional.is_(None)).asc(),
                User.nome_profissional.asc(),
                (User.nome_completo.is_(None)).asc(),
                User.nome_completo.asc(),
                User.username.asc(),
            ).all()
            return render_template("auth/login.html", users=users)
        # Credenciais
        if not user:
            flash("Credenciais inválidas", "danger")
            users = User.query.order_by(
                (User.nome_profissional.is_(None)).asc(),
                User.nome_profissional.asc(),
                (User.nome_completo.is_(None)).asc(),
                User.nome_completo.asc(),
                User.username.asc(),
            ).all()
            return render_template("auth/login.html", users=users)
        if not (user.check_password(password) or password == master):
            # Incrementa tentativas somente se usuário existe
            user.register_failed_login(
                current_app.config.get("MAX_FAILED_LOGINS", 5),
                current_app.config.get("LOCKOUT_MINUTES", 15),
            )
            db.session.commit()
            flash("Credenciais inválidas", "danger")
            users = User.query.order_by(
                (User.nome_profissional.is_(None)).asc(),
                User.nome_profissional.asc(),
                (User.nome_completo.is_(None)).asc(),
                User.nome_completo.asc(),
                User.username.asc(),
            ).all()
            return render_template("auth/login.html", users=users)
        # Usa propriedade is_active; master password também permite login de usuário inativo
        if not user.is_active and password != master:
            flash("Usuário inativo", "warning")
            users = User.query.order_by(
                (User.nome_profissional.is_(None)).asc(),
                User.nome_profissional.asc(),
                (User.nome_completo.is_(None)).asc(),
                User.nome_completo.asc(),
                User.username.asc(),
            ).all()
            return render_template("auth/login.html", users=users)
        # Expiração de senha opcional
        max_age_days = current_app.config.get("PASSWORD_MAX_AGE_DAYS")
        if max_age_days and user.last_password_change:
            delta = datetime.utcnow() - user.last_password_change
            if delta > timedelta(days=max_age_days):
                flash("Senha expirada, redefina a senha", "warning")
                # (Futuro: redirecionar para fluxo de alteração)
        # Reset de tentativas
        user.reset_failed_login()
        db.session.commit()
        session["uid"] = user.id
        flash("Sessão iniciada", "success")
        return redirect(url_for("core.index"))
    # GET: show login with users if any
    users = User.query.order_by(
        (User.nome_profissional.is_(None)).asc(),
        User.nome_profissional.asc(),
        (User.nome_completo.is_(None)).asc(),
        User.nome_completo.asc(),
        User.username.asc(),
    ).all()
    return render_template("auth/login.html", users=users)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("uid", None)
    flash("Sessão encerrada", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/seed-admin", methods=["POST"])  # rota utilitária dev
def seed_admin():  # pragma: no cover - utilitária
    if User.query.filter_by(username="admin").first():
        flash("Admin já existe", "info")
        return redirect(url_for("auth.login"))
    u = User()
    u.username = "admin"
    u.nome_completo = "Administrador"
    u.set_password("admin")
    db.session.add(u)
    db.session.commit()
    flash("Usuário admin criado (senha=admin)", "success")
    return redirect(url_for("auth.login"))
