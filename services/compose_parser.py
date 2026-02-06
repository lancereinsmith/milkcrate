"""Docker Compose file parsing and validation utilities."""

from typing import Any

import yaml


def parse_docker_compose(
    compose_path: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Parse and validate a docker-compose.yml file.

    Args:
        compose_path: Path to the docker-compose.yml file

    Returns:
        Tuple of (is_valid, error_message, parsed_data)
    """
    try:
        with open(compose_path, encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, f"Invalid YAML format: {e!s}", None
    except FileNotFoundError:
        return False, "docker-compose.yml file not found", None
    except Exception as e:
        return False, f"Error reading docker-compose.yml: {e!s}", None

    # Validate basic structure
    if not isinstance(compose_data, dict):
        return False, "docker-compose.yml must contain a dictionary", None

    if "services" not in compose_data:
        return False, "docker-compose.yml must contain a 'services' section", None

    services = compose_data["services"]
    if not isinstance(services, dict) or not services:
        return False, "docker-compose.yml must contain at least one service", None

    # Validate each service
    for service_name, service_config in services.items():
        if not isinstance(service_config, dict):
            return False, f"Service '{service_name}' must be a dictionary", None

    return True, "", compose_data


def get_main_service(compose_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Identify the main service from a docker-compose configuration.

    Priority order:
    1. Service with 'milkcrate.main_service=true' label
    2. First service in the file

    Args:
        compose_data: Parsed docker-compose data

    Returns:
        Tuple of (service_name, service_config)
    """
    services = compose_data["services"]

    # First, look for service with milkcrate.main_service label
    for service_name, service_config in services.items():
        labels = service_config.get("labels", {})
        if isinstance(labels, dict) and labels.get("milkcrate.main_service") == "true":
            return service_name, service_config
        if isinstance(labels, list):
            # Handle list format labels
            for label in labels:
                if label == "milkcrate.main_service=true":
                    return service_name, service_config

    # Fallback to first service
    first_service_name = next(iter(services.keys()))
    return first_service_name, services[first_service_name]


def extract_service_port(service_config: dict[str, Any]) -> int:
    """Extract the internal port from a service configuration.

    Args:
        service_config: Service configuration dictionary

    Returns:
        Internal port number (defaults to 8000)
    """
    # Check for ports mapping
    ports = service_config.get("ports", [])
    if ports:
        for port_mapping in ports:
            if isinstance(port_mapping, str):
                # Format: "8000:8000" or "8000"
                parts = port_mapping.split(":")
                if len(parts) >= 2:
                    try:
                        return int(parts[1])
                    except ValueError:
                        continue
                elif len(parts) == 1:
                    try:
                        return int(parts[0])
                    except ValueError:
                        continue
            elif isinstance(port_mapping, dict):
                # Format: {"target": 8000, "published": 8000}
                target_port = port_mapping.get("target")
                if target_port:
                    try:
                        return int(target_port)
                    except ValueError:
                        continue

    # Check for expose directive
    expose = service_config.get("expose", [])
    if expose:
        try:
            return int(expose[0])
        except (ValueError, IndexError):
            pass

    # Default port
    return 8000


def validate_compose_for_milkcrate(compose_data: dict[str, Any]) -> tuple[bool, str]:
    """Validate that a docker-compose configuration is suitable for milkcrate deployment.

    Args:
        compose_data: Parsed docker-compose data

    Returns:
        Tuple of (is_valid, error_message)
    """
    services = compose_data["services"]

    # Check if we have at least one service
    if not services:
        return False, "No services defined in docker-compose.yml"

    # Get main service
    main_service_name, main_service_config = get_main_service(compose_data)

    # Check if main service has a build context or image
    if "build" not in main_service_config and "image" not in main_service_config:
        return (
            False,
            f"Main service '{main_service_name}' must have either 'build' or 'image' defined",
        )

    # Check if main service has port exposure
    ports = main_service_config.get("ports", [])
    expose = main_service_config.get("expose", [])

    if not ports and not expose:
        return (
            False,
            f"Main service '{main_service_name}' must expose at least one port",
        )

    return True, ""


def get_compose_services_info(compose_data: dict[str, Any]) -> dict[str, Any]:
    """Extract useful information from a docker-compose configuration.

    Args:
        compose_data: Parsed docker-compose data

    Returns:
        Dictionary with extracted information
    """
    main_service_name, main_service_config = get_main_service(compose_data)
    internal_port = extract_service_port(main_service_config)

    return {
        "main_service": main_service_name,
        "main_service_config": main_service_config,
        "internal_port": internal_port,
        "total_services": len(compose_data["services"]),
        "service_names": list(compose_data["services"].keys()),
    }
