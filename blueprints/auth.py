"""Authentication routes for login and logout.

Provides a minimal password-only admin login suitable for demos. In
production, integrate a proper user system with hashed passwords and CSRF-
protected forms.
"""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import login_required, login_user, logout_user

from database import verify_admin_password
from milkcrate_core.models.user import User

auth_bp = Blueprint("auth", __name__)
"""Auth blueprint routes."""


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    """Render login form and handle credential submission."""
    # Detect environment override directly via process environment
    import os as _os

    env_override_active = bool(
        str(_os.environ.get("MILKCRATE_ADMIN_PASSWORD", "")).strip()
    )
    if request.method == "POST":
        # Password-only admin login
        submitted_password = request.form.get("password", "")

        if submitted_password and verify_admin_password(submitted_password):
            user = User("admin")
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid password")

    return render_template("login.html", env_override_active=env_override_active)


@auth_bp.route("/logout")
@login_required
def logout() -> ResponseReturnValue:
    """Log the current user out and redirect to the public index."""
    logout_user()
    return redirect(url_for("public.index"))
