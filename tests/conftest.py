import pytest
import os
from flask import Flask

os.environ.setdefault('CHALLENGE_SECRET_KEY', 'test_challenge_secret_key')
from honeypot.adapters.driving.challenge_api import challenge_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(challenge_bp, url_prefix='/api/challenge')
    return app

@pytest.fixture
def client(app):
    return app.test_client()
