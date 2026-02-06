"""Flask extension instances.

Provides CSRF protection, login manager, and rate limiting.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf import CSRFProtect

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

login_manager = LoginManager()
