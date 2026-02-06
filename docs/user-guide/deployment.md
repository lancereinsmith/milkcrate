# Deployment

This section covers running milkcrate itself and deploying apps to it.

## Installation

For production deployment on Ubuntu servers, use the [automated installation script.](../getting-started/ubuntu-installation.md)

**Important**: Change the default admin password and update the SECRET_KEY in `/opt/milkcrate/.env` for production use.

### Service Management

```bash
# Control the service
sudo systemctl start|stop|restart|status milkcrate

# View logs
sudo journalctl -u milkcrate -f

# View container logs
sudo docker logs -f milkcrate
sudo docker logs -f traefik
```

## Post-Installation

After installation, milkcrate will be available at:

- Main interface: `http://localhost/admin` (or `http://your-domain/admin`)
- Traefik dashboard: `http://localhost:8080`

## Deploying indivudual apps

- Continue to [Dockerfile Apps](dockerfile-apps.md) for single-container applications
- Continue to [Docker Compose Apps](docker-compose-apps.md) for multi-container applications
