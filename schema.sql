-- Database schema for milkcrate
-- This file contains the SQL statements to create the initial database tables

DROP TABLE IF EXISTS deployed_apps;
CREATE TABLE deployed_apps (
    app_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT NOT NULL,
    container_id TEXT NOT NULL,
    image_tag TEXT NOT NULL,
    public_route TEXT NOT NULL,
    internal_port INTEGER NOT NULL,
    is_public INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    deployment_date TEXT NOT NULL DEFAULT (datetime('now')),
    deployment_type TEXT NOT NULL DEFAULT 'dockerfile',
    compose_file TEXT,
    main_service TEXT,
    volume_mounts TEXT
);

-- Create an index on container_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_container_id ON deployed_apps(container_id);

-- Create an index on internal_port to prevent conflicts
CREATE INDEX IF NOT EXISTS idx_internal_port ON deployed_apps(internal_port);

-- Create an index on deployment_type for filtering
CREATE INDEX IF NOT EXISTS idx_deployment_type ON deployed_apps(deployment_type);

-- Create an index on public_route for faster lookups
CREATE INDEX IF NOT EXISTS idx_public_route ON deployed_apps(public_route);

-- Settings table for storing configuration options
DROP TABLE IF EXISTS settings;
CREATE TABLE settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    updated_date TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Insert default setting for default home route
INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES ('default_home_route', '');

-- Volumes table for managing Docker volumes with file uploads
DROP TABLE IF EXISTS volumes;
CREATE TABLE volumes (
    volume_id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_name TEXT NOT NULL UNIQUE,
    docker_volume_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_date TEXT NOT NULL DEFAULT (datetime('now')),
    file_count INTEGER NOT NULL DEFAULT 0,
    total_size_bytes INTEGER NOT NULL DEFAULT 0
);

-- Create an index on volume_name for faster lookups
CREATE INDEX IF NOT EXISTS idx_volume_name ON volumes(volume_name);

-- Volume files table to track uploaded files
DROP TABLE IF EXISTS volume_files;
CREATE TABLE volume_files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    uploaded_date TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (volume_id) REFERENCES volumes(volume_id) ON DELETE CASCADE
);

-- Create an index on volume_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_volume_files_volume_id ON volume_files(volume_id);
