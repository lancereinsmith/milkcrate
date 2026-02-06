"""Tests for docker-compose deployment functionality."""

import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

from services.deploy import detect_deployment_type, extract_zip_safely


def test_detect_deployment_type_dockerfile():
    """Test detection of Dockerfile deployment type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a Dockerfile
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write("FROM python:3.12-slim\n")

        deployment_type = detect_deployment_type(temp_dir)
        assert deployment_type == "dockerfile"


def test_detect_deployment_type_compose():
    """Test detection of docker-compose deployment type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a docker-compose.yml
        compose_path = os.path.join(temp_dir, "docker-compose.yml")
        with open(compose_path, "w") as f:
            f.write("services:\n  app:\n    build: .\n")

        deployment_type = detect_deployment_type(temp_dir)
        assert deployment_type == "docker-compose"


def test_detect_deployment_type_compose_priority():
    """Test that docker-compose.yml takes priority over Dockerfile."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create both files
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write("FROM python:3.12-slim\n")

        compose_path = os.path.join(temp_dir, "docker-compose.yml")
        with open(compose_path, "w") as f:
            f.write("services:\n  app:\n    build: .\n")

        deployment_type = detect_deployment_type(temp_dir)
        assert deployment_type == "docker-compose"


def test_detect_deployment_type_neither():
    """Test detection when neither file exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        deployment_type = detect_deployment_type(temp_dir)
        assert deployment_type == "dockerfile"  # Default fallback


def test_extract_zip_safely_with_dockerfile():
    """Test extracting ZIP with Dockerfile."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a ZIP with Dockerfile and Python file
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("Dockerfile", "FROM python:3.12-slim\n")
            zf.writestr("app.py", "print('hello')\n")

        extract_path = os.path.join(temp_dir, "extracted")
        result = extract_zip_safely(zip_path, extract_path)

        assert result is True
        assert os.path.exists(os.path.join(extract_path, "Dockerfile"))
        assert os.path.exists(os.path.join(extract_path, "app.py"))


def test_extract_zip_safely_with_compose():
    """Test extracting ZIP with docker-compose.yml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a ZIP with docker-compose.yml and Python file
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("docker-compose.yml", "services:\n  app:\n    build: .\n")
            zf.writestr("app.py", "print('hello')\n")

        extract_path = os.path.join(temp_dir, "extracted")
        result = extract_zip_safely(zip_path, extract_path)

        assert result is True
        assert os.path.exists(os.path.join(extract_path, "docker-compose.yml"))
        assert os.path.exists(os.path.join(extract_path, "app.py"))


def test_extract_zip_safely_with_both():
    """Test extracting ZIP with both Dockerfile and docker-compose.yml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a ZIP with both files
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("Dockerfile", "FROM python:3.12-slim\n")
            zf.writestr("docker-compose.yml", "services:\n  app:\n    build: .\n")
            zf.writestr("app.py", "print('hello')\n")

        extract_path = os.path.join(temp_dir, "extracted")
        result = extract_zip_safely(zip_path, extract_path)

        assert result is True
        assert os.path.exists(os.path.join(extract_path, "Dockerfile"))
        assert os.path.exists(os.path.join(extract_path, "docker-compose.yml"))
        assert os.path.exists(os.path.join(extract_path, "app.py"))


def test_extract_zip_safely_neither():
    """Test extracting ZIP with neither Dockerfile nor docker-compose.yml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a ZIP with only Python file
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("app.py", "print('hello')\n")

        extract_path = os.path.join(temp_dir, "extracted")
        result = extract_zip_safely(zip_path, extract_path)

        assert result is False


def test_extract_zip_safely_no_python():
    """Test extracting ZIP with Dockerfile but no Python file - should now pass."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a ZIP with only Dockerfile
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("Dockerfile", "FROM python:3.12-slim\n")

        extract_path = os.path.join(temp_dir, "extracted")
        result = extract_zip_safely(zip_path, extract_path)

        # Should now pass since we removed Python restrictions
        assert result is True


def test_extract_zip_safely_path_traversal():
    """Test that path traversal is prevented."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a ZIP with path traversal
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../Dockerfile", "FROM python:3.12-slim\n")
            zf.writestr("app.py", "print('hello')\n")

        extract_path = os.path.join(temp_dir, "extracted")
        result = extract_zip_safely(zip_path, extract_path)

        assert result is False


@patch("services.deploy.deploy_docker_compose")
def test_deploy_application_detects_compose(mock_deploy_compose):
    """Test that deploy_application detects and calls docker-compose deployment."""
    from services.deploy import deploy_application

    mock_deploy_compose.return_value = (True, "container123", "image:tag")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create docker-compose.yml
        compose_path = os.path.join(temp_dir, "docker-compose.yml")
        with open(compose_path, "w") as f:
            f.write("services:\n  app:\n    build: .\n")

        result = deploy_application(temp_dir, "test-app", "/test", is_public=False)

        assert result == (True, "container123", "image:tag")
        mock_deploy_compose.assert_called_once_with(
            temp_dir, "test-app", "/test", None, False, None
        )


@patch("services.deploy.docker")
def test_deploy_application_falls_back_to_dockerfile(mock_docker):
    """Test that deploy_application falls back to Dockerfile deployment."""
    from services.deploy import deploy_application

    # Mock Docker client
    mock_client = MagicMock()
    mock_docker.from_env.return_value = mock_client

    # Mock container
    mock_container = MagicMock()
    mock_container.id = "container123"
    mock_client.containers.run.return_value = mock_container

    # Mock image
    mock_image = MagicMock()
    mock_image.attrs = {"Config": {"ExposedPorts": {"8000/tcp": {}}}}
    mock_client.images.get.return_value = mock_image

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create Dockerfile
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write("FROM python:3.12-slim\n")

        with patch("database.insert_app") as mock_insert:
            result = deploy_application(temp_dir, "test-app", "/test", is_public=False)

            assert result[0] is True  # Success
            assert result[1] == "container123"  # Container ID
            mock_insert.assert_called_once()
