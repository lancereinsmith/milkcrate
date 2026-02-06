"""Volumes blueprint for managing Docker volumes and file uploads."""

import os

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import login_required
from werkzeug.utils import secure_filename

from database import (
    delete_volume,
    get_all_volumes,
    get_volume_by_id,
    get_volume_by_name,
    insert_volume,
    insert_volume_file,
    update_volume_stats,
)
from milkcrate_core.extensions import limiter
from services.audit import log_admin_action
from services.volume_manager import get_volume_manager

volumes_bp = Blueprint("volumes", __name__, url_prefix="/admin/volumes")


@volumes_bp.route("")
@login_required
def list_volumes() -> ResponseReturnValue:
    """List all volumes."""
    volumes = get_all_volumes()
    return render_template("volumes/list.html", volumes=volumes)


@volumes_bp.route("/create", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
@login_required
def create_volume() -> ResponseReturnValue:
    """Create a new volume."""
    if request.method == "POST":
        volume_name = request.form.get("volume_name", "").strip()
        description = request.form.get("description", "").strip()

        if not volume_name:
            flash("Volume name is required")
            return redirect(request.url)

        # Validate volume name (alphanumeric, hyphens, underscores)
        if not all(c.isalnum() or c in "-_" for c in volume_name):
            flash(
                "Volume name can only contain letters, numbers, hyphens, and underscores"
            )
            return redirect(request.url)

        # Check if volume already exists
        if get_volume_by_name(volume_name):
            flash(f"Volume {volume_name} already exists")
            return redirect(request.url)

        try:
            volume_manager = get_volume_manager()
            success, message, docker_volume_name = volume_manager.create_volume(
                volume_name, description
            )

            if success and docker_volume_name:
                # Insert into database
                insert_volume(volume_name, docker_volume_name, description)

                log_admin_action(
                    action="create",
                    resource_type="volume",
                    resource_id=volume_name,
                    details={
                        "docker_volume_name": docker_volume_name,
                        "description": description,
                    },
                    success=True,
                )

                flash(f"Volume {volume_name} created successfully")
                return redirect(url_for("volumes.list_volumes"))

            flash(f"Failed to create volume: {message}")
            log_admin_action(
                action="create",
                resource_type="volume",
                resource_id=volume_name,
                details={"description": description},
                success=False,
                error_message=message,
            )
            return redirect(request.url)

        except Exception as e:
            flash(f"Error creating volume: {e!s}")
            return redirect(request.url)

    return render_template("volumes/create.html")


@volumes_bp.route("/<int:volume_id>")
@login_required
def view_volume(volume_id: int) -> ResponseReturnValue:
    """View volume details and files."""
    volume = get_volume_by_id(volume_id)
    if not volume:
        flash("Volume not found")
        return redirect(url_for("volumes.list_volumes"))

    try:
        volume_manager = get_volume_manager()
        success, message, files = volume_manager.list_volume_files(
            volume["docker_volume_name"]
        )

        if not success:
            flash(f"Warning: Could not list files: {message}")
            files = []

        # Update volume stats
        total_size = sum(f["size"] for f in files)
        update_volume_stats(volume_id, len(files), total_size)

        return render_template("volumes/view.html", volume=dict(volume), files=files)

    except Exception as e:
        flash(f"Error loading volume: {e!s}")
        return render_template("volumes/view.html", volume=dict(volume), files=[])


@volumes_bp.route("/<int:volume_id>/upload", methods=["POST"])
@limiter.limit("30 per hour")
@login_required
def upload_file(volume_id: int) -> ResponseReturnValue:
    """Upload a file to a volume."""
    volume = get_volume_by_id(volume_id)
    if not volume:
        flash("Volume not found")
        return redirect(url_for("volumes.list_volumes"))

    if "file" not in request.files:
        flash("No file selected")
        return redirect(url_for("volumes.view_volume", volume_id=volume_id))

    file = request.files["file"]
    if not file.filename:
        flash("No file selected")
        return redirect(url_for("volumes.view_volume", volume_id=volume_id))

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        try:
            volume_manager = get_volume_manager()
            docker_volume_name = volume["docker_volume_name"]

            # Check if it's a ZIP file
            if filename.lower().endswith(".zip"):
                success, message, file_count = volume_manager.upload_zip_to_volume(
                    docker_volume_name, filepath
                )
            else:
                success, message = volume_manager.upload_file_to_volume(
                    docker_volume_name, filepath
                )
                file_count = 1 if success else 0

            if success:
                # Track uploaded file(s) in database
                if filename.lower().endswith(".zip"):
                    # Get updated file list
                    _, _, files = volume_manager.list_volume_files(docker_volume_name)
                    total_size = sum(f["size"] for f in files)
                    update_volume_stats(volume_id, len(files), total_size)
                else:
                    file_size = os.path.getsize(filepath)
                    insert_volume_file(volume_id, filename, f"/{filename}", file_size)
                    # Update stats
                    _, _, files = volume_manager.list_volume_files(docker_volume_name)
                    total_size = sum(f["size"] for f in files)
                    update_volume_stats(volume_id, len(files), total_size)

                log_admin_action(
                    action="upload",
                    resource_type="volume_file",
                    resource_id=f"{volume['volume_name']}/{filename}",
                    details={
                        "volume_id": volume_id,
                        "filename": filename,
                        "file_count": file_count,
                    },
                    success=True,
                )

                flash(message)
            else:
                flash(f"Upload failed: {message}")
                log_admin_action(
                    action="upload",
                    resource_type="volume_file",
                    resource_id=f"{volume['volume_name']}/{filename}",
                    details={"volume_id": volume_id, "filename": filename},
                    success=False,
                    error_message=message,
                )

        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

        return redirect(url_for("volumes.view_volume", volume_id=volume_id))

    except Exception as e:
        flash(f"Error uploading file: {e!s}")
        return redirect(url_for("volumes.view_volume", volume_id=volume_id))


@volumes_bp.route("/<int:volume_id>/delete", methods=["POST"])
@login_required
def delete_volume_route(volume_id: int) -> ResponseReturnValue:
    """Delete a volume."""
    volume = get_volume_by_id(volume_id)
    if not volume:
        flash("Volume not found")
        return redirect(url_for("volumes.list_volumes"))

    try:
        volume_manager = get_volume_manager()
        success, message = volume_manager.delete_volume(volume["docker_volume_name"])

        if success:
            delete_volume(volume_id)

            log_admin_action(
                action="delete",
                resource_type="volume",
                resource_id=volume["volume_name"],
                details={
                    "docker_volume_name": volume["docker_volume_name"],
                    "file_count": volume["file_count"],
                },
                success=True,
            )

            flash(f"Volume {volume['volume_name']} deleted successfully")
        else:
            flash(f"Failed to delete volume: {message}")
            log_admin_action(
                action="delete",
                resource_type="volume",
                resource_id=volume["volume_name"],
                details={"docker_volume_name": volume["docker_volume_name"]},
                success=False,
                error_message=message,
            )

    except Exception as e:
        flash(f"Error deleting volume: {e!s}")

    return redirect(url_for("volumes.list_volumes"))


@volumes_bp.route("/api/list")
@login_required
def api_list_volumes() -> ResponseReturnValue:
    """API endpoint to list all volumes."""
    volumes = get_all_volumes()
    return jsonify(
        {
            "volumes": [
                {
                    "volume_id": v["volume_id"],
                    "volume_name": v["volume_name"],
                    "docker_volume_name": v["docker_volume_name"],
                    "description": v["description"],
                    "file_count": v["file_count"],
                    "total_size_bytes": v["total_size_bytes"],
                    "created_date": v["created_date"],
                }
                for v in volumes
            ]
        }
    )
