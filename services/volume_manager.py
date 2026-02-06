"""Volume management service for Docker volumes and file uploads.

Provides functionality to create, manage, and upload files to Docker volumes.
"""

import os
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path

import docker
from docker.errors import APIError, NotFound


class VolumeManager:
    """Manager for Docker volumes and file operations."""

    def __init__(self) -> None:
        """Initialize the volume manager with Docker client."""
        self.client = docker.from_env()

    def create_volume(
        self, volume_name: str, description: str | None = None
    ) -> tuple[bool, str, str | None]:
        """Create a new Docker volume.

        Args:
            volume_name: Name for the volume (user-friendly)
            description: Optional description of the volume

        Returns:
            Tuple of (success, message, docker_volume_name)
        """
        try:
            # Create Docker-safe volume name
            docker_volume_name = (
                f"milkcrate-vol-{volume_name.lower().replace('_', '-')}"
            )

            # Check if volume already exists
            try:
                self.client.volumes.get(docker_volume_name)
                return False, f"Volume {docker_volume_name} already exists", None
            except NotFound:
                pass

            # Create the volume
            volume = self.client.volumes.create(
                name=docker_volume_name,
                driver="local",
                labels={
                    "milkcrate.managed": "true",
                    "milkcrate.volume_name": volume_name,
                },
            )

            return (
                True,
                f"Volume {docker_volume_name} created successfully",
                volume.name,
            )

        except APIError as e:
            return False, f"Docker API error: {e!s}", None
        except Exception as e:
            return False, f"Error creating volume: {e!s}", None

    def delete_volume(self, docker_volume_name: str) -> tuple[bool, str]:
        """Delete a Docker volume.

        Args:
            docker_volume_name: Docker volume name to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            volume = self.client.volumes.get(docker_volume_name)
            volume.remove(force=False)
            return True, f"Volume {docker_volume_name} deleted successfully"
        except NotFound:
            return False, f"Volume {docker_volume_name} not found"
        except APIError as e:
            return False, f"Docker API error: {e!s}"
        except Exception as e:
            return False, f"Error deleting volume: {e!s}"

    def upload_file_to_volume(
        self, docker_volume_name: str, file_path: str, destination_path: str = "/"
    ) -> tuple[bool, str]:
        """Upload a file to a Docker volume.

        Args:
            docker_volume_name: Docker volume name
            file_path: Path to the file to upload
            destination_path: Destination path within the volume

        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify volume exists
            self.client.volumes.get(docker_volume_name)

            # Create a temporary container to mount the volume and copy files
            container_name = f"milkcrate-vol-upload-{os.urandom(4).hex()}"

            # Use a minimal Alpine image for file operations
            container = self.client.containers.create(
                image="alpine:latest",
                name=container_name,
                volumes={docker_volume_name: {"bind": "/volume", "mode": "rw"}},
                command="sleep 5",
            )

            try:
                # Start the container
                container.start()

                # Prepare the file for copying
                file_name = os.path.basename(file_path)
                tar_path = self._create_tar_archive(file_path)

                try:
                    # Copy file to container
                    with open(tar_path, "rb") as tar_file:
                        container.put_archive(
                            path=f"/volume{destination_path}", data=tar_file
                        )

                    return True, f"File {file_name} uploaded successfully"
                finally:
                    # Clean up tar file
                    if os.path.exists(tar_path):
                        os.remove(tar_path)

            finally:
                # Clean up container
                try:
                    container.stop(timeout=1)
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        except NotFound:
            return False, f"Volume {docker_volume_name} not found"
        except APIError as e:
            return False, f"Docker API error: {e!s}"
        except Exception as e:
            return False, f"Error uploading file: {e!s}"

    def upload_zip_to_volume(
        self, docker_volume_name: str, zip_path: str, destination_path: str = "/"
    ) -> tuple[bool, str, int]:
        """Extract and upload a ZIP file to a Docker volume.

        Args:
            docker_volume_name: Docker volume name
            zip_path: Path to the ZIP file
            destination_path: Destination path within the volume

        Returns:
            Tuple of (success, message, file_count)
        """
        try:
            # Verify volume exists
            self.client.volumes.get(docker_volume_name)

            # Extract ZIP to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        # Security check: prevent path traversal
                        for member in zip_ref.namelist():
                            if ".." in member or member.startswith("/"):
                                return (
                                    False,
                                    f"Invalid ZIP file: path traversal detected in {member}",
                                    0,
                                )
                        zip_ref.extractall(temp_dir)
                except zipfile.BadZipFile:
                    return False, "Invalid ZIP file", 0

                # Count files
                file_count = sum(1 for _ in Path(temp_dir).rglob("*") if _.is_file())

                # Create a temporary container to mount the volume and copy files
                container_name = f"milkcrate-vol-upload-{os.urandom(4).hex()}"

                container = self.client.containers.create(
                    image="alpine:latest",
                    name=container_name,
                    volumes={docker_volume_name: {"bind": "/volume", "mode": "rw"}},
                    command="sleep 5",
                )

                try:
                    # Start the container
                    container.start()

                    # Create tar archive of extracted files
                    tar_path = self._create_tar_archive(temp_dir)

                    try:
                        # Copy files to container
                        with open(tar_path, "rb") as tar_file:
                            container.put_archive(
                                path=f"/volume{destination_path}", data=tar_file
                            )

                        return (
                            True,
                            f"ZIP extracted successfully ({file_count} files)",
                            file_count,
                        )
                    finally:
                        # Clean up tar file
                        if os.path.exists(tar_path):
                            os.remove(tar_path)

                finally:
                    # Clean up container
                    try:
                        container.stop(timeout=1)
                    except Exception:
                        pass
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

        except NotFound:
            return False, f"Volume {docker_volume_name} not found", 0
        except APIError as e:
            return False, f"Docker API error: {e!s}", 0
        except Exception as e:
            return False, f"Error uploading ZIP: {e!s}", 0

    def list_volume_files(
        self, docker_volume_name: str, path: str = "/"
    ) -> tuple[bool, str, list[dict]]:
        """List files in a Docker volume.

        Args:
            docker_volume_name: Docker volume name
            path: Path within the volume to list

        Returns:
            Tuple of (success, message, files_list)
        """
        try:
            # Verify volume exists
            self.client.volumes.get(docker_volume_name)

            # Create a temporary container to mount the volume and list files
            container_name = f"milkcrate-vol-list-{os.urandom(4).hex()}"

            # Don't use remove=True, we'll manage cleanup manually
            container = self.client.containers.create(
                image="alpine:latest",
                name=container_name,
                volumes={docker_volume_name: {"bind": "/volume", "mode": "ro"}},
                command=f"find /volume{path} -type f -exec stat -c '%n|%s' {{}} \\;",
            )

            try:
                # Start the container
                container.start()

                # Wait for container to finish
                result = container.wait(timeout=10)

                if result["StatusCode"] != 0:
                    return False, "Failed to list files", []

                # Get output before removing container
                logs = container.logs(stdout=True, stderr=False).decode("utf-8")

                files = []
                for line in logs.strip().split("\n"):
                    if line:
                        parts = line.split("|")
                        if len(parts) == 2:
                            file_path, file_size = parts
                            # Remove /volume prefix
                            file_path = file_path.replace("/volume", "", 1)
                            files.append(
                                {
                                    "path": file_path,
                                    "name": os.path.basename(file_path),
                                    "size": int(file_size),
                                }
                            )

                return True, f"Found {len(files)} files", files

            except Exception as e:
                return False, f"Error listing files: {e!s}", []
            finally:
                # Clean up container
                try:
                    container.remove(force=True)
                except Exception:
                    # Ignore errors during cleanup
                    pass

        except NotFound:
            return False, f"Volume {docker_volume_name} not found", []
        except APIError as e:
            return False, f"Docker API error: {e!s}", []
        except Exception as e:
            return False, f"Error listing files: {e!s}", []

    def get_volume_size(self, docker_volume_name: str) -> tuple[bool, str, int]:
        """Get the total size of files in a volume.

        Args:
            docker_volume_name: Docker volume name

        Returns:
            Tuple of (success, message, size_bytes)
        """
        success, message, files = self.list_volume_files(docker_volume_name)
        if not success:
            return False, message, 0

        total_size = sum(f["size"] for f in files)
        return True, f"Volume size: {total_size} bytes", total_size

    def _create_tar_archive(self, path: str) -> str:
        """Create a tar archive from a file or directory.

        Args:
            path: Path to file or directory

        Returns:
            Path to created tar archive
        """
        import tarfile

        fd, tar_path = tempfile.mkstemp(suffix=".tar")
        os.close(fd)
        with tarfile.open(tar_path, "w") as tar:
            if os.path.isfile(path):
                tar.add(path, arcname=os.path.basename(path))
            else:
                # Add directory contents
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    tar.add(item_path, arcname=item)

        return tar_path


@lru_cache(maxsize=1)
def get_volume_manager() -> VolumeManager:
    """Get or create the volume manager singleton.

    Returns:
        VolumeManager instance
    """
    return VolumeManager()
