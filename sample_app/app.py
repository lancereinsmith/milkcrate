#!/usr/bin/env python3
"""Sample Flask application for milkcrate.

A simple web application demonstrating deployment with milkcrate.
"""

import os
import sys
from datetime import datetime

import flask
from flask import Flask, jsonify, redirect, render_template, request

app = Flask(__name__)


@app.before_request
def ensure_trailing_slash():
    """Ensure URLs have trailing slash for consistent relative path resolution.

    Only applies to non-API routes (API endpoints should not have trailing slashes).
    """
    # Skip API routes entirely
    if request.path.startswith("/api/"):
        return None

    # Skip root path and paths that already have trailing slash
    if request.path == "/" or request.path.endswith("/"):
        return None

    # Redirect other paths to add trailing slash
    return redirect(request.path + "/", code=301)


@app.route("/")
def index():
    """Main page of the sample application."""
    context = {
        "deployment_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "container_id": os.environ.get("HOSTNAME", "unknown"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "flask_version": getattr(flask, "__version__", "unknown"),
        "environment": os.environ.get("FLASK_ENV", "production"),
    }
    return render_template("index.html", **context)


@app.route("/api/status")
def status():
    """API endpoint to check application status."""
    return jsonify(
        {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
        }
    )


@app.route("/api/info")
def info():
    """API endpoint to get system information."""
    return jsonify(
        {
            "app_name": "Sample App",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "flask_version": getattr(flask, "__version__", "unknown"),
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "environment": os.environ.get("FLASK_ENV", "production"),
        }
    )


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
