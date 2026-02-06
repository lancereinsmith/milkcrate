# Docker Compose Applications

milkcrate supports deploying multi-container applications using Docker Compose. This allows you to deploy complex applications with databases, caches, message queues, and other supporting services.

## Overview

Docker Compose applications in milkcrate:

- Deploy entire application stacks with multiple services
- Automatically integrate with Traefik for routing
- Support health checks and status monitoring

## Creating a Docker Compose Application

### 1. Application Structure

Your application should have this structure:

```text
my-compose-app/
├── app.py                 # Your main application (not confined to Python)
├── requirements.txt       # Dependencies (not confined to Python)
├── Dockerfile            # Build instructions for main service
├── docker-compose.yml    # Multi-service configuration
└── README.md             # Documentation
```

### 2. Required docker-compose.yml Configuration

Your `docker-compose.yml` must include these essential elements:

```yaml
version: '3.8'
services:
  app:  # Main service (name can be anything)
    build: .  # Build from local Dockerfile
    ports:
      - "8000:8000"  # Expose the port your app runs on
    labels:
      - milkcrate.main_service=true  # REQUIRED: Mark as main service
    environment:
      - FLASK_ENV=production
      - FLASK_APP=app.py
```

### 3. Main Service Requirements

The service marked with `milkcrate.main_service=true` must:

- **Expose a port**: Use `ports` mapping (e.g., `"8000:8000"`)
- **Be accessible**: Respond to HTTP requests on the exposed port
- **Have a health endpoint**: Respond to health check requests

### 4. Complete Example

Here's a complete example with a web app and database:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - FLASK_APP=app.py
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
    labels:
      - milkcrate.main_service=true
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Health Check Endpoints

milkcrate automatically checks these endpoints to determine if your application is healthy:

1. `/health` - Primary health check endpoint
2. `/status` - Alternative status endpoint
3. `/api/health` - API health endpoint
4. `/api/status` - API status endpoint
5. `/` - Fallback to main page

### Health Check Response

Your application should respond with a 200 status code. For JSON endpoints, include status information:

```python
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })
```

## Advanced Configuration

### Environment Variables

Pass configuration through environment variables:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    labels:
      - milkcrate.main_service=true
```

### Volume Mounts

#### Docker Compose Volumes

Use volumes defined in your docker-compose.yml for persistent data:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - app_data:/app/data
    labels:
      - milkcrate.main_service=true

volumes:
  app_data:
```

#### Milkcrate-Managed Volumes

You can also mount volumes created through Milkcrate's volume management interface during deployment.

To use Milkcrate-managed volumes:

1. Create and populate volumes through the Milkcrate UI (Admin → Manage Volumes)
2. During deployment, select volumes to mount and specify paths
3. Volumes will be mounted to your main service container

See [Volume Management](volumes.md) for detailed instructions on creating and managing volumes.

### Service Dependencies

Define service startup order:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    labels:
      - milkcrate.main_service=true
```

## Deployment Process

1. **Package your application**:

   ```bash
   cd my-compose-app
   zip -r my-app.zip . -x "*.git*" "*.pyc" "__pycache__/*"

   # Or, run:
   milkcrate package --output my-app.zip
   ```

2. **Upload via milkcrate UI**:
    - Go to Admin Dashboard
    - Click "Deploy New App"
    - Upload your ZIP file
    - Set app name and public route

3. **milkcrate will**:
    - Extract the ZIP file
    - Detect it's a Docker Compose application
    - Add Traefik labels to the main service
    - Deploy the entire stack
    - Monitor health and status

## Network Integration

### Traefik Labels (Auto-generated)

milkcrate adds these labels to your main service:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.myapp.rule=PathPrefix(`/myapp`)
  - traefik.http.routers.myapp.entrypoints=web
  - traefik.http.services.myapp.loadbalancer.server.port=8000
  - traefik.http.middlewares.myapp_stripprefix.stripprefix.prefixes=/myapp
  - traefik.http.routers.myapp.middlewares=myapp_stripprefix
```

Note: These rules accept requests from any hostname. To restrict to specific domains, use `Host(`yourdomain.com`) && PathPrefix(`/myapp`)` instead.

## Troubleshooting

### Common Issues

1. **"No main service found"**:
    - Ensure one service has `milkcrate.main_service=true` label

2. **"Service refers to undefined network"**:
    - milkcrate automatically adds the Traefik network
    - Don't manually define external networks

3. **Health check failures**:
    - Ensure your app responds to health endpoints
    - Check that the exposed port is correct

4. **Service startup order**:
    - Use `depends_on` for service dependencies
    - Consider using health checks in your services

### Debugging

Check application logs:

```bash
# View compose stack logs
docker compose -p milkcrate-myapp logs

# View specific service logs
docker compose -p milkcrate-myapp logs app
```

## When to Use Docker Compose vs Dockerfile

Use **Docker Compose apps** when:

- Multiple containers are required
- Need databases, caches, or other supporting services
- Complex service dependencies
- Services need to communicate with each other

Use **Dockerfile apps** when:

- Single-container application
- No external services required
- Simple deployment and configuration

See [Dockerfile Applications](dockerfile-apps.md) for single-container deployments.

## Best Practices

1. **Use named volumes** for persistent data
2. **Set restart policies** (`restart: unless-stopped`)
3. **Include health endpoints** in your main service
4. **Use environment variables** for configuration
5. **Document dependencies** with `depends_on`
6. **Use specific image tags** for reproducibility

## Example Applications

### Simple Web App with Database

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
    labels:
      - milkcrate.main_service=true
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Microservices Application

```yaml
version: '3.8'
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    labels:
      - milkcrate.main_service=true
    depends_on:
      - db
      - redis

  worker:
    build: ./worker
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:

```

## Next Steps

- See [Volume Management](volumes.md) for persistent data
- See [Docker Compose Apps](docker-compose-apps.md) for multi-container applications
- See [Deployment](deployment.md) for production setup
