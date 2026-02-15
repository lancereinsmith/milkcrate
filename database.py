"""
Database helper functions for milkcrate.

Follows the recommended Flask pattern for SQLite connections using the
application context global `g` and teardown callbacks.
"""

import hmac
import logging
import os
import sqlite3

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)


def get_db() -> sqlite3.Connection:
    """Get database connection, creating it if it doesn't exist."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        _migrate_schema_if_needed(g.db)

    return g.db


def close_db(_e: BaseException | None = None) -> None:
    """Close database connection if it exists."""
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db() -> None:
    """Initialize the database with the schema."""
    db = get_db()

    # Find the schema.sql file in the project root
    # The Flask app is created from milkcrate_core, so we need to go up one level
    package_dir = os.path.dirname(current_app.root_path)
    schema_path = os.path.join(package_dir, "schema.sql")

    with open(schema_path, encoding="utf8") as f:
        db.executescript(f.read())


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Clear the existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")


def init_app(app: Flask) -> None:
    """Register database functions with the app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


def get_app_by_container_id(container_id: str) -> sqlite3.Row | None:
    """Get application details by container ID."""
    db = get_db()
    return db.execute(
        "SELECT * FROM deployed_apps WHERE container_id = ?", (container_id,)
    ).fetchone()


def get_app_by_id(app_id: int) -> sqlite3.Row | None:
    """Get application details by app ID."""
    db = get_db()
    return db.execute(
        "SELECT * FROM deployed_apps WHERE app_id = ?", (app_id,)
    ).fetchone()


def get_all_apps() -> list[sqlite3.Row]:
    """Get all deployed applications."""
    db = get_db()
    return db.execute(
        "SELECT * FROM deployed_apps ORDER BY deployment_date DESC"
    ).fetchall()


def get_public_apps() -> list[sqlite3.Row]:
    """Get all public deployed applications."""
    db = get_db()
    return db.execute(
        "SELECT * FROM deployed_apps WHERE is_public = 1 ORDER BY deployment_date DESC"
    ).fetchall()


def insert_app(
    app_name: str,
    container_id: str,
    image_tag: str,
    public_route: str,
    internal_port: int,
    is_public: bool = False,
    deployment_type: str = "dockerfile",
    compose_file: str | None = None,
    main_service: str | None = None,
    volume_mounts: str | None = None,
) -> None:
    """Insert a new deployed application."""
    db = get_db()
    db.execute(
        """INSERT INTO deployed_apps
           (app_name, container_id, image_tag, public_route, internal_port, is_public, status, deployment_date, deployment_type, compose_file, main_service, volume_mounts)
           VALUES (?, ?, ?, ?, ?, ?, 'running', datetime('now'), ?, ?, ?, ?)""",
        (
            app_name,
            container_id,
            image_tag,
            public_route,
            internal_port,
            1 if is_public else 0,
            deployment_type,
            compose_file,
            main_service,
            volume_mounts,
        ),
    )
    db.commit()


def delete_app(app_id: int) -> None:
    """Delete a deployed application by ID."""
    db = get_db()
    db.execute("DELETE FROM deployed_apps WHERE app_id = ?", (app_id,))
    db.commit()


def update_app_status(app_id: int, status: str) -> None:
    """Update the status of a deployed application."""
    db = get_db()
    db.execute("UPDATE deployed_apps SET status = ? WHERE app_id = ?", (status, app_id))
    db.commit()


def _apply_fallback_status(app_dict: dict) -> None:
    """Apply basic fallback status fields when enhanced status is unavailable."""
    status = app_dict.get("status", "")
    app_dict.update(
        {
            "real_status": status,
            "display_status": status.title() if status else "Unknown",
            "badge_color": "success" if status == "running" else "secondary",
            "status_details": {},
            "last_status_check": "Status checking unavailable",
        }
    )


def _apply_enhanced_status(app_dict: dict, status_info: dict) -> None:
    """Apply enhanced status fields from the status manager."""
    app_dict.update(
        {
            "real_status": status_info["status"],
            "display_status": status_info["display_status"],
            "badge_color": status_info["badge_color"],
            "status_details": status_info,
            "last_status_check": status_info["last_checked"],
        }
    )


def _enhance_app_status(app_dict: dict) -> None:
    """Try to enhance an app dict with real-time Docker status, falling back to basic."""
    try:
        from services.status_manager import get_status_manager  # noqa: PLC0415

        status_manager = get_status_manager()
        status_info = status_manager.get_comprehensive_status(
            container_id=app_dict["container_id"],
            app_name=app_dict["app_name"],
            public_route=app_dict["public_route"],
            internal_port=app_dict["internal_port"],
        )
        _apply_enhanced_status(app_dict, status_info)
    except Exception:
        _apply_fallback_status(app_dict)


def get_app_with_real_status(app_id: int) -> dict | None:
    """Get application with real-time Docker status check."""
    app = get_app_by_id(app_id)
    if not app:
        return None

    app_dict = dict(app)
    _enhance_app_status(app_dict)
    return app_dict


def get_all_apps_with_real_status() -> list[dict]:
    """Get all applications with real-time Docker status checks."""
    apps = get_all_apps()
    enhanced_apps = []

    for app in apps:
        app_dict = dict(app)
        _enhance_app_status(app_dict)
        enhanced_apps.append(app_dict)

    return enhanced_apps


def set_app_public(app_id: int, is_public: bool) -> None:
    """Set whether an application is public (listed on homepage)."""
    db = get_db()
    db.execute(
        "UPDATE deployed_apps SET is_public = ? WHERE app_id = ?",
        (1 if is_public else 0, app_id),
    )
    db.commit()


def _migrate_schema_if_needed(db: sqlite3.Connection) -> None:
    """Ensure the database schema has required columns, performing lightweight migrations.

    This function is idempotent and safe to run on each connection creation.
    If the database is empty, it will initialize it with the full schema.
    """
    try:
        # Check if deployed_apps table exists
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='deployed_apps'"
        )
        deployed_apps_exists = cursor.fetchone() is not None

        # If the deployed_apps table doesn't exist, initialize the full schema
        if not deployed_apps_exists:
            # Find the schema.sql file
            package_dir = os.path.dirname(current_app.root_path)
            schema_path = os.path.join(package_dir, "schema.sql")

            if os.path.exists(schema_path):
                with open(schema_path, encoding="utf8") as f:
                    db.executescript(f.read())
                db.commit()
                return

        # Table exists, perform incremental migrations
        cursor = db.execute("PRAGMA table_info(deployed_apps)")
        columns = [row[1] for row in cursor.fetchall()]

        if "is_public" not in columns:
            db.execute(
                "ALTER TABLE deployed_apps ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0"
            )
            db.commit()

        # Add new docker-compose support columns
        if "deployment_type" not in columns:
            db.execute(
                "ALTER TABLE deployed_apps ADD COLUMN deployment_type TEXT NOT NULL DEFAULT 'dockerfile'"
            )
            db.commit()

        if "compose_file" not in columns:
            db.execute("ALTER TABLE deployed_apps ADD COLUMN compose_file TEXT")
            db.commit()

        if "main_service" not in columns:
            db.execute("ALTER TABLE deployed_apps ADD COLUMN main_service TEXT")
            db.commit()

        if "volume_mounts" not in columns:
            db.execute("ALTER TABLE deployed_apps ADD COLUMN volume_mounts TEXT")
            db.commit()

        # Ensure public_route index exists (may be missing on older databases)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_public_route ON deployed_apps(public_route)"
        )
        db.commit()

        # Check if settings table exists, create if not
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        )
        if not cursor.fetchone():
            db.execute("""
                CREATE TABLE settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT,
                    updated_date TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            db.execute(
                "INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES ('default_home_route', '')"
            )
            db.commit()

        # Check if volumes table exists, create if not
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='volumes'"
        )
        if not cursor.fetchone():
            db.executescript("""
                CREATE TABLE volumes (
                    volume_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    volume_name TEXT NOT NULL UNIQUE,
                    docker_volume_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_date TEXT NOT NULL DEFAULT (datetime('now')),
                    file_count INTEGER NOT NULL DEFAULT 0,
                    total_size_bytes INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_volume_name ON volumes(volume_name);

                CREATE TABLE volume_files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    volume_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    uploaded_date TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (volume_id) REFERENCES volumes(volume_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_volume_files_volume_id ON volume_files(volume_id);
            """)
            db.commit()
    except sqlite3.Error:
        # If migration fails, we don't want to crash app startup; leave as-is
        logger.warning("Database schema migration failed", exc_info=True)


def get_setting(key: str) -> str | None:
    """Get a setting value from the database.

    Args:
        key: The setting key to retrieve.

    Returns:
        The setting value if found, None otherwise.
    """
    db = get_db()
    cursor = db.execute(
        "SELECT setting_value FROM settings WHERE setting_key = ?", (key,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def update_setting(key: str, value: str) -> None:
    """Update or insert a setting in the database.

    Args:
        key: The setting key to update.
        value: The new setting value.
    """
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO settings (setting_key, setting_value, updated_date) VALUES (?, ?, datetime('now'))",
        (key, value),
    )
    db.commit()


def get_default_home_route() -> str:
    """Get the configured default home route.

    Returns:
        The default home route path, or empty string if not configured.
    """
    return get_setting("default_home_route") or ""


def set_default_home_route(route: str) -> None:
    """Set the default home route.

    Args:
        route: The route path to set as default (e.g., '/my-app').
    """
    update_setting("default_home_route", route)


def get_admin_password() -> str:
    """Return the effective admin password.

    Precedence:
    1. MILKCRATE_ADMIN_PASSWORD environment variable (override in all cases)
    2. Database setting 'admin_password' if set via the UI
    3. Default fallback "admin"
    """
    # Highest priority: environment override
    env_override = os.environ.get("MILKCRATE_ADMIN_PASSWORD", "")
    if str(env_override).strip():
        return str(env_override)

    # UI-configured password stored in DB
    db_value = get_setting("admin_password")
    if db_value is not None and str(db_value).strip():
        return str(db_value)

    # Default fallback
    return "admin"


def set_admin_password(new_password: str) -> None:
    """Persist a new admin password in the database with hashing.

    Note: If MILKCRATE_ADMIN_PASSWORD is set, that will still override the
    stored value during authentication.
    """
    hashed_password = generate_password_hash(new_password)
    update_setting("admin_password", hashed_password)


def verify_admin_password(provided_password: str) -> bool:
    """Verify the provided password against the stored admin password.

    Handles both hashed passwords and plain text.
    Environment overrides are always treated as plain text.
    """
    # Highest priority: environment override (always plain text)
    env_override = os.environ.get("MILKCRATE_ADMIN_PASSWORD", "")
    if str(env_override).strip():
        return hmac.compare_digest(provided_password, str(env_override))

    # Check database stored password (may be hashed or plain text)
    db_value = get_setting("admin_password")
    if db_value is not None and str(db_value).strip():
        stored_password = str(db_value)
        # Check if it's a hashed password (Werkzeug hashes start with method)
        if stored_password.startswith(("pbkdf2:", "scrypt:", "argon2:")):
            return check_password_hash(stored_password, provided_password)
        # Plain text password
        return hmac.compare_digest(provided_password, stored_password)

    # Default fallback
    return hmac.compare_digest(provided_password, "admin")


def get_app_by_route(public_route: str) -> sqlite3.Row | None:
    """Get application details by public route.

    Args:
        public_route: The public route to search for.

    Returns:
        The application record if found, None otherwise.
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM deployed_apps WHERE public_route = ?", (public_route,)
    ).fetchone()


def route_exists(public_route: str) -> bool:
    """Check if a route already exists.

    Args:
        public_route: The public route to check.

    Returns:
        True if the route exists, False otherwise.
    """
    return get_app_by_route(public_route) is not None


def update_app_container_info(
    app_id: int,
    container_id: str,
    image_tag: str,
    deployment_type: str | None = None,
    compose_file: str | None = None,
    main_service: str | None = None,
) -> None:
    """Update application container information after an update.

    Args:
        app_id: The application ID to update.
        container_id: New Docker container ID.
        image_tag: New Docker image tag.
        deployment_type: Deployment type (optional).
        compose_file: Path to compose file (optional).
        main_service: Main service name (optional).
    """
    db = get_db()

    if deployment_type is not None:
        db.execute(
            """UPDATE deployed_apps
               SET container_id = ?, image_tag = ?, deployment_date = datetime('now'), status = 'running',
                   deployment_type = ?, compose_file = ?, main_service = ?
               WHERE app_id = ?""",
            (
                container_id,
                image_tag,
                deployment_type,
                compose_file,
                main_service,
                app_id,
            ),
        )
    else:
        db.execute(
            """UPDATE deployed_apps
               SET container_id = ?, image_tag = ?, deployment_date = datetime('now'), status = 'running'
               WHERE app_id = ?""",
            (container_id, image_tag, app_id),
        )
    db.commit()


# Volume management functions


def insert_volume(
    volume_name: str,
    docker_volume_name: str,
    description: str | None = None,
) -> int:
    """Insert a new volume record.

    Args:
        volume_name: User-friendly volume name
        docker_volume_name: Docker volume name
        description: Optional description

    Returns:
        The volume_id of the newly created volume
    """
    db = get_db()
    cursor = db.execute(
        """INSERT INTO volumes (volume_name, docker_volume_name, description)
           VALUES (?, ?, ?)""",
        (volume_name, docker_volume_name, description),
    )
    db.commit()
    rowid = cursor.lastrowid
    assert rowid is not None, "INSERT must return rowid"
    return rowid


def get_all_volumes() -> list[sqlite3.Row]:
    """Get all volumes.

    Returns:
        List of all volume records
    """
    db = get_db()
    return db.execute("SELECT * FROM volumes ORDER BY created_date DESC").fetchall()


def get_volume_by_id(volume_id: int) -> sqlite3.Row | None:
    """Get volume by ID.

    Args:
        volume_id: The volume ID

    Returns:
        Volume record or None if not found
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM volumes WHERE volume_id = ?", (volume_id,)
    ).fetchone()


def get_volume_by_name(volume_name: str) -> sqlite3.Row | None:
    """Get volume by name.

    Args:
        volume_name: The volume name

    Returns:
        Volume record or None if not found
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM volumes WHERE volume_name = ?", (volume_name,)
    ).fetchone()


def get_volume_by_docker_name(docker_volume_name: str) -> sqlite3.Row | None:
    """Get volume by Docker volume name.

    Args:
        docker_volume_name: The Docker volume name

    Returns:
        Volume record or None if not found
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM volumes WHERE docker_volume_name = ?", (docker_volume_name,)
    ).fetchone()


def delete_volume(volume_id: int) -> None:
    """Delete a volume record.

    Args:
        volume_id: The volume ID to delete
    """
    db = get_db()
    db.execute("DELETE FROM volumes WHERE volume_id = ?", (volume_id,))
    db.commit()


def update_volume_stats(volume_id: int, file_count: int, total_size_bytes: int) -> None:
    """Update volume statistics.

    Args:
        volume_id: The volume ID
        file_count: Number of files in the volume
        total_size_bytes: Total size of files in bytes
    """
    db = get_db()
    db.execute(
        """UPDATE volumes SET file_count = ?, total_size_bytes = ?
           WHERE volume_id = ?""",
        (file_count, total_size_bytes, volume_id),
    )
    db.commit()


def insert_volume_file(
    volume_id: int, file_name: str, file_path: str, file_size_bytes: int
) -> None:
    """Insert a volume file record.

    Args:
        volume_id: The volume ID
        file_name: Name of the file
        file_path: Path within the volume
        file_size_bytes: Size of the file in bytes
    """
    db = get_db()
    db.execute(
        """INSERT INTO volume_files (volume_id, file_name, file_path, file_size_bytes)
           VALUES (?, ?, ?, ?)""",
        (volume_id, file_name, file_path, file_size_bytes),
    )
    db.commit()


def get_volume_files(volume_id: int) -> list[sqlite3.Row]:
    """Get all files for a volume.

    Args:
        volume_id: The volume ID

    Returns:
        List of file records
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM volume_files WHERE volume_id = ? ORDER BY uploaded_date DESC",
        (volume_id,),
    ).fetchall()
