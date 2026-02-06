# Security

## Authentication

- **Password-only** login (no username). Stored passwords hashed with werkzeug.
- **MILKCRATE_ADMIN_PASSWORD** env var overrides stored password.
- Default password is `admin` — change it in production.
- Admin routes protected with flask-login; CSRF on all forms.

## Containers

- **Limits**: 512MB RAM, 50% CPU, 100 PIDs. Dropped capabilities; NET_BIND_SERVICE only.
- Non-root user (`nobody:nogroup`), secure tmp, log rotation.
- Single Docker network; apps reachable only via Traefik (no direct port exposure).

## Rate Limiting

- App upload: 10/hour. Volume create: 20/hour. Volume upload: 30/hour. App update: 5/hour.
- Default: 1000/hour, 100/minute per IP.

## Traefik Dashboard

- The Traefik dashboard (port 8080) is **bound to localhost only** (`127.0.0.1:8080:8080`) so it is not reachable from the network.
- Access it on the server at `http://localhost:8080`, or from your machine via SSH tunnel: `ssh -L 8080:localhost:8080 user@server`.
- In `traefik.yml`, `api.insecure: true` exposes the dashboard on that entrypoint without auth; binding to 127.0.0.1 is the primary protection. For production, set `insecure: false` if you do not need the dashboard, or put it behind a router with BasicAuth (see [Traefik — Advanced](traefik-advanced.md)).

## HTTPS & Headers

- **Headers**: CSP, X-Frame-Options, HSTS, X-Content-Type-Options, Referrer-Policy.
- **SSL**: Configure `SSL_CERT_FILE` and `SSL_KEY_FILE`; use `FORCE_HTTPS=true` to force redirects.
- **Domain-level SSL**: Certificates are per domain, not per app route. Traefik terminates TLS; traffic to app containers is HTTP on localhost.

## Audit & Logging

- Admin actions logged (action, resource, success/failure, IP, user agent) to `instance/audit.log`.

## Production Checklist

1. Change default admin password; set **SECRET_KEY** and **MILKCRATE_ADMIN_PASSWORD** via env.
2. Use HTTPS (Traefik + Let's Encrypt or your certs); restrict hostnames in production.
3. Restrict admin access (firewall, VPN, or auth proxy).
4. Back up database and instance data regularly; monitor audit logs.

## Security-Related Config

| Variable | Purpose |
|---------|---------|
| `MILKCRATE_ADMIN_PASSWORD` | Override admin password |
| `SECRET_KEY` | Flask session signing |
| `SSL_CERT_FILE` / `SSL_KEY_FILE` | HTTPS certificates |
| `FORCE_HTTPS` | Force HTTP→HTTPS redirect |

See [Configuration](../reference/configuration.md) for full options.
