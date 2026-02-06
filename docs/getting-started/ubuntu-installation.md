# Ubuntu Installation Guide

This guide provides detailed instructions for installing milkcrate on Ubuntu servers using the automated installation script.

## Prerequisites

- Ubuntu 20.04 or later (Ubuntu 25.04+ recommended)
- Root access (sudo)
- Internet connection
- Minimum 2GB RAM, 10GB disk space

## Quick Installation

1. Clone the repository:

   ```bash
   git clone <your-repo-url>
   cd milkcrate
   ```

2. Run the installation script:

   ```bash
   sudo ./install_ubuntu.sh
   ```

3. Follow the interactive prompts:
   - Enter your domain name (or press Enter for localhost)
   - Enter admin password (or press Enter for default "admin")
   - **Optional**: Add nginx front proxy (NOT recommended - can be added later)
   - Choose whether to configure UFW firewall

**Note**: The installer automatically detects and handles common issues like broken repository entries (e.g., deadsnakes PPA on Ubuntu 25.04).

## Installation Process

The script performs these steps automatically:

### System Setup

- Updates Ubuntu packages (automatically fixes broken repositories)
- Installs system dependencies (curl, wget, git, build tools, python3-dev)
- Uses system Python (3.13+ on Ubuntu 25.04, or installs Python 3.12+ on older versions)
- Installs Docker and Docker Compose
- Installs uv (modern Python package manager)

### Application Setup

- Creates a service user `milkcrate`
- Sets up application in `/opt/milkcrate`
- Installs Python dependencies using `uv sync` (creates virtual environment automatically)
- Initializes SQLite database
- Configures environment variables with secure defaults
- Sets up SSL certificate storage (acme.json)

### Service Configuration

- Installs systemd service (`_server/milkcrate.service`) for automatic startup
- Optionally configures UFW firewall
- Starts all services with Traefik handling routing on port 80

**Note**: The systemd service file is located in `_server/milkcrate.service` and is automatically copied to `/etc/systemd/system/` during installation. All HTTP routing is handled by Traefik - no additional reverse proxy is needed.

**Optional nginx**: During installation, you'll be prompted to optionally add nginx as a front proxy. This is only needed if you want to run OTHER websites (non-milkcrate apps) on the same server. For most users, the default Traefik-only setup is recommended. You can add nginx later using `sudo ./install_nginx.sh`.

## Post-Installation

### Access Points

After installation, milkcrate will be available at:

- **Main interface**: <http://localhost/admin> (or <http://your-domain/admin>)
- **Direct access** (bypasses Traefik): <http://localhost:5001>
- **Traefik dashboard**: <http://localhost:8080>

**Note**: All production traffic should go through port 80 (Traefik). Port 5001 is for direct access if needed.

### Default Credentials

- **Password**: `admin` (or what you specified during installation)

**Note**: Milkcrate uses password-only authentication (no username required).

### Security Configuration

**Critical first steps:**

1. **Change the admin password** via the web interface
2. **Update the SECRET_KEY** in `/opt/milkcrate/.env`:

   ```bash
   sudo nano /opt/milkcrate/.env
   # Change SECRET_KEY to a secure random value
   sudo systemctl restart milkcrate
   ```

3. **Configure your domain** in `/opt/milkcrate/docker-compose.yml` if using a custom domain
4. **Review firewall settings** for your environment

## Service Management

### Systemd Commands

Control the milkcrate service:

```bash
# Start the service
sudo systemctl start milkcrate

# Stop the service
sudo systemctl stop milkcrate

# Restart the service
sudo systemctl restart milkcrate

# Check service status
sudo systemctl status milkcrate

# Enable auto-start on boot (done by installer)
sudo systemctl enable milkcrate
```

### Viewing Logs

```bash
# View service logs
sudo journalctl -u milkcrate -f

# View container logs
sudo docker-compose -f /opt/milkcrate/docker-compose.yml logs -f

# View specific container logs
sudo docker logs milkcrate
sudo docker logs traefik
```

## Configuration

### Environment Variables

Edit `/opt/milkcrate/.env` to customize:

```bash
MILKCRATE_ENV=production
SECRET_KEY=your-secret-key-here
MILKCRATE_ADMIN_PASSWORD=your-admin-password
TRAEFIK_NETWORK=milkcrate-traefik
DEFAULT_HOME_ROUTE=/my-app  # Optional
MAX_CONTENT_LENGTH=16777216  # 16MB upload limit
```

After changing configuration:

```bash
sudo systemctl restart milkcrate
```

### Domain Configuration

**By default**, milkcrate accepts requests from ANY hostname (localhost, IP address, domain name). This makes it work out-of-the-box with:

- `http://localhost/admin`
- `http://your-ip/admin`
- `http://your-domain.com/admin`

**To restrict access to specific domains** (recommended for production), edit `/opt/milkcrate/docker-compose.yml`:

```bash
sudo nano /opt/milkcrate/docker-compose.yml
```

Find the Traefik router rules and add Host restrictions:

```yaml
# Change line 47 from:
- "traefik.http.routers.milkcrate-admin.rule=PathPrefix(`/admin`) || ..."

# To (restrict to specific domain):
- "traefik.http.routers.milkcrate-admin.rule=Host(`yourdomain.com`) && (PathPrefix(`/admin`) || ...)"

# Change line 52 from:
- "traefik.http.routers.milkcrate-fallback.rule=PathPrefix(`/`)"

# To (restrict to specific domain):
- "traefik.http.routers.milkcrate-fallback.rule=Host(`yourdomain.com`)"
```

Then restart:

```bash
sudo systemctl restart milkcrate
```

### Adding nginx for Multi-Website Hosting

If you need to run other websites alongside milkcrate (WordPress, static sites, etc.):

```bash
cd /opt/milkcrate
sudo ./install_nginx.sh
```

See the [Multi-Website Setup Guide](../production/multi-website-setup.md) for detailed instructions.

## File Structure

The installation creates this structure:

```text
/opt/milkcrate/
├── app.py                 # Main application
├── docker-compose.yml     # Container orchestration
├── .env                   # Environment configuration
├── acme.json             # SSL certificates (Traefik)
├── uploads/              # Uploaded applications
├── extracted_apps/       # Extracted application files
├── instance/             # SQLite database
├── logs/                 # Application logs
├── _server/              # Server configuration files
│   ├── milkcrate.service # Systemd service file (copied to /etc/systemd/system/)
│   └── milkcrate.conf    # Example nginx configuration (if manually adding nginx)
└── ...                   # Application source code
```

### Server Configuration Files

The `_server/` directory contains configuration files:

- **`milkcrate.service`**: Systemd service unit file that manages the Docker Compose stack. This file is copied to `/etc/systemd/system/milkcrate.service` during installation. It runs `docker compose up -d` on start and `docker compose down` on stop.

- **`milkcrate.conf`**: Example nginx configuration for reference only. Nginx is not used by default - Traefik handles all routing on port 80. This file is provided if you want to manually add nginx as an additional layer.

## Troubleshooting

For common issues and solutions, see the [Troubleshooting Guide](../support/troubleshooting.md#ubuntu-installation-issues).

### Common Installation Issues

**Repository errors (Ubuntu 25.04)**:

```bash
E: The repository 'https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu plucky Release' does not have a Release file.
```

- **Solution**: The installer automatically detects and fixes this. If you see this briefly, it's normal and will be resolved automatically.

**uv command not found**:

```bash
sudo: uv: command not found
```

- **Solution**: The installer now places `uv` in `/usr/local/bin/` for system-wide access. This is fixed in the latest version.

**Cannot access admin interface**:

If you can't access the admin interface at `http://your-domain/admin`:

1. Check that services are running: `sudo systemctl status milkcrate`
2. Check containers: `sudo docker ps`
3. Verify port 80 is accessible: `sudo lsof -i :80`
4. Try direct access: `http://your-domain:5001/admin`

### Quick Checks

```bash
# Check service status
sudo systemctl status milkcrate

# Check containers
sudo docker ps

# Check ports
sudo netstat -tlnp | grep -E ':(80|5001|8080)'

# Check logs for errors
sudo journalctl -u milkcrate --since "1 hour ago"
```

## Updates and Maintenance

### Updating milkcrate

```bash
cd /opt/milkcrate
sudo git pull origin main
sudo systemctl restart milkcrate
```

### Monitoring

```bash
# Check disk usage
df -h /opt/milkcrate

# Check memory usage
free -h

# Monitor container resource usage
sudo docker stats
```

## Uninstallation

To completely remove milkcrate:

```bash
# Stop and disable service
sudo systemctl stop milkcrate
sudo systemctl disable milkcrate

# Remove service file
sudo rm /etc/systemd/system/milkcrate.service
sudo systemctl daemon-reload

# Remove application directory
sudo rm -rf /opt/milkcrate

# Remove service user
sudo userdel milkcrate

# Optional: Remove Docker (if not needed)
# sudo apt remove docker-ce docker-ce-cli containerd.io
```

## Support

For additional help:

- Check the [main documentation](../index.md)
- Review the [troubleshooting guide](../support/troubleshooting.md)
- Check [GitHub issues](https://github.com/your-repo/milkcrate/issues)
- Verify system requirements and network connectivity
