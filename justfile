# Milkcrate Justfile - Common development commands

# Default recipe - show available commands
default:
    @just --list

# Install dependencies with uv
sync:
    uv sync

# Update dependencies
update:
    uv lock --upgrade
    uv sync

# Run all checks (lint, format, rumdl, ty)
check: lint-check format-check rumdl-check ty

# Run all checks (lint, format, rumdl)
doit: lint format rumdl

# Lint code with ruff
lint-check:
    uv run ruff check .

# Lint code with ruff
lint:
    uv run ruff check --fix .

# Check code formatting without making changes
format-check:
    uv run ruff format --check .

# Format code with ruff
format:
    uv run ruff format .

# Lint markdown files with rumdl
rumdl-check:
    uv run rumdl check .

# Lint markdown files with rumdl
rumdl:
    uv run rumdl check --fix .

# Type check with ty
ty:
    uv run ty check

# Run tests with pytest
test:
    uv run pytest

# Run tests with coverage report
test-cov:
    uv run pytest --cov --cov-report=html --cov-report=term

# Run development server
run:
    uv run milkcrate run

# Run production server
up:
    uv run milkcrate up

# Stop production server
down:
    uv run milkcrate down

# Rebuild milkcrate image
rebuild:
    uv run milkcrate rebuild

# Restart Docker Compose services
restart: down up

# Restart Docker Compose services
restart-all: down rebuild up

# View Docker Compose logs
docker-logs:
    docker-compose logs -f

# Serve documentation locally
docs:
    uv run mkdocs serve

# Build documentation
docs-build:
    uv run mkdocs build

# Clean build artifacts and caches
clean:
    uv run milkcrate clean

# Initialize database schema
db-init:
    uv run milkcrate init-db

# Backup deployment data
backup DIR:
    uv run milkcrate backup {{DIR}}