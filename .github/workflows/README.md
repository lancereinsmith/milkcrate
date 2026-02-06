# CI/CD Workflows

## Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| **tests.yml** | Push/PR to main | Runs pytest across OS/Python matrix and lints with ruff + ty |
| **docker.yml** | Push/PR to main | Builds Docker image, pushes to GHCR on merge |
| **docs.yml** | Push/PR to main | Builds mkdocs site, deploys to GitHub Pages on merge |
| **release.yml** | Tag `v*` or manual | Runs tests, builds package, creates GitHub Release, publishes to PyPI |

## Required Repository Settings

### GitHub Pages

Go to **Settings > Pages > Build and deployment** and set **Source** to **GitHub Actions**.

### Secrets

| Secret | Workflow | Description |
|---|---|---|
| `GITHUB_TOKEN` | docker, release | Provided automatically by GitHub Actions — no setup needed |

### Permissions

Under **Settings > Actions > General > Workflow permissions**, select **Read and write permissions** so that workflows can push Docker images (GHCR) and create releases.

### Container Registry (GHCR)

If the Docker workflow fails with `403 Forbidden` when pushing to `ghcr.io`:

1. Confirm **Read and write permissions** is set (see above).
2. If the package already exists, go to **your user Settings > Packages**, find the `milkcrate` container, open its **Settings > Manage Actions access**, and add your repository with **Write** role.

### Environments

The docs workflow deploys to a `github-pages` environment. GitHub creates this automatically the first time a Pages deployment runs. No manual setup is needed.
