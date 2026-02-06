# Traefik — Advanced Configuration

This page covers optional and advanced Traefik configuration for milkcrate. For essentials, see [Traefik Configuration](traefik.md).

## Content-Type Handling

Traefik v3 does not auto-detect `Content-Type` headers. Ensure your apps set appropriate `Content-Type` headers in responses. If you need Traefik to set `Content-Type` when the backend omits it, use the ContentType middleware.

**Where to add it:** Add these as **Docker labels** on the container whose responses need auto-detection (e.g. the milkcrate service in `docker-compose.yml`, or the specific app container). You need two kinds of labels:

- **Define the middleware** (one label per middleware)

```yaml
labels:
  - "traefik.http.middlewares.autodetect.contenttype=true"
```

- **Attach it to the router** by adding the middleware name to that router's `middlewares` list. Use a comma to chain with existing middlewares (order can matter). Example for the milkcrate fallback router in `docker-compose.yml`

```yaml
# Before (existing):
- "traefik.http.routers.milkcrate-fallback.rule=PathPrefix(`/`)"
# Add or update the middlewares line to include autodetect:
- "traefik.http.routers.milkcrate-fallback.middlewares=autodetect"
```

For **deployed apps**, milkcrate generates Traefik labels in code (see `services/deploy.py`). To enable ContentType for those apps you would need to extend the generated labels to define this middleware and add it to each app's router (e.g. chain `autodetect` with the existing `stripprefix` middleware).

## Container Labels Reference

### Deployed App Containers

milkcrate **automatically generates** the appropriate Traefik labels based on the `ENABLE_HTTPS` environment variable.

**Development (HTTP-only, default):**

When `ENABLE_HTTPS=false` or unset:

- `traefik.enable=true`
- `traefik.http.routers.<name>.rule=PathPrefix(`<route>`)`
- `traefik.http.routers.<name>.entrypoints=web`
- `traefik.http.routers.<name>.priority=<calculated>`
- `traefik.http.services.<name>.loadbalancer.server.port=<internal_port>`
- `traefik.http.middlewares.<name>_stripprefix.stripprefix.prefixes=<route>`
- `traefik.http.routers.<name>.middlewares=<name>_stripprefix`

**Production (HTTPS enabled):**

When `ENABLE_HTTPS=true`:

- `traefik.enable=true`
- `traefik.http.routers.<name>.rule=PathPrefix(`<route>`)`
- `traefik.http.routers.<name>.entrypoints=websecure` ← HTTPS port 443
- `traefik.http.routers.<name>.tls.certresolver=letsencrypt` ← Auto SSL
- `traefik.http.routers.<name>.priority=<calculated>`
- `traefik.http.services.<name>.loadbalancer.server.port=<internal_port>`
- `traefik.http.middlewares.<name>_stripprefix.stripprefix.prefixes=<route>`
- `traefik.http.routers.<name>.middlewares=<name>_stripprefix`

**Host Restrictions (Optional):**

To restrict apps to specific domains, manually edit container labels to add:

- Change rule to: `Host(`yourdomain.com`) && PathPrefix(`<route>`)`
- Use when: Hosting multiple domains or requiring domain-specific routing

### MilkCrate Service

- High-priority router for `/admin`, `/login`, `/logout`, `/upload`, `/static`
- Fallback router to catch `/` and other unmatched paths
- In production: Uses `websecure` entrypoint with Let's Encrypt certificates

## SSL Certificate Management

### Let's Encrypt (Production)

1. **Automatic Certificate Generation**: Traefik automatically requests and renews certificates
2. **ACME Challenge**: Uses HTTP-01 challenge for domain validation
3. **Certificate Storage**: Certificates stored in `acme.json` file
4. **Auto-Renewal**: Certificates automatically renewed before expiration

### Self-Signed Certificates (Development)

- MilkCrate can generate self-signed certificates for local development
- Configured via `SSL_CERT_FILE` and `SSL_KEY_FILE` environment variables
- Only for testing HTTPS functionality locally
