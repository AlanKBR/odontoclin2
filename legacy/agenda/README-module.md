# Agenda module

This folder is a reusable Flask blueprint + models for a calendar/agenda.

How to integrate into another Flask project:

- Install runtime deps:
  - pip install -r agenda/requirements.txt  # Python only
  - (optional) also see agenda/requirements-all.txt for Node packages list
- Initialize in your app factory:

    from agenda import init_agenda
    app = Flask(__name__)
    init_agenda(app)  # or pass database_uri, url_prefix

- Optional parameters:
  - database_uri: SQLAlchemy URI. Default is sqlite:///agenda/instance/calendario.db
  - url_prefix: e.g., "/agenda" to mount under a path
  - auto_create_db: default True to create tables if missing

Command-line run (standalone):

- python -m agenda

Instance folder location:
- By default, databases are now stored under the app's instance folder (../instance).
- On first run, existing DBs under agenda/instance will be copied over if missing.

Migrations utilities in this package operate directly on the SQLite files under agenda/instance/.