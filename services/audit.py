"""Audit logging service for tracking administrative actions.

Provides comprehensive logging of all administrative actions including
deployments, deletions, start/stop operations, and configuration changes.
"""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from flask import current_app, request
from flask_login import current_user


class AuditLogger:
    """Centralized audit logging for administrative actions."""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the audit logger with Flask app."""
        # Set up audit log file path
        audit_log_path = os.path.join(app.instance_path, "audit.log")

        # Create audit logger
        audit_logger = logging.getLogger("milkcrate.audit")
        audit_logger.setLevel(logging.INFO)

        # Create file handler
        handler = logging.FileHandler(audit_log_path)
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        if not audit_logger.handlers:
            audit_logger.addHandler(handler)

        app.audit_logger = audit_logger

    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ):
        """Log an administrative action.

        Args:
            action: The action performed (e.g., 'deploy', 'delete', 'start', 'stop')
            resource_type: Type of resource (e.g., 'application', 'settings')
            resource_id: ID or name of the resource
            details: Additional details about the action
            success: Whether the action was successful
            error_message: Error message if action failed
        """
        try:
            # Get user info
            user_id = "anonymous"
            if hasattr(current_user, "id") and current_user.is_authenticated:
                user_id = current_user.id

            # Get request info
            ip_address = request.remote_addr if request else "unknown"
            user_agent = (
                request.headers.get("User-Agent", "unknown") if request else "unknown"
            )

            # Build audit entry
            audit_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "success": success,
                "details": details or {},
            }

            if error_message:
                audit_entry["error_message"] = error_message

            # Log the entry
            logger = getattr(current_app, "audit_logger", None) if current_app else None
            if isinstance(logger, logging.Logger):
                log_message = json.dumps(audit_entry, separators=(",", ":"))
                if success:
                    logger.info(log_message)
                else:
                    logger.error(log_message)

        except Exception as e:
            # Don't let audit logging break the application
            if current_app:
                current_app.logger.warning(f"Audit logging failed: {e}")


# Global audit logger instance
audit_logger = AuditLogger()


def log_admin_action(
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    success: bool = True,
    error_message: str | None = None,
):
    """Convenience function for logging admin actions."""
    audit_logger.log_action(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        success=success,
        error_message=error_message,
    )


def get_audit_logs(limit: int = 100) -> list[dict]:
    """Retrieve recent audit logs for display in admin interface.

    Args:
        limit: Maximum number of log entries to return

    Returns:
        List of audit log entries
    """
    try:
        if not current_app or not hasattr(current_app, "audit_logger"):
            return []

        # Get the audit log file path
        audit_log_path = os.path.join(current_app.instance_path, "audit.log")

        if not os.path.exists(audit_log_path):
            return []

        logs = []
        with open(audit_log_path) as f:
            lines = f.readlines()

        # Get the last 'limit' lines and parse them
        for line in lines[-limit:]:
            try:
                # Parse the log line to extract JSON
                # Format: "timestamp - level - json_data"
                parts = line.strip().split(" - ", 2)
                if len(parts) >= 3:
                    json_data = parts[2]
                    log_entry = json.loads(json_data)
                    logs.append(log_entry)
            except (json.JSONDecodeError, IndexError):
                continue

        # Return in reverse chronological order (newest first)
        return list(reversed(logs))

    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Failed to retrieve audit logs: {e}")
        return []
