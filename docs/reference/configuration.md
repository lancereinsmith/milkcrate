# Configuration

Configuration is provided via environment variables and the Flask config objects in `milkcrate_core/config.py`.

## Environment variables

### Core Configuration

- **SECRET_KEY**: Flask secret key. Default: `dev-key-change-in-production`.
- **MILKCRATE_ENV**: `development` or `production`. Default: `development`.
- **FLASK_INSTANCE_PATH**: Directory for instance data (SQLite DB and app state). Default: `instance`. The database file is `<instance>/milkcrate.sqlite`.
- **UPLOAD_FOLDER**: Upload directory for raw uploaded ZIPs. Default: `uploads`.
- **EXTRACTED_FOLDER**: Directory for extracted app contents during build. Default: `extracted_apps`.
- **TRAEFIK_NETWORK**: Docker network name for Traefik. Default: `milkcrate-traefik`.
- **MAX_CONTENT_LENGTH**: Max upload size in bytes. Set in `BaseConfig` to 16MB; not read from env.
- **DEFAULT_HOME_ROUTE**: Optional path to redirect `/` to (e.g., `/my-app`). Empty = home lists apps or shows instructions.

### Security Configuration

- **MILKCRATE_ADMIN_PASSWORD**: Overrides the admin password stored in DB (plain text).
- **SSL_CERT_FILE**: Path to SSL certificate file for HTTPS support.
- **SSL_KEY_FILE**: Path to SSL private key file for HTTPS support.
- **FORCE_HTTPS**: Force HTTPS redirects even when not in production. Set to `true` or `false`.

### Rate Limiting (Flask-Limiter)

Rate limiting defaults are set in code (`memory://`, `fixed-window`). To customize, set these on the Flask config (e.g. from env in `config.py`):

- **RATELIMIT_STORAGE_URI**: Storage backend. Default: `memory://`.
- **RATELIMIT_STRATEGY**: Strategy. Default: `fixed-window`.

## Precedence for admin password

Milkcrate uses **password-only authentication** (no username required). The admin password is determined by the following precedence:

1. **Environment**: `MILKCRATE_ADMIN_PASSWORD` (highest priority, always plain text)
2. **Database setting**: `admin_password` (set from admin UI, stored as hash if set via UI)
3. **Fallback**: `admin` (plain text default)

**Important Notes:**

- Environment variable always takes precedence and is treated as plain text
- Passwords stored in the database via the admin UI are hashed using werkzeug
- The default password `admin` does not meet password strength requirements - change it immediately in production

## Example: docker-compose

```yaml
services:
  milkcrate:
    environment:
      - MILKCRATE_ENV=production
      - SECRET_KEY=change-me
      - MILKCRATE_ADMIN_PASSWORD=${MILKCRATE_ADMIN_PASSWORD}
      - TRAEFIK_NETWORK=milkcrate-traefik
    volumes:
      - ./uploads:/app/uploads
      - ./extracted_apps:/app/extracted_apps
      - ./instance:/app/instance
```

## Example: .env (local)

```bash
SECRET_KEY=super-secret
MILKCRATE_ENV=development
DEFAULT_HOME_ROUTE=/my-app
```
