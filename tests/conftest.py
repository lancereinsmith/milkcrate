import os

import pytest
from flask import Flask

from database import init_db
from milkcrate_core import create_app


@pytest.fixture(name="flask_app")
def app(tmp_path) -> Flask:
    test_instance_path = tmp_path / "instance"
    test_uploads = tmp_path / "uploads"
    test_extracted = tmp_path / "extracted_apps"
    test_db = tmp_path / "test.sqlite"

    os.makedirs(test_instance_path, exist_ok=True)
    os.makedirs(test_uploads, exist_ok=True)
    os.makedirs(test_extracted, exist_ok=True)

    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
        "DATABASE": str(test_db),
        "UPLOAD_FOLDER": str(test_uploads),
        "EXTRACTED_FOLDER": str(test_extracted),
        "ADMIN_PASSWORD": "admin",
    }

    flask_app = create_app(test_config)

    with flask_app.app_context():
        init_db()

    return flask_app


@pytest.fixture
def client(flask_app: Flask):
    return flask_app.test_client()


@pytest.fixture
def runner(flask_app: Flask):
    return flask_app.test_cli_runner()


@pytest.fixture
def logged_in_client(flask_app: Flask):
    test_client = flask_app.test_client()
    resp = test_client.post(
        "/login",
        data={"password": flask_app.config.get("ADMIN_PASSWORD", "admin")},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    return test_client
