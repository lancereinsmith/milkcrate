# Services

## services.deploy

Responsibilities:

- **allowed_file(filename)**: Accepts only `.zip`.
- **extract_zip_safely(zip_path, extract_path)**:
  - Prevents path traversal (rejects absolute paths and `..`).
  - Ensures `Dockerfile` or `docker-compose.yml` exists.
  - **Multi-language support**: No longer restricted to Python applications.
- **detect_deployment_type(app_path)**: Returns `"dockerfile"` or `"docker-compose"` based on presence of Dockerfile vs docker-compose.yml.
- **deploy_application(app_path, app_name, public_route, traefik_network, is_public=False, volume_mounts=None)**:
  - Builds Docker image (tag: `milkcrate-<name>:<timestamp>`).
  - Picks internal port (prefers 8000; else lowest exposed TCP).
  - Ensures no conflicting container name (`app-<name>`), then runs container.
  - **Enhanced Security**: Applies comprehensive security policies and resource quotas.
  - **Volume Support**: Mounts specified volumes to container (format: `{volume_name: {bind: path, mode: rw}}`).
  - Applies Traefik labels for routing and prefix stripping.
  - Inserts app record into DB (including volume_mounts as JSON) and updates status after a short delay.
- **deploy_docker_compose(...)**: Deploys a Docker Compose application (parse compose, inject Traefik labels, deploy stack).
- **update_application(app_id, app_path, new_zip_filename, traefik_network=None)**:
  - Updates an existing Dockerfile-based app with new code from a ZIP file.
  - Stops and removes the old container and image.
  - Builds new Docker image with timestamp.
  - Starts new container with same route and configuration.
  - Updates database record with new container/image info.
- **update_docker_compose_application(app_id, ...)**: Updates an existing Docker Compose app with new code.

### Container Security Policies

- **Resource Limits**: Memory (512MB), CPU (50%), process limits (100)
- **Security Constraints**: Dropped capabilities, non-root execution, secure temp directories
- **Logging**: Structured logging with rotation and size limits

Traefik labels on containers:

- `traefik.http.routers.<name>.rule`: `PathPrefix(`<route>`)` (accepts any hostname)
- `traefik.http.services.<name>.loadbalancer.server.port`: resolved internal port
- `traefik.http.middlewares.<name>_stripprefix.stripprefix.prefixes`: the route

## services.status_manager

Responsibilities:

- Query Docker for precise container state and attributes.
- Optionally probe HTTP endpoints for health.
- Return a composite status with display text and color.

Key classes/functions:

- **ContainerStatus**: constants for states and UI mapping including:
  - Docker states: `created`, `running`, `paused`, `restarting`, `exited`, `dead`, `removing`
  - Custom states: `starting`, `healthy`, `unhealthy`, `ready`, `not_ready`, `deploying`, `updating`, `deleting`, `error`
- **StatusManager**:
  - `get_container_status(container_id)`: Returns (status, details) from Docker API.
  - `check_application_health(app_name, public_route, internal_port, timeout=5)`: Probes HTTP endpoints; returns (is_healthy, health_details).
  - `get_comprehensive_status(container_id, app_name, public_route, internal_port)`: Combines Docker state and optional health check; returns display status and badge color.
- **get_status_manager()**: Returns singleton (cached via `lru_cache`).

Health endpoints tried:

- `<route>/api/health`
- `<route>/api/status`
- `<route>/health`
- `<route>/status`
- `<route>/` (fallback)

## services.audit

**New in latest version**: Comprehensive audit logging for administrative actions.

Responsibilities:

- **AuditLogger**: Centralized logging for all admin actions
- **log_admin_action()**: Log deployment, deletion, start/stop operations
- **get_audit_logs()**: Retrieve audit logs for admin dashboard
- **JSON Structured Logging**: Timestamped, structured logs with user context

Features:

- **User Context**: IP addresses, user agents, authenticated user tracking
- **Action Details**: Resource types, IDs, success/failure status, error messages
- **Log Rotation**: Automatic log rotation and size management
- **Security Monitoring**: Track all administrative actions for compliance

## services.validation

**New in latest version**: Input validation and sanitization utilities.

Responsibilities:

- **validate_app_name()**: Strict validation of application names
- **validate_public_route()**: Route validation with reserved path protection
- **validate_password()**: Password strength requirements
- **sanitize_input()**: General input sanitization
- **validate_and_sanitize_app_input()**: Combined validation for app deployment

Security Features:

- **XSS Prevention**: HTML tag removal and input sanitization
- **Reserved Names**: Protection against system reserved names
- **Path Validation**: Route format and conflict prevention
- **Character Filtering**: Alphanumeric validation with safe special characters

## services.security

**New in latest version**: HTTPS support and security headers middleware.

Responsibilities:

- **SecurityHeaders**: Comprehensive security headers for all responses
- **SSL/TLS Support**: Certificate management and HTTPS configuration
- **Self-signed Certificates**: Automatic certificate generation for development
- **HTTPS Redirects**: Automatic HTTP to HTTPS redirects in production

Security Headers Applied:

- **Content Security Policy**: Strict CSP to prevent XSS
- **X-Frame-Options**: Clickjacking protection
- **HSTS**: HTTP Strict Transport Security
- **Cache Control**: No-cache headers for admin pages
- **Referrer Policy**: Privacy-focused referrer handling

## services.volume_manager

**New in latest version**: Docker volume management with file upload capabilities.

Responsibilities:

- **VolumeManager**: Core service for managing Docker volumes and files (DB metadata is in `database.py`).
- **create_volume(volume_name, description=None)**: Create new Docker volume; returns (success, message, docker_volume_name). Naming: `milkcrate-vol-{name}`.
- **delete_volume(docker_volume_name)**: Remove Docker volume; returns (success, message).
- **upload_file_to_volume(docker_volume_name, file_path, destination_path="/")**: Upload a single file via temporary Alpine container.
- **upload_zip_to_volume(docker_volume_name, zip_path, destination_path="/")**: Extract ZIP into volume via temporary container; returns (success, message, file_count).
- **list_volume_files(docker_volume_name, path="/")**: List files in a volume; returns (success, message, list of file dicts).
- **get_volume_size(docker_volume_name)**: Get total size of volume; returns (success, message, size_bytes).

Volume Operations:

- **Docker Integration**: Uses Docker Python SDK for volume operations
- **Temporary Containers**: Uses Alpine containers for file operations
- **TAR Archives**: Efficient file transfer via Docker's `put_archive` API
- **Automatic Cleanup**: Removes temporary containers and files
- **Path Safety**: Prevents path traversal attacks in ZIP extraction

File Upload Process:

1. File received via Flask and saved to temporary location
2. If ZIP file: extracted and validated for path traversal
3. Temporary Alpine container created with volume mounted
4. Files copied to volume via Docker API
5. Container removed and temporary files cleaned up
6. Database updated with file metadata (name, path, size)

Volume Naming:

- User-provided names are prefixed: `milkcrate-vol-{name}`
- Prevents conflicts with other Docker volumes
- Names validated (alphanumeric, hyphens, underscores only)

Security Features:

- Secure filename handling with `secure_filename()`
- Path traversal prevention in ZIP extraction
- Rate limiting on upload endpoints (30 per hour)
- Volume name validation and sanitization

## services.backup

Backup and restore for milkcrate data (database, uploads, extracted apps). Used by the CLI `milkcrate backup` and `milkcrate restore` commands.

Responsibilities:

- **create_backup(project_root, backup_dir=None, include_uploads=True, include_extracted=True)**: Creates a timestamped `.tar.gz` in `backups/` (or `backup_dir`). Includes `instance/milkcrate.sqlite`, optional `uploads/` and `extracted_apps/`. Returns path to archive.
- **list_backups(backup_dir)**: Returns list of (path, timestamp, size_bytes) for backups in directory.
- **restore_backup(backup_path, project_root, restore_uploads=True, restore_extracted=True)**: Restores from a backup archive.
- **get_backup_info(backup_path)**: Returns metadata (e.g. timestamp, size) for a backup file.

## services.compose_parser

Docker Compose file parsing and validation. Used by deploy when deploying or updating Compose-based applications.

Responsibilities:

- **parse_docker_compose(compose_path)**: Load and validate YAML; returns `(is_valid, error_message, parsed_data)`.
- **get_main_service(compose_data)**: Identify main service: first service with `milkcrate.main_service=true` label, else first service. Returns `(service_name, service_config)`.
- **extract_service_port(service_config)**: Get internal port from `ports` or `expose` (default 8000).
- **validate_compose_for_milkcrate(compose_data)**: Ensures main service has build/image and exposes a port; returns `(is_valid, error_message)`.
- **get_compose_services_info(compose_data)**: Returns dict with `main_service`, `main_service_config`, `internal_port`, `total_services`, `service_names`.
