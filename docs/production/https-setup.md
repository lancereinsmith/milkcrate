# HTTPS Setup Guide

This guide explains how to enable HTTPS with Let's Encrypt SSL certificates in production.

## Prerequisites

- A registered domain name pointing to your server's IP address
- Ports 80 and 443 open in your firewall
- Valid email address for Let's Encrypt notifications

## Configuration Steps

### 1. Update Traefik Configuration

Edit `traefik.yml` and uncomment the production HTTPS sections:

```yaml
api:
  dashboard: true
  insecure: false  # Set to false in production

entryPoints:
  web:
    address: ":80"
    # Uncomment these lines to redirect HTTP to HTTPS
    http:
      redirections:
        entrypoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"
    # Uncomment for production HTTPS
    http:
      tls:
        certResolver: letsencrypt
  traefik:
    address: ":8080"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: milkcrate-traefik

# Uncomment and configure for production
certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@example.com  # CHANGE THIS
      storage: /acme.json
      httpChallenge:
        entryPoint: web

log:
  level: INFO

accessLog: {}
```

### 2. Update Docker Compose Labels

Edit `docker-compose.yml` and uncomment the HTTPS router labels for the milkcrate service:

```yaml
labels:
  - "traefik.enable=true"
  # HTTP routes remain active (will redirect to HTTPS)
  - "traefik.http.routers.milkcrate-admin.rule=PathPrefix(`/admin`) || PathPrefix(`/login`) || PathPrefix(`/logout`) || PathPrefix(`/upload`) || PathPrefix(`/static`) || PathPrefix(`/favicon.ico`)"
  - "traefik.http.routers.milkcrate-admin.entrypoints=web"
  - "traefik.http.routers.milkcrate-admin.priority=30"
  - "traefik.http.routers.milkcrate-admin.service=milkcrate"
  - "traefik.http.routers.milkcrate-fallback.rule=PathPrefix(`/`)"
  - "traefik.http.routers.milkcrate-fallback.entrypoints=web"
  - "traefik.http.routers.milkcrate-fallback.priority=1"
  - "traefik.http.routers.milkcrate-fallback.service=milkcrate"
  # HTTPS routes - Uncomment these
  - "traefik.http.routers.milkcrate-admin-secure.rule=PathPrefix(`/admin`) || PathPrefix(`/login`) || PathPrefix(`/logout`) || PathPrefix(`/upload`) || PathPrefix(`/static`) || PathPrefix(`/favicon.ico`)"
  - "traefik.http.routers.milkcrate-admin-secure.entrypoints=websecure"
  - "traefik.http.routers.milkcrate-admin-secure.priority=30"
  - "traefik.http.routers.milkcrate-admin-secure.tls.certresolver=letsencrypt"
  - "traefik.http.routers.milkcrate-admin-secure.service=milkcrate"
  - "traefik.http.routers.milkcrate-fallback-secure.rule=PathPrefix(`/`)"
  - "traefik.http.routers.milkcrate-fallback-secure.entrypoints=websecure"
  - "traefik.http.routers.milkcrate-fallback-secure.priority=1"
  - "traefik.http.routers.milkcrate-fallback-secure.tls.certresolver=letsencrypt"
  - "traefik.http.routers.milkcrate-fallback-secure.service=milkcrate"
  - "traefik.http.services.milkcrate.loadbalancer.server.port=5001"
```

### 3. Enable HTTPS in Environment

Edit `docker-compose.yml` and uncomment/set these environment variables:

```yaml
environment:
  - MILKCRATE_ENV=production
  - ENABLE_HTTPS=true  # Enable HTTPS mode
  - LETSENCRYPT_EMAIL=your-email@example.com  # Your email
```

### 4. Prepare acme.json File

The `acme.json` file stores Let's Encrypt certificates and must have restricted permissions:

```bash
touch acme.json
chmod 600 acme.json
```

**Note**: This file is already in `.gitignore` and should never be committed to version control.

### 5. Restart Services

After making all configuration changes:

```bash
docker-compose down
docker-compose up -d
```

## How It Works

### Certificate Acquisition

1. When you deploy an app, milkcrate automatically adds HTTPS labels if `ENABLE_HTTPS=true`
2. Traefik detects the new container and routing rules
3. On first access, Traefik requests a certificate from Let's Encrypt via HTTP-01 challenge
4. The certificate is stored in `acme.json`
5. All subsequent requests use the cached certificate

### Certificate Renewal

- Let's Encrypt certificates expire after 90 days
- Traefik automatically renews certificates before expiration
- No manual intervention required

### HTTP to HTTPS Redirect

When properly configured, all HTTP traffic on port 80 is automatically redirected to HTTPS on port 443.

## Automatic HTTPS for Deployed Apps

Once HTTPS is enabled, **all newly deployed applications automatically get HTTPS**. The deployment code detects the `ENABLE_HTTPS` environment variable and generates appropriate labels:

- Router uses `websecure` entrypoint (port 443)
- TLS is configured with `certresolver=letsencrypt`
- Let's Encrypt automatically provisions certificates

**No additional configuration needed per app!**

## Verification

### Check Traefik Dashboard

Access the Traefik dashboard at `http://localhost:8080` on the server, or from your machine via `ssh -L 8080:localhost:8080 user@server` (dashboard is bound to localhost only). Then verify:

- Certificates are present in the "TLS" section
- Routers show both HTTP and HTTPS configurations

### Test HTTPS Access

1. Visit `http://your-domain.com` - should redirect to `https://`
2. Check for valid SSL certificate in browser
3. Verify deployed apps work at `https://your-domain.com/your-app`

### Monitor Certificate Status

```bash
# View certificate details in acme.json
docker-compose exec traefik cat /acme.json | jq
```

## Troubleshooting

### Certificate Acquisition Fails

**Symptoms**: Can't access site via HTTPS, certificate errors

**Solutions**:

1. Verify DNS points to your server: `nslookup your-domain.com`
2. Check ports 80 and 443 are open: `netstat -tuln | grep -E ':(80|443)'`
3. Ensure email is valid in `traefik.yml`
4. Check Traefik logs: `docker-compose logs traefik`

### HTTP Still Accessible (Not Redirecting)

**Symptoms**: Site accessible on both HTTP and HTTPS

**Solution**: Verify the HTTP to HTTPS redirect is uncommented in `traefik.yml`:

```yaml
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entrypoint:
          to: websecure
          scheme: https
```

### Deployed Apps Not Getting HTTPS

**Symptoms**: Milkcrate admin works on HTTPS, but deployed apps don't

**Solution**: Verify `ENABLE_HTTPS=true` is set in environment before deploying apps. Existing apps need to be redeployed to get HTTPS labels.

### Rate Limiting

Let's Encrypt has rate limits:

- 50 certificates per domain per week
- 5 duplicate certificates per week

**Solution**: For testing, use Let's Encrypt staging environment by modifying `traefik.yml`:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@example.com
      storage: /acme.json
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory  # Staging
      httpChallenge:
        entryPoint: web
```

## Security Best Practices

1. **Keep acme.json secure**: Never commit to version control, maintain 600 permissions
2. **Use strong SECRET_KEY**: Set a random secret key in production
3. **Dashboard access**: Dashboard is bound to 127.0.0.1:8080; use an SSH tunnel for remote access, or set `api.insecure: false` and expose it behind BasicAuth if needed
4. **Monitor certificate expiry**: Although auto-renewed, monitor for failures
5. **Regular backups**: Backup `acme.json` along with your database

## Development vs Production

| Feature | Development | Production |
|---------|-------------|------------|
| Port 80 (HTTP) | ✅ Active | ✅ Redirects to HTTPS |
| Port 443 (HTTPS) | ❌ Not used | ✅ Active with SSL |
| `ENABLE_HTTPS` | `false` | `true` |
| Let's Encrypt | ❌ Disabled | ✅ Enabled |
| Dashboard | Localhost only (`127.0.0.1:8080`) | Same; use SSH tunnel or BasicAuth if exposed |
| Deployed Apps | HTTP only | HTTPS with valid certs |

## Migrating from HTTP to HTTPS

If you have existing apps deployed in HTTP-only mode:

1. Follow all configuration steps above
2. Restart Traefik and milkcrate services
3. Redeploy existing applications (update them with their same code)
4. Old containers will be replaced with HTTPS-enabled versions
