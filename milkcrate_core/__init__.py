"""Core application factory and setup for milkcrate.

Exposes the `create_app` factory used by both the CLI entrypoint and tests.
"""

import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from blueprints import admin_bp, auth_bp, public_bp, upload_bp
from blueprints.volumes import volumes_bp
from database import init_app as init_db
from services.audit import audit_logger
from services.security import security_headers

from .config import get_config
from .errors import register_error_handlers
from .extensions import csrf, limiter, login_manager
from .models.user import User


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory.

    Args:
        test_config: Optional overrides to apply when testing.

    Returns:
        A configured `Flask` application instance.
    """
    # Ensure Flask knows where to find top-level templates/static
    package_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(package_dir, ".."))
    templates_dir = os.path.join(project_root, "templates")
    static_dir = os.path.join(project_root, "static")

    app = Flask(
        __name__,
        template_folder=templates_dir,
        static_folder=static_dir,
    )

    # Configuration
    if test_config is None:
        config_obj = get_config()
        app.config.from_object(config_obj)
        # Validate production settings
        if hasattr(config_obj, "validate"):
            config_obj.validate()
    else:
        app.config.update(test_config)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Extensions
    init_db(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    limiter.init_app(app)
    audit_logger.init_app(app)
    security_headers.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return User.get(user_id)

    # Reverse proxy (intentional replacement of wsgi_app with wrapped middleware)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # type: ignore[invalid-assignment]

    # Blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(volumes_bp)

    # Errors
    register_error_handlers(app)

    return app
