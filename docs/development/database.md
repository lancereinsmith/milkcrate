# Database

milkcrate uses SQLite with helpers in `database.py` and an initial schema in `schema.sql`.

## Location

- Default path: `<instance>/milkcrate.sqlite`
- Configurable via **FLASK_INSTANCE_PATH** (instance directory; DB file name is fixed).

## Schema

Tables:

- **deployed_apps**:
  - `app_id` (PK)
  - `app_name`
  - `container_id`
  - `image_tag`
  - `public_route`
  - `internal_port`
  - `is_public` (0/1; currently unused in UI but present for compatibility)
  - `status`
  - `deployment_date`
  - `deployment_type` (`dockerfile` or `docker-compose`)
  - `compose_file` (path to compose file; compose apps only)
  - `main_service` (main service name; compose apps only)
  - `volume_mounts` (JSON string; format: `{"docker_vol_name": {"bind": "/path", "mode": "rw"}}`)
- **settings**:
  - `setting_key` (PK)
  - `setting_value`
  - `updated_date`
- **volumes**:
  - `volume_id` (PK)
  - `volume_name` (UNIQUE)
  - `docker_volume_name` (UNIQUE; format: `milkcrate-vol-{name}`)
  - `description`
  - `created_date`
  - `file_count`
  - `total_size_bytes`
- **volume_files**:
  - `file_id` (PK)
  - `volume_id` (FK → volumes)
  - `file_name`
  - `file_path`
  - `file_size_bytes`
  - `uploaded_date`

Indexes:

- `idx_container_id` on `deployed_apps(container_id)`
- `idx_internal_port` on `deployed_apps(internal_port)`
- `idx_deployment_type` on `deployed_apps(deployment_type)`
- `idx_volume_name` on `volumes(volume_name)`
- `idx_volume_files_volume_id` on `volume_files(volume_id)`

## Lifecycle

- **init_db()**: Reads `schema.sql` and creates tables.
- **_migrate_schema_if_needed()**: Idempotent, adds columns/tables if missing.

## Common helpers

### Application Helpers

- **get_all_apps()**: List all apps.
- **get_app_by_id(app_id)**: Single app by ID.
- **get_app_by_container_id(container_id)**: Lookup via Docker ID.
- **get_app_by_route(public_route)**: Lookup by public route.
- **get_public_apps()**: List apps with is_public=1.
- **insert_app(...)**: Create record after container run.
- **update_app_status(app_id, status)**: Update status value.
- **update_app_container_info(app_id, container_id, image_tag, deployment_type=None, compose_file=None, main_service=None)**: Update container info after app update.
- **set_app_public(app_id, is_public)**: Set is_public flag.
- **delete_app(app_id)**: Remove record.

### Volume Helpers

- **insert_volume(volume_name, docker_volume_name, description)**: Create volume record.
- **get_all_volumes()**: List all volumes with metadata.
- **get_volume_by_id(volume_id)**: Single volume by ID.
- **get_volume_by_name(volume_name)**: Lookup by user-provided name.
- **get_volume_by_docker_name(docker_volume_name)**: Lookup by Docker volume name.
- **update_volume_stats(volume_id, file_count, total_size_bytes)**: Update aggregated statistics.
- **delete_volume(volume_id)**: Remove volume and associated file records (CASCADE).
- **insert_volume_file(volume_id, file_name, file_path, file_size_bytes)**: Record uploaded file.
- **get_volume_files(volume_id)**: List all files in a volume.

### Settings Helpers

- **get_default_home_route() / set_default_home_route(route)**: Persist homepage redirect.
- **get_admin_password() / set_admin_password(pw)**: Manage effective admin password.

## Settings precedence

- Admin password precedence documented in Configuration.
