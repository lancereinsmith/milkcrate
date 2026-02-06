# CLI Reference

milkcrate provides a unified command-line interface for all operations.

## Usage

```bash
uv run milkcrate <command>
```

For detailed help on any command, use:

```bash
milkcrate <command> --help
```

## Commands

The following commands are available. All commands support `--help` for detailed usage information.

::: mkdocs-click
    :module: milkcrate_core.cli
    :command: cli
    :depth: 2

## Packaging Applications

```bash
# Package current directory (basic)
milkcrate package

# Package with custom name
milkcrate package --output my-webapp.zip

# Package excluding specific files
milkcrate package --exclude "*.log" --exclude "temp/*"

# Package docker-compose application
milkcrate package --output my-multi-service-app.zip
```

## Maintenance

```bash
# Create a backup of all data
milkcrate backup

# List available backups
milkcrate restore --list

# Restore from a backup
milkcrate restore backups/milkcrate_backup_20250127_143022.tar.gz

# Clean Python cache and build artifacts
milkcrate clean --cache

# Clean up development artifacts
milkcrate clean --uploads --extracted

# Full reset including cache, uploads, extracted apps, and database (caution!)
milkcrate clean --all
```

## Project Root Detection

The CLI automatically detects the milkcrate project root by looking for key files (`app.py`, `pyproject.toml`, `justfile`). You can run CLI commands from any subdirectory within the project.
