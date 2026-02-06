import io
import zipfile
from unittest.mock import patch


def make_zip_with(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_upload_requires_login(client):
    res = client.get("/upload", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert "/login" in res.headers.get("Location", "")


def test_upload_get_renders_when_logged_in(logged_in_client):
    res = logged_in_client.get("/upload")
    assert res.status_code == 200


def test_upload_rejects_reserved_routes(logged_in_client):
    zip_bytes = make_zip_with(
        {
            "Dockerfile": b"FROM python:3.12-slim\n",
            "app.py": b"print('hello')\n",
        }
    )
    data = {
        "app_name": "demo",
        "public_route": "/admin",
        "file": (io.BytesIO(zip_bytes), "demo.zip"),
    }
    res = logged_in_client.post(
        "/upload", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert res.status_code == 200
    assert b"reserved" in res.data.lower()


@patch("services.deploy.deploy_application")
def test_upload_success_flow(mock_deploy, logged_in_client):
    mock_deploy.return_value = (True, "container123", "image:tag")

    zip_bytes = make_zip_with(
        {
            "Dockerfile": b"FROM python:3.12-slim\n",
            "app.py": b"print('hello')\n",
        }
    )
    data = {
        "app_name": "demo",
        "public_route": "/demo",
        "file": (io.BytesIO(zip_bytes), "demo.zip"),
    }

    res = logged_in_client.post(
        "/upload", data=data, content_type="multipart/form-data", follow_redirects=False
    )
    assert res.status_code in (302, 303)


def test_upload_validation_missing_file_field(logged_in_client):
    res = logged_in_client.post("/upload", data={}, follow_redirects=True)
    assert res.status_code == 200
    assert b"no file selected" in res.data.lower()


def test_upload_rejects_duplicate_routes(logged_in_client, flask_app):
    """Test that upload rejects routes that already exist."""
    from database import insert_app

    with flask_app.app_context():
        # First, insert an app with a specific route
        insert_app("existing-app", "container123", "image:tag", "/demo", 8000)

    # Try to upload another app with the same route
    zip_bytes = make_zip_with(
        {
            "Dockerfile": b"FROM python:3.12-slim\n",
            "app.py": b"print('hello')\n",
        }
    )
    data = {
        "app_name": "new-app",
        "public_route": "/demo",
        "file": (io.BytesIO(zip_bytes), "new-app.zip"),
    }

    res = logged_in_client.post(
        "/upload", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert res.status_code == 200
    assert b"already in use" in res.data.lower()
