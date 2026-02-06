"""Unified CLI for milkcrate - container orchestration platform management.

This CLI provides a comprehensive interface for managing the milkcrate platform,
including setup, development, deployment, and maintenance tasks.

Key features:
- Project setup and dependency management
- Development server management
- Docker compose stack management
- Application packaging for deployment
- Database management
- System status monitoring
- Cleanup utilities

Supports both Dockerfile and docker-compose.yml based applications.
"""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import click
import docker


def find_project_root() -> Path:
    """Find the milkcrate project root directory."""
    current = Path.cwd()

    # Look for key files that indicate we're in the milkcrate root
    # We need at least app.py and pyproject.toml to confirm it's the right directory
    required_files = ["app.py", "pyproject.toml"]
    optional_files = [
        "justfile",
        "dev/justfile",
        "docker-compose.yml",
        "milkcrate_core",
    ]

    # Check current directory and parents
    for path in [current, *list(current.parents)]:
        # Must have required files
        if all((path / file).exists() for file in required_files):
            # And at least one optional file/directory
            if any((path / file).exists() for file in optional_files):
                return path

    # If not found, assume current directory
    click.echo(
        "Warning: Could not find milkcrate root directory. Using current directory.",
        err=True,
    )
    return current


def run_command(
    cmd: str, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a shell command with proper error handling."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=check
        )
        if result.stdout:
            click.echo(result.stdout.strip())
        return result
    except subprocess.CalledProcessError as e:
        click.echo(f"Command failed: {cmd}", err=True)
        if e.stderr:
            click.echo(f"Error: {e.stderr.strip()}", err=True)
        if e.stdout:
            click.echo(f"Output: {e.stdout.strip()}", err=True)
        sys.exit(1)


def clean_directory(directory: Path, directory_name: str) -> None:
    """Clean a directory by removing all contents except .gitkeep."""
    click.echo(f"🧹 Cleaning {directory_name} directory...")
    directory.mkdir(exist_ok=True)

    # Remove all contents except .gitkeep
    for item in directory.iterdir():
        if item.name != ".gitkeep":
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            click.echo(f"🗑️  Removed: {item.name}")

    click.echo(f"✅ {directory_name} directory cleaned!")


def clean_python_cache(root: Path) -> None:
    """Remove Python bytecode and cache files."""
    click.echo("🧹 Cleaning Python cache files...")
    removed_count = 0

    # Remove __pycache__ directories
    for cache_dir in root.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            click.echo(f"🗑️  Removed: {cache_dir.relative_to(root)}")
            removed_count += 1

    # Remove .pyc, .pyo, .pyd files
    for pattern in ["*.pyc", "*.pyo", "*.pyd"]:
        for cache_file in root.rglob(pattern):
            if cache_file.is_file():
                cache_file.unlink()
                removed_count += 1

    if removed_count > 0:
        click.echo(f"✅ Removed {removed_count} Python cache file(s)")
    else:
        click.echo("✅ No Python cache files found")


def clean_build_cache(root: Path) -> None:
    """Remove build and test cache directories."""
    click.echo("🧹 Cleaning build and test cache...")
    removed_count = 0

    # Cache directories to remove
    cache_dirs = [
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",
        ".coverage",
        ".tox",
        ".ruff_cache",
        ".ty_cache",
        ".rumdl_cache",
        "dist",
        "build",
        "*.egg-info",
    ]

    for pattern in cache_dirs:
        if "*" in pattern:
            # Handle glob patterns like *.egg-info
            for item in root.rglob(pattern):
                if item.is_dir() or item.is_file():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    click.echo(f"🗑️  Removed: {item.relative_to(root)}")
                    removed_count += 1
        else:
            # Handle exact directory names
            cache_path = root / pattern
            if cache_path.exists():
                if cache_path.is_dir():
                    shutil.rmtree(cache_path)
                else:
                    cache_path.unlink()
                click.echo(f"🗑️  Removed: {pattern}")
                removed_count += 1

    # Also clean .coverage.* files
    for coverage_file in root.rglob(".coverage.*"):
        if coverage_file.is_file():
            coverage_file.unlink()
            click.echo(f"🗑️  Removed: {coverage_file.relative_to(root)}")
            removed_count += 1

    if removed_count > 0:
        click.echo(f"✅ Removed {removed_count} cache item(s)")
    else:
        click.echo("✅ No build cache files found")


def check_prerequisites() -> bool:
    """Check if all prerequisites are installed."""
    issues = []

    # Check uv
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        click.echo("✅ uv package manager found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append(
            "❌ uv is not installed. Install from: https://docs.astral.sh/uv/getting-started/installation/"
        )

    # Check Python via uv
    try:
        result = subprocess.run(
            ["uv", "run", "python3", "--version"],
            capture_output=True,
            check=True,
            text=True,
        )
        click.echo(f"✅ Python found: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        issues.append("❌ Python 3 is not accessible through uv")

    # Check Docker
    try:
        client = docker.from_env()
        client.ping()
        click.echo("✅ Docker is running")
    except Exception:
        issues.append("❌ Docker is not running or not accessible")

    if issues:
        click.echo("\nPrerequisite issues found:")
        for issue in issues:
            click.echo(issue)
        return False

    click.echo("\n✅ All prerequisites are met!")
    return True


@click.group()
@click.version_option(package_name="milkcrate")
def cli():
    """milkcrate - A unified CLI for container orchestration platform management."""


# === Setup & Dependencies ===
@cli.command()
def install():
    """Install Python dependencies via uv."""
    click.echo("📦 Installing dependencies...")
    project_root = find_project_root()
    run_command("uv sync", cwd=project_root)
    click.echo("✅ Dependencies installed successfully!")


@cli.command("init-db")
def init_db():
    """Initialize the SQLite database."""
    click.echo("🗄️  Initializing database...")
    project_root = find_project_root()

    # Change to project root and run the initialization
    os.chdir(project_root)

    # Import and initialize the database
    try:
        from app import create_app
        from database import init_db as db_init

        app = create_app()
        with app.app_context():
            db_init()
        click.echo("✅ Database initialized successfully!")
    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def setup(ctx: click.Context):
    """Complete setup: install dependencies and initialize database."""
    click.echo("🚀 Running complete milkcrate setup...")

    # Run install
    ctx.invoke(install)

    # Run init-db
    ctx.invoke(init_db)

    click.echo("\n🎉 milkcrate setup complete!")


@cli.command()
def check():
    """Check system prerequisites and project status."""
    click.echo("🔍 Checking milkcrate prerequisites...")
    project_root = find_project_root()
    click.echo(f"📁 Project root: {project_root}")

    if not check_prerequisites():
        sys.exit(1)

    # Check if database exists
    db_path = project_root / "instance" / "milkcrate.sqlite"
    if db_path.exists():
        click.echo("✅ Database file exists")
    else:
        click.echo("⚠️  Database not initialized. Run 'milkcrate init-db'")

    # Check key directories
    for dir_name in ["uploads", "extracted_apps", "templates", "static"]:
        dir_path = project_root / dir_name
        if dir_path.exists():
            click.echo(f"✅ {dir_name}/ directory exists")
        else:
            click.echo(f"⚠️  {dir_name}/ directory missing")


# === Development ===
@cli.command()
def run():
    """Start the development server locally (port 5001)."""
    click.echo("🚀 Starting milkcrate development server...")
    project_root = find_project_root()
    run_command("uv run python3 app.py", cwd=project_root)


# === Docker & Deployment ===
@cli.command()
def up():
    """Start docker compose stack."""
    click.echo("🐳 Starting docker compose stack...")
    project_root = find_project_root()
    run_command("docker compose up -d", cwd=project_root)


@cli.command()
def down():
    """Stop docker compose stack."""
    click.echo("🛑 Stopping docker compose stack...")
    project_root = find_project_root()
    run_command("docker compose down --remove-orphans", cwd=project_root)


@cli.command()
def rebuild():
    """Rebuild milkcrate image."""
    click.echo("🔨 Rebuilding milkcrate image...")
    project_root = find_project_root()
    run_command("docker compose build --no-cache milkcrate", cwd=project_root)


@cli.command("rebuild-all")
def rebuild_all():
    """Rebuild all compose services."""
    click.echo("🔨 Rebuilding all compose services...")
    project_root = find_project_root()
    run_command("docker compose build --no-cache", cwd=project_root)


@cli.command()
def status():
    """Show system status."""
    click.echo("📊 milkcrate system status:")
    project_root = find_project_root()

    # Check if compose services are running
    try:
        result = run_command(
            "docker compose ps --format json", cwd=project_root, check=False
        )
        if result.returncode == 0:
            click.echo("✅ Docker compose stack accessible")
        else:
            click.echo("⚠️  Docker compose stack not running")
    except Exception:
        click.echo("❌ Could not check docker compose status")

    # Check if development server might be running
    try:
        import requests

        response = requests.get("http://localhost:5001", timeout=2)
        if response.status_code == 200:
            click.echo("✅ Development server running on port 5001")
        else:
            click.echo(
                f"⚠️  Development server responded with status {response.status_code}"
            )
    except ImportError:
        click.echo("ℹ️  requests module not available - cannot check development server")  # noqa: RUF001
    except Exception:
        click.echo("ℹ️  Development server not running on port 5001")  # noqa: RUF001


# === Utilities ===
@cli.command()
@click.option("--output", "-o", help="Output filename (default: app.zip)")
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="Additional patterns to exclude (can be used multiple times)",
)
@click.option(
    "--include-git", is_flag=True, help="Include .git directory (normally excluded)"
)
def package(output: str | None, exclude: tuple, include_git: bool):
    """Package the current directory as a milkcrate-deployable ZIP file."""
    current_dir = Path.cwd()

    # Determine output filename
    if not output:
        output = "app.zip"

    # Ensure .zip extension
    if not output.endswith(".zip"):
        output += ".zip"

    zip_path = current_dir / output

    click.echo(f"📦 Packaging current directory: {current_dir}")
    click.echo(f"📄 Output file: {zip_path}")

    # Check for essential files
    dockerfile_exists = (current_dir / "Dockerfile").exists()
    compose_exists = (current_dir / "docker-compose.yml").exists()
    app_py_exists = (current_dir / "app.py").exists()
    pyproject_exists = (current_dir / "pyproject.toml").exists()

    if not dockerfile_exists and not compose_exists:
        click.echo(
            "⚠️  Warning: No Dockerfile or docker-compose.yml found. Your app may not deploy properly.",
            err=True,
        )
    elif compose_exists:
        click.echo("✅ Found docker-compose.yml - will deploy using Docker Compose")
    elif dockerfile_exists:
        click.echo("✅ Found Dockerfile - will deploy using Docker")

    if not (app_py_exists or pyproject_exists):
        click.echo(
            "⚠️  Warning: No app.py or pyproject.toml found. Make sure your app has an entry point.",
            err=True,
        )

    # Default exclusion patterns
    default_excludes = [
        ".git",
        ".gitignore",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".pytest_cache",
        ".coverage",
        ".mypy_cache",
        ".tox",
        ".venv",
        "venv",
        ".env",
        "node_modules",
        ".DS_Store",
        "Thumbs.db",
        "*.zip",
        "*.tar.gz",
        "*.tar",
        ".idea",
        ".vscode",
        "*.log",
    ]

    # Add user-specified exclusions
    all_excludes = set(default_excludes)
    all_excludes.update(exclude)

    # Remove .git from excludes if --include-git is specified
    if include_git and ".git" in all_excludes:
        all_excludes.remove(".git")

    # Remove existing zip if it exists
    if zip_path.exists():
        click.echo(f"🗑️  Removing existing {output}...")
        zip_path.unlink()

    # Create the zip file
    click.echo("📦 Creating ZIP archive...")
    files_added = 0

    def should_exclude(file_path: Path) -> bool:
        """Check if a file should be excluded based on patterns."""
        path_str = str(file_path.relative_to(current_dir))

        for pattern in all_excludes:
            # Handle glob patterns
            if "*" in pattern:
                if file_path.match(pattern) or any(
                    parent.match(pattern) for parent in file_path.parents
                ):
                    return True
            # Handle exact matches and directory names
            elif pattern in path_str or file_path.name == pattern:
                return True

        return False

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in current_dir.rglob("*"):
                if file_path.is_file() and not should_exclude(file_path):
                    # Don't include the output zip file itself
                    if file_path.name == output:
                        continue

                    arcname = file_path.relative_to(current_dir)
                    zipf.write(file_path, arcname)
                    files_added += 1

        if zip_path.exists() and files_added > 0:
            size = zip_path.stat().st_size
            size_mb = size / (1024 * 1024)
            click.echo("✅ Application packaged successfully!")
            click.echo(f"📦 File: {zip_path}")
            click.echo(f"📏 Size: {size_mb:.2f} MB")
            click.echo(f"📁 Files included: {files_added}")

            if not dockerfile_exists and not compose_exists:
                click.echo("\n⚠️  Deployment Tips:")
                click.echo(
                    "• Create a Dockerfile or docker-compose.yml for your application"
                )
                click.echo(
                    "• Ensure your app runs on port 8000 or set PORT environment variable"
                )
            elif compose_exists:
                click.echo("\n✅ Docker Compose detected!")
                click.echo("• Your app will be deployed using docker-compose.yml")
                click.echo("• Make sure your main service has port exposure configured")

            click.echo("\n🚀 Ready for milkcrate deployment:")
            click.echo("1. Go to the milkcrate admin dashboard")
            click.echo("2. Click 'Deploy New App'")
            click.echo(f"3. Upload {output}")
            click.echo("4. Set your app name and public route")
            click.echo("5. Deploy!")
        else:
            click.echo("❌ Error: No files were added to the archive", err=True)
            if zip_path.exists():
                zip_path.unlink()
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error creating ZIP file: {e}", err=True)
        if zip_path.exists():
            zip_path.unlink()
        sys.exit(1)


def reset_database(project_root: Path) -> None:
    """Reset the database by deleting and re-initializing it."""
    click.echo("🔄 Resetting database...")
    db_path = project_root / "instance" / "milkcrate.sqlite"

    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        click.echo("🗑️  Removed existing database")

    # Re-initialize database
    click.echo("🗄️  Initializing database...")
    os.chdir(project_root)

    try:
        from app import create_app
        from database import init_db as db_init

        app = create_app()
        with app.app_context():
            db_init()
        click.echo("✅ Database initialized successfully!")
    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}", err=True)
        sys.exit(1)

    click.echo("✅ Database reset complete!")


@cli.command()
@click.option(
    "--cache",
    is_flag=True,
    help="Remove Python cache files, bytecode, and build artifacts.",
)
@click.option(
    "--uploads",
    is_flag=True,
    help="Remove all files from uploads/ directory.",
)
@click.option(
    "--extracted",
    is_flag=True,
    help="Remove all files from extracted_apps/ directory.",
)
@click.option(
    "--db",
    "reset_db_flag",
    is_flag=True,
    help="Delete and re-initialize the database.",
)
@click.option(
    "--all",
    "clean_all_flag",
    is_flag=True,
    help="Clean everything: cache, uploads, extracted apps, and database.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompts (use with caution).",
)
def clean(
    cache: bool,
    uploads: bool,
    extracted: bool,
    reset_db_flag: bool,
    clean_all_flag: bool,
    yes: bool,
) -> None:
    """Clean cache files, uploads, extracted apps, and/or reset database.

    Cache cleaning does not require confirmation. All other operations require
    confirmation unless --yes is provided.

    Examples:
        milkcrate clean --cache
        milkcrate clean --uploads --extracted
        milkcrate clean --all
    """
    project_root = find_project_root()

    # If --all is specified, set all flags
    if clean_all_flag:
        cache = True
        uploads = True
        extracted = True
        reset_db_flag = True

    # If no options specified, show help
    if not any([cache, uploads, extracted, reset_db_flag]):
        click.echo("No cleanup options specified. Use --help for available options.")
        return

    # Clean cache (no confirmation needed)
    if cache:
        clean_python_cache(project_root)
        clean_build_cache(project_root)
        click.echo("✅ Cache cleanup complete!")

    # Clean uploads (requires confirmation)
    if uploads:
        if not yes:
            if not click.confirm(
                "⚠️  This will delete all files in the uploads/ directory. Continue?"
            ):
                click.echo("Cancelled.")
                return
        uploads_dir = project_root / "uploads"
        clean_directory(uploads_dir, "uploads")

    # Clean extracted apps (requires confirmation)
    if extracted:
        if not yes:
            if not click.confirm(
                "⚠️  This will delete all files in the extracted_apps/ directory. Continue?"
            ):
                click.echo("Cancelled.")
                return
        extracted_dir = project_root / "extracted_apps"
        clean_directory(extracted_dir, "extracted_apps")

    # Reset database (requires confirmation)
    if reset_db_flag:
        if not yes:
            if not click.confirm(
                "⚠️  This will delete all application data and user records. Continue?"
            ):
                click.echo("Cancelled.")
                return
        reset_database(project_root)

    click.echo("✅ Cleanup finished!")


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Directory to store backups (default: ./backups).",
)
@click.option(
    "--no-uploads",
    is_flag=True,
    help="Exclude uploads directory from backup.",
)
@click.option(
    "--no-extracted",
    is_flag=True,
    help="Exclude extracted_apps directory from backup.",
)
def backup(output: Path | None, no_uploads: bool, no_extracted: bool) -> None:
    """Create a backup of milkcrate data (database, uploads, extracted apps).

    Creates a timestamped compressed archive containing:
    - Database (instance/milkcrate.sqlite)
    - Uploads directory (unless --no-uploads is specified)
    - Extracted apps directory (unless --no-extracted is specified)

    Backups are stored in the backups/ directory by default.

    Examples:
        milkcrate backup
        milkcrate backup --output /path/to/backups
        milkcrate backup --no-uploads --no-extracted  # Database only
    """
    project_root = find_project_root()

    try:
        from services.backup import create_backup

        backup_path = create_backup(
            project_root=project_root,
            backup_dir=output,
            include_uploads=not no_uploads,
            include_extracted=not no_extracted,
        )

        size_mb = backup_path.stat().st_size / (1024 * 1024)
        click.echo("✅ Backup created successfully!")
        click.echo(f"📦 File: {backup_path}")
        click.echo(f"📏 Size: {size_mb:.2f} MB")
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Backup failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument(
    "backup_file", type=click.Path(exists=True, path_type=Path), required=False
)
@click.option(
    "--list",
    "list_backups_flag",
    is_flag=True,
    help="List all available backups.",
)
@click.option(
    "--backup-dir",
    type=click.Path(path_type=Path),
    help="Directory containing backups (default: ./backups).",
)
@click.option(
    "--no-uploads",
    is_flag=True,
    help="Do not restore uploads directory.",
)
@click.option(
    "--no-extracted",
    is_flag=True,
    help="Do not restore extracted_apps directory.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
def restore(
    backup_file: Path | None,
    list_backups_flag: bool,
    backup_dir: Path | None,
    no_uploads: bool,
    no_extracted: bool,
    yes: bool,
) -> None:
    """Restore milkcrate data from a backup.

    Restores the database and optionally uploads/extracted apps from a backup archive.
    Requires confirmation unless --yes is provided.

    Examples:
        milkcrate restore --list
        milkcrate restore backup_file.tar.gz
        milkcrate restore --backup-dir /path/to/backups
        milkcrate restore backup_file.tar.gz --no-uploads  # Database only
    """
    project_root = find_project_root()

    try:
        from services.backup import list_backups, restore_backup

        # List backups if requested
        if list_backups_flag:
            if backup_dir is None:
                backup_dir = project_root / "backups"

            backups = list_backups(backup_dir)
            if not backups:
                click.echo(f"No backups found in {backup_dir}")
                return

            click.echo(f"Available backups in {backup_dir}:")
            click.echo()
            for backup_path, timestamp, size_bytes in backups:
                size_mb = size_bytes / (1024 * 1024)
                click.echo(
                    f"  {backup_path.name} ({size_mb:.2f} MB) - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            return

        # Determine backup file
        if backup_file is None:
            if backup_dir is None:
                backup_dir = project_root / "backups"

            backups = list_backups(backup_dir)
            if not backups:
                click.echo(f"No backups found in {backup_dir}")
                click.echo("Use 'milkcrate restore --list' to see available backups.")
                sys.exit(1)

            # Use most recent backup
            backup_file = backups[0][0]
            click.echo(f"Using most recent backup: {backup_file.name}")

        # Confirm restoration
        if not yes:
            click.echo("⚠️  This will overwrite existing data:")
            click.echo("   - Database will be replaced")
            if not no_uploads:
                click.echo("   - Uploads directory will be replaced")
            if not no_extracted:
                click.echo("   - Extracted apps directory will be replaced")
            click.echo()

            if not click.confirm("Continue with restore?"):
                click.echo("Cancelled.")
                return

        # Perform restore
        click.echo("🔄 Restoring backup...")
        restore_backup(
            backup_path=backup_file,
            project_root=project_root,
            restore_uploads=not no_uploads,
            restore_extracted=not no_extracted,
        )

        click.echo("✅ Restore completed successfully!")
        click.echo(
            "⚠️  You may need to restart the milkcrate service for changes to take effect."
        )

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Restore failed: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
