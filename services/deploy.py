"""Deployment service utilities.

Includes helpers for validating uploads, extracting archives safely, and
building/running Docker containers for applications.
"""

import contextlib
import os
import zipfile
from datetime import datetime

import docker

from services.compose_parser import (
    get_compose_services_info,
    parse_docker_compose,
    validate_compose_for_milkcrate,
)


def _parse_bool(val: str) -> bool:
    """Parse a string as boolean for env config."""
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _is_https_enabled() -> bool:
    """Check if HTTPS mode is enabled via environment variable."""
    return _parse_bool(os.environ.get("ENABLE_HTTPS", "false"))


def _generate_traefik_labels(
    app_name: str,
    public_route: str,
    internal_port: int,
    route_priority: int,
    enable_https: bool = False,
) -> dict[str, str]:
    """Generate Traefik labels for an application.

    Args:
        app_name: Name of the application (will be sanitized)
        public_route: Public route path (e.g., /myapp)
        internal_port: Internal container port
        route_priority: Routing priority value
        enable_https: Whether to enable HTTPS/TLS configuration

    Returns:
        Dictionary of Traefik labels
    """
    sanitized_name = app_name.replace("-", "_")
    entrypoint = "websecure" if enable_https else "web"

    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.{sanitized_name}.rule": f"PathPrefix(`{public_route}`)",
        f"traefik.http.routers.{sanitized_name}.entrypoints": entrypoint,
        f"traefik.http.routers.{sanitized_name}.priority": str(route_priority),
        f"traefik.http.services.{sanitized_name}.loadbalancer.server.port": str(
            internal_port
        ),
        f"traefik.http.middlewares.{sanitized_name}_stripprefix.stripprefix.prefixes": public_route,
        f"traefik.http.routers.{sanitized_name}.middlewares": f"{sanitized_name}_stripprefix",
    }

    # Add TLS configuration for HTTPS
    if enable_https:
        labels[f"traefik.http.routers.{sanitized_name}.tls.certresolver"] = (
            "letsencrypt"
        )

    return labels


def allowed_file(filename: str | None) -> bool:
    """Return True if the filename looks like a ZIP archive."""
    return (
        filename is not None
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() == "zip"
    )


def detect_deployment_type(app_path: str) -> str:
    """Detect whether the application uses Dockerfile or docker-compose.yml.

    Args:
        app_path: Path to the extracted application directory

    Returns:
        'dockerfile' or 'docker-compose'
    """
    if os.path.exists(os.path.join(app_path, "docker-compose.yml")):
        return "docker-compose"
    if os.path.exists(os.path.join(app_path, "Dockerfile")):
        return "dockerfile"
    # Default to dockerfile
    return "dockerfile"


def extract_zip_safely(zip_path: str, extract_path: str) -> bool:
    """Safely extract a zip archive and verify required files exist.

    Prevents path traversal and ensures either a `Dockerfile` or `docker-compose.yml`
    is present after extraction. Supports any containerized application type.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            file_list = zip_ref.namelist()
            for filename in file_list:
                if ".." in filename or filename.startswith("/"):
                    return False
                if os.path.isabs(filename):
                    return False

            os.makedirs(extract_path, exist_ok=True)
            zip_ref.extractall(extract_path)

            extracted_files = os.listdir(extract_path)
            has_dockerfile = "Dockerfile" in extracted_files
            has_compose_file = "docker-compose.yml" in extracted_files

            # Must have either Dockerfile or docker-compose.yml
            # No longer restricted to Python applications
            return has_dockerfile or has_compose_file
    except Exception:
        return False


def deploy_application(
    app_path: str,
    app_name: str,
    public_route: str,
    traefik_network: str | None = None,
    is_public: bool = False,
    volume_mounts: dict[str, dict] | None = None,
) -> tuple[bool, str, str | None]:
    """Build and run the uploaded application as a Docker container.

    Supports both Dockerfile and docker-compose.yml deployments.

    Args:
        app_path: Path to the application directory
        app_name: Name of the application
        public_route: Public route for the application
        traefik_network: Traefik network name
        is_public: Whether the app should be public
        volume_mounts: Dict of volume mounts {docker_volume_name: {'bind': '/path', 'mode': 'rw'}}

    Returns a tuple: (success flag, container id or error message, image tag
    when available).
    """
    # Detect deployment type
    deployment_type = detect_deployment_type(app_path)

    if deployment_type == "docker-compose":
        return deploy_docker_compose(
            app_path, app_name, public_route, traefik_network, is_public, volume_mounts
        )
    # Original Dockerfile deployment logic
    try:
        client = docker.from_env()
        network_name = traefik_network or os.environ.get(
            "TRAEFIK_NETWORK", "milkcrate-traefik"
        )

        image_tag = (
            f"milkcrate-{app_name.lower()}:{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        try:
            client.images.build(path=app_path, tag=image_tag, rm=True, pull=True)
        except Exception as build_error:
            build_logs_str = str(build_error)
            return False, f"Image build failed: {build_logs_str}", None

        try:
            image_obj = client.images.get(image_tag)
            exposed = (image_obj.attrs or {}).get("Config", {}).get(
                "ExposedPorts", {}
            ) or {}
            internal_port = 8000
            if exposed:
                preferred = [p for p in exposed if p.endswith("/tcp")]
                ports_numeric: list[int] = []
                for key in preferred:
                    try:
                        port_num = int(key.split("/")[0])
                        ports_numeric.append(port_num)
                    except Exception:
                        continue
                if 8000 in ports_numeric:
                    internal_port = 8000
                elif ports_numeric:
                    internal_port = min(ports_numeric)
        except Exception:
            internal_port = 8000

        # Ensure no existing container with the same name is lingering
        container_name = f"app-{app_name.lower().replace('-', '_')}"
        try:
            existing_container = client.containers.get(container_name)
            try:
                existing_container.stop()
            except Exception:
                # It may already be stopped
                pass
            try:
                existing_container.remove(force=True)
            except Exception:
                # Best-effort cleanup
                pass
        except docker.errors.NotFound:  # type: ignore[attr-defined]
            pass

        # Calculate priority based on route path length - longer paths get higher priority
        # This ensures /test2 gets higher priority than /test
        route_priority = (
            100 + len(public_route.strip("/").split("/")) * 10 + len(public_route)
        )

        # Ensure network exists before deploying
        try:
            client.networks.get(network_name)
        except docker.errors.NotFound:  # type: ignore[attr-defined]
            # Network doesn't exist, create it
            try:
                client.networks.create(network_name, driver="bridge")
            except Exception as network_error:
                return (
                    False,
                    f"Failed to create network '{network_name}': {network_error!s}",
                    None,
                )

        # Security and resource policies for containers
        security_policies = {
            # Resource limits
            "mem_limit": "512m",  # 512MB memory limit
            "memswap_limit": "512m",  # Same as memory (no swap)
            "cpu_period": 100000,  # 100ms period
            "cpu_quota": 50000,  # 50% of CPU
            "pids_limit": 100,  # Limit number of processes
            # Security policies
            "read_only": False,  # Keep writable for app functionality
            "cap_drop": ["ALL"],  # Drop all capabilities
            "cap_add": ["NET_BIND_SERVICE"],  # Only allow binding to ports
            "security_opt": [
                "no-new-privileges:true",  # Prevent privilege escalation
                "apparmor:unconfined",  # Use default AppArmor profile
            ],
            "user": "nobody:nogroup",  # Run as non-root user when possible
            # Filesystem security
            "tmpfs": {
                "/tmp": "rw,noexec,nosuid,size=100m",  # Secure tmp directory
            },
            # Logging configuration
            "log_config": {
                "type": "json-file",
                "config": {"max-size": "10m", "max-file": "3"},
            },
        }

        # Prepare volume mounts if provided
        volumes_dict = volume_mounts if volume_mounts else {}

        # Generate Traefik labels with HTTPS support if enabled
        traefik_labels = _generate_traefik_labels(
            app_name=app_name,
            public_route=public_route,
            internal_port=internal_port,
            route_priority=route_priority,
            enable_https=_is_https_enabled(),
        )

        container = client.containers.run(
            image_tag,
            detach=True,
            name=container_name,
            network=network_name,  # Connect to named network (not network_mode)
            volumes=volumes_dict,
            labels=traefik_labels,
            **security_policies,
        )

        # Insert app with basic database entry
        # Serialize volume mounts for database storage
        import json

        from database import get_app_by_container_id, insert_app, update_app_status

        volume_mounts_json = json.dumps(volume_mounts) if volume_mounts else None

        insert_app(
            app_name,
            container.id,
            image_tag,
            public_route,
            internal_port,
            is_public=is_public,
            deployment_type="dockerfile",
            volume_mounts=volume_mounts_json,
        )

        # Try to enhance with status checking, but don't fail deployment if it doesn't work
        try:
            app_record = get_app_by_container_id(container.id)
            if app_record:
                # Set initial status to deploying
                update_app_status(app_record["app_id"], "deploying")

                # Wait longer for container to start and become healthy
                import time

                time.sleep(5)  # Increased from 2 to 5 seconds

                # Try to update to actual container status
                try:
                    from services.status_manager import get_status_manager

                    status_manager = get_status_manager()
                    status_info = status_manager.get_comprehensive_status(
                        container_id=container.id,
                        app_name=app_name,
                        public_route=public_route,
                        internal_port=internal_port,
                    )

                    update_app_status(app_record["app_id"], status_info["status"])
                except Exception:
                    # If status checking fails, fallback to basic "running" status
                    update_app_status(app_record["app_id"], "running")
        except Exception:
            # If any status management fails, deployment still succeeds
            pass

        return True, container.id, image_tag
    except Exception as e:
        return False, str(e), None


def update_docker_compose_application(
    app_id: int,
    app_path: str,
    new_zip_filename: str,
    traefik_network: str | None = None,
) -> tuple[bool, str, str | None]:
    """Update an existing docker-compose application with new code.

    Args:
        app_id: ID of the existing application to update
        app_path: Path to extracted application files
        new_zip_filename: Original filename of the uploaded ZIP
        traefik_network: Traefik network name (optional)

    Returns:
        A tuple: (success flag, container id or error message, image tag when available)
    """
    try:
        # Get existing app info
        from database import get_app_by_id, update_app_container_info, update_app_status

        app_record = get_app_by_id(app_id)
        if not app_record:
            return False, "Application not found", None

        app_name = app_record["app_name"]
        public_route = app_record["public_route"]
        app_record["container_id"]
        app_record["image_tag"]
        internal_port = app_record["internal_port"]
        bool(app_record["is_public"])
        main_service = dict(app_record).get("main_service")

        if not main_service:
            return False, "No main service found for docker-compose application", None

        # Update status to indicate update in progress
        update_app_status(app_id, "updating")

        # Get network name
        network_name = traefik_network or os.environ.get(
            "TRAEFIK_NETWORK", "milkcrate-traefik"
        )

        # Ensure network exists before deploying
        client = docker.from_env()
        try:
            client.networks.get(network_name)
        except docker.errors.NotFound:  # type: ignore[attr-defined]
            # Network doesn't exist, create it
            try:
                client.networks.create(network_name, driver="bridge")
            except Exception as network_error:
                update_app_status(app_id, "error")
                return (
                    False,
                    f"Failed to create network '{network_name}': {network_error!s}",
                    None,
                )

        # Create project name
        project_name = f"milkcrate-{app_name.lower().replace('-', '_')}"

        # Stop and remove existing containers
        try:
            import subprocess

            subprocess.run(
                ["docker-compose", "-p", project_name, "down"],
                cwd=app_path,
                capture_output=True,
                timeout=30,
            )
        except Exception:
            # Ignore errors if no existing containers
            pass

        # Parse and validate the new compose file
        compose_path = os.path.join(app_path, "docker-compose.yml")
        is_valid, error_msg, compose_data = parse_docker_compose(compose_path)
        if not is_valid:
            update_app_status(app_id, "error")
            return False, f"Invalid docker-compose.yml: {error_msg}", None
        if compose_data is None:
            update_app_status(app_id, "error")
            return False, "Invalid docker-compose.yml: no data", None

        # Validate for milkcrate requirements
        is_valid, error_msg = validate_compose_for_milkcrate(compose_data)
        if not is_valid:
            update_app_status(app_id, "error")
            return False, f"docker-compose.yml validation failed: {error_msg}", None

        # Get compose information
        compose_info = get_compose_services_info(compose_data)
        new_main_service = compose_info["main_service"]
        new_internal_port = compose_info["internal_port"]

        # Update main service if it changed
        if new_main_service != main_service:
            main_service = new_main_service
            internal_port = new_internal_port

        # Add Traefik labels to the main service
        modified_compose_data = compose_data.copy()
        main_service_config = modified_compose_data["services"][main_service].copy()

        # Calculate priority based on route path length
        route_priority = (
            100 + len(public_route.strip("/").split("/")) * 10 + len(public_route)
        )

        # Prepare Traefik labels with HTTPS support if enabled
        traefik_labels = _generate_traefik_labels(
            app_name=app_name,
            public_route=public_route,
            internal_port=internal_port,
            route_priority=route_priority,
            enable_https=_is_https_enabled(),
        )

        # Add labels to main service
        existing_labels = main_service_config.get("labels", {})
        if isinstance(existing_labels, dict):
            main_service_config["labels"] = {**existing_labels, **traefik_labels}
        elif isinstance(existing_labels, list):
            # Convert dict labels to list format
            label_list = existing_labels.copy()
            for key, value in traefik_labels.items():
                label_list.append(f"{key}={value}")
            main_service_config["labels"] = label_list
        else:
            main_service_config["labels"] = traefik_labels

        # Ensure the main service joins the Traefik network
        networks = main_service_config.get("networks", [])
        if isinstance(networks, list):
            if network_name not in networks:
                networks.append(network_name)
            main_service_config["networks"] = networks
        elif isinstance(networks, dict):
            networks[network_name] = {}
            main_service_config["networks"] = networks
        else:
            main_service_config["networks"] = [network_name]

        # Update the compose data
        modified_compose_data["services"][main_service] = main_service_config

        # Add network definition to compose file
        if "networks" not in modified_compose_data:
            modified_compose_data["networks"] = {}
        modified_compose_data["networks"][network_name] = {"external": True}

        # Write modified compose file
        import yaml

        modified_compose_path = os.path.join(app_path, "docker-compose-modified.yml")
        with open(modified_compose_path, "w") as f:
            yaml.dump(modified_compose_data, f, default_flow_style=False)

        # Deploy using docker-compose
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "-p",
                    project_name,
                    "-f",
                    "docker-compose-modified.yml",
                    "up",
                    "-d",
                ],
                cwd=app_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                update_app_status(app_id, "error")
                return False, f"docker-compose deployment failed: {result.stderr}", None

        except subprocess.TimeoutExpired:
            update_app_status(app_id, "error")
            return False, "docker-compose deployment timed out", None
        except Exception as e:
            update_app_status(app_id, "error")
            return False, f"docker-compose deployment error: {e!s}", None

        # Get the container ID of the main service
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "-p",
                    project_name,
                    "-f",
                    "docker-compose-modified.yml",
                    "ps",
                    "-q",
                    main_service,
                ],
                cwd=app_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0 or not result.stdout.strip():
                update_app_status(app_id, "error")
                return (
                    False,
                    f"Could not get container ID for main service '{main_service}'",
                    None,
                )

            new_container_id = result.stdout.strip()

            # Generate new image tag for database consistency
            new_image_tag = f"milkcrate-{app_name.lower()}:{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            # Update database record
            update_app_container_info(
                app_id,
                new_container_id,
                new_image_tag,
                deployment_type="docker-compose",
                compose_file="docker-compose.yml",
                main_service=main_service,
            )

            # Try to enhance with status checking
            try:
                # Set initial status to deploying
                update_app_status(app_id, "deploying")

                import time

                time.sleep(5)

                try:
                    from services.status_manager import get_status_manager

                    status_manager = get_status_manager()
                    status_info = status_manager.get_comprehensive_status(
                        container_id=new_container_id,
                        app_name=app_name,
                        public_route=public_route,
                        internal_port=internal_port,
                    )

                    update_app_status(app_id, status_info["status"])
                except Exception:
                    update_app_status(app_id, "running")
            except Exception:
                pass

            return True, new_container_id, new_image_tag

        except Exception as e:
            update_app_status(app_id, "error")
            return False, f"Error getting container information: {e!s}", None

    except Exception as e:
        with contextlib.suppress(Exception):
            update_app_status(app_id, "error")
        return False, str(e), None


def deploy_docker_compose(
    app_path: str,
    app_name: str,
    public_route: str,
    traefik_network: str | None = None,
    is_public: bool = False,
    volume_mounts: dict[str, dict] | None = None,
) -> tuple[bool, str, str | None]:
    """Deploy an application using docker-compose.yml.

    Args:
        app_path: Path to the application directory
        app_name: Name of the application
        public_route: Public route for the application
        traefik_network: Traefik network name
        is_public: Whether the app should be public

    Returns:
        Tuple of (success flag, container id or error message, image tag when available)
    """
    try:
        compose_path = os.path.join(app_path, "docker-compose.yml")

        # Parse and validate the compose file
        is_valid, error_msg, compose_data = parse_docker_compose(compose_path)
        if not is_valid:
            return False, f"Invalid docker-compose.yml: {error_msg}", None
        if compose_data is None:
            return False, "Invalid docker-compose.yml: no data", None

        # Validate for milkcrate requirements
        is_valid, error_msg = validate_compose_for_milkcrate(compose_data)
        if not is_valid:
            return False, f"docker-compose.yml validation failed: {error_msg}", None

        # Get compose information
        compose_info = get_compose_services_info(compose_data)
        main_service = compose_info["main_service"]
        internal_port = compose_info["internal_port"]

        # Get network name
        network_name = traefik_network or os.environ.get(
            "TRAEFIK_NETWORK", "milkcrate-traefik"
        )

        # Ensure network exists before deploying
        client = docker.from_env()
        try:
            client.networks.get(network_name)
        except docker.errors.NotFound:  # type: ignore[attr-defined]
            # Network doesn't exist, create it
            try:
                client.networks.create(network_name, driver="bridge")
            except Exception as network_error:
                return (
                    False,
                    f"Failed to create network '{network_name}': {network_error!s}",
                    None,
                )

        # Create a unique project name for this deployment
        project_name = f"milkcrate-{app_name.lower().replace('-', '_')}"

        # Ensure no existing containers with the same project name
        try:
            # Try to stop and remove existing containers with this project name
            import subprocess

            subprocess.run(
                ["docker-compose", "-p", project_name, "down"],
                cwd=app_path,
                capture_output=True,
                timeout=30,
            )
        except Exception:
            # Ignore errors if no existing containers
            pass

        # Add Traefik labels to the main service
        modified_compose_data = compose_data.copy()
        main_service_config = modified_compose_data["services"][main_service].copy()

        # Calculate priority based on route path length
        route_priority = (
            100 + len(public_route.strip("/").split("/")) * 10 + len(public_route)
        )

        # Prepare Traefik labels with HTTPS support if enabled
        traefik_labels = _generate_traefik_labels(
            app_name=app_name,
            public_route=public_route,
            internal_port=internal_port,
            route_priority=route_priority,
            enable_https=_is_https_enabled(),
        )

        # Add labels to main service
        existing_labels = main_service_config.get("labels", {})
        if isinstance(existing_labels, dict):
            main_service_config["labels"] = {**existing_labels, **traefik_labels}
        elif isinstance(existing_labels, list):
            # Convert dict labels to list format
            label_list = existing_labels.copy()
            for key, value in traefik_labels.items():
                label_list.append(f"{key}={value}")
            main_service_config["labels"] = label_list
        else:
            main_service_config["labels"] = traefik_labels

        # Ensure the main service joins the Traefik network
        networks = main_service_config.get("networks", [])
        if isinstance(networks, list):
            if network_name not in networks:
                networks.append(network_name)
            main_service_config["networks"] = networks
        elif isinstance(networks, dict):
            networks[network_name] = {}
            main_service_config["networks"] = networks
        else:
            main_service_config["networks"] = [network_name]

        # Update the compose data
        modified_compose_data["services"][main_service] = main_service_config

        # Add network definition to compose file
        if "networks" not in modified_compose_data:
            modified_compose_data["networks"] = {}
        modified_compose_data["networks"][network_name] = {"external": True}

        # Write modified compose file
        import yaml

        modified_compose_path = os.path.join(app_path, "docker-compose-modified.yml")
        with open(modified_compose_path, "w") as f:
            yaml.dump(modified_compose_data, f, default_flow_style=False)

        # Deploy using docker-compose
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "-p",
                    project_name,
                    "-f",
                    "docker-compose-modified.yml",
                    "up",
                    "-d",
                ],
                cwd=app_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return False, f"docker-compose deployment failed: {result.stderr}", None

        except subprocess.TimeoutExpired:
            return False, "docker-compose deployment timed out", None
        except Exception as e:
            return False, f"docker-compose deployment error: {e!s}", None

        # Get the container ID of the main service
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "-p",
                    project_name,
                    "-f",
                    "docker-compose-modified.yml",
                    "ps",
                    "-q",
                    main_service,
                ],
                cwd=app_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return (
                    False,
                    f"Could not get container ID for main service '{main_service}'",
                    None,
                )

            container_id = result.stdout.strip()

            # Verify container exists
            client.containers.get(container_id)

            # Generate image tag for database consistency
            image_tag = f"milkcrate-{app_name.lower()}:{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            # Insert app with compose-specific information
            # Serialize volume mounts for database storage
            import json

            from database import insert_app

            volume_mounts_json = json.dumps(volume_mounts) if volume_mounts else None

            insert_app(
                app_name,
                container_id,
                image_tag,
                public_route,
                internal_port,
                is_public=is_public,
                deployment_type="docker-compose",
                compose_file="docker-compose.yml",
                main_service=main_service,
                volume_mounts=volume_mounts_json,
            )

            # Try to enhance with status checking
            try:
                from database import get_app_by_container_id, update_app_status

                app_record = get_app_by_container_id(container_id)
                if app_record:
                    update_app_status(app_record["app_id"], "deploying")

                    import time

                    time.sleep(5)

                    try:
                        from services.status_manager import get_status_manager

                        status_manager = get_status_manager()
                        status_info = status_manager.get_comprehensive_status(
                            container_id=container_id,
                            app_name=app_name,
                            public_route=public_route,
                            internal_port=internal_port,
                        )

                        update_app_status(app_record["app_id"], status_info["status"])
                    except Exception:
                        update_app_status(app_record["app_id"], "running")
            except Exception:
                pass

            return True, container_id, image_tag

        except Exception as e:
            return False, f"Error getting container information: {e!s}", None

    except Exception as e:
        return False, str(e), None


def update_application(
    app_id: int,
    app_path: str,
    new_zip_filename: str,
    traefik_network: str | None = None,
) -> tuple[bool, str, str | None]:
    """Update an existing application with new code from a ZIP file.

    Supports both Dockerfile and docker-compose.yml updates.

    Args:
        app_id: ID of the existing application to update
        app_path: Path to extracted application files
        new_zip_filename: Original filename of the uploaded ZIP
        traefik_network: Traefik network name (optional)

    Returns:
        A tuple: (success flag, container id or error message, image tag when available)
    """
    # Get existing app info to determine deployment type
    from database import get_app_by_id

    app_record = get_app_by_id(app_id)
    if not app_record:
        return False, "Application not found", None

    deployment_type = dict(app_record).get("deployment_type", "dockerfile")

    if deployment_type == "docker-compose":
        return update_docker_compose_application(
            app_id, app_path, new_zip_filename, traefik_network
        )
    # Original Dockerfile update logic
    try:
        # Get existing app info
        from database import (
            get_app_by_id,
            update_app_container_info,
            update_app_status,
        )

        app_record = get_app_by_id(app_id)
        if not app_record:
            return False, "Application not found", None

        app_name = app_record["app_name"]
        public_route = app_record["public_route"]
        old_container_id = app_record["container_id"]
        old_image_tag = app_record["image_tag"]
        internal_port = app_record["internal_port"]
        bool(app_record["is_public"])

        # Update status to indicate update in progress
        update_app_status(app_id, "updating")

        client = docker.from_env()
        network_name = traefik_network or os.environ.get(
            "TRAEFIK_NETWORK", "milkcrate-traefik"
        )

        # Stop and remove old container
        try:
            old_container = client.containers.get(old_container_id)
            try:
                old_container.stop(timeout=10)
            except Exception:
                # Container might already be stopped
                pass
            try:
                old_container.remove(force=True)
            except Exception:
                # Best effort cleanup
                pass
        except docker.errors.NotFound:  # type: ignore[attr-defined]
            # Container doesn't exist, that's fine
            pass

        # Build new image with timestamp
        new_image_tag = (
            f"milkcrate-{app_name.lower()}:{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        try:
            client.images.build(path=app_path, tag=new_image_tag, rm=True, pull=True)
        except Exception as build_error:
            update_app_status(app_id, "error")
            return False, f"Image build failed: {build_error!s}", None

        # Clean up old image (best effort, don't fail update if this fails)
        try:
            if old_image_tag:
                client.images.remove(image=old_image_tag, force=True, noprune=False)
        except Exception:
            # Don't fail the update if old image cleanup fails
            pass

        # Detect internal port from new image (reuse logic from deploy_application)
        try:
            image_obj = client.images.get(new_image_tag)
            exposed = (image_obj.attrs or {}).get("Config", {}).get(
                "ExposedPorts", {}
            ) or {}
            if exposed:
                preferred = [p for p in exposed if p.endswith("/tcp")]
                ports_numeric: list[int] = []
                for key in preferred:
                    try:
                        port_num = int(key.split("/")[0])
                        ports_numeric.append(port_num)
                    except Exception:
                        continue
                if 8000 in ports_numeric:
                    internal_port = 8000
                elif ports_numeric:
                    internal_port = min(ports_numeric)
        except Exception:
            # Keep existing internal port if detection fails
            pass

        # Ensure network exists before deploying
        try:
            client.networks.get(network_name)
        except docker.errors.NotFound:  # type: ignore[attr-defined]
            # Network doesn't exist, create it
            try:
                client.networks.create(network_name, driver="bridge")
            except Exception as network_error:
                update_app_status(app_id, "error")
                return (
                    False,
                    f"Failed to create network '{network_name}': {network_error!s}",
                    None,
                )

        # Start new container with same configuration
        container_name = f"app-{app_name.lower().replace('-', '_')}"

        # Calculate priority based on route path length - longer paths get higher priority
        # This ensures /test2 gets higher priority than /test
        route_priority = (
            100 + len(public_route.strip("/").split("/")) * 10 + len(public_route)
        )

        # Security and resource policies for containers
        security_policies = {
            # Resource limits
            "mem_limit": "512m",  # 512MB memory limit
            "memswap_limit": "512m",  # Same as memory (no swap)
            "cpu_period": 100000,  # 100ms period
            "cpu_quota": 50000,  # 50% of CPU
            "pids_limit": 100,  # Limit number of processes
            # Security policies
            "read_only": False,  # Keep writable for app functionality
            "cap_drop": ["ALL"],  # Drop all capabilities
            "cap_add": ["NET_BIND_SERVICE"],  # Only allow binding to ports
            "security_opt": [
                "no-new-privileges:true",  # Prevent privilege escalation
                "apparmor:unconfined",  # Use default AppArmor profile
            ],
            "user": "nobody:nogroup",  # Run as non-root user when possible
            # Filesystem security
            "tmpfs": {
                "/tmp": "rw,noexec,nosuid,size=100m",  # Secure tmp directory
            },
            # Logging configuration
            "log_config": {
                "type": "json-file",
                "config": {"max-size": "10m", "max-file": "3"},
            },
        }

        # Generate Traefik labels with HTTPS support if enabled
        traefik_labels = _generate_traefik_labels(
            app_name=app_name,
            public_route=public_route,
            internal_port=internal_port,
            route_priority=route_priority,
            enable_https=_is_https_enabled(),
        )

        new_container = client.containers.run(
            new_image_tag,
            detach=True,
            name=container_name,
            network=network_name,  # Connect to named network
            labels=traefik_labels,
            **security_policies,
        )

        # Update database record with new container and image info
        update_app_container_info(app_id, new_container.id, new_image_tag)

        # Try to enhance with status checking, but don't fail update if it doesn't work
        try:
            # Set initial status to deploying
            update_app_status(app_id, "deploying")

            # Wait for container to start and become healthy
            import time

            time.sleep(5)

            # Try to update to actual container status
            try:
                from services.status_manager import get_status_manager

                status_manager = get_status_manager()
                status_info = status_manager.get_comprehensive_status(
                    container_id=new_container.id,
                    app_name=app_name,
                    public_route=public_route,
                    internal_port=internal_port,
                )

                update_app_status(app_id, status_info["status"])
            except Exception:
                # If status checking fails, fallback to basic "running" status
                update_app_status(app_id, "running")
        except Exception:
            # If any status management fails, update still succeeds
            pass

        return True, new_container.id, new_image_tag

    except Exception as e:
        with contextlib.suppress(Exception):
            update_app_status(app_id, "error")
        return False, str(e), None
