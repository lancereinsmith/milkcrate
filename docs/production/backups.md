# Backups

milkcrate includes a built-in backup system accessible via the CLI.

## Creating Backups

Use the `milkcrate backup` command to create timestamped backups:

```bash
# Create a full backup (database, uploads, extracted apps)
milkcrate backup

# Create backup in a specific directory
milkcrate backup --output /path/to/backups

# Create database-only backup
milkcrate backup --no-uploads --no-extracted
```

Backups are stored as compressed tar.gz archives in the `backups/` directory by default, with filenames like `milkcrate_backup_20250127_143022.tar.gz`.

## Restoring Backups

Use the `milkcrate restore` command to restore from a backup:

```bash
# List available backups
milkcrate restore --list

# Restore from a specific backup file
milkcrate restore backups/milkcrate_backup_20250127_143022.tar.gz

# Restore most recent backup (auto-detected)
milkcrate restore

# Restore database only (skip uploads and extracted apps)
milkcrate restore backup_file.tar.gz --no-uploads --no-extracted
```

## Backup Contents

Each backup archive contains:

- **Database**: `instance/milkcrate.sqlite` - All application data and settings
- **Instance files**: Other files in `instance/` directory (e.g., audit logs)
- **Uploads** (optional): `uploads/` directory - Uploaded application ZIP files
- **Extracted apps** (optional): `extracted_apps/` directory - Extracted application source
