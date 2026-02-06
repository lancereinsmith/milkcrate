"""Backup and restore functionality for milkcrate data.

This module provides functions to create and restore backups of milkcrate's
critical data including the database, uploads, and extracted applications.
"""

import shutil
import sqlite3
import tarfile
from datetime import UTC, datetime
from pathlib import Path


def create_backup(
    project_root: Path,
    backup_dir: Path | None = None,
    include_uploads: bool = True,
    include_extracted: bool = True,
) -> Path:
    """Create a timestamped backup of milkcrate data.

    Creates a compressed tar archive containing:
    - Database file (instance/milkcrate.sqlite)
    - Uploads directory (if include_uploads is True)
    - Extracted apps directory (if include_extracted is True)

    Args:
        project_root: Root directory of the milkcrate project.
        backup_dir: Directory to store backups. Defaults to project_root/backups.
        include_uploads: Whether to include the uploads directory.
        include_extracted: Whether to include the extracted_apps directory.

    Returns:
        Path to the created backup archive.

    Raises:
        FileNotFoundError: If required files/directories don't exist.
        OSError: If backup creation fails.
    """
    if backup_dir is None:
        backup_dir = project_root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"milkcrate_backup_{timestamp}.tar.gz"
    backup_path = backup_dir / backup_filename

    # Check if database exists
    db_path = project_root / "instance" / "milkcrate.sqlite"
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    # Create backup archive
    with tarfile.open(backup_path, "w:gz") as tar:
        # Add database file
        tar.add(db_path, arcname="instance/milkcrate.sqlite")

        # Add instance directory contents (for audit logs, etc.)
        instance_dir = project_root / "instance"
        if instance_dir.exists():
            for item in instance_dir.iterdir():
                if item.is_file() and item.name != "milkcrate.sqlite":
                    tar.add(item, arcname=f"instance/{item.name}")

        # Add uploads directory if requested
        if include_uploads:
            uploads_dir = project_root / "uploads"
            if uploads_dir.exists() and any(uploads_dir.iterdir()):
                tar.add(uploads_dir, arcname="uploads", filter=_exclude_gitkeep)

        # Add extracted apps directory if requested
        if include_extracted:
            extracted_dir = project_root / "extracted_apps"
            if extracted_dir.exists() and any(extracted_dir.iterdir()):
                tar.add(
                    extracted_dir, arcname="extracted_apps", filter=_exclude_gitkeep
                )

    return backup_path


def _exclude_gitkeep(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    """Filter function to exclude .gitkeep files from backups."""
    if tarinfo.name.endswith(".gitkeep"):
        return None
    return tarinfo


def list_backups(backup_dir: Path) -> list[tuple[Path, datetime, int]]:
    """List all available backups with metadata.

    Args:
        backup_dir: Directory containing backup files.

    Returns:
        List of tuples containing (backup_path, timestamp, size_bytes).
    """
    if not backup_dir.exists():
        return []

    backups = []
    for backup_file in backup_dir.glob("milkcrate_backup_*.tar.gz"):
        try:
            # Extract timestamp from filename
            timestamp_str = backup_file.stem.replace("milkcrate_backup_", "")
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(
                tzinfo=UTC
            )
            size = backup_file.stat().st_size
            backups.append((backup_file, timestamp, size))
        except ValueError:
            # Skip files with invalid timestamp format
            continue

    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x[1], reverse=True)
    return backups


def restore_backup(
    backup_path: Path,
    project_root: Path,
    restore_uploads: bool = True,
    restore_extracted: bool = True,
) -> None:
    """Restore milkcrate data from a backup archive.

    Args:
        backup_path: Path to the backup archive file.
        project_root: Root directory of the milkcrate project.
        restore_uploads: Whether to restore the uploads directory.
        restore_extracted: Whether to restore the extracted_apps directory.

    Raises:
        FileNotFoundError: If backup file doesn't exist.
        tarfile.TarError: If backup archive is corrupted.
        OSError: If restoration fails.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # Verify backup is a valid tar.gz file
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.getnames()  # Verify archive is readable
    except tarfile.TarError as e:
        raise tarfile.TarError(f"Invalid backup archive: {e}") from e

    # Extract backup
    with tarfile.open(backup_path, "r:gz") as tar:
        # Restore database
        db_member = None
        for member in tar.getmembers():
            if member.name == "instance/milkcrate.sqlite":
                db_member = member
                break

        if db_member:
            # Ensure instance directory exists
            instance_dir = project_root / "instance"
            instance_dir.mkdir(parents=True, exist_ok=True)

            # Extract database
            tar.extract(db_member, project_root)

            # Verify database integrity
            db_path = project_root / "instance" / "milkcrate.sqlite"
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
            except sqlite3.Error as e:
                raise OSError(f"Database integrity check failed: {e}") from e

        # Restore other instance files (audit logs, etc.)
        for member in tar.getmembers():
            if (
                member.name.startswith("instance/")
                and member.name != "instance/milkcrate.sqlite"
            ):
                tar.extract(member, project_root)

        # Restore uploads if requested
        if restore_uploads:
            uploads_dir = project_root / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)

            # Remove existing uploads (except .gitkeep)
            for item in uploads_dir.iterdir():
                if item.name != ".gitkeep":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            # Extract uploads
            for member in tar.getmembers():
                if member.name.startswith("uploads/"):
                    tar.extract(member, project_root)

        # Restore extracted apps if requested
        if restore_extracted:
            extracted_dir = project_root / "extracted_apps"
            extracted_dir.mkdir(parents=True, exist_ok=True)

            # Remove existing extracted apps (except .gitkeep)
            for item in extracted_dir.iterdir():
                if item.name != ".gitkeep":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            # Extract extracted apps
            for member in tar.getmembers():
                if member.name.startswith("extracted_apps/"):
                    tar.extract(member, project_root)


def get_backup_info(backup_path: Path) -> dict[str, str | int]:
    """Get information about a backup file.

    Args:
        backup_path: Path to the backup archive.

    Returns:
        Dictionary with backup metadata (timestamp, size, etc.).
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    stat = backup_path.stat()
    size_mb = stat.st_size / (1024 * 1024)

    # Extract timestamp from filename
    timestamp_str = backup_path.stem.replace("milkcrate_backup_", "")
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(
            tzinfo=UTC
        )
        timestamp_formatted = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        timestamp_formatted = "Unknown"

    return {
        "filename": backup_path.name,
        "path": str(backup_path),
        "size_bytes": stat.st_size,
        "size_mb": round(size_mb, 2),
        "timestamp": timestamp_formatted,
        "created": datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    }
