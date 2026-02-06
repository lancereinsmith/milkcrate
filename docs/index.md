# milkcrate

![milkcrate logo](assets/img/logo.png)

A web-based platform for deploying and managing containerized applications.

## Features

- Upload ZIP files containing Dockerfile or docker-compose.yml for deployment
- Deploy applications in any language via containers
- Multi-container applications with Docker Compose support
- Docker volume management with drag-and-drop file uploads
- Traefik reverse proxy with automatic routing and prefix stripping
- Hashed passwords, CSRF protection, and rate limiting
- HTTPS/TLS support with security headers
- SQLite storage (no external database required)

## Quick Reference

### Essential Commands

```bash
# Setup
uv run milkcrate setup

# Production mode (full Docker stack; with Traefik)
uv run milkcrate up
uv run milkcrate down

# Package app
uv run milkcrate package --output my-app.zip
```

### Default Ports

- **milkcrate**: 5001
- **Traefik**: 80 (HTTP), 8080 (dashboard)
- **Apps**: 8000 (internal)
