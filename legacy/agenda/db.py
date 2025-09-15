from flask_sqlalchemy import SQLAlchemy

# Global SQLAlchemy instance to be initialized in the app factory
# Keeps models decoupled from the Flask app object

db = SQLAlchemy()
