from flask import Flask

# create_app is exercised via the flask_app fixture in conftest


def test_app_factory_smoke(flask_app: Flask):
    assert isinstance(flask_app, Flask)


def test_app_has_blueprints(flask_app: Flask):
    rules = [r.rule for r in flask_app.url_map.iter_rules()]
    assert "/" in rules  # public.index
    assert "/login" in rules
    assert any(r.startswith("/admin") for r in rules)
    assert "/upload" in rules


def test_error_handlers_registered(client):
    # Hit a missing URL to get 404
    res = client.get("/does-not-exist", headers={"Accept": "text/html"})
    assert res.status_code == 404
    assert b"<!DOCTYPE" in res.data or b"Not Found" in res.data
