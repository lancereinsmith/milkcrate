"""Input validation and sanitization utilities.

Provides comprehensive validation for app names, routes, and other user inputs
to prevent security issues and ensure data integrity.
"""

import re
import string


class ValidationError(Exception):
    """Raised when input validation fails."""


def validate_app_name(app_name: str) -> tuple[bool, str | None]:
    """Validate application name.

    Args:
        app_name: The application name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not app_name:
        return False, "Application name is required"

    if len(app_name) < 2:
        return False, "Application name must be at least 2 characters long"

    if len(app_name) > 50:
        return False, "Application name must be 50 characters or less"

    # Allow only alphanumeric characters, hyphens, and underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", app_name):
        return (
            False,
            "Application name can only contain letters, numbers, hyphens, and underscores",
        )

    # Must start with a letter or number
    if not app_name[0].isalnum():
        return False, "Application name must start with a letter or number"

    # Cannot end with hyphen or underscore
    if app_name.endswith(("-", "_")):
        return False, "Application name cannot end with a hyphen or underscore"

    # Reserved names
    reserved_names = {
        "admin",
        "api",
        "www",
        "mail",
        "ftp",
        "localhost",
        "milkcrate",
        "traefik",
        "docker",
        "root",
        "system",
        "service",
        "app",
        "web",
        "server",
        "host",
        "node",
        "cluster",
        "master",
        "slave",
        "backup",
    }

    if app_name.lower() in reserved_names:
        return False, f"'{app_name}' is a reserved application name"

    return True, None


def validate_public_route(route: str) -> tuple[bool, str | None]:
    """Validate public route.

    Args:
        route: The public route to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not route:
        return False, "Public route is required"

    # Ensure route starts with /
    if not route.startswith("/"):
        return False, "Public route must start with a forward slash"

    if len(route) > 100:
        return False, "Public route must be 100 characters or less"

    # Validate route format
    if not re.match(r"^/[a-zA-Z0-9_/-]*$", route):
        return (
            False,
            "Public route can only contain letters, numbers, hyphens, underscores, and forward slashes",
        )

    # Cannot end with / unless it's the root route
    if len(route) > 1 and route.endswith("/"):
        return False, "Public route cannot end with a forward slash"

    # Cannot have consecutive slashes
    if "//" in route:
        return False, "Public route cannot contain consecutive forward slashes"

    # Cannot contain only special characters in segments
    segments = route.split("/")
    for segment in segments[1:]:  # Skip empty first segment
        if segment and not re.match(r"^[a-zA-Z0-9_-]+$", segment):
            return (
                False,
                "Route segments can only contain letters, numbers, hyphens, and underscores",
            )

    # Reserved routes
    reserved_routes = {
        "/admin",
        "/login",
        "/logout",
        "/upload",
        "/traefik",
        "/api",
        "/settings",
        "/health",
        "/status",
        "/metrics",
        "/debug",
    }

    # Check if route or any parent path is reserved
    for reserved in reserved_routes:
        if route == reserved or route.startswith(reserved + "/"):
            return False, f"Route '{route}' conflicts with reserved path '{reserved}'"

    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed"

    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)

    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:95] + ("." + ext if ext else "")

    # Ensure it's not empty after sanitization
    if not filename or filename == ".":
        filename = "unnamed"

    return filename


def validate_password(password: str) -> tuple[bool, str | None]:
    """Validate password strength.

    Args:
        password: The password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must be 128 characters or less"

    # Check for at least one lowercase, uppercase, digit, and special character
    checks = [
        (
            any(c.islower() for c in password),
            "Password must contain at least one lowercase letter",
        ),
        (
            any(c.isupper() for c in password),
            "Password must contain at least one uppercase letter",
        ),
        (
            any(c.isdigit() for c in password),
            "Password must contain at least one digit",
        ),
        (
            any(c in string.punctuation for c in password),
            "Password must contain at least one special character",
        ),
    ]

    for check_passed, error_msg in checks:
        if not check_passed:
            return False, error_msg

    # Check for common weak passwords
    weak_passwords = {
        "password",
        "12345678",
        "qwerty123",
        "admin123",
        "password123",
        "milkcrate",
        "milkcrate123",
        "admin",
        "administrator",
    }

    if password.lower() in weak_passwords:
        return False, "Password is too common. Please choose a stronger password"

    return True, None


def sanitize_input(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
    """Sanitize general text input.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes and control characters except newlines and tabs
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

    # Remove HTML tags if not allowed
    if not allow_html:
        text = re.sub(r"<[^>]*>", "", text)

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    # Remove leading/trailing whitespace
    return text.strip()


def validate_and_sanitize_app_input(
    app_name: str, public_route: str
) -> tuple[bool, str | None, str, str]:
    """Validate and sanitize app name and route together.

    Args:
        app_name: Application name
        public_route: Public route

    Returns:
        Tuple of (is_valid, error_message, sanitized_app_name, sanitized_route)
    """
    # Sanitize inputs first
    app_name = sanitize_input(app_name, 50).lower()
    public_route = sanitize_input(public_route, 100)

    # Ensure route starts with / (but don't modify the original for validation)
    if public_route and not public_route.startswith("/"):
        public_route = "/" + public_route

    # Validate app name
    is_valid, error = validate_app_name(app_name)
    if not is_valid:
        return False, error, app_name, public_route

    # Validate route
    is_valid, error = validate_public_route(public_route)
    if not is_valid:
        return False, error, app_name, public_route

    return True, None, app_name, public_route
