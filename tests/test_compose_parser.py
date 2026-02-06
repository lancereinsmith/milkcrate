"""Tests for docker-compose parsing functionality."""

import os
import tempfile

from services.compose_parser import (
    extract_service_port,
    get_compose_services_info,
    get_main_service,
    parse_docker_compose,
    validate_compose_for_milkcrate,
)


def test_parse_docker_compose_valid():
    """Test parsing a valid docker-compose.yml file."""
    compose_content = """
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(compose_content)
        compose_path = f.name

    try:
        is_valid, error_msg, compose_data = parse_docker_compose(compose_path)

        assert is_valid
        assert error_msg == ""
        assert compose_data is not None
        assert "services" in compose_data
        assert "app" in compose_data["services"]
    finally:
        os.unlink(compose_path)


def test_parse_docker_compose_invalid_yaml():
    """Test parsing an invalid YAML file."""
    compose_content = """
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
  db:
    image: postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=test
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # Invalid YAML - unclosed string
    command: "echo 'hello world
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(compose_content)
        compose_path = f.name

    try:
        is_valid, error_msg, compose_data = parse_docker_compose(compose_path)

        assert not is_valid
        assert "Invalid YAML format" in error_msg
        assert compose_data is None
    finally:
        os.unlink(compose_path)


def test_parse_docker_compose_missing_services():
    """Test parsing a compose file without services section."""
    compose_content = """
version: "3.8"
networks:
  default:
    driver: bridge
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(compose_content)
        compose_path = f.name

    try:
        is_valid, error_msg, compose_data = parse_docker_compose(compose_path)

        assert not is_valid
        assert "must contain a 'services' section" in error_msg
        assert compose_data is None
    finally:
        os.unlink(compose_path)


def test_get_main_service_first_service():
    """Test getting the first service as main service."""
    compose_data = {"services": {"app": {"build": "."}, "db": {"image": "postgres:13"}}}

    service_name, service_config = get_main_service(compose_data)

    assert service_name == "app"
    assert service_config == {"build": "."}


def test_get_main_service_with_label():
    """Test getting service with milkcrate.main_service label."""
    compose_data = {
        "services": {
            "app": {"build": "."},
            "api": {"build": "./api", "labels": {"milkcrate.main_service": "true"}},
        }
    }

    service_name, service_config = get_main_service(compose_data)

    assert service_name == "api"
    assert service_config["build"] == "./api"


def test_extract_service_port_from_ports():
    """Test extracting port from ports mapping."""
    service_config = {"ports": ["8000:8000"]}

    port = extract_service_port(service_config)
    assert port == 8000


def test_extract_service_port_from_expose():
    """Test extracting port from expose directive."""
    service_config = {"expose": ["8000"]}

    port = extract_service_port(service_config)
    assert port == 8000


def test_extract_service_port_default():
    """Test default port when no port information is available."""
    service_config = {}

    port = extract_service_port(service_config)
    assert port == 8000


def test_validate_compose_for_milkcrate_valid():
    """Test validation of a valid compose file for milkcrate."""
    compose_data = {"services": {"app": {"build": ".", "ports": ["8000:8000"]}}}

    is_valid, error_msg = validate_compose_for_milkcrate(compose_data)

    assert is_valid
    assert error_msg == ""


def test_validate_compose_for_milkcrate_no_services():
    """Test validation of compose file with no services."""
    compose_data = {"services": {}}

    is_valid, error_msg = validate_compose_for_milkcrate(compose_data)

    assert not is_valid
    assert "No services defined" in error_msg


def test_validate_compose_for_milkcrate_no_build_or_image():
    """Test validation of compose file with no build or image."""
    compose_data = {"services": {"app": {"ports": ["8000:8000"]}}}

    is_valid, error_msg = validate_compose_for_milkcrate(compose_data)

    assert not is_valid
    assert "must have either 'build' or 'image' defined" in error_msg


def test_validate_compose_for_milkcrate_no_ports():
    """Test validation of compose file with no port exposure."""
    compose_data = {"services": {"app": {"build": "."}}}

    is_valid, error_msg = validate_compose_for_milkcrate(compose_data)

    assert not is_valid
    assert "must expose at least one port" in error_msg


def test_get_compose_services_info():
    """Test getting comprehensive compose services information."""
    compose_data = {
        "services": {
            "app": {"build": ".", "ports": ["8000:8000"]},
            "db": {"image": "postgres:13"},
        }
    }

    info = get_compose_services_info(compose_data)

    assert info["main_service"] == "app"
    assert info["internal_port"] == 8000
    assert info["total_services"] == 2
    assert "app" in info["service_names"]
    assert "db" in info["service_names"]
