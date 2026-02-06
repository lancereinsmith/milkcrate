from database import insert_app


def test_index_redirects_when_authenticated(logged_in_client):
    res = logged_in_client.get("/", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert "/admin" in res.headers.get("Location", "")


def test_index_lists_apps_when_any_exist(flask_app, client):
    with flask_app.app_context():
        insert_app("demo", "cid123", "img:tag", "/demo", 8000, is_public=False)

    res = client.get("/")
    assert res.status_code == 200
    assert b"demo" in res.data


def test_index_respects_default_home_route(flask_app, client):
    flask_app.config.update({"DEFAULT_HOME_ROUTE": "/my-app"})
    res = client.get("/", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert res.headers["Location"].endswith("/my-app")
