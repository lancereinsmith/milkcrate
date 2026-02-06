#!/bin/bash
set -e

# Add Nginx Front Proxy to Existing milkcrate Installation
# This script adds nginx as a front proxy to an existing milkcrate installation
# allowing you to run multiple websites on the same server.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/milkcrate"

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

# Function to check if milkcrate is installed
check_milkcrate_installed() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        print_error "milkcrate is not installed at $INSTALL_DIR"
        exit 1
    fi
    
    if [[ ! -f "$INSTALL_DIR/docker-compose.yml" ]]; then
        print_error "docker-compose.yml not found at $INSTALL_DIR"
        exit 1
    fi
    
    print_success "milkcrate installation found"
}

# Function to check if nginx is already installed
check_nginx_status() {
    if systemctl is-active --quiet nginx; then
        print_warning "Nginx is already installed and running"
        print_status "This script will reconfigure it for milkcrate"
        print_status "Existing nginx sites will be preserved"
        echo
    fi
    
    # Check if Traefik is already on port 8081
    if grep -q '"8081:80"' "$INSTALL_DIR/docker-compose.yml"; then
        print_warning "Traefik is already configured for port 8081"
        print_status "It appears nginx may already be configured"
        print_status "Do you want to continue? [y/N]"
        read -r response
        if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            print_status "Exiting..."
            exit 0
        fi
    fi
}

# Function to display disclaimer
show_disclaimer() {
    echo
    print_warning "════════════════════════════════════════════════════════════"
    print_warning "IMPORTANT: Read Before Proceeding"
    print_warning "════════════════════════════════════════════════════════════"
    echo
    echo "This script will:"
    echo "  1. Install nginx (if not already installed)"
    echo "  2. Move Traefik from port 80 to port 8081"
    echo "  3. Configure nginx on port 80 to proxy to Traefik"
    echo "  4. Restart milkcrate services"
    echo
    print_warning "Why you might NOT need this:"
    echo "  - If you only use milkcrate (no other websites), keep the default setup"
    echo "  - The default Traefik-only setup is simpler and easier to maintain"
    echo
    print_status "Why you MIGHT need this:"
    echo "  - You want to run other websites (WordPress, etc.) on this server"
    echo "  - You need nginx-specific features or familiarity"
    echo
    print_status "Do you want to continue? [y/N]"
    read -r response
    
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Installation cancelled"
        exit 0
    fi
}

# Function to backup current configuration
backup_configuration() {
    print_status "Backing up current configuration..."
    
    local backup_dir="$INSTALL_DIR/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    cp "$INSTALL_DIR/docker-compose.yml" "$backup_dir/"
    
    if [[ -f "/etc/nginx/sites-available/milkcrate" ]]; then
        cp /etc/nginx/sites-available/milkcrate "$backup_dir/"
    fi
    
    print_success "Backup created at $backup_dir"
}

# Function to stop services
stop_services() {
    print_status "Stopping milkcrate services..."
    systemctl stop milkcrate
    print_success "Services stopped"
}

# Function to modify docker-compose.yml
modify_docker_compose() {
    print_status "Modifying docker-compose.yml to move Traefik to port 8081..."
    
    # Check if already modified
    if grep -q '"8081:80"' "$INSTALL_DIR/docker-compose.yml"; then
        print_warning "Traefik port already set to 8081, skipping modification"
        return
    fi
    
    # Replace "80:80" with "8081:80" in the Traefik ports section
    sed -i 's/"80:80"/"8081:80"/' "$INSTALL_DIR/docker-compose.yml"
    
    # Verify the change
    if grep -q '"8081:80"' "$INSTALL_DIR/docker-compose.yml"; then
        print_success "docker-compose.yml updated successfully"
    else
        print_error "Failed to update docker-compose.yml"
        print_status "To manually fix, edit $INSTALL_DIR/docker-compose.yml"
        print_status "Change Traefik ports from '80:80' to '8081:80'"
        exit 1
    fi
}

# Function to install and configure nginx
install_nginx() {
    print_status "Installing nginx..."
    
    # Install nginx if not present
    if ! command -v nginx &> /dev/null; then
        apt-get update
        apt-get install -y nginx
        print_success "Nginx installed"
    else
        print_success "Nginx already installed"
    fi
    
    # Create nginx configuration
    print_status "Creating nginx configuration..."
    
    cat > /etc/nginx/sites-available/milkcrate << 'EOF'
# Nginx configuration for milkcrate with multi-website support
# milkcrate apps are proxied through Traefik on port 8081
#
# To add additional websites, add new server blocks below

server {
    listen 80;
    server_name _;  # Accept any hostname (change to specific domain in production)

    # Increase buffer sizes to handle large headers
    client_header_buffer_size 8k;
    large_client_header_buffers 8 32k;
    proxy_buffer_size 16k;
    proxy_buffers 8 16k;
    proxy_busy_buffers_size 32k;

    # All traffic proxies to Traefik on port 8081
    # Traefik routes to milkcrate admin or deployed apps
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

# Example: Additional website #1
# Uncomment and modify for your other websites
#
# server {
#     listen 80;
#     server_name blog.yourdomain.com;
#
#     location / {
#         proxy_pass http://127.0.0.1:3000;  # Your other website's port
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
# }

# Example: Additional website #2
#
# server {
#     listen 80;
#     server_name shop.yourdomain.com;
#
#     location / {
#         proxy_pass http://127.0.0.1:4000;  # Another website's port
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
# }
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/milkcrate /etc/nginx/sites-enabled/
    
    # Remove default site if it exists
    rm -f /etc/nginx/sites-enabled/default
    
    print_success "Nginx configuration created"
}

# Function to test nginx configuration
test_nginx() {
    print_status "Testing nginx configuration..."
    
    if nginx -t; then
        print_success "Nginx configuration is valid"
    else
        print_error "Nginx configuration test failed"
        print_status "Configuration file: /etc/nginx/sites-available/milkcrate"
        exit 1
    fi
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Enable and start nginx
    systemctl enable nginx
    systemctl start nginx
    print_success "Nginx started on port 80"
    
    # Start milkcrate (Traefik will now be on 8081)
    systemctl start milkcrate
    
    # Wait for services to start
    sleep 5
    
    # Check status
    if systemctl is-active --quiet nginx && systemctl is-active --quiet milkcrate; then
        print_success "All services started successfully"
    else
        print_error "Some services failed to start"
        print_status "Check status with:"
        print_status "  sudo systemctl status nginx"
        print_status "  sudo systemctl status milkcrate"
        exit 1
    fi
}

# Function to verify setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check nginx is on port 80
    if lsof -i :80 | grep -q nginx; then
        print_success "Nginx is listening on port 80"
    else
        print_warning "Nginx may not be listening on port 80"
    fi
    
    # Check Traefik is on port 8081
    if lsof -i :8081 | grep -q docker; then
        print_success "Traefik is listening on port 8081"
    else
        print_warning "Traefik may not be listening on port 8081"
    fi
    
    # Test local access
    print_status "Testing local access..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost/admin | grep -q "200\|302"; then
        print_success "Admin interface is accessible"
    else
        print_warning "Admin interface returned unexpected status code"
    fi
}

# Function to display final information
display_final_info() {
    echo
    print_success "════════════════════════════════════════════════════════════"
    print_success "Nginx Front Proxy Successfully Configured!"
    print_success "════════════════════════════════════════════════════════════"
    echo
    echo "Configuration:"
    echo "  - Nginx: Port 80 (front proxy)"
    echo "  - Traefik: Port 8081 (milkcrate apps)"
    echo "  - milkcrate admin: http://localhost/admin"
    echo
    echo "To add additional websites:"
    echo "  1. Edit: sudo nano /etc/nginx/sites-available/milkcrate"
    echo "  2. Add new server blocks (see examples in file)"
    echo "  3. Test: sudo nginx -t"
    echo "  4. Reload: sudo systemctl reload nginx"
    echo
    echo "Configuration files:"
    echo "  - Nginx: /etc/nginx/sites-available/milkcrate"
    echo "  - docker-compose: $INSTALL_DIR/docker-compose.yml"
    echo "  - Backup: $backup_dir"
    echo
    echo "Documentation:"
    echo "  See docs/production/multi-website-setup.md for:"
    echo "  - Adding SSL/HTTPS with Let's Encrypt"
    echo "  - Configuring additional websites"
    echo "  - Troubleshooting tips"
    echo
    print_warning "To remove nginx and revert to Traefik-only:"
    echo "  1. sudo systemctl stop nginx"
    echo "  2. sudo systemctl disable nginx"
    echo "  3. Edit $INSTALL_DIR/docker-compose.yml: change '8081:80' to '80:80'"
    echo "  4. sudo systemctl restart milkcrate"
    echo
}

# Main function
main() {
    echo "════════════════════════════════════════════════════════════"
    echo "Add Nginx Front Proxy to milkcrate"
    echo "════════════════════════════════════════════════════════════"
    echo
    
    check_root
    check_milkcrate_installed
    check_nginx_status
    show_disclaimer
    backup_configuration
    stop_services
    modify_docker_compose
    install_nginx
    test_nginx
    start_services
    verify_setup
    display_final_info
    
    print_success "Setup completed successfully!"
}

# Run main function
main "$@"
