# Multi-Website Server Setup

This guide explains how to run multiple websites on the same server alongside milkcrate using nginx as a front proxy.

!!! warning "For Advanced Users Only"
    This setup is **NOT recommended** for most users. The default Traefik-only configuration is simpler, easier to maintain, and works fine for dedicated milkcrate servers. Only use this setup if you need to run OTHER websites (non-milkcrate apps) on the same server.

## Quick Start

### Option 1: Add During Installation

When running `install_ubuntu.sh`, you'll be prompted to optionally add nginx. Unless you know you need it, choose "No".

### Option 2: Add to Existing Installation

Use the provided script:

```bash
cd /opt/milkcrate
sudo ./install_nginx.sh
```

Briefly, this script will:

- Install nginx on port 80
- Move Traefik to port 8081
- Configure nginx to proxy to Traefik
- Restart all services

### Option 3: Remove nginx Later

To revert to Traefik-only:

```bash
cd /opt/milkcrate
sudo bash remove_nginx.sh
```

## Architecture Overview

By default, milkcrate uses Traefik on port 80 for all routing. To run multiple websites, you need nginx as a front proxy:

```text
Internet (Port 80/443)
         ↓
    Nginx (Front Proxy)
         ├─→ Port 8081 → Traefik → milkcrate + deployed apps
         ├─→ Port 3000 → WordPress blog
         ├─→ Port 4000 → E-commerce site
         └─→ Port 5000 → Another application
```

## Why Use Nginx with Traefik?

### Traefik Only (Default - Simpler)

- ✅ Simple setup
- ✅ Automatic routing for milkcrate apps
- ✅ Traefik handles HTTPS/SSL
- ❌ Cannot easily run other websites on port 80
- **Use when**: Server is dedicated to milkcrate

### Nginx + Traefik (Multi-Website)

- ✅ Run multiple websites on same server
- ✅ Each website can use different domains
- ✅ Nginx handles HTTPS/SSL for all sites
- ✅ Centralized access logging
- ❌ More complex setup
- **Use when**: You need other websites alongside milkcrate

## Setup Instructions

### Automated Setup (Recommended)

Use the provided script for safe, automated setup:

```bash
cd /opt/milkcrate
sudo ./install_nginx.sh
```

The script will:

1. Check prerequisites
2. Backup current configuration
3. Stop services
4. Modify docker-compose.yml (Step 1 below)
5. Install and configure nginx (Step 2 below)
6. Test configuration (Step 2 below)
7. Start services (Step 3 below)
8. Verify setup (Step 4 below)

**If the script fails at any step**, it will show an error and stop. You can then manually fix the issue or restore from the backup.

### Manual Setup (Advanced)

If you prefer manual setup or need to customize:

#### Step 1: Modify Traefik Port

Edit `/opt/milkcrate/docker-compose.yml`:

```bash
sudo nano /opt/milkcrate/docker-compose.yml
```

Change Traefik's port mapping from:

```yaml
ports:
  - "80:80"
  - "8080:8080"
```

To:

```yaml
ports:
  - "8081:80"  # Change host port to 8081
  - "8080:8080"
```

#### Step 2: Install and Configure Nginx

```bash
# Install nginx
sudo apt install -y nginx

# Copy the example configuration
sudo cp /opt/milkcrate/_server/milkcrate.conf /etc/nginx/sites-available/milkcrate

# Edit to match your domain
sudo nano /etc/nginx/sites-available/milkcrate
# Change 'yourdomain.com' to your actual domain

# Enable the site
sudo ln -sf /etc/nginx/sites-available/milkcrate /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# If test passes, enable and start nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

#### Step 3: Restart milkcrate

```bash
sudo systemctl restart milkcrate
```

#### Step 4: Verify Setup

```bash
# Check that Traefik is on port 8081
sudo lsof -i :8081

# Check that nginx is on port 80
sudo lsof -i :80

# Test access
curl http://localhost/admin

# Check from your browser
# http://your-domain/admin
```

## Adding Additional Websites

Edit nginx configuration to add more websites:

```bash
sudo nano /etc/nginx/sites-available/milkcrate
```

Add a new server block:

```nginx
server {
    listen 80;
    server_name blog.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;  # Your website's port
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then reload nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## HTTPS/SSL Setup

Nginx can handle SSL for all websites using Let's Encrypt:

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Get SSL Certificates

```bash
# For milkcrate domain
sudo certbot --nginx -d yourdomain.com

# For additional websites
sudo certbot --nginx -d blog.yourdomain.com
sudo certbot --nginx -d shop.yourdomain.com
```

Certbot will automatically:

- Get SSL certificates
- Update nginx configuration
- Set up auto-renewal

### SSL Configuration Example

After running certbot, your nginx config will look like:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Increase buffer sizes
    client_header_buffer_size 8k;
    large_client_header_buffers 8 32k;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;  # Redirect to HTTPS
}
```

## Traefik HTTPS vs Nginx HTTPS

You have two options for HTTPS:

### Option A: Nginx Handles SSL (Recommended for Multi-Website)

```text
Internet → Nginx (SSL) → Traefik (HTTP) → Apps
```

- Centralized SSL management
- One certificate per domain
- Easier to manage multiple websites

!!! warning "milkcrate / Traefik HTTPS"
    Leave HTTPS **off** in milkcrate. Nginx terminates SSL; Traefik only receives HTTP on port 8081.

    - Keep `ENABLE_HTTPS` **unset or `false`** in milkcrate's environment (e.g. in `docker-compose.yml` or your env file).
    - Do **not** uncomment the HTTPS sections in `traefik.yml` or the HTTPS router labels in `docker-compose.yml`.

Traefik will use the `web` (HTTP) entrypoint and existing HTTP router labels. SSL is handled entirely by Nginx in front.

### Option B: Traefik Handles SSL

```text
Internet → Nginx (HTTP) → Traefik (SSL) → Apps
```

- More complex
- Requires HTTPS passthrough in nginx
- Not recommended for multi-website setups

## Firewall Configuration

Update UFW to allow only needed ports:

```bash
# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS through nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct access to Traefik (now on 8081)
# Don't add UFW rule for 8081

# Block direct access to milkcrate (port 5001)
# Don't add UFW rule for 5001

# Enable firewall
sudo ufw --force enable
```

## Monitoring and Logs

```bash
# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Traefik logs
sudo docker logs -f traefik

# milkcrate logs
sudo docker logs -f milkcrate
```

## Troubleshooting

### Port Conflict Errors

If you see "address already in use" errors:

```bash
# Check what's using port 80
sudo lsof -i :80

# Check what's using port 8081
sudo lsof -i :8081

# Make sure you changed docker-compose.yml
grep "8081:80" /opt/milkcrate/docker-compose.yml
```

### 502 Bad Gateway

If nginx shows 502 errors:

```bash
# Check if Traefik is running
sudo docker ps | grep traefik

# Check Traefik logs
sudo docker logs traefik

# Verify Traefik is on port 8081
sudo lsof -i :8081
```

### SSL Certificate Issues

```bash
# Test SSL renewal
sudo certbot renew --dry-run

# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal
```

## Example: Complete Multi-Website Setup

Here's a complete example with milkcrate + WordPress + static site:

### docker-compose.yml (Traefik on 8081)

```yaml
services:
  traefik:
    image: traefik:v3.6.7
    ports:
      - "8081:80"  # Changed from 80:80
      - "8080:8080"
    # ... rest of config
```

### /etc/nginx/sites-available/multi-site

```nginx
# milkcrate and deployed apps
server {
    listen 80;
    server_name apps.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# WordPress blog
server {
    listen 80;
    server_name blog.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Static marketing site
server {
    listen 80;
    server_name www.yourdomain.com yourdomain.com;

    root /var/www/marketing;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

## Removing nginx (Reverting to Traefik-Only)

If you decide you don't need nginx, you can easily revert:

### Using the Script (Recommended)

```bash
cd /opt/milkcrate
sudo bash remove_nginx.sh
```

### Manual Removal

```bash
# Stop services
sudo systemctl stop milkcrate
sudo systemctl stop nginx

# Edit docker-compose.yml to change "8081:80" back to "80:80"
sudo nano /opt/milkcrate/docker-compose.yml

# Disable nginx site
sudo rm -f /etc/nginx/sites-enabled/milkcrate

# Disable nginx (if you don't have other sites)
sudo systemctl disable nginx

# Restart milkcrate
sudo systemctl start milkcrate
```

!!! tip "Recommendation"
    For most users, the default Traefik-only setup is sufficient. Only add nginx if you need to run other websites on the same server. You can always add it later using `install_nginx.sh`.
