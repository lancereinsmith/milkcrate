# Changelog

All notable changes to milkcrate will be documented in this file.

## [0.1.1] - 2025-02-15

### Security

- Use timing-safe `hmac.compare_digest()` for all plaintext password comparisons to prevent timing attacks
- Remove `shell=True` from CLI `run_command()` — commands are now parsed via `shlex.split()` and passed as lists to `subprocess.run()`
- Fail loudly when `SECRET_KEY` is still set to a default value in production mode

### Added

- `--yes` / `-y` flag on `milkcrate init-db` to skip confirmation prompt
- Confirmation prompt before `init-db` destroys existing data
- Database index on `deployed_apps.public_route` for faster route lookups
- Migration code to add the `public_route` index to existing databases
- Logging for database schema migration failures (previously silently ignored)

### Changed

- Extracted duplicated status-enrichment logic in `database.py` into `_apply_fallback_status()`, `_apply_enhanced_status()`, and `_enhance_app_status()` helpers
- Extracted duplicated container security policies in `deploy.py` into `_default_security_policies()` function
- Updated `test_security_policies_structure` test to import and verify the actual `_default_security_policies()` function

## [0.1.0] - 2025-02-06

- Initial release
- Flask-based web UI for deploying and managing Docker containers
- Support for both Dockerfile and docker-compose.yml deployments
- Traefik reverse proxy integration with automatic PathPrefix routing
- HTTPS support via Let's Encrypt
- Volume management with file uploads
- Backup and restore functionality
- Unified CLI (`milkcrate`) for setup, deployment, and maintenance
- CSRF protection, rate limiting, and security headers
- Audit logging for admin actions
