from flask import Flask


def test_login_get_renders(client):
    res = client.get("/login")
    assert res.status_code == 200
    assert b"login" in res.data.lower()


def test_login_valid_password_redirects(flask_app: Flask, client):
    res = client.post(
        "/login",
        data={"password": flask_app.config.get("ADMIN_PASSWORD", "admin")},
        follow_redirects=False,
    )
    assert res.status_code in (302, 303)
    assert "/admin" in res.headers.get("Location", "")


def test_login_invalid_password_shows_flash(client):
    res = client.post("/login", data={"password": "wrong"}, follow_redirects=True)
    assert res.status_code == 200
    # Flash message content
    assert b"invalid password" in res.data.lower()


def test_logout_requires_login(client):
    res = client.get("/logout", follow_redirects=False)
    # Should redirect to login page due to @login_required
    assert res.status_code in (302, 303)
    assert "/login" in res.headers.get("Location", "")
