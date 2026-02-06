"""Root routes for milkcrate.

Provides the main index which lists all installed apps when present,
or shows the informational landing page when no apps are installed.
"""

from flask import Blueprint, current_app, redirect, render_template, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user

from database import get_all_apps, get_default_home_route

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index() -> ResponseReturnValue:
    """Root route.

    Behavior:
    - If authenticated, redirect to admin dashboard.
    - If default_home_route is set in database, redirect there.
    - Else if DEFAULT_HOME_ROUTE is set in config, redirect there (fallback).
    - Else show all installed apps or milkcrate info page.
    """
    # If authenticated, redirect to admin dashboard
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    # Check database for default route first (highest priority)
    default_home = get_default_home_route().strip()

    # Fallback to config if database setting is empty
    if not default_home:
        default_home = str(current_app.config.get("DEFAULT_HOME_ROUTE", "")).strip()

    if default_home:
        target = default_home if default_home.startswith("/") else f"/{default_home}"
        normalized = target.rstrip("/") or "/"
        if normalized != "/":
            return redirect(target)

    # Show all installed apps (not just public)
    apps = get_all_apps()
    return render_template("index.html", apps=apps)


# The dedicated /public listing is no longer used
