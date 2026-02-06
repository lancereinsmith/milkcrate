# Blueprints & Routes

This section documents the primary Flask blueprints and their routes.

## public

- **Blueprint**: `blueprints/public.py`
- **Prefix**: none
- **Routes**:
  - `GET /`: Home. Redirects to admin if authenticated; otherwise, if a default home is configured, redirects there; else lists installed apps.

## auth

- **Blueprint**: `blueprints/auth.py`
- **Prefix**: none
- **Routes**:
  - `GET|POST /login`: Password-only login. Accepts `password` form field. Uses `get_admin_password()` precedence.
  - `GET /logout`: Logs out current user; redirects to public index.

## admin

- **Blueprint**: `blueprints/admin.py`
- **Prefix**: `/admin`
- **Routes**:
  - `GET /admin`: Admin dashboard with deployed app list and default route UI.
  - `POST /admin/delete/<app_id>`: Delete an application. Stops/removes container, removes image, cleans extracted files, deletes DB record.
  - `POST /admin/update/<app_id>`: Update an existing application with a new ZIP file. Stops old container, builds new image, starts new container with same route.
  - `POST /admin/toggle_status/<app_id>`: Start/stop container based on real-time status.
  - `GET /admin/htmx/status-badges`: HTMX endpoint returning status badges HTML for all apps.
  - `POST /admin/settings/default-route`: Set default home route.
  - `POST /admin/settings/password`: Set stored admin password (env var still overrides).

## upload

- **Blueprint**: `blueprints/upload.py`
- **Prefix**: none
- **Routes**:
  - `GET|POST /upload`: Upload page for ZIP archives. Validates, extracts, deploys via `services.deploy`. Includes volume mount selection interface.

## volumes

- **Blueprint**: `blueprints/volumes.py`
- **Prefix**: `/admin/volumes`
- **Routes**:
  - `GET /admin/volumes`: List all volumes with statistics (file count, total size).
  - `GET /admin/volumes/create`: Create volume form.
  - `POST /admin/volumes/create`: Create new volume. Validates name, creates Docker volume, stores metadata.
  - `GET /admin/volumes/<volume_id>`: View volume details with file list and drag-and-drop upload interface.
  - `POST /admin/volumes/<volume_id>/upload`: Upload file to volume. Supports individual files and automatic ZIP extraction.
  - `POST /admin/volumes/<volume_id>/delete`: Delete volume. Removes Docker volume and database records.
  - `GET /admin/volumes/api/list`: JSON API endpoint returning all volumes with metadata.

## Reserved routes

- `/traefik`, `/admin`, `/login`, `/logout`, `/upload`, `/static`, and paths under `/admin` (e.g. `/admin/volumes`, `/admin/settings`) are reserved and cannot be used as application public routes.
