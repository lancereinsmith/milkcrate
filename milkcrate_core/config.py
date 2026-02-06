"""Configuration objects for different environments."""

import os


def _parse_bool(val: str) -> bool:
    """Parse a string as boolean for env config."""
    return str(val).strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    DATABASE = os.path.join(
        os.environ.get("FLASK_INSTANCE_PATH", "instance"), "milkcrate.sqlite"
    )
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    EXTRACTED_FOLDER = os.environ.get("EXTRACTED_FOLDER", "extracted_apps")
    TRAEFIK_NETWORK = os.environ.get("TRAEFIK_NETWORK", "milkcrate-traefik")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ADMIN_PASSWORD = os.environ.get("MILKCRATE_ADMIN_PASSWORD", "admin")
    # Optional: set a custom default route for '/'. Example: '/my-app'.
    # If empty, the home page lists all installed apps, or shows instructions when none are installed.
    DEFAULT_HOME_ROUTE = os.environ.get("DEFAULT_HOME_ROUTE", "")
    # SSL/HTTPS (security.py also reads these from env if not on config)
    SSL_CERT_FILE = os.environ.get("SSL_CERT_FILE") or None
    SSL_KEY_FILE = os.environ.get("SSL_KEY_FILE") or None
    FORCE_HTTPS = _parse_bool(os.environ.get("FORCE_HTTPS", "false"))
    # Traefik HTTPS mode - enables Let's Encrypt certificates and HTTPS routing
    ENABLE_HTTPS = _parse_bool(os.environ.get("ENABLE_HTTPS", "false"))
    LETSENCRYPT_EMAIL = os.environ.get("LETSENCRYPT_EMAIL", "your-email@example.com")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


def get_config():
    """Return a config class based on the MILKCRATE_ENV environment variable."""
    env = os.environ.get("MILKCRATE_ENV", "development").lower()
    if env.startswith("prod"):
        return ProductionConfig
    return DevelopmentConfig
