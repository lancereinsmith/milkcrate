# Traefik Configuration

milkcrate integrates with Traefik for path-based routing and SSL termination.

## SSL Architecture

**Important**: SSL certificates are handled at the **domain level**, not per individual app route. All deployed applications share the same SSL certificate for the domain.

### How SSL Works

1. **Traefik terminates SSL** using the domain's certificate (e.g., `yourdomain.com`)
2. **All routes** under that domain (`/my-app`, `/another-app`) automatically get HTTPS
3. **Internal communication** between Traefik and app containers is unencrypted
4. **Apps receive requests** at `http://localhost:port/` (Traefik strips the route prefix)

## Traefik service (Compose)

The default `docker-compose.yml` includes Traefik configured for both HTTP (development) and HTTPS (production). Port 443 is exposed but only used when HTTPS is enabled.

### Default Configuration (HTTP-Only)

```yaml
services:
  traefik:
    image: traefik:v3.6.7
    ports:
      - "80:80"      # HTTP
      - "443:443"    # HTTPS (dormant until enabled)
      - "127.0.0.1:8080:8080"  # dashboard (localhost only; see Security)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./acme.json:/acme.json
    networks:
      - milkcrate-traefik
```

### Production HTTPS Configuration

To enable HTTPS in production:

1. Set `ENABLE_HTTPS=true` in environment
2. Update `traefik.yml` to uncomment HTTPS sections
3. Add HTTPS router labels to milkcrate service

See the [HTTPS Setup Guide](https-setup.md) for complete instructions.

## Traefik Configuration

The default `traefik.yml` is configured for HTTP-only (development mode) with HTTPS sections commented out.

### Default Configuration

The repository includes `traefik.yml` pre-configured for development with production sections commented:

```yaml
api:
  dashboard: true
  insecure: true  # Set to false in production

entryPoints:
  web:
    address: ":80"
    # Uncomment for production HTTPS - redirects HTTP to HTTPS
    # http:
    #   redirections:
    #     entrypoint:
    #       to: websecure
    #       scheme: https
  websecure:
    address: ":443"
    # Uncomment for production HTTPS
    # http:
    #   tls:
    #     certResolver: letsencrypt
  traefik:
    address: ":8080"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: milkcrate-traefik

# Uncomment for production HTTPS with Let's Encrypt
# certificatesResolvers:
#   letsencrypt:
#     acme:
#       email: your-email@example.com  # CHANGE THIS
#       storage: /acme.json
#       httpChallenge:
#         entryPoint: web

log:
  level: INFO

accessLog: {}
```

### Enabling Production HTTPS

To enable HTTPS, uncomment the production sections in `traefik.yml`. See the [HTTPS Setup Guide](https-setup.md) for detailed instructions and complete configuration examples.

## Version Compatibility

milkcrate uses **Traefik v3** syntax for all routing rules.

### Key V3 Features Used

- **PathPrefix** - Simple path matching without regex
- **Host** - Domain matching (HostHeader removed in v3)
- **Priority-based routing** - Ensures correct route matching order

Traefik v3 does not auto-detect `Content-Type` headers; ensure your apps set appropriate `Content-Type` in responses. For optional ContentType middleware and other advanced options, see [Traefik — Advanced Configuration](traefik-advanced.md).

## Dashboard Access

The dashboard is bound to `127.0.0.1:8080` so it is not reachable from the network. Use `http://localhost:8080` on the server or an SSH tunnel from your machine. See [Security](security.md#traefik-dashboard) for details.

## Container Labels Overview

- **Deployed app containers**: milkcrate generates Traefik labels automatically (routers, stripprefix middleware, HTTP or HTTPS entrypoints based on `ENABLE_HTTPS`).
- **MilkCrate service**: High-priority routes for `/admin`, `/login`, `/upload`, `/static`, etc., and a fallback route for `/`. In production it uses the `websecure` entrypoint with Let's Encrypt.

For the full label reference, host restrictions, and SSL certificate details, see [Traefik — Advanced Configuration](traefik-advanced.md).

## Production Deployment Checklist

For a complete production HTTPS deployment:

1. **DNS**: Point your domain to your server's IP address
2. **Firewall**: Open ports 80 and 443
3. **Email**: Set `LETSENCRYPT_EMAIL` environment variable
4. **Enable HTTPS**: Set `ENABLE_HTTPS=true` in docker-compose.yml
5. **Update traefik.yml**: Uncomment production HTTPS sections
6. **Update Labels**: Uncomment HTTPS router labels in docker-compose.yml
7. **Permissions**: Ensure `acme.json` has 600 permissions
8. **Restart**: Run `docker-compose down && docker-compose up -d`
9. **Test**: Verify HTTPS works and HTTP redirects properly

See the [HTTPS Setup Guide](https-setup.md) for detailed step-by-step instructions.
