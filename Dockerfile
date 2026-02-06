FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Docker Compose
RUN curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Copy application code (respects .dockerignore)
COPY . .

# Install Python dependencies for this project
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv pip install --system .

# Create runtime directories that will be mounted as volumes
RUN mkdir -p uploads extracted_apps instance && \
    chmod 755 uploads extracted_apps instance

# Expose port
EXPOSE 5001

# Run the application
CMD ["python", "app.py"]
