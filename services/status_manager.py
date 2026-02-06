"""Status management service for Docker containers and applications.

This module provides enhanced status tracking that integrates with Docker API
to provide real-time container state information and optional health checks.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, ClassVar

import docker
import requests
from docker.errors import NotFound

logger = logging.getLogger(__name__)


class ContainerStatus:
    """Container status constants with human-readable descriptions."""

    # Docker container states
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"

    # Custom application states
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    READY = "ready"
    NOT_READY = "not_ready"
    DEPLOYING = "deploying"
    UPDATING = "updating"
    DELETING = "deleting"
    ERROR = "error"

    # Status display mapping
    STATUS_DISPLAY: ClassVar[dict[str, str]] = {
        CREATED: "Created",
        RUNNING: "Running",
        PAUSED: "Paused",
        RESTARTING: "Restarting",
        REMOVING: "Removing",
        EXITED: "Stopped",
        DEAD: "Dead",
        STARTING: "Starting",
        HEALTHY: "Healthy",
        UNHEALTHY: "Unhealthy",
        READY: "Ready",
        NOT_READY: "Not Ready",
        DEPLOYING: "Deploying",
        UPDATING: "Updating",
        DELETING: "Deleting",
        ERROR: "Error",
    }

    # Status badge colors for UI
    STATUS_COLORS: ClassVar[dict[str, str]] = {
        CREATED: "secondary",
        RUNNING: "success",
        PAUSED: "warning",
        RESTARTING: "warning",
        REMOVING: "danger",
        EXITED: "secondary",
        DEAD: "danger",
        STARTING: "info",
        HEALTHY: "success",
        UNHEALTHY: "danger",
        READY: "success",
        NOT_READY: "warning",
        DEPLOYING: "info",
        UPDATING: "info",
        DELETING: "warning",
        ERROR: "danger",
    }


class StatusManager:
    """Manages application status using Docker API and health checks."""

    def __init__(self):
        """Initialize the status manager."""
        self.docker_client = None
        self._init_docker_client()

    def _init_docker_client(self):
        """Initialize Docker client with error handling."""
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None

    def get_container_status(self, container_id: str) -> tuple[str, dict[str, Any]]:
        """Get detailed container status from Docker API.

        Args:
            container_id: The container ID to check

        Returns:
            Tuple of (status, details_dict)
        """
        if not self.docker_client:
            return ContainerStatus.ERROR, {"error": "Docker client not available"}

        try:
            container = self.docker_client.containers.get(container_id)

            # Get basic container state
            state = container.status.lower()

            # Get detailed container information
            container.reload()
            attrs = container.attrs

            details = {
                "docker_status": state,
                "started_at": attrs.get("State", {}).get("StartedAt"),
                "finished_at": attrs.get("State", {}).get("FinishedAt"),
                "exit_code": attrs.get("State", {}).get("ExitCode"),
                "error": attrs.get("State", {}).get("Error"),
                "health": self._get_health_status(attrs),
                "restart_count": attrs.get("RestartCount", 0),
            }

            # Determine enhanced status
            enhanced_status = self._determine_enhanced_status(state, details)

            return enhanced_status, details

        except NotFound:
            return ContainerStatus.EXITED, {"error": "Container not found"}
        except Exception as e:
            logger.error(f"Error getting container status for {container_id}: {e}")
            return ContainerStatus.ERROR, {"error": str(e)}

    def _get_health_status(
        self, container_attrs: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract health check information from container attributes."""
        state = container_attrs.get("State", {})
        health = state.get("Health")

        if not health:
            return None

        return {
            "status": health.get("Status"),
            "failing_streak": health.get("FailingStreak", 0),
            "log": health.get("Log", [])[-1:]
            if health.get("Log")
            else [],  # Last entry
        }

    def _determine_enhanced_status(
        self, docker_state: str, details: dict[str, Any]
    ) -> str:
        """Determine enhanced application status based on Docker state and health."""

        # Handle basic Docker states
        if docker_state == "created":
            return ContainerStatus.CREATED
        if docker_state == "paused":
            return ContainerStatus.PAUSED
        if docker_state == "restarting":
            return ContainerStatus.RESTARTING
        if docker_state == "exited":
            return ContainerStatus.EXITED
        if docker_state == "dead":
            return ContainerStatus.DEAD
        if docker_state == "removing":
            return ContainerStatus.REMOVING

        # Handle running state with health checks
        if docker_state == "running":
            health = details.get("health")

            if health:
                health_status = health.get("status", "").lower()
                if health_status == "healthy":
                    return ContainerStatus.HEALTHY
                if health_status == "unhealthy":
                    return ContainerStatus.UNHEALTHY
                if health_status == "starting":
                    return ContainerStatus.STARTING

            # Check if container just started (might not be ready)
            started_at = details.get("started_at")
            if started_at:
                try:
                    # Parse Docker's timestamp format
                    start_time = datetime.fromisoformat(
                        started_at.replace("Z", "+00:00")
                    )
                    now = datetime.now(start_time.tzinfo)

                    # Consider container "starting" for first 30 seconds
                    if now - start_time < timedelta(seconds=30):
                        return ContainerStatus.STARTING
                except Exception:
                    pass

            return ContainerStatus.RUNNING

        return ContainerStatus.ERROR

    def check_application_health(
        self, app_name: str, public_route: str, internal_port: int, timeout: int = 5
    ) -> tuple[bool, dict[str, Any]]:
        """Check application health via HTTP endpoints.

        Args:
            app_name: Name of the application
            public_route: Public route for the application
            internal_port: Internal port the app is running on
            timeout: HTTP request timeout in seconds

        Returns:
            Tuple of (is_healthy, health_details)
        """
        # For Docker Compose applications, we need to check through Traefik
        # since the milkcrate container can't directly access other containers
        health_endpoints = [
            f"http://localhost{public_route}/api/health",
            f"http://localhost{public_route}/api/status",
            f"http://localhost{public_route}/health",
            f"http://localhost{public_route}/status",
            f"http://localhost{public_route}/",  # Fallback to main page
        ]

        endpoints_checked: list[str] = []
        health_details: dict[str, Any] = {
            "endpoints_checked": endpoints_checked,
            "successful_endpoint": None,
            "response_time": None,
            "status_code": None,
            "error": None,
        }

        for endpoint in health_endpoints:
            try:
                endpoints_checked.append(endpoint)

                start_time = time.time()

                # For health checks from within the milkcrate container,
                # we need to access Traefik directly with proper Host header
                if endpoint.startswith("http://localhost"):
                    # Extract the path from the endpoint
                    path = endpoint.replace("http://localhost", "")
                    # Access Traefik directly with Host header
                    response = requests.get(
                        f"http://traefik:80{path}",
                        headers={"Host": "localhost"},
                        timeout=timeout,
                    )
                else:
                    response = requests.get(endpoint, timeout=timeout)

                response_time = time.time() - start_time

                health_details["response_time"] = response_time
                health_details["status_code"] = response.status_code

                if response.status_code == 200:
                    health_details["successful_endpoint"] = endpoint

                    # Try to parse JSON response for additional health info
                    try:
                        json_data = response.json()
                        if isinstance(json_data, dict):
                            health_details["response_data"] = json_data
                    except Exception:
                        pass

                    return True, health_details

            except requests.exceptions.RequestException as e:
                health_details["error"] = str(e)
                continue
            except Exception as e:
                health_details["error"] = str(e)
                continue

        return False, health_details

    def get_comprehensive_status(
        self,
        container_id: str,
        app_name: str = "",
        public_route: str = "",
        internal_port: int = 8000,
    ) -> dict[str, Any]:
        """Get comprehensive status including Docker state and application health.

        Args:
            container_id: Docker container ID
            app_name: Application name
            public_route: Public route for health checks
            internal_port: Internal port

        Returns:
            Dictionary with comprehensive status information
        """
        # Get Docker container status
        docker_status, docker_details = self.get_container_status(container_id)

        result = {
            "status": docker_status,
            "display_status": ContainerStatus.STATUS_DISPLAY.get(
                docker_status, docker_status
            ),
            "badge_color": ContainerStatus.STATUS_COLORS.get(
                docker_status, "secondary"
            ),
            "docker_details": docker_details,
            "health_check": None,
            "last_checked": datetime.now().isoformat(),
        }

        # Only check application health if container is running
        if docker_status in [ContainerStatus.RUNNING, ContainerStatus.STARTING]:
            if public_route and app_name:
                is_healthy, health_details = self.check_application_health(
                    app_name, public_route, internal_port
                )

                result["health_check"] = {
                    "is_healthy": is_healthy,
                    "details": health_details,
                }

                # Override status if we have health check results
                if is_healthy and docker_status == ContainerStatus.RUNNING:
                    result["status"] = ContainerStatus.READY
                    result["display_status"] = ContainerStatus.STATUS_DISPLAY[
                        ContainerStatus.READY
                    ]
                    result["badge_color"] = ContainerStatus.STATUS_COLORS[
                        ContainerStatus.READY
                    ]
                elif not is_healthy and docker_status == ContainerStatus.RUNNING:
                    result["status"] = ContainerStatus.NOT_READY
                    result["display_status"] = ContainerStatus.STATUS_DISPLAY[
                        ContainerStatus.NOT_READY
                    ]
                    result["badge_color"] = ContainerStatus.STATUS_COLORS[
                        ContainerStatus.NOT_READY
                    ]

        return result


# Global status manager instance
status_manager = StatusManager()


def get_status_manager() -> StatusManager:
    """Get the global status manager instance."""
    return status_manager
