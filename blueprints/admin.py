"""Admin blueprint routes for managing deployed applications.

This module provides routes for the admin dashboard, deleting applications,
and starting/stopping containers. Public/private visibility controls have
been removed.
"""

import contextlib
import os
import shutil
from datetime import datetime

import docker
from docker.errors import APIError, NotFound
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

from database import (
    delete_app,
    get_all_apps_with_real_status,
    get_app_by_id,
    get_app_with_real_status,
    get_default_home_route,
    set_admin_password,
    set_default_home_route,
    update_app_status,
)
from milkcrate_core.extensions import limiter
from services.audit import log_admin_action
from services.deploy import allowed_file, extract_zip_safely, update_application

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("")
@login_required
def dashboard() -> ResponseReturnValue:
    """Render the admin dashboard with a list of deployed applications."""
    apps = get_all_apps_with_real_status()
    default_route = get_default_home_route()
    # Detect environment override directly via process environment
    env_override_active = bool(
        str(os.environ.get("MILKCRATE_ADMIN_PASSWORD", "")).strip()
    )
    return render_template(
        "admin_dashboard.html",
        apps=apps,
        default_route=default_route,
        env_override_active=env_override_active,
    )


@admin_bp.route("/delete/<int:app_id>", methods=["POST"])
@login_required
def delete_app_route(app_id: int) -> ResponseReturnValue:
    """Delete a deployed application and its resources.

    Attempts to stop and remove the associated Docker container, remove the
    built image, clean up extracted files on disk, and delete the database
    record.

    Args:
        app_id: Identifier of the deployed application.

    Returns:
        A redirect response to the admin dashboard.
    """
    try:
        app_record = get_app_by_id(app_id)
        if not app_record:
            flash("Application not found")
            return redirect(url_for("admin.dashboard"))

        # Update status to indicate deletion in progress
        update_app_status(app_id, "deleting")

        client = docker.from_env()
        container_removed = False

        try:
            # Prefer container ID, but also attempt by expected name as fallback
            container = client.containers.get(app_record["container_id"])

            # Stop container with timeout
            try:
                container.stop(timeout=10)
                flash("Container stopped successfully")
            except APIError as e:
                flash(f"Warning: Could not stop container gracefully: {e}")

            # Remove container
            try:
                container.remove(force=True)
                container_removed = True
                flash("Container removed successfully")
            except APIError as e:
                flash(f"Warning: Could not remove container: {e}")

        except NotFound:
            # Try removing by the conventional name if ID lookup failed
            try:
                fallback_name = (
                    f"app-{(app_record['app_name'] or '').lower().replace('-', '_')}"
                )
                named = client.containers.get(fallback_name)

                try:
                    named.stop(timeout=10)
                except APIError as e:
                    flash(f"Warning: Could not stop container by name: {e}")

                try:
                    named.remove(force=True)
                    container_removed = True
                    flash("Container removed by name successfully")
                except APIError as e:
                    flash(f"Warning: Could not remove container by name: {e}")

            except NotFound:
                flash("Container not found - may have been already removed")

        # Attempt to remove the image associated with this app as well
        image_removed = False
        try:
            image_tag = app_record["image_tag"]
            if image_tag:
                try:
                    client.images.remove(image=image_tag, force=True, noprune=False)
                    image_removed = True
                    flash("Docker image removed successfully")
                except APIError as e:
                    flash(f"Warning: Could not remove image: {e}")
        except KeyError:
            pass

        # Clean up extracted files
        files_cleaned = False
        try:
            extracted_folder = current_app.config["EXTRACTED_FOLDER"]

            for item in os.listdir(extracted_folder):
                item_path = os.path.join(extracted_folder, item)
                if os.path.isdir(item_path) and app_record["app_name"] in item:
                    shutil.rmtree(item_path, ignore_errors=True)
                    files_cleaned = True
                    flash("Application files cleaned up successfully")
                    break
        except Exception as cleanup_error:
            flash(f"Warning: Could not clean up extracted files: {cleanup_error}")

        # Remove database record
        delete_app(app_id)

        # Log successful deletion
        log_admin_action(
            action="delete",
            resource_type="application",
            resource_id=app_record["app_name"],
            details={
                "app_id": app_id,
                "container_id": app_record["container_id"] if app_record else None,
                "image_tag": app_record["image_tag"] if app_record else None,
                "public_route": app_record["public_route"] if app_record else None,
                "container_removed": container_removed,
                "image_removed": image_removed,
                "files_cleaned": files_cleaned,
            },
            success=True,
        )

        # Summary message
        if container_removed and image_removed and files_cleaned:
            flash("Application deleted completely and successfully")
        elif container_removed:
            flash("Application deleted successfully (with some cleanup warnings)")
        else:
            flash(
                "Application database record deleted (container may need manual cleanup)"
            )

    except Exception as e:
        # Make sure to clear deleting status on error
        with contextlib.suppress(Exception):
            update_app_status(app_id, "error")

        # Log failed deletion
        app_name = app_record["app_name"] if app_record else str(app_id)
        log_admin_action(
            action="delete",
            resource_type="application",
            resource_id=app_name,
            details={"app_id": app_id},
            success=False,
            error_message=str(e),
        )

        flash(f"Error deleting application: {e!s}")

    return redirect(url_for("admin.dashboard"))


## Public/private visibility controls have been removed.


@admin_bp.route("/toggle_status/<int:app_id>", methods=["POST"])
@login_required
def toggle_status_route(app_id: int) -> ResponseReturnValue:
    """Start or stop the Docker container for a deployed application.

    If the application is running, this will attempt to stop it; otherwise it
    will attempt to start it.

    Args:
        app_id: Identifier of the deployed application.

    Returns:
        A redirect response to the admin dashboard.
    """
    try:
        app_record = get_app_with_real_status(app_id)
        if not app_record:
            flash("Application not found")
            return redirect(url_for("admin.dashboard"))

        client = docker.from_env()
        try:
            container = client.containers.get(app_record["container_id"])
        except docker.errors.NotFound:  # type: ignore[attr-defined]
            flash("Container not found on host")
            return redirect(url_for("admin.dashboard"))

        # Use real-time status instead of database status
        current_status = app_record.get("real_status", "").lower()

        if current_status in ["ready", "healthy", "running"]:
            try:
                container.stop(timeout=10)
                update_app_status(app_id, "stopped")

                # Log successful stop action
                log_admin_action(
                    action="stop",
                    resource_type="application",
                    resource_id=app_record["app_name"],
                    details={
                        "app_id": app_id,
                        "container_id": app_record.get("container_id"),
                        "previous_status": current_status,
                    },
                    success=True,
                )

                flash("Application stopped successfully")
            except Exception as e:
                update_app_status(app_id, "error")

                # Log failed stop action
                log_admin_action(
                    action="stop",
                    resource_type="application",
                    resource_id=app_record["app_name"],
                    details={
                        "app_id": app_id,
                        "container_id": app_record.get("container_id"),
                        "previous_status": current_status,
                    },
                    success=False,
                    error_message=str(e),
                )

                flash(f"Failed to stop container: {e}")
        elif current_status in ["stopped", "exited"]:
            try:
                container.start()
                update_app_status(app_id, "starting")

                # Log successful start action
                log_admin_action(
                    action="start",
                    resource_type="application",
                    resource_id=app_record["app_name"],
                    details={
                        "app_id": app_id,
                        "container_id": app_record.get("container_id"),
                        "previous_status": current_status,
                    },
                    success=True,
                )

                flash("Application starting... (check status in a moment)")
            except Exception as e:
                update_app_status(app_id, "error")

                # Log failed start action
                log_admin_action(
                    action="start",
                    resource_type="application",
                    resource_id=app_record["app_name"],
                    details={
                        "app_id": app_id,
                        "container_id": app_record.get("container_id"),
                        "previous_status": current_status,
                    },
                    success=False,
                    error_message=str(e),
                )

                flash(f"Failed to start container: {e}")
        else:
            flash(
                f"Cannot start/stop application in current status: {current_status.title()}. Only Ready/Healthy/Running or Stopped applications can be controlled."
            )
    except Exception as e:
        flash(f"Error toggling application status: {e!s}")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/htmx/status-badges", methods=["GET"])
@login_required
def get_status_badges_htmx():
    """HTMX endpoint to get updated status badges for all applications."""
    try:
        apps = get_all_apps_with_real_status()
        return render_template("admin/status_badges_partial.html", apps=apps)
    except Exception as e:
        return f'<div class="alert alert-danger">Error loading status: {e!s}</div>'


@admin_bp.route("/settings/default-route", methods=["POST"])
@login_required
def update_default_route() -> ResponseReturnValue:
    """Update the default home route setting.

    Returns:
        A redirect response to the admin dashboard.
    """

    try:
        new_route = request.form.get("default_route", "").strip()

        # Validate the route format
        if new_route and not new_route.startswith("/"):
            new_route = f"/{new_route}"

        set_default_home_route(new_route)

        if new_route:
            flash(f"Default route updated to: {new_route}")
        else:
            flash("Default route cleared - will show app listing")

    except Exception as e:
        flash(f"Error updating default route: {e!s}")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/settings/password", methods=["POST"])
@login_required
def update_admin_password() -> ResponseReturnValue:
    """Update the admin password stored in the database.

    If the MILKCRATE_ADMIN_PASSWORD environment variable is set, it will
    continue to override the stored value during login. We inform the user via
    a flash message in that case.
    """

    try:
        new_password = (request.form.get("new_password", "") or "").strip()
        confirm_password = (request.form.get("confirm_password", "") or "").strip()

        if not new_password:
            flash("Password cannot be empty")
            return redirect(url_for("admin.dashboard"))

        if new_password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for("admin.dashboard"))

        set_admin_password(new_password)
        if str(os.environ.get("MILKCRATE_ADMIN_PASSWORD", "")).strip():
            flash(
                "Password saved, but environment override is active and will be used for login"
            )
        else:
            flash("Admin password updated successfully")
    except Exception as e:
        flash(f"Error updating password: {e!s}")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/update/<int:app_id>", methods=["POST"])
@limiter.limit("5 per hour")  # Limit updates to prevent abuse
@login_required
def update_app_route(app_id: int) -> ResponseReturnValue:
    """Update an existing application with a new ZIP file.

    Uploads a new ZIP file, extracts it, stops the old container,
    builds a new image, and starts a new container with the same configuration.

    Args:
        app_id: Identifier of the deployed application to update.

    Returns:
        A redirect response to the admin dashboard.
    """
    try:
        # Check if app exists
        app_record = get_app_by_id(app_id)
        if not app_record:
            flash("Application not found")
            return redirect(url_for("admin.dashboard"))

        app_name = app_record["app_name"]

        # Check if file was uploaded
        if "file" not in request.files:
            flash(f"No file selected for {app_name} update")
            return redirect(url_for("admin.dashboard"))

        file = request.files["file"]
        if file.filename == "":
            flash(f"No file selected for {app_name} update")
            return redirect(url_for("admin.dashboard"))

        fname = file.filename
        if not fname or not allowed_file(fname):
            flash(
                f"Invalid file type for {app_name} update. Only ZIP files are allowed."
            )
            return redirect(url_for("admin.dashboard"))

        try:
            # Save uploaded file
            filename = secure_filename(fname)
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Extract ZIP file
            extract_path = os.path.join(
                current_app.config["EXTRACTED_FOLDER"],
                f"{app_name}_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )

            if not extract_zip_safely(filepath, extract_path):
                flash(
                    f"Invalid ZIP file for {app_name} update or missing required files"
                )
                os.remove(filepath)
                return redirect(url_for("admin.dashboard"))

            # Perform the update
            success, result_message, _ = update_application(
                app_id,
                extract_path,
                filename,
                current_app.config.get("TRAEFIK_NETWORK"),
            )

            if success:
                flash(f"Application {app_name} updated successfully!")
                # Add query parameter to trigger status refresh
                return redirect(url_for("admin.dashboard", updated=app_name))
            flash(f"Failed to update {app_name}: {result_message}")
            # Clean up files on failure
            shutil.rmtree(extract_path, ignore_errors=True)
            os.remove(filepath)
            return redirect(url_for("admin.dashboard"))

        except Exception as e:
            flash(f"Error during {app_name} update: {e!s}")
            # Clean up files on error
            try:
                if "filepath" in locals():
                    os.remove(filepath)
                if "extract_path" in locals():
                    shutil.rmtree(extract_path, ignore_errors=True)
            except Exception:
                pass
            return redirect(url_for("admin.dashboard"))

    except Exception as e:
        flash(f"Error updating application: {e!s}")

    return redirect(url_for("admin.dashboard"))
