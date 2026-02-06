"""Minimal user model for demo authentication."""

from flask_login import UserMixin


class User(UserMixin):
    """Simple demo user.

    For demonstration purposes only. Real applications should integrate a
    database-backed user model with proper credential storage.
    """

    def __init__(self, user_id: str):
        self.id = user_id

    @staticmethod
    def get(user_id: str) -> "User | None":
        """Return a `User` instance for the given ID, if available."""
        if user_id == "admin":
            return User("admin")
        return None
