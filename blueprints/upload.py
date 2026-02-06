"""Upload blueprint for handling ZIP uploads and deployments."""

import os
import shutil
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import login_required
from werkzeug.utils import secure_filename

from database import get_all_volumes, get_volume_by_id, route_exists
from milkcrate_core.extensions import limiter
from services.audit import log_admin_action
from services.deploy import allowed_file, deploy_application, extract_zip_safely
from services.validation import validate_and_sanitize_app_input

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/upload", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])  # Limit uploads to prevent abuse
@limiter.limit("50 per hour", methods=["GET"])  # Allow more GET requests for the form
@login_required
def upload_app() -> ResponseReturnValue:
    """Render the upload page and process application ZIP uploads.

    Validates the provided file, extracts the archive safely, and triggers
    deployment. Reserved prefix checks are no longer enforced.
    """
    if request.method == "GET":
        # Load available volumes for the form
        volumes = get_all_volumes()
        return render_template("upload.html", volumes=volumes)

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected")
            return redirect(request.url)

        file = request.files["file"]
        fname = file.filename
        if not fname:
            flash("No file selected")
            return redirect(request.url)

        if file and allowed_file(fname):
            try:
                app_name_input = request.form.get("app_name", "")
                public_route_input = request.form.get("public_route", "")

                # Validate and sanitize inputs
                is_valid, error_msg, app_name, public_route = (
                    validate_and_sanitize_app_input(app_name_input, public_route_input)
                )

                if not is_valid:
                    flash(f"Validation error: {error_msg}")
                    return redirect(request.url)

                # Check for route conflicts
                if route_exists(public_route):
                    flash(
                        f"Route '{public_route}' is already in use by another application. Please choose a different route."
                    )
                    return redirect(request.url)

                filename = secure_filename(fname)
                filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                extract_path = os.path.join(
                    current_app.config["EXTRACTED_FOLDER"],
                    f"{app_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                )

                if not extract_zip_safely(filepath, extract_path):
                    flash(
                        "Invalid ZIP file. Must contain either a Dockerfile or docker-compose.yml file."
                    )
                    os.remove(filepath)
                    return redirect(request.url)

                # Process volume mounts
                volume_mounts = {}
                selected_volumes = request.form.getlist("volumes[]")

                for volume_id_str in selected_volumes:
                    try:
                        volume_id = int(volume_id_str)
                        volume = get_volume_by_id(volume_id)
                        mount_path = request.form.get(
                            f"volume_path_{volume_id}", ""
                        ).strip()

                        if volume and mount_path:
                            # Format: {docker_volume_name: {'bind': '/path', 'mode': 'rw'}}
                            volume_mounts[volume["docker_volume_name"]] = {
                                "bind": mount_path,
                                "mode": "rw",
                            }
                    except (ValueError, TypeError):
                        continue

                success, container_id, image_tag = deploy_application(
                    extract_path,
                    app_name,
                    public_route,
                    current_app.config.get("TRAEFIK_NETWORK"),
                    is_public=False,
                    volume_mounts=volume_mounts if volume_mounts else None,
                )

                # Log the deployment action
                log_admin_action(
                    action="deploy",
                    resource_type="application",
                    resource_id=app_name,
                    details={
                        "public_route": public_route,
                        "image_tag": image_tag,
                        "container_id": container_id if success else None,
                        "is_public": False,
                    },
                    success=success,
                    error_message=container_id if not success else None,
                )

                if success:
                    flash(f"Application {app_name} deployed successfully!")
                    # Add a query parameter to trigger immediate status refresh
                    return redirect(url_for("admin.dashboard", deployed=app_name))
                flash(f"Failed to deploy application: {container_id}")
                shutil.rmtree(extract_path, ignore_errors=True)
                os.remove(filepath)
                return redirect(url_for("admin.dashboard"))

            except Exception as e:
                flash(f"Error during deployment: {e!s}")
                return redirect(request.url)

    # Fallback for other methods
    volumes = get_all_volumes()
    return render_template("upload.html", volumes=volumes)
