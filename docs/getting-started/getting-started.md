# Getting Started

## Prerequisites

- **Python**: 3.12+
- **Docker**: Engine and Compose
- **uv**: Python package manager (preferred)

> **For Ubuntu Server**: Use the [Ubuntu Installation Guide](../getting-started/ubuntu-installation.md) for automated setup.

## Package Management with uv

Milkcrate uses `uv` for Python dependency management. All commands use `uv run` to execute within the managed environment:

```bash
# Install dependencies
uv sync

# Run milkcrate commands
uv run milkcrate <command>

# Or, manually activate virtual environment and run:
milkcrate <command>
```

## Quick Start with CLI

```bash
# Check prerequisites
uv run milkcrate check

# Complete setup (install dependencies + initialize database)
uv run milkcrate setup
```

## Starting in Production mode

```bash
# Start Docker Compose stack
uv run milkcrate up
```

## Default credentials

- **Password**: `admin` (⚠️ **Change in production**)

**Note**: Milkcrate uses password-only authentication (no username required). The default password is `admin` if no other password is configured.

## First containerized application deployment

### Dockerfile Application

1. Prepare a ZIP containing your app with `Dockerfile` (any programming language supported).
    - See the [CLI Reference: package application](../reference/cli.md#package).
2. Log in to the admin dashboard.
3. Click "Deploy Your First App" or select "Deploy New App" from the top menu.
4. Fill in:
    - **Application Name**: e.g., `sample-app` (alphanumeric, hyphens, underscores only)
    - **Route**: e.g., `/sample` (validated for conflicts and reserved paths)
    - **Application Package (ZIP)**: upload your archive
5. Click "Deploy Applicaiton" and wait for deployment to complete.

### Docker Compose Application

1. Prepare a ZIP containing your app with `docker-compose.yml` and required labels.
2. Follow the Steps 2-5 above.

**Note**: Your `docker-compose.yml` must include a service with `milkcrate.main_service=true` label. See [Docker Compose Apps](../user-guide/docker-compose-apps.md) for detailed configuration.

## Updating an app

1. Prepare a new ZIP containing your updated app with `Dockerfile` or `docker-compose.yml`.
2. In the admin dashboard, find your deployed app.
3. Click the **Update** button (upload icon) in the Actions column.
4. In the modal, select your new ZIP file.
5. Click "Update Application" and wait for the process to complete.
6. The app will maintain the same route while launching the new code.

## CLI Reference

For a complete list of available commands, see the [CLI Reference](../reference/cli.md) or run:

```bash
uv run milkcrate --help
```

Common commands:

- `milkcrate up` - Start Docker services
- `milkcrate down` - Stop Docker services
- `milkcrate setup` - Complete setup
- `milkcrate check` - Verify prerequisites
- `milkcrate backup` - Create a backup of milkcrate data
- `milkcrate status` - Check system status
- `milkcrate package` - Package the current directory as a milkcrate-deployable app

## Next steps

- **User guide**: [Deploying Applications](../user-guide/deployment.md), [Dockerfile Apps](../user-guide/dockerfile-apps.md), [Docker Compose Apps](../user-guide/docker-compose-apps.md), [Volume Management](../user-guide/volumes.md), [Routing](../user-guide/routing.md)
- **Production**: [Traefik Configuration](../production/traefik.md), [Multi-Website Setup](../production/multi-website-setup.md), [Security](../production/security.md), [Backups](../production/backups.md)
- **Reference**: [CLI Reference](../reference/cli.md), [Configuration](../reference/configuration.md), [Nginx Reference](../reference/nginx-reference.md)
- **Development**: [Running Milkcrate](../development/running.md), [Architecture](../development/architecture.md), [Blueprints & Routes](../development/blueprints.md), [Database](../development/database.md)
- **Support**: [Troubleshooting](../support/troubleshooting.md)
