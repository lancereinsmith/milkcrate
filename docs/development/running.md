# Running Milkcrate

Milkcrate can be run in two modes: **development mode** and **production mode**. Choose the mode that fits your needs.

## Development Mode (`milkcrate run`)

**Use for**: Active development, debugging, and quick testing.

```bash
# Start development server
uv run milkcrate run
```

**Characteristics:**

- ✅ Runs Flask directly on your host machine (not containerized)
- ✅ Debug mode enabled with auto-reload on code changes
- ✅ Fast startup and immediate code changes visible
- ❌ No Traefik reverse proxy (direct Flask access only)
- ❌ Cannot test full production routing setup

**Access:**

- Milkcrate: `http://localhost:5001` (direct access, bypasses Traefik)

**When to use:**

- Making code changes and need immediate feedback
- Debugging issues with detailed error messages
- Quick testing without Docker overhead
- Development workflow

## Production Mode (`milkcrate up`)

**Use for**: Testing production setup, verifying Traefik routing, and preparing for deployment.

```bash
# Start Docker Compose stack
uv run milkcrate up
```

**Characteristics:**

- ✅ Full containerized stack (Traefik + Milkcrate)
- ✅ Production-like environment matching real deployment
- ✅ Traefik reverse proxy with full routing capabilities
- ✅ Container security policies and resource limits applied
- ❌ Slower startup (container initialization)
- ❌ No debug mode or auto-reload

**Access:**

- Milkcrate via Traefik: `http://localhost` (routed through Traefik on port 80)
- Milkcrate direct: `http://localhost:5001` (bypasses Traefik)
- Traefik dashboard: `http://localhost:8080` (filter traffic in production)

**When to use:**

- Testing the complete production setup
- Verifying Traefik routing and load balancing
- Testing deployed applications through Traefik
- Preparing for production deployment
- Validating container deployments

## Quick Comparison

| Feature | `milkcrate run` | `milkcrate up` |
|---------|----------------|----------------|
| **Access URL** | `http://localhost:5001` | `http://localhost` (via Traefik) |
| **Traefik** | ❌ No | ✅ Yes |
| **Containerized** | ❌ No | ✅ Yes |
| **Debug Mode** | ✅ Yes | ❌ No |
| **Auto-reload** | ✅ Yes | ❌ No |
| **Production-like** | ❌ No | ✅ Yes |
| **Startup Speed** | ⚡ Fast | 🐢 Slower |
| **Best For** | Development | Production testing |

## Related Documentation

- [Blueprints & Routes](blueprints.md) - Route definitions
- [Database](database.md) - Schema and helpers
- [CLI Reference](../reference/cli.md) - Command-line tools
- [Routing](../user-guide/routing.md) - How Traefik routing works
