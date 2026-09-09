# OdontoClin 2

An earlier, modular prototype for dental-clinic operations built with Flask, SQLAlchemy, Alembic, and server-rendered web interfaces.

> **Project status:** historical prototype and architecture study. For the more complete, actively developed dental-management platform, see [EchoDent](https://github.com/AlanKBR/EchoDent).

## What this prototype explores

- Patient registration and CRUD workflows
- Appointment and holiday scheduling
- Role-based authentication and protected application routes
- Modular Flask blueprints for `core`, `agenda`, and `pacientes`
- Domain-separated SQLite databases through SQLAlchemy binds
- Explicit Alembic migrations per bind
- Automated tests with `pytest`

## Architecture

The application separates domains into Flask blueprints and uses independent database binds for users, patients, calendar data, treatments, and prescriptions. This repository documents an intermediate step toward a larger clinic-management product, so some modules remain intentionally incomplete.

## Run locally

### Requirements

- Python 3.10+
- `pip`

### Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python run.py
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q --maxfail=1
```

## Database migrations

Automatic migration on application startup is disabled. Run migrations explicitly for the required bind:

```powershell
alembic upgrade head
alembic upgrade head -x target_bind=pacientes
alembic upgrade head -x target_bind=users
alembic upgrade head -x target_bind=receitas
alembic upgrade head -x target_bind=tratamentos
alembic upgrade head -x target_bind=calendario
```

## Security configuration

The repository does not include working default passwords or a predictable session key.

Set a stable `SECRET_KEY` in every persistent environment:

```bash
export SECRET_KEY="replace-with-a-long-random-value"
```

Optional development-only controls are disabled unless explicitly configured:

- `DEBUG_LOGIN_BYPASS=true` enables the local development bypass.
- `DEV_ADMIN_PASSWORD` supplies a password when bootstrapping a development admin.
- `MASTER_PASSWORD` enables the optional support override. Leave it unset to keep that mechanism disabled.

Never enable development bypasses in a public or production deployment.

## Scope

This repository is useful as a record of architecture experiments around modularization, authentication, database separation, and migrations. It is not presented as production-ready clinical software.
