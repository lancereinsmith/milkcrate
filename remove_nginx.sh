#!/bin/bash
set -e

# Remove Nginx Front Proxy and Restore Traefik-Only Configuration
# This script removes nginx and reverts milkcrate to use Traefik directly on port 80

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

# Function to show confirmation
confirm_removal() {
    echo
    print_warning "════════════════════════════════════════════════════════════"
    print_warning "Remove Nginx and Restore Traefik-Only Setup"
    print_warning "════════════════════════════════════════════════════════════"
    echo
    echo "This script will:"
    echo "  1. Stop and disable nginx"
    echo "  2. Move Traefik back from port 8081 to port 80"
    echo "  3. Restart milkcrate services"
    echo
    print_warning "Note: This will NOT uninstall nginx, just disable it"
    print_warning "Other nginx sites will be preserved"
    echo
    print_status "Do you want to continue? [y/N]"
    read -r response
    
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Operation cancelled"
        exit 0
    fi
}

# Function to backup configuration
backup_configuration() {
    print_status "Backing up current configuration..."
    
    local backup_dir="$INSTALL_DIR/backup-remove-nginx-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    cp "$INSTALL_DIR/docker-compose.yml" "$backup_dir/"
    
    if [[ -f "/etc/nginx/sites-available/milkcrate" ]]; then
        cp /etc/nginx/sites-available/milkcrate "$backup_dir/"
    fi
    
    print_success "Backup created at $backup_dir"
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    if systemctl is-active --quiet milkcrate; then
        systemctl stop milkcrate
        print_success "milkcrate stopped"
    fi
    
    if systemctl is-active --quiet nginx; then
        systemctl stop nginx
        print_success "nginx stopped"
    fi
}

# Function to modify docker-compose.yml
restore_traefik_port() {
    print_status "Restoring Traefik to port 80..."
    
    # Check if Traefik is on port 8081
    if ! grep -q '"8081:80"' "$INSTALL_DIR/docker-compose.yml"; then
        print_warning "Traefik is not on port 8081, may already be on port 80"
        return
    fi
    
    # Replace "8081:80" with "80:80"
    sed -i 's/"8081:80"/"80:80"/' "$INSTALL_DIR/docker-compose.yml"
    
    # Verify the change
    if grep -q '"80:80"' "$INSTALL_DIR/docker-compose.yml"; then
        print_success "Traefik restored to port 80"
    else
        print_error "Failed to update docker-compose.yml"
        exit 1
    fi
}

# Function to disable nginx milkcrate site
disable_nginx_site() {
    print_status "Disabling nginx milkcrate site..."
    
    if [[ -L "/etc/nginx/sites-enabled/milkcrate" ]]; then
        rm -f /etc/nginx/sites-enabled/milkcrate
        print_success "Nginx milkcrate site disabled"
    else
        print_status "Nginx milkcrate site not found"
    fi
    
    # Optionally disable nginx service
    print_status "Do you want to completely disable nginx? [y/N]"
    print_status "(Choose 'N' if you have other websites using nginx)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        systemctl disable nginx
        print_success "Nginx service disabled"
    else
        print_status "Nginx service remains enabled for other sites"
    fi
}

# Function to start milkcrate
start_milkcrate() {
    print_status "Starting milkcrate..."
    
    systemctl start milkcrate
    
    sleep 5
    
    if systemctl is-active --quiet milkcrate; then
        print_success "milkcrate started successfully"
    else
        print_error "Failed to start milkcrate"
        systemctl status milkcrate
        exit 1
    fi
}

# Function to verify setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check Traefik is on port 80
    if lsof -i :80 | grep -q docker; then
        print_success "Traefik is listening on port 80"
    else
        print_warning "Traefik may not be listening on port 80"
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
    print_success "Nginx Removed - Traefik-Only Configuration Restored"
    print_success "════════════════════════════════════════════════════════════"
    echo
    echo "Configuration:"
    echo "  - Traefik: Port 80 (handles all routing)"
    echo "  - milkcrate admin: http://localhost/admin"
    echo
    echo "To access milkcrate:"
    echo "  - http://localhost/admin"
    echo "  - http://your-ip/admin"
    echo "  - http://your-domain/admin"
    echo
    print_status "To add nginx back later:"
    echo "  sudo ./install_nginx.sh"
    echo
}

# Main function
main() {
    echo "════════════════════════════════════════════════════════════"
    echo "Remove Nginx Front Proxy from milkcrate"
    echo "════════════════════════════════════════════════════════════"
    echo
    
    check_root
    confirm_removal
    backup_configuration
    stop_services
    restore_traefik_port
    disable_nginx_site
    start_milkcrate
    verify_setup
    display_final_info
    
    print_success "Removal completed successfully!"
}

# Run main function
main "$@"
