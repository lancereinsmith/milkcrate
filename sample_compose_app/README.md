# Sample Compose App

A Flask application demonstrating docker-compose.yml deployment with milkcrate.

## Files

- `app.py` - Flask application
- `docker-compose.yml` - Compose configuration with `milkcrate.main_service=true` label
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies
- `templates/index.html` - Web interface

## API Endpoints

- `/` - Web interface
- `/api/status` - Application status
- `/api/health` - Health check

## Usage

1. Package: `zip -r sample-compose-app.zip . -x "*.git*" "__pycache__/*"`
2. Upload to milkcrate with route `/compose`
3. Access at `http://localhost/compose/`

## Docker Compose Configuration

The `milkcrate.main_service=true` label identifies which service receives traffic:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    labels:
      - milkcrate.main_service=true
```
