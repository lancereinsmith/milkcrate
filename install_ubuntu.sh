#!/bin/bash
set -e

# milkcrate Ubuntu Installation Script
# Installs milkcrate container orchestration platform on Ubuntu

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/milkcrate"
SERVICE_USER="milkcrate"
DEFAULT_DOMAIN="localhost"
DEFAULT_ADMIN_PASSWORD="admin"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check Ubuntu version
check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release; then
        print_error "This script is designed for Ubuntu. Detected: $(lsb_release -d | cut -f2)"
        exit 1
    fi
    
    local version=$(lsb_release -rs)
    local major_version=$(echo $version | cut -d. -f1)
    
    if [[ $major_version -lt 20 ]]; then
        print_error "Ubuntu 20.04 or later required. Detected: $version"
        exit 1
    fi
    
    print_success "Ubuntu $version detected"
}

# Function to update system packages
update_system() {
    print_status "Updating system packages..."
    
    # First attempt to update - if it fails, try to fix broken repositories
    if ! apt-get update 2>/dev/null; then
        print_warning "Package list update failed, attempting to fix broken repositories..."
        
        # Remove any problematic deadsnakes PPA entries
        find /etc/apt/sources.list.d/ -name "*deadsnakes*" -delete 2>/dev/null || true
        
        # Try update again
        if ! apt-get update; then
            print_error "Failed to update package lists even after cleanup"
            exit 1
        fi
        
        print_success "Fixed broken repositories and updated package lists"
    else
        print_success "Package lists updated successfully"
    fi
    
    # Upgrade system packages
    print_status "Upgrading system packages..."
    apt-get upgrade -y
    print_success "System packages updated"
}

# Function to install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Install basic dependencies
    apt-get install -y \
        curl \
        wget \
        git \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        build-essential \
        python3-dev \
        python3-pip \
        python3-venv
    
    print_success "System dependencies installed"
}

# Function to install Python 3.12+
install_python312() {
    print_status "Installing Python 3.12 or newer..."
    
    # Check if Python 3.12+ is already installed
    if command -v python3.12 &> /dev/null; then
        print_success "Python 3.12 already installed"
        return
    fi
    
    # Check if Python 3.13+ is available (Ubuntu 25.04+)
    if command -v python3.13 &> /dev/null; then
        print_success "Python 3.13 already available"
        # Make Python 3.13 the default python3
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1
        return
    fi
    
    # Check default python3 version
    if command -v python3 &> /dev/null; then
        local py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        local py_major=$(echo $py_version | cut -d. -f1)
        local py_minor=$(echo $py_version | cut -d. -f2)
        
        if [[ $py_major -eq 3 && $py_minor -ge 12 ]]; then
            print_success "Python $py_version already available (sufficient for milkcrate)"
            return
        fi
    fi
    
    # Try to install from default repositories first
    print_status "Trying to install Python 3.12 from default repositories..."
    if apt-get install -y python3.12 python3.12-venv python3.12-dev &> /dev/null; then
        print_success "Python 3.12 installed from default repositories"
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
        return
    fi
    
    # Get Ubuntu version to determine if deadsnakes PPA is needed
    local version=$(lsb_release -rs)
    local major_version=$(echo $version | cut -d. -f1)
    local minor_version=$(echo $version | cut -d. -f2)
    
    # Only try deadsnakes PPA for Ubuntu versions that are likely to be supported
    if [[ $major_version -lt 25 || ($major_version -eq 22 && $minor_version -eq 4) || ($major_version -eq 24 && $minor_version -eq 4) ]]; then
        print_status "Trying deadsnakes PPA for Python 3.12..."
        
        # Add deadsnakes PPA for Python 3.12
        if add-apt-repository ppa:deadsnakes/ppa -y; then
            apt-get update
            
            # Install Python 3.12
            if apt-get install -y python3.12 python3.12-venv python3.12-dev; then
                # Make Python 3.12 the default python3
                update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
                print_success "Python 3.12 installed from deadsnakes PPA"
                return
            else
                print_warning "Failed to install Python 3.12 from deadsnakes PPA"
            fi
        else
            print_warning "Failed to add deadsnakes PPA"
        fi
    else
        print_warning "Deadsnakes PPA likely not supported for Ubuntu $version"
    fi
    
    # Final fallback - check if any suitable Python version is available
    if command -v python3 &> /dev/null; then
        local py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        local py_major=$(echo $py_version | cut -d. -f1)
        local py_minor=$(echo $py_version | cut -d. -f2)
        
        if [[ $py_major -eq 3 && $py_minor -ge 12 ]]; then
            print_warning "Using Python $py_version (minimum Python 3.12 required)"
            print_status "Installing additional Python packages..."
            apt-get install -y python3-venv python3-dev python3-pip
            return
        fi
    fi
    
    print_error "Could not install suitable Python version (3.12+ required for milkcrate)"
    exit 1
}

# Function to install Docker
install_docker() {
    print_status "Installing Docker..."
    
    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        print_success "Docker already installed"
        return
    fi
    
    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc || true
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    print_success "Docker installed and started"
}

# Function to install uv (Python package manager)
install_uv() {
    print_status "Installing uv..."
    
    # Check if uv is already available system-wide
    if command -v uv &> /dev/null; then
        print_success "uv already installed"
        return
    fi
    
    # Install uv for root user
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Copy uv to system-wide location from the correct path
    if [[ -f ~/.local/bin/uv ]]; then
        cp ~/.local/bin/uv /usr/local/bin/uv
        chmod +x /usr/local/bin/uv
        print_success "uv installed to /usr/local/bin/"
    elif [[ -f ~/.cargo/bin/uv ]]; then
        cp ~/.cargo/bin/uv /usr/local/bin/uv
        chmod +x /usr/local/bin/uv
        print_success "uv installed to /usr/local/bin/ (from cargo)"
    else
        # Try to find uv in common locations
        if find $HOME -name "uv" -type f -executable 2>/dev/null | head -1 | xargs -I {} cp {} /usr/local/bin/uv; then
            chmod +x /usr/local/bin/uv
            print_success "uv found and installed to /usr/local/bin/"
        else
            print_warning "Could not find uv binary after installation, but continuing..."
        fi
    fi
    
    # Verify installation
    if command -v uv &> /dev/null; then
        print_success "uv is now available system-wide"
    else
        print_error "uv installation failed"
        exit 1
    fi
}

# Function to create service user
create_service_user() {
    print_status "Creating service user: $SERVICE_USER"
    
    if id "$SERVICE_USER" &>/dev/null; then
        print_success "User $SERVICE_USER already exists"
    else
        useradd --system --home $INSTALL_DIR --shell /bin/bash --comment "milkcrate service user" $SERVICE_USER
        print_success "User $SERVICE_USER created"
    fi
    
    # Add service user to docker group
    usermod -aG docker $SERVICE_USER
    print_success "User $SERVICE_USER added to docker group"
}

# Function to set up application directory
setup_application() {
    print_status "Setting up application in $INSTALL_DIR..."
    
    # Create install directory
    mkdir -p $INSTALL_DIR
    
    # If we're running from the milkcrate directory, copy files
    if [[ -f "app.py" && -f "docker-compose.yml" && -d "milkcrate_core" ]]; then
        print_status "Copying application files from current directory..."
        # Copy files, excluding unnecessary directories
        # Use rsync if available for better control, otherwise cp
        if command -v rsync &> /dev/null; then
            rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' --exclude='site' --exclude='.DS_Store' . $INSTALL_DIR/
        else
            # Fallback to cp - exclude patterns won't work, but basic copy will
            cp -r . $INSTALL_DIR/ 2>/dev/null || {
                print_warning "Some files may not have copied correctly. Continuing..."
            }
        fi
    else
        print_status "Current directory doesn't contain milkcrate. Please ensure you run this script from the milkcrate directory or manually copy files to $INSTALL_DIR"
        exit 1
    fi
    
    # Create necessary directories
    mkdir -p $INSTALL_DIR/{uploads,extracted_apps,instance,logs}
    
    # Set up acme.json for Traefik SSL
    touch $INSTALL_DIR/acme.json
    chmod 600 $INSTALL_DIR/acme.json
    
    # Set ownership
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    
    print_success "Application directory set up"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Verify Python version before proceeding
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not available. Please install Python 3.12+ first."
        exit 1
    fi
    
    local py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    local py_major=$(echo $py_version | cut -d. -f1)
    local py_minor=$(echo $py_version | cut -d. -f2)
    
    if [[ $py_major -lt 3 ]] || [[ $py_major -eq 3 && $py_minor -lt 12 ]]; then
        print_error "Python 3.12+ required. Found Python $py_version"
        exit 1
    fi
    
    cd $INSTALL_DIR
    
    # Install using uv as the service user
    sudo -u $SERVICE_USER uv sync
    
    print_success "Python dependencies installed"
}

# Function to initialize database
initialize_database() {
    print_status "Initializing database..."
    
    cd $INSTALL_DIR
    
    # Initialize database as service user
    sudo -u $SERVICE_USER uv run python3 -c "
from milkcrate_core import create_app
app = create_app()
app.app_context().push()
from database import init_db
init_db()
print('Database initialized successfully')
"
    
    print_success "Database initialized"
}

# Function to configure environment
configure_environment() {
    print_status "Configuring environment..."
    
    # Create environment file
    cat > $INSTALL_DIR/.env << EOF
# milkcrate Environment Configuration
MILKCRATE_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
MILKCRATE_ADMIN_PASSWORD=$DEFAULT_ADMIN_PASSWORD
TRAEFIK_NETWORK=milkcrate-traefik

# Optional configurations
# DEFAULT_HOME_ROUTE=/my-app
# MAX_CONTENT_LENGTH=16777216
EOF
    
    # Set ownership and permissions
    chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/.env
    chmod 600 $INSTALL_DIR/.env
    
    print_success "Environment configured"
}

# Function to install systemd service
install_systemd_service() {
    print_status "Installing systemd service..."
    
    # Copy service file
    cp $INSTALL_DIR/_server/milkcrate.service /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable milkcrate.service
    
    print_success "Systemd service installed and enabled"
}

# Function to configure nginx as optional front proxy (advanced use case)
configure_nginx_optional() {
    echo
    print_status "════════════════════════════════════════════════════════════"
    print_status "OPTIONAL: Nginx Front Proxy (NOT RECOMMENDED)"
    print_status "════════════════════════════════════════════════════════════"
    echo
    print_warning "DISCLAIMER: This is NOT recommended for most users."
    echo
    echo "By default, Traefik handles all routing on port 80. This is simpler"
    echo "and works perfectly for most use cases."
    echo
    echo "Only add nginx if you need to run OTHER websites (non-milkcrate apps)"
    echo "on this server alongside milkcrate."
    echo
    echo "You can add nginx later using: sudo ./install_nginx.sh"
    echo
    print_status "Do you want to install nginx as a front proxy? [y/N]"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Installing nginx as front proxy..."
        
        # Install nginx
        apt-get install -y nginx
        
        # Modify docker-compose.yml to move Traefik to port 8081
        print_status "Configuring Traefik to use port 8081..."
        sed -i 's/"80:80"/"8081:80"/' $INSTALL_DIR/docker-compose.yml
        
        # Create nginx configuration
        cat > /etc/nginx/sites-available/milkcrate << 'EOF'
# Nginx configuration for milkcrate with multi-website support
# milkcrate apps are proxied through Traefik on port 8081

server {
    listen 80;
    server_name _;  # Accept any hostname

    # Increase buffer sizes to handle large headers
    client_header_buffer_size 8k;
    large_client_header_buffers 8 32k;
    proxy_buffer_size 16k;
    proxy_buffers 8 16k;
    proxy_busy_buffers_size 32k;

    # All traffic proxies to Traefik on port 8081
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }
}

# Add additional server blocks here for other websites
# Example:
# server {
#     listen 80;
#     server_name blog.yourdomain.com;
#     location / {
#         proxy_pass http://127.0.0.1:3000;
#         proxy_set_header Host $host;
#     }
# }
EOF
        
        # Enable site
        ln -sf /etc/nginx/sites-available/milkcrate /etc/nginx/sites-enabled/
        
        # Remove default site
        rm -f /etc/nginx/sites-enabled/default
        
        # Test nginx configuration
        if nginx -t; then
            # Start and enable nginx
            systemctl enable nginx
            systemctl start nginx
            print_success "Nginx configured and started on port 80"
            print_success "Traefik moved to port 8081"
            print_status "Edit /etc/nginx/sites-available/milkcrate to add other websites"
        else
            print_error "Nginx configuration test failed"
            exit 1
        fi
    else
        print_status "Skipping nginx installation (recommended)"
        print_status "Traefik will handle all routing on port 80"
    fi
}

# Function to start services
start_services() {
    print_status "Starting milkcrate services..."
    
    # Start the service
    systemctl start milkcrate.service
    
    # Check status
    sleep 5
    if systemctl is-active --quiet milkcrate.service; then
        print_success "milkcrate service started successfully"
    else
        print_error "Failed to start milkcrate service"
        systemctl status milkcrate.service
        exit 1
    fi
}

# Function to setup firewall
setup_firewall() {
    print_status "Do you want to configure UFW firewall? [y/N]"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Configuring UFW firewall..."
        
        # Install ufw if not present
        apt-get install -y ufw
        
        # Allow SSH
        ufw allow ssh
        
        # Allow HTTP and HTTPS
        ufw allow 80/tcp
        ufw allow 443/tcp
        
        # Allow milkcrate admin port (optional, only if accessing directly)
        # ufw allow 5001/tcp
        
        # Allow Traefik dashboard (optional, for debugging)
        # ufw allow 8080/tcp
        
        # Enable firewall
        ufw --force enable
        
        print_success "UFW firewall configured"
    else
        print_status "Skipping firewall configuration"
    fi
}

# Function to display final information
display_final_info() {
    print_success "milkcrate installation completed!"
    echo
    echo "==================================="
    echo "Installation Summary:"
    echo "==================================="
    echo "Installation directory: $INSTALL_DIR"
    echo "Service user: $SERVICE_USER"
    echo "Default admin password: $DEFAULT_ADMIN_PASSWORD (password-only, no username required)"
    echo
    echo "Services:"
    echo "- milkcrate web interface: http://localhost (or http://your-domain)"
    echo "- milkcrate direct access: http://localhost:5001 (bypasses Traefik)"
    echo "- Traefik dashboard: http://localhost:8080"
    echo
    echo "Commands:"
    echo "- Start: sudo systemctl start milkcrate"
    echo "- Stop: sudo systemctl stop milkcrate"
    echo "- Status: sudo systemctl status milkcrate"
    echo "- Logs: sudo journalctl -u milkcrate -f"
    echo "- Container logs: sudo docker compose -f $INSTALL_DIR/docker-compose.yml logs -f"
    echo
    echo "Configuration:"
    echo "- Environment: $INSTALL_DIR/.env"
    echo "- Edit and restart service after changes"
    echo
    print_warning "IMPORTANT:"
    echo "1. Change the default admin password after first login"
    echo "2. Update SECRET_KEY in $INSTALL_DIR/.env for production use"
    echo "3. Configure your domain name in docker-compose.yml if needed"
    echo "4. The service will start automatically on boot"
    echo "5. All routing is handled by Traefik on port 80"
    echo "6. Access admin interface at http://your-domain/admin"
}

# Main installation function
main() {
    echo "============================================"
    echo "milkcrate Ubuntu Installation Script"
    echo "============================================"
    echo
    
    # Get domain name (for documentation purposes, configured in docker-compose.yml)
    print_status "Enter your domain name (default: $DEFAULT_DOMAIN):"
    print_status "(This is for reference only. Update docker-compose.yml for production domains.)"
    read -r domain_input
    DOMAIN=${domain_input:-$DEFAULT_DOMAIN}
    
    # Get admin password
    print_status "Enter admin password (default: $DEFAULT_ADMIN_PASSWORD):"
    read -r -s password_input
    ADMIN_PASSWORD=${password_input:-$DEFAULT_ADMIN_PASSWORD}
    DEFAULT_ADMIN_PASSWORD=$ADMIN_PASSWORD
    echo
    
    # Run installation steps
    check_root
    check_ubuntu
    update_system
    install_dependencies  # Includes python3-dev, python3-pip, python3-venv
    install_python312     # Ensure Python 3.12+ is available (required for milkcrate)
    # Note: Ubuntu 25.04 comes with Python 3.13, which meets milkcrate's >=3.12 requirement
    # uv will handle virtual environment and dependency management automatically
    install_docker
    install_uv
    create_service_user
    setup_application
    install_python_dependencies
    initialize_database
    configure_environment
    install_systemd_service
    configure_nginx_optional
    setup_firewall
    start_services
    display_final_info
    
    print_success "Installation completed successfully!"
}

# Run main function
main "$@"
