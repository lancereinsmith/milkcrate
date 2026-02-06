# Troubleshooting

## Service Won't Start

```bash
# Check service status
sudo systemctl status milkcrate

# Check logs for detailed error information
sudo journalctl -u milkcrate -f

# Check Docker containers
sudo docker ps -a

# Check if uv environment is working
sudo -u milkcrate uv run python --version
```

**Common causes**:

- Database initialization failure
- Port conflicts (80, 5001, 8080)
- Docker not running
- Insufficient permissions

## Permission Issues

```bash
# Fix ownership
sudo chown -R milkcrate:milkcrate /opt/milkcrate

# Fix permissions
sudo chmod 600 /opt/milkcrate/acme.json
sudo chmod 600 /opt/milkcrate/.env
```

## Docker Issues

```bash
# Restart Docker
sudo systemctl restart docker

# Check Docker status
sudo systemctl status docker

# Test Docker
sudo docker run hello-world

# Check if user is in docker group
groups milkcrate
```

## Port Conflicts

Common port conflicts on Ubuntu:

- **Port 80**: Apache, nginx, or other web servers (disable before installation)
- **Port 5001**: Other applications
- **Port 8080**: Other services

```bash
# Check what's using a port
sudo lsof -i :80
sudo lsof -i :5001
sudo lsof -i :8080

# Stop conflicting services before running milkcrate
sudo systemctl stop apache2
sudo systemctl stop nginx
```

**Note**: milkcrate uses Traefik on port 80 for all routing. Do not install nginx unless you specifically need it as an additional front proxy.

## Nginx Configuration (Advanced)

**Note**: milkcrate does not use nginx by default. Traefik handles all routing on port 80. Only add nginx if you have specific requirements for an additional front proxy layer.

If you manually add nginx and encounter "400 Bad Request - Request Header Or Cookie Too Large":

1. **Avoid port conflicts**: Change Traefik's port in `docker-compose.yml` from `"80:80"` to `"8081:80"`
2. **Configure nginx** to proxy to port 8081
3. **Add buffer size settings** to nginx configuration (see `_server/milkcrate.conf` for example)

## Python and uv Issues

```bash
# Check uv installation
uv --version

# Reinstall dependencies if corrupted
cd /opt/milkcrate
sudo -u milkcrate uv sync --reinstall
```

## Database Issues

```bash
# Check database file
ls -la /opt/milkcrate/instance/

# Reinitialize database (destructive)
cd /opt/milkcrate
sudo -u milkcrate uv run python3 -c "
from milkcrate_core import create_app
app = create_app()
app.app_context().push()
from database import init_db
init_db()
"
```

## Container won't start

```bash
# Check container logs
docker logs <container_id>

# Verify Dockerfile
docker build -t test .

# Check port conflicts
lsof -i :8000
```

## Traefik routing issues

```bash
# Check Traefik version & config
docker exec traefik traefik version

# Inspect labels on the container
docker inspect <container_id> | grep -A 10 Labels

# Traefik logs
docker-compose logs traefik
```

## Port configuration

- milkcrate: 5001
- Apps: default 8000 if exposed, otherwise resolved from image metadata

## App update issues

```bash
# Check update status
docker ps -a | grep <app_name>

# If update fails, check build logs
docker images | grep milkcrate-<app_name>

# Manual cleanup if needed
docker stop <container_id>
docker rm <container_id>
docker rmi <image_tag>
```

## Common UI messages

- **"Route is reserved"**: Choose a route not starting with `/traefik`, `/admin`, `/login`, `/logout`, `/upload`, `/settings`.
- **"Route already in use"**: Another app has this `public_route`; pick a unique one.
- **"Invalid ZIP file"**: Ensure the archive contains `Dockerfile` OR `docker-compose.yml`.
- **"Failed to update app"**: Check that the new ZIP has valid structure and Docker can build the image.
- **"Application not found"**: The app ID may have been deleted; refresh the page.
- **"Container failed to start"**: Check Docker logs and ensure your application starts correctly.
- **"Health check failed"**: Ensure your app responds to `/health`, `/status`, or `/` endpoints.
- **"Rate limit exceeded"**: Wait before retrying; limits are 10 uploads/hour, 5 admin actions/hour.
- **"Permission denied"**: Check file permissions and Docker socket access.
- **"Out of disk space"**: Clean up old containers and images with `milkcrate clean-all`.

## Docker Compose specific issues

### "No main service found"

- Ensure one service in your `docker-compose.yml` has `milkcrate.main_service=true` label
- Check that the label is properly formatted

### "Service refers to undefined network"

- milkcrate automatically adds the Traefik network
- Don't manually define external networks in your compose file

### "docker-compose deployment failed"

- Check that your compose file is valid: `docker-compose config`
- Verify all services have proper build contexts or image references
- Ensure the main service exposes a port

### Health check failures

- Ensure your main service responds to health endpoints (`/health`, `/status`, etc.)
- Check that the exposed port matches your application's listening port
- Verify the application starts successfully within the container

### Debugging Docker Compose apps

```bash
# Check compose stack logs
docker compose -p milkcrate-<app_name> logs

# Check specific service logs
docker compose -p milkcrate-<app_name> logs <service_name>

# Validate compose file
docker-compose config
```

## Performance Issues

### High Memory Usage

```bash
# Check container memory usage
docker stats

# Check system memory
free -h

# Clean up old containers and images
milkcrate clean-all
```

### Slow Application Startup

```bash
# Check container logs for startup time
docker logs <container_id>

# Verify health check endpoints respond quickly
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/my-app/health

# Check if container has sufficient resources
docker inspect <container_id> | grep -A 5 "Memory\|Cpu"
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Clean up Docker system
docker system prune -a

# Check upload and extracted directories
du -sh uploads/ extracted_apps/

# Clean milkcrate data
milkcrate clean-all
```

## Monitoring and Logs

### Application Logs

```bash
# View all application logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f milkcrate
docker-compose logs -f traefik

# View deployed app logs
docker logs <container_id>
```

### System Monitoring

```bash
# Check service status
systemctl status milkcrate

# Monitor resource usage
htop
iotop

# Check network connectivity
netstat -tlnp | grep -E ':(80|5001|8080)'
```

### Health Checks

```bash
# Test milkcrate health
curl -f http://localhost:5001/

# Test Traefik health
curl -f http://localhost:8080/ping

# Test deployed app health
curl -f http://localhost/my-app/health
```
