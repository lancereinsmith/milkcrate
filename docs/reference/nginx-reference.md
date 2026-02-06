# Nginx Reference

Quick reference for nginx-related operations in milkcrate.

## TL;DR

- **Don't need nginx?** Stick with the default Traefik-only setup (recommended)
- **Need other websites?** Run `sudo ./install_nginx.sh`
- **Changed your mind?** Run `sudo bash remove_nginx.sh`

## Scripts

### install_nginx.sh

**Purpose**: Add nginx as a front proxy to an existing milkcrate installation.

**Usage**:

```bash
cd /opt/milkcrate
sudo ./install_nginx.sh
```

**What it does**:

1. Checks prerequisites
2. Backs up configuration
3. Moves Traefik from port 80 to 8081
4. Installs nginx on port 80
5. Configures nginx to proxy to Traefik
6. Restarts services

**When to use**: You want to run other websites (WordPress, etc.) on the same server as milkcrate.

**Requirements**: Existing milkcrate installation at `/opt/milkcrate`

### remove_nginx.sh

**Purpose**: Remove nginx and restore Traefik-only configuration.

**Usage**:

```bash
cd /opt/milkcrate
sudo bash remove_nginx.sh
```

**What it does**:

1. Backs up configuration
2. Stops nginx
3. Moves Traefik back to port 80
4. Disables nginx milkcrate site
5. Restarts milkcrate

**When to use**: You no longer need multiple websites or want to simplify your setup.

## Configuration Files

### /etc/nginx/sites-available/milkcrate

Main nginx configuration file created by `install_nginx.sh`.

**Key sections**:

```nginx
# Main server block - proxies to Traefik
server {
    listen 80;
    server_name _;  # Accept any hostname

    location / {
        proxy_pass http://127.0.0.1:8081;  # Traefik port
        # ... proxy headers
    }
}
```

**To add another website**:

```nginx
server {
    listen 80;
    server_name blog.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;  # Your site's port
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**After editing**:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### /opt/milkcrate/docker-compose.yml

**Without nginx** (default):

```yaml
ports:
  - "80:80"      # Traefik on port 80
  - "8080:8080"  # Dashboard
```

**With nginx**:

```yaml
ports:
  - "8081:80"    # Traefik on port 8081 (nginx proxies to this)
  - "8080:8080"  # Dashboard
```

## Port Configuration

### Default Setup (Traefik Only)

| Service | Port | Purpose |
|---------|------|---------|
| Traefik | 80 | All HTTP traffic |
| Traefik Dashboard | 8080 | Monitoring |
| milkcrate Direct | 5001 | Direct access (bypasses Traefik) |

**Access**:

- Admin: `http://your-domain/admin`
- Apps: `http://your-domain/app-route`

### With nginx

| Service | Port | Purpose |
|---------|------|---------|
| nginx | 80 | Front proxy (receives all traffic) |
| Traefik | 8081 | milkcrate apps (nginx proxies to this) |
| Traefik Dashboard | 8080 | Monitoring |
| milkcrate Direct | 5001 | Direct access (bypasses all proxies) |

**Access**:

- Admin: `http://your-domain/admin` (nginx → Traefik → milkcrate)
- Apps: `http://your-domain/app-route` (nginx → Traefik → app)
- Other sites: `http://other-domain/` (nginx → other port)

## Common Operations

### Check Current Setup

```bash
# Check if nginx is installed and running
systemctl status nginx

# Check what's on port 80
sudo lsof -i :80

# Check what's on port 8081
sudo lsof -i :8081

# Check Traefik port in docker-compose.yml
grep '".*:80"' /opt/milkcrate/docker-compose.yml
```

### Add nginx During Fresh Install

When running `install_ubuntu.sh`, you'll see:

```text
OPTIONAL: Nginx Front Proxy (Advanced)
Do you want to install nginx as a front proxy? [y/N]
```

Answer 'y' only if you need multiple websites.

### Test nginx Configuration

```bash
# Test configuration syntax
sudo nginx -t

# View nginx error log
sudo tail -f /var/log/nginx/error.log

# View nginx access log
sudo tail -f /var/log/nginx/access.log
```

### Reload nginx After Changes

```bash
# Test first
sudo nginx -t

# If test passes, reload
sudo systemctl reload nginx

# Or restart if needed
sudo systemctl restart nginx
```

### Troubleshooting

**502 Bad Gateway from nginx**:

```bash
# Check if Traefik is running on 8081
sudo docker ps | grep traefik
sudo lsof -i :8081

# Check Traefik logs
sudo docker logs traefik
```

**Port conflict**:

```bash
# Check what's using port 80
sudo lsof -i :80

# If nginx and Traefik conflict, check docker-compose.yml
# Should be "8081:80" with nginx, or "80:80" without
```

**nginx won't start**:

```bash
# Check nginx error log
sudo tail -50 /var/log/nginx/error.log

# Test configuration
sudo nginx -t

# Check if port 80 is already in use
sudo lsof -i :80
```

## SSL/HTTPS with nginx

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Get Certificate

```bash
# For milkcrate domain
sudo certbot --nginx -d yourdomain.com

# For additional websites
sudo certbot --nginx -d blog.yourdomain.com
```

Certbot automatically:

- Gets SSL certificate from Let's Encrypt
- Updates nginx configuration
- Sets up auto-renewal

### Manual SSL Configuration

If you have your own certificates:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    # ... rest of configuration
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;  # Redirect to HTTPS
}
```

## Decision Tree

```text
Do you need to run OTHER websites (non-milkcrate apps) on this server?
│
├─ No → Use default Traefik-only setup (recommended)
│       (Simpler, easier to maintain)
│
└─ Yes → Do you need it right now?
         │
         ├─ No → Install default, add nginx later with install_nginx.sh (recommended)
         │       (You can always add it when needed)
         │
         └─ Yes → Add nginx during installation or run install_nginx.sh
                  (More complex, requires understanding both proxies)
```

## Further Reading

- [Multi-Website Setup Guide](../production/multi-website-setup.md) - Comprehensive guide
- [Traefik Configuration](../production/traefik.md) - Traefik-specific docs
- [Ubuntu Installation](../getting-started/ubuntu-installation.md) - Installation guide
