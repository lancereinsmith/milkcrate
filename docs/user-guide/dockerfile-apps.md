# Dockerfile Applications

milkcrate supports deploying single-container applications using Dockerfiles. This is ideal for simple web applications, APIs, and services that don't require multiple containers.

## Overview

Dockerfile applications in milkcrate:

- Deploy standalone containerized applications
- Automatically integrate with Traefik for routing
- Support health checks and status monitoring
- Simple to package and deploy

## Creating a Dockerfile Application

### 1. Application Structure

Your application should have this structure:

```text
my-app/
├── app.py                # Your main application (Not confined to Python)
├── requirements.txt      # Dependencies (Not confined to Python)
├── Dockerfile           # Build instructions
├── templates/           # Optional: HTML templates
│   └── index.html
└── README.md            # Documentation
```

### 2. Required Dockerfile Configuration

Your `Dockerfile` must include these essential elements:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# REQUIRED: Expose the port your app runs on, e.g.:
EXPOSE 8000

# Start the application, e.g.:
CMD ["python", "app.py"]
```

### 3. Application Requirements

Your application must:

- **Expose a port**: Use `EXPOSE` directive (e.g., `EXPOSE 8000`)
- **Be accessible**: Respond to HTTP requests on the exposed port
- **Have a health endpoint**: Respond to health check requests (see below)

### 4. Complete Example

Here's a complete example with a Flask web application:

**Dockerfile:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

# Optional: Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "app.py"]
```

**app.py:**

```python
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello from milkcrate!"

@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
```

**requirements.txt:**

```text
flask==3.0.0
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

### Docker Healthcheck (Optional)

You can also define a Docker `HEALTHCHECK` in your Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
```

This provides container-level health monitoring in addition to milkcrate's application health checks.

## Advanced Configuration

### Environment Variables

Pass configuration through environment variables in your application:

**Dockerfile:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set default environment variables
ENV FLASK_ENV=production
ENV LOG_LEVEL=info

EXPOSE 8000

CMD ["python", "app.py"]
```

**app.py:**

```python
import os
from flask import Flask

app = Flask(__name__)

# Read configuration from environment
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")
FLASK_ENV = os.environ.get("FLASK_ENV", "production")
```

### Volume Mounts

#### Milkcrate-Managed Volumes

You can mount volumes created through Milkcrate's volume management interface during deployment. This is useful for:

- Persistent application data
- Configuration files
- Shared assets

To use Milkcrate-managed volumes:

1. Create and populate volumes through the Milkcrate UI (Admin → Manage Volumes)
2. During deployment, select volumes to mount and specify paths
3. Volumes will be mounted to your container

**Example volume mount paths:**

- `/app/data` - Application data
- `/app/uploads` - User uploads
- `/app/config` - Configuration files

See [Volume Management](volumes.md) for detailed instructions on creating and managing volumes.

#### Dockerfile Volume Declarations

You can also declare volumes in your Dockerfile:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies and copy application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Declare volume for persistent data
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["python", "app.py"]
```

## Deployment Process

1. **Package your application**:

   ```bash
   cd my-app
   zip -r my-app.zip . -x "*.git*" "*.pyc" "__pycache__/*"

   # Or, run:
   milkcrate package --output my-app.zip
   ```

2. **Upload via milkcrate UI**:
    - Go to Admin Dashboard and click "Deploy New App"
    - Upload your ZIP file
    - Set app name and public route
    - (Optional) Mount volumes if needed
    - Deploy

3. **milkcrate will**:
    - Extract the ZIP file
    - Detect the Dockerfile
    - Build the Docker image
    - Add Traefik labels for routing
    - Start the container
    - Monitor health and status

## Network Integration

### Traefik Labels (Auto-generated)

milkcrate adds these labels to your container:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.myapp.rule=PathPrefix(`/myapp`)
  - traefik.http.routers.myapp.entrypoints=web
  - traefik.http.services.myapp.loadbalancer.server.port=8000
  - traefik.http.middlewares.myapp_stripprefix.stripprefix.prefixes=/myapp
  - traefik.http.routers.myapp.middlewares=myapp_stripprefix
```

Note: These rules accept requests from any hostname. To restrict to specific domains, configure Traefik to use `Host(`yourdomain.com`) && PathPrefix(`/myapp`)` instead.

### Path Handling

When deployed with a route prefix (e.g., `/myapp`), milkcrate strips the prefix before forwarding to your application. Your app should:

1. **Use relative paths** for URLs, API calls, and assets
2. **Handle trailing slashes** consistently
3. **Avoid hardcoded absolute paths**

**Example - Correct path handling:**

```python
from flask import Flask, redirect, request

app = Flask(__name__)

@app.before_request
def ensure_trailing_slash():
    """Ensure URLs have trailing slash for relative path resolution."""
    # Skip API routes
    if request.path.startswith("/api/"):
        return None

    # Skip root and paths with trailing slash
    if request.path == "/" or request.path.endswith("/"):
        return None

    # Redirect to add trailing slash
    return redirect(request.path + "/", code=301)
```

## Troubleshooting

### Common Issues

1. **"Build failed"**:
    - Check Dockerfile syntax
    - Ensure all COPY sources exist
    - Verify base image is accessible

2. **"Container exits immediately"**:
    - Check application logs
    - Ensure CMD/ENTRYPOINT is correct
    - Verify dependencies are installed

3. **Health check failures**:
    - Ensure your app responds to health endpoints
    - Check that the exposed port is correct
    - Verify the app starts successfully

4. **"Port already in use"**:
    - milkcrate manages port assignment automatically
    - Don't use `ports` mapping in custom configurations

### Debugging

Check application logs:

```bash
# View container logs
docker logs milkcrate-myapp

# Follow logs in real-time
docker logs -f milkcrate-myapp

# View last 100 lines
docker logs --tail 100 milkcrate-myapp
```

Check container status:

```bash
# List all containers
docker ps -a

# Inspect container
docker inspect milkcrate-myapp
```

## Best Practices

1. **Use specific base image tags** (e.g., `python:3.12-slim`, not `python:latest`)
2. **Minimize image size** with multi-stage builds and slim base images
3. **Include health endpoints** for monitoring
4. **Use .dockerignore** to exclude unnecessary files
5. **Set proper logging** to stdout/stderr for Docker log collection
6. **Handle signals properly** for graceful shutdown
7. **Use environment variables** for configuration

## Example Applications

### Simple Flask Web App

**Dockerfile:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "app.py"]
```

**requirements.txt:**

```text
flask==3.0.0
```

**app.py:**

```python
from flask import Flask, jsonify, render_template
from datetime import datetime
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/info")
def info():
    return jsonify({
        "app_name": "My App",
        "environment": os.environ.get("FLASK_ENV", "production"),
        "version": "1.0.0"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
```

### FastAPI Application

**Dockerfile:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**requirements.txt:**

```text
fastapi==0.109.0
uvicorn[standard]==0.27.0
```

**main.py:**

```python
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="My API")

@app.get("/")
async def root():
    return {"message": "Welcome to my API"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/users")
async def get_users():
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]
```

### Node.js Express Application

**Dockerfile:**

```dockerfile
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node healthcheck.js || exit 1

CMD ["node", "server.js"]
```

**package.json:**

```json
{
  "name": "my-express-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

**server.js:**

```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.send('Hello from Express!');
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString()
  });
});

const PORT = 8000;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
});
```

## Comparison with Docker Compose Apps

Use **Dockerfile apps** when:

- You have a single-container application
- No external services required (database, cache, etc.)
- Simple deployment and configuration

Use **Docker Compose apps** when:

- Multiple containers required
- Need databases, caches, or other services
- Complex service dependencies
- Multiple containers need to communicate

See [Docker Compose Applications](docker-compose-apps.md) for multi-container deployments.

## Next Steps

- See [Volume Management](volumes.md) for persistent data
- See [Docker Compose Apps](docker-compose-apps.md) for multi-container applications
- See [Deployment](deployment.md) for production setup
