# milkcrate

![milkcrate logo](static/logo.png)

Deploy and manage containerized apps with Flask, Docker, and Traefik — from a simple web UI.

[**Full documentation**](https://lancereinsmith.github.io/milkcrate/)

## Features

- **Upload to deploy**: ZIP an app (with `Dockerfile` or `docker-compose.yml`) and deploy from the dashboard.
- **Volume management**: Create Docker volumes, upload files, mount to containers.
- **Traefik routing**: Automatic `PathPrefix` routing and prefix stripping.
- **HTTPS support**: Automatic Let's Encrypt SSL certificates for production deployments.
- **Status & control**: Real-time status, start/stop, and delete.

## Quick start

Prereqs: Python 3.12+, Docker, Docker Compose, uv

```bash
uv run milkcrate setup
uv run milkcrate run
```

Access at `http://localhost:5001` (development) or `http://localhost/admin` (Docker Compose)

Run with Docker Compose:

```bash
uv run milkcrate up
```

Access at `http://localhost/admin` or `http://your-ip/admin` (accepts any hostname by default)

Default credentials:

- **Password**: `admin` (change in production)

**Note**: Password-only authentication (no username required).

## Deploy an app

1. Prepare a ZIP containing your app with a `Dockerfile` or `docker-compose.yml`.
2. Log in → Upload → choose name and public route (e.g., `/sample`).
3. Submit; access at `http://localhost/<route>` (dev) or your domain.

Sample app:

```bash
uv run milkcrate package-sample
# Upload the generated sample-app.zip via the UI
```

## Configuration (env)

- `SECRET_KEY` — Flask secret key.
- `MILKCRATE_ENV` — `development` (default) or `production`.
- `ENABLE_HTTPS` — Enable HTTPS/Let's Encrypt mode (`true`/`false`, default: `false`).
- `LETSENCRYPT_EMAIL` — Email for Let's Encrypt certificate notifications.
- `DATABASE` — path to SQLite DB (defaults under `instance/`).
- `UPLOAD_FOLDER`, `EXTRACTED_FOLDER` — storage paths.
- `TRAEFIK_NETWORK` — Docker network for routing.
- `MILKCRATE_ADMIN_PASSWORD` — overrides stored admin password.
- `DEFAULT_HOME_ROUTE` — optional `/path` to redirect `/`.

For production HTTPS setup, see `docs/production/https-setup.md`.

## Multi-Website Hosting (Optional)

Want to run other websites alongside milkcrate? Add nginx:

```bash
sudo ./install_nginx.sh
```

See `docs/production/multi-website-setup.md` for details.

```bash
uv run milkcrate docs-serve
```

## License

MIT — see [LICENSE](LICENSE) file.
