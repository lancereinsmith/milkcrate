# Architecture

Milkcrate is a self-contained web platform for deploying containerized applications through a simple web interface.

## System Overview

```text
┌──────────────────────────────────────────────────────────┐
│                     Internet/Browser                     │
└────────────────────────┬─────────────────────────────────┘
                         │ Port 80
                         ▼
┌───────────────────────────────────────────────────────────┐
│                   Traefik (Reverse Proxy)                 │
│  • Service Discovery via Docker Labels                    │
│  • PathPrefix Routing with Dynamic Priorities             │
│  • SSL Termination (Production)                           │
└────────┬─────────────────────┬────────────────────────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌───────────────────────────────┐
│ Milkcrate App   │   │  Deployed User Applications   │
│ (Flask)         │   │  • Dockerfile-based           │
│ Port 5001       │   │  • Docker Compose-based       │
└────────┬────────┘   │  • Volume mounts supported    │
         │            └───────────────────────────────┘
         ▼                     │
┌─────────────────┐            │
│ SQLite Database │            ▼
└─────────────────┘   ┌───────────────────────────────┐
                      │     Docker Volumes            │
                      │  • Persistent storage         │
                      │  • Shared across containers   │
                      └───────────────────────────────┘
```

## Core Components

| Component | Purpose |
|-----------|---------|
| **Flask App** | Web interface, orchestrates deployments (port 5001) |
| **Traefik** | Reverse proxy, routes traffic to containers (port 80) |
| **Docker** | Builds and runs uploaded applications |
| **Docker Volumes** | Persistent storage for application data |
| **SQLite** | Stores app metadata, volume info, and settings |

## Project Structure

```text
milkcrate/
├── app.py                      # Application entrypoint
├── milkcrate_core/             # App factory, CLI, config
├── blueprints/                 # Flask routes (admin, auth, public, upload, volumes)
├── services/                   # Business logic (deploy, status, audit, volume_manager)
├── database.py                 # SQLite helpers
├── templates/                  # Jinja2 templates
├── static/                     # CSS, JavaScript
├── tests/                      # Test suite
└── docs/                       # Documentation
```

## Request Flow

### Traffic Routing

| Route | Handler | Priority |
|-------|---------|----------|
| `/traefik` | Blocked on port 80 | 50 |
| `/admin`, `/login`, `/logout`, `/upload` | Milkcrate platform | 30 |
| `/my-app` (deployed apps) | User containers | 100+ (dynamic) |
| `/` (catch-all) | Milkcrate platform | 1 |

### Deployment Flow

**Dockerfile apps:**

1. Upload ZIP → Extract → Build Docker image
2. Detect port from `EXPOSE` directive (default: 8000)
3. Create container with Traefik labels
4. Mount selected volumes (optional)
5. Apply security policies → Start container

**Docker Compose apps:**

1. Upload ZIP → Extract → Parse `docker-compose.yml`
2. Identify main service (via `milkcrate.main_service=true` label)
3. Inject Traefik labels → Deploy stack
4. Mount selected volumes (optional)

## Network Architecture

- **Network**: `milkcrate-traefik` (Docker bridge)
- All services join this network automatically
- Deployed apps accessible only through Traefik (security)
- Port 5001 provides direct access (bypasses Traefik)

## Security

- **Container limits**: 512MB RAM, 50% CPU, 100 PIDs
- **Dropped capabilities**: ALL (only NET_BIND_SERVICE added)
- **Authentication**: Password-only with hashed storage
- **Protection**: CSRF, rate limiting, audit logging

See [Security](../production/security.md) for details.

## Configuration

Key environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MILKCRATE_ENV` | `development` | `development` or `production` |
| `MILKCRATE_ADMIN_PASSWORD` | `admin` | Admin password |
| `SECRET_KEY` | `dev-key...` | Flask sessions |
| `FLASK_INSTANCE_PATH` | `instance` | Instance directory (DB path: `<instance>/milkcrate.sqlite`) |
| `TRAEFIK_NETWORK` | `milkcrate-traefik` | Docker network |

See [Configuration](../reference/configuration.md) for complete reference.

## Related Documentation

- [Blueprints & Routes](blueprints.md) - Route definitions
- [Database](database.md) - Schema and helpers
- [CLI Reference](../reference/cli.md) - Command-line tools
- [Routing](../user-guide/routing.md) - How Traefik routing works
