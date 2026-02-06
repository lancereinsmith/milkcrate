from unittest.mock import MagicMock, patch

from database import insert_app


def test_dashboard_requires_login(client):
    res = client.get("/admin", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert "/login" in res.headers.get("Location", "")


def test_dashboard_renders_when_logged_in(logged_in_client):
    res = logged_in_client.get("/admin")
    assert res.status_code == 200


@patch("docker.from_env")
def test_delete_app_happy_path(mock_from_env, flask_app, logged_in_client):
    # Prepare a fake deployed app
    with flask_app.app_context():
        insert_app("demo", "cid123", "image:tag", "/demo", 8000, is_public=False)

    # Mock docker client and container
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_client.images.get.return_value = MagicMock()
    mock_from_env.return_value = mock_client

    # Find app id from DB
    from database import get_all_apps

    with flask_app.app_context():
        app_id = get_all_apps()[0]["app_id"]

    res = logged_in_client.post(f"/admin/delete/{app_id}", follow_redirects=False)
    # Redirect back to dashboard
    assert res.status_code in (302, 303)


@patch("docker.from_env")
def test_toggle_status_start_and_stop(mock_from_env, flask_app, logged_in_client):
    with flask_app.app_context():
        insert_app("demo", "cid123", "image:tag", "/demo", 8000, is_public=False)

    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_from_env.return_value = mock_client

    from database import get_all_apps, update_app_status

    with flask_app.app_context():
        row = get_all_apps()[0]
        app_id = row["app_id"]
        update_app_status(app_id, "stopped")

    # Start when stopped
    res = logged_in_client.post(
        f"/admin/toggle_status/{app_id}", follow_redirects=False
    )
    assert res.status_code in (302, 303)

    # Stop when running
    with flask_app.app_context():
        update_app_status(app_id, "running")
    res2 = logged_in_client.post(
        f"/admin/toggle_status/{app_id}", follow_redirects=False
    )
    assert res2.status_code in (302, 303)
