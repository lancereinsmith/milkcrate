import os

REQUIRED_FILES = [
    "app.py",
    "database.py",
    "schema.sql",
    "templates/base.html",
    "templates/index.html",
    "templates/login.html",
    "templates/admin_dashboard.html",
    "templates/upload.html",
    "static/style.css",
    "static/app.js",
]

REQUIRED_DIRS = [
    "templates",
    "static",
    "uploads",
    "extracted_apps",
    "sample_app",
]


def test_required_files_exist():
    all_good = True
    missing = []
    for path in REQUIRED_FILES:
        if not os.path.exists(path):
            all_good = False
            missing.append(path)
    assert all_good, f"Missing files: {missing}"


def test_required_dirs_exist():
    all_good = True
    missing = []
    for path in REQUIRED_DIRS:
        if not os.path.isdir(path):
            all_good = False
            missing.append(path)
    assert all_good, f"Missing directories: {missing}"
