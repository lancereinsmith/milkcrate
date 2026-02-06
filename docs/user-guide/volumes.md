# Volume Management

Milkcrate provides built-in Docker volume management to store and share persistent data across your containerized applications.

## Overview

Volumes are persistent storage for Docker containers that:

- Persist data even when containers are stopped or deleted and can thus store configuration files, databases, assets, and more
- Can be shared across multiple containers
- Support file uploads via drag-and-drop interface

## Creating a Volume

1. Navigate to the Admin Dashboard
2. Click **Manage Volumes** button
3. Click **Create Volume**
4. Enter:
    - **Volume Name**: A unique identifier (alphanumeric, hyphens, underscores)
    - **Description**: Optional description of the volume's purpose

The system will create a Docker volume with the name `milkcrate-vol-{volume_name}`.

## Uploading Files to a Volume

Once a volume is created, you can upload files to it:

### Using the Web Interface

1. Navigate to **Manage Volumes**
2. Click on a volume to view its details
3. Use the **drag-and-drop** upload area to upload files:
    - Drag files directly onto the upload zone
    - Or click to browse and select files
4. Click **Upload File** to complete the upload

### Supported Upload Types

- **Individual files**: Upload any file type
- **ZIP archives**: Automatically extracted into the volume

## Mounting Volumes to Containers

When deploying an application, you can mount volumes to make their contents accessible to your containers:

### During Deployment

1. Navigate to **Deploy New App**
2. Fill in application details (name, route)
3. In the **Mount Volumes** section:
    - Check the volumes you want to mount
    - Specify the mount path (e.g., `/data`, `/config`)
4. Upload your application ZIP
5. Click **Deploy Application**

### Volume Mount Example

If you have a volume named `app-config` containing configuration files, you can:

1. Create the volume
2. Upload `config.json` to the volume
3. When deploying your app, mount the volume to `/config`
4. Your application can access the file at `/config/config.json`

## Managing Volumes

### Viewing Volume Contents

1. Navigate to **Manage Volumes**
2. Click on a volume name
3. View the list of files with their sizes and paths

### Deleting a Volume

1. Navigate to **Manage Volumes**
2. Click the **Delete** (trash) icon for the volume
3. Confirm the deletion

> **Warning**: Deleting a volume permanently removes all files. Ensure no running containers are using the volume.

## Use Cases

### Configuration Files

Store application configuration that doesn't change with deployments:

```text
volumes/app-config/
├── database.json
├── api-keys.json
└── settings.yaml
```

### Shared Data

Share data between multiple containers:

- Upload shared libraries
- Store common assets
- Maintain shared databases

### Persistent Storage

Store data that must persist across container restarts:

- User uploads
- SQLite databases
- Log files
- Cache data

## Technical Details

### Docker Volume Naming

Milkcrate creates volumes with the prefix `milkcrate-vol-` followed by your volume name:

- Volume name: `my-data`
- Docker volume: `milkcrate-vol-my-data`

### Volume Permissions

Files in volumes are accessible by containers with read-write permissions (`rw` mode).

### File Upload Implementation

Milkcrate uses temporary Alpine containers to copy files into volumes:

1. A temporary container is created with the volume mounted
2. Files are copied via Docker's `put_archive` API
3. The temporary container is removed

## Best Practices

1. **Organize volumes by purpose**: Create separate volumes for configs, data, and logs
2. **Document mount paths**: Use consistent paths like `/data`, `/config`, `/logs`
3. **Use descriptive names**: Name volumes based on their content (e.g., `postgres-data`, `nginx-config`)

## Troubleshooting

### Upload Fails

- Check available disk space
- Verify ZIP files are not corrupted
- Ensure the volume exists in Docker (`docker volume ls`)

### Container Can't Access Volume

- Verify the volume is mounted during deployment
- Check the mount path in your application code
- Ensure the container has proper permissions
- Verify the container name (may have `milkcrate-vol` prefix)

### Volume Not Listed

- Refresh the volumes page
- Check if the volume exists: `docker volume ls | grep milkcrate-vol`

## API Reference

Volumes can also be managed via the API endpoints:

- `GET /admin/volumes/api/list` - List all volumes

## Next Steps

- Learn about [Routing](routing.md)
