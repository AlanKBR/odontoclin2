"""
Decoradores personalizados para o sistema OdontoClinic
"""

from functools import wraps

from flask import current_app, flash, redirect, url_for
from flask_login import current_user, login_user

from app.models.user import User


def admin_required(f):
    """
    Decorador que requer que o usuário tenha cargo 'admin' para acessar a rota.
    Deve ser usado após o decorador @login_required.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        if current_user.cargo != "admin":
            flash(
                "Acesso negado. Apenas administradores podem acessar esta funcionalidade.",
                "error",
            )
            return redirect(url_for("main.dashboard"))

        return f(*args, **kwargs)

    return decorated_function


def debug_login_optional(f):
    """
    Decorador que permite acesso sem login quando a aplicação está em modo debug.
    Em modo debug, faz login automático com o primeiro usuário admin encontrado.
    Em produção, funciona como login_required normal.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Se estiver em debug e usuário não está autenticado
        if current_app.debug and not current_user.is_authenticated:
            # Tenta fazer login automático com primeiro admin
            try:
                from app import extensions

                admin_user = extensions.users_db.query(User).filter_by(cargo="admin").first()
                if admin_user:
                    login_user(admin_user)
                    flash("Login automático realizado (modo debug)", "info")
                else:
                    # Se não há admin, tenta qualquer usuário
                    any_user = extensions.users_db.query(User).first()
                    if any_user:
                        login_user(any_user)
                        flash(
                            f"Login automático realizado com {any_user.username} (modo debug)",
                            "info",
                        )
            except Exception as e:
                # Se houver erro no login automático, continua sem autenticação em debug
                if current_app.debug:
                    flash(
                        f"Aviso: Executando sem autenticação (modo debug). Erro: {str(e)}",
                        "warning",
                    )
                    # Em modo debug, permite continuar mesmo sem usuário
                    return f(*args, **kwargs)
                else:
                    # Em produção, redireciona para login
                    return redirect(url_for("auth.login"))

        # Se não está em debug e não está autenticado, redireciona para login
        elif not current_app.debug and not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        # Se chegou aqui, está autenticado ou em debug - executa a função
        return f(*args, **kwargs)

    return decorated_function


def debug_admin_optional(f):
    """
    Decorador que requer admin em produção, mas permite qualquer usuário em debug.
    Em modo debug, se não há usuário autenticado, faz login automático.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Primeiro garante que há um usuário (em debug faz login automático)
        if current_app.debug and not current_user.is_authenticated:
            try:
                from app import extensions

                admin_user = extensions.users_db.query(User).filter_by(cargo="admin").first()
                if admin_user:
                    login_user(admin_user)
                else:
                    any_user = extensions.users_db.query(User).first()
                    if any_user:
                        login_user(any_user)
            except Exception:
                pass

        # Verifica se está autenticado
        if not current_user.is_authenticated:
            if current_app.debug:
                flash("Executando sem autenticação (modo debug)", "warning")
                return f(*args, **kwargs)
            else:
                return redirect(url_for("auth.login"))

        # Em produção, verifica se é admin
        if not current_app.debug and current_user.cargo != "admin":
            flash(
                "Acesso negado. Apenas administradores podem acessar esta funcionalidade.",
                "error",
            )
            return redirect(url_for("main.dashboard"))

        # Em debug, permite qualquer usuário
        if current_app.debug and current_user.cargo != "admin":
            flash(
                f"Acesso permitido em modo debug (usuário: {current_user.username})",
                "info",
            )

        return f(*args, **kwargs)

    return decorated_function
