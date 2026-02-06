"""Blueprint package for milkcrate routes.

Exports the registered blueprints to be imported by the application factory.
"""

from .admin import admin_bp  # noqa: F401
from .auth import auth_bp  # noqa: F401
from .public import public_bp  # noqa: F401
from .upload import upload_bp  # noqa: F401
from .volumes import volumes_bp  # noqa: F401
