#!/usr/bin/env python3
"""
Single-file runner to start a Flask app and expose it via ngrok.

Usage examples:
  - python run_with_ngrok.py --app mypkg.app:app --port 5000
  - python run_with_ngrok.py --app mypkg:create_app --region us
  - Set env vars instead of flags: APP_IMPORT_STRING, FLASK_HOST, FLASK_PORT,
    NGROK_AUTHTOKEN, NGROK_REGION

Dependencies: Flask (Werkzeug), pyngrok. Optional: python-dotenv for .env.
"""
from __future__ import annotations

import argparse
import atexit
import os
import socket
import sys
import threading
import time
from typing import Any, Optional

from flask import Flask
from pyngrok import conf, ngrok
from werkzeug.serving import BaseWSGIServer, make_server

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover

    def load_dotenv() -> None:  # type: ignore
        return


def _truthy(val: Optional[str]) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def import_app(import_string: str) -> Flask:
    """Import a Flask app or factory from 'module:obj'."""
    if ":" not in import_string:
        raise ValueError("APP_IMPORT_STRING must be in the form 'module:attr'")
    module_name, obj_path = import_string.split(":", 1)
    mod = __import__(module_name, fromlist=[obj_path.split(".")[0]])
    obj: Any = mod
    for part in obj_path.split("."):
        obj = getattr(obj, part)
    if callable(obj):
        app = obj()  # type: ignore[misc]
    else:
        app = obj  # type: ignore[assignment]
    if not isinstance(app, Flask):
        raise TypeError("Resolved object is not a Flask instance or factory")
    return app


class _FlaskServerThread(threading.Thread):
    def __init__(self, app: Flask, host: str, port: int) -> None:
        super().__init__(daemon=True)
        try:
            self._server: BaseWSGIServer = make_server(host, port, app)
        except OSError as exc:
            raise OSError(f"Failed to bind to {host}:{port}. Is the port in use?") from exc
        self._ctx = app.app_context()
        self._ctx.push()

    def run(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        try:
            self._server.shutdown()
        finally:
            try:
                self._ctx.pop()
            except Exception:
                pass


def wait_for_port(host: str, port: int, timeout: float = 10.0) -> None:
    start = time.time()
    last_err: Optional[Exception] = None
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as exc:
            last_err = exc
            time.sleep(0.1)
    raise TimeoutError(
        "Timed out waiting for server to start listening on "
        f"{host}:{port}. Last error: {last_err}"
    )


def open_tunnel(
    host: str,
    port: int,
    auth_token: Optional[str],
    region: Optional[str],
    domain: Optional[str] = None,
    edge_id: Optional[str] = None,
) -> str:
    # Always use a clean, v3-compatible config local to this repo to avoid
    # legacy keys (e.g., request_header_add) from a global ngrok.yml.
    try:
        runtime_cfg = os.path.join(os.getcwd(), ".ngrok.runtime.yml")
        conf.get_default().config_path = runtime_cfg
    except Exception:
        pass

    # Resolve auth token: CLI arg > env var > token.ngrok file
    token = auth_token or os.getenv("NGROK_AUTHTOKEN")
    if not token:
        token_file = os.path.join(os.getcwd(), "token.ngrok")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    token = f.read().strip()
            except Exception:
                token = token
    # Prefer not to persist the token to disk; pass via env for the ngrok process.
    if token:
        os.environ["NGROK_AUTHTOKEN"] = token
    # Default region to 'sa' (South America/Brazil) if not provided
    reg = (region or os.getenv("NGROK_REGION") or "sa").lower()
    conf.get_default().region = reg

    # Ensure no stale local ngrok processes are lingering
    try:
        ngrok.kill()
    except Exception:
        pass

    connect_kwargs: dict[str, Any] = {
        "addr": f"{host}:{port}",
        "bind_tls": True,
    }
    # Prefer explicit domain if provided; fall back to edge id if present
    if domain:
        connect_kwargs["domain"] = domain
    elif edge_id:
        connect_kwargs["edge"] = edge_id

    tunnel = ngrok.connect(**connect_kwargs)  # type: ignore[arg-type]
    public_url = tunnel.public_url
    if not public_url:
        raise RuntimeError("ngrok did not return a public URL")

    print(f"[INFO] Local URL:  http://{host}:{port}")
    print(f"[INFO] Public URL: {public_url}")

    def _cleanup() -> None:
        try:
            ngrok.disconnect(public_url)
        except Exception:
            pass
        try:
            ngrok.kill()
        except Exception:
            pass

    atexit.register(_cleanup)
    return public_url


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Run a Flask app and expose it via ngrok",
    )
    parser.add_argument(
        "--app",
        dest="app_import_string",
        default=os.getenv("APP_IMPORT_STRING", ""),
        help="Import string for app or factory (module:attr)",
    )
    parser.add_argument("--host", default=os.getenv("FLASK_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("FLASK_PORT", "5000")))
    parser.add_argument("--auth-token", dest="auth_token", default=None)
    parser.add_argument("--region", dest="region", default=None)
    parser.add_argument("--domain", dest="domain", default=os.getenv("NGROK_DOMAIN"))
    parser.add_argument("--edge", dest="edge_id", default=os.getenv("NGROK_EDGE_ID"))

    args = parser.parse_args()

    app_str = args.app_import_string
    if not app_str:
        # Try a few common defaults
        for candidate in ("app:app", "app:create_app"):
            try:
                app = import_app(candidate)
                app_str = candidate
                break
            except Exception:
                continue
        else:
            print(
                "[ERROR] Provide --app module:attr or set APP_IMPORT_STRING "
                "env.\nExamples: mypkg.app:app or mypkg:create_app",
                file=sys.stderr,
            )
            sys.exit(2)

    try:
        app = import_app(app_str)
    except Exception as exc:
        print(
            f"[ERROR] Failed to import app '{app_str}': {exc}",
            file=sys.stderr,
        )
        sys.exit(2)

    host = args.host
    port = int(args.port)

    print(f"[INFO] Starting Flask dev server at http://{host}:{port} ...")
    server = _FlaskServerThread(app, host, port)
    server.start()

    try:
        wait_for_port(host, port, timeout=10.0)
    except Exception as exc:
        print(f"[ERROR] Server failed to start: {exc}", file=sys.stderr)
        try:
            server.shutdown()
        except Exception:
            pass
        sys.exit(1)

    try:
        open_tunnel(
            host,
            port,
            auth_token=args.auth_token,
            region=args.region,
            domain=args.domain,
            edge_id=args.edge_id,
        )
    except Exception as exc:
        print(f"[ERROR] Failed to open ngrok tunnel: {exc}", file=sys.stderr)
        try:
            server.shutdown()
        except Exception:
            pass
        sys.exit(1)

    print("[INFO] Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
    finally:
        try:
            server.shutdown()
        except Exception:
            pass
        # ngrok cleanup is handled by atexit


if __name__ == "__main__":
    main()
