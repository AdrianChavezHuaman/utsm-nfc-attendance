"""Configuración de pytest: app aislada con base temporal."""

import pytest

from app import create_app
from app.config import Config
from app.extensions import db
from seeds.seed_base import seed_base


@pytest.fixture()
def app(tmp_path):
    class TestingConfig(Config):
        TESTING = True
        SECRET_KEY = "test-shaula-efc"
        WTF_CSRF_ENABLED = False
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        SQLALCHEMY_ENGINE_OPTIONS = {}
        UPLOAD_FOLDER = str(tmp_path / "uploads")
        EXPORT_FOLDER = str(tmp_path / "exports")

    aplicacion = create_app(TestingConfig)
    with aplicacion.app_context():
        db.create_all()
        seed_base()
    yield aplicacion
    with aplicacion.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield db.session
