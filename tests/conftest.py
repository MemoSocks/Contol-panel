import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from config import TestingConfig
from app.models.models import User, Stage

@pytest.fixture(scope='module')
def app():
    app = create_app(TestingConfig)
    yield app

@pytest.fixture(scope='module')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def database(app):
    with app.app_context():
        db.create_all()
        admin = User(username='admin', role='admin', can_manage_routes=True, can_manage_stages=True)
        admin.set_password('password123')
        stage1 = Stage(name='Test Stage 1')
        stage2 = Stage(name='Test Stage 2')
        db.session.add_all([admin, stage1, stage2])
        db.session.commit()
        yield db
        db.session.remove()
        db.drop_all()