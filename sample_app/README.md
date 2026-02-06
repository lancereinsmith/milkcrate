# Sample App

A simple Flask application for testing milkcrate Dockerfile deployments.

## Files

- `app.py` - Flask application with API endpoints
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies
- `templates/index.html` - Web interface

## API Endpoints

- `/` - Web interface
- `/api/status` - Application status
- `/api/info` - System information  
- `/api/health` - Health check

## Usage

1. Package: `zip -r sample-app.zip . -x "*.git*" "__pycache__/*"`
2. Upload to milkcrate with route `/sample`
3. Access at `http://localhost/sample/`

## Notes

- Uses relative API paths for correct routing at any mount point
- Includes health check for container monitoring
