"""Extensiones compartidas de Flask.

Se inicializan en create_app() para evitar ciclos de importación.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
