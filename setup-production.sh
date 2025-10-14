#!/bin/bash
# Quick Start Production Deployment for applylens.app
# This script sets up the production environment step by step

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   ApplyLens Production Setup - applylens.app               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print status messages
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run as root. Run as regular user with sudo access."
    exit 1
fi

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================
echo ""
print_status "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/engine/install/"
    exit 1
fi
print_success "Docker found: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi
print_success "Docker Compose found: $(docker-compose --version)"

# Check if user can run docker without sudo
if ! docker ps &> /dev/null; then
    print_error "Cannot run docker commands. Please add your user to docker group:"
    echo "  sudo usermod -aG docker $USER"
    echo "  Then log out and log back in."
    exit 1
fi
print_success "Docker permissions OK"

# =============================================================================
# Step 2: Setup Environment Configuration
# =============================================================================
echo ""
print_status "Setting up environment configuration..."

ENV_FILE="infra/.env.prod"

if [ -f "$ENV_FILE" ]; then
    print_warning "Environment file already exists: $ENV_FILE"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Using existing $ENV_FILE"
    else
        cp infra/.env.prod.example $ENV_FILE
        print_success "Created new $ENV_FILE from template"
    fi
else
    cp infra/.env.prod.example $ENV_FILE
    print_success "Created $ENV_FILE from template"
fi

# =============================================================================
# Step 3: Generate Secure Secrets
# =============================================================================
echo ""
print_status "Generating secure secrets..."

OAUTH_SECRET=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -base64 32)
SESSION_SECRET=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 24)
GRAFANA_PASSWORD=$(openssl rand -base64 16)

print_success "Generated secrets"

# =============================================================================
# Step 4: Configure Environment Variables
# =============================================================================
echo ""
print_warning "You need to configure the following in $ENV_FILE:"
echo ""
echo "1. Database Password (POSTGRES_PASSWORD)"
echo "   Generated: $DB_PASSWORD"
echo ""
echo "2. OAuth State Secret (OAUTH_STATE_SECRET)"
echo "   Generated: $OAUTH_SECRET"
echo ""
echo "3. Secret Keys (SECRET_KEY, SESSION_SECRET)"
echo "   SECRET_KEY: $SECRET_KEY"
echo "   SESSION_SECRET: $SESSION_SECRET"
echo ""
echo "4. Grafana Admin Password (GRAFANA_ADMIN_PASSWORD)"
echo "   Generated: $GRAFANA_PASSWORD"
echo ""
echo "5. Google OAuth Credentials (from Google Cloud Console)"
echo "   GOOGLE_CLIENT_ID: your-client-id.apps.googleusercontent.com"
echo "   GOOGLE_CLIENT_SECRET: your-client-secret"
echo ""

read -p "Press Enter to open the environment file in nano..."
nano $ENV_FILE

# =============================================================================
# Step 5: SSL Certificate Setup
# =============================================================================
echo ""
print_status "Checking SSL certificates..."

SSL_DIR="infra/nginx/ssl"
mkdir -p $SSL_DIR

if [ ! -f "$SSL_DIR/fullchain.pem" ] || [ ! -f "$SSL_DIR/privkey.pem" ]; then
    print_warning "SSL certificates not found in $SSL_DIR"
    echo ""
    echo "Options:"
    echo "1. Use Let's Encrypt (Recommended)"
    echo "2. Use existing certificates"
    echo "3. Skip SSL setup (test only)"
    echo ""
    read -p "Choose option (1/2/3): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            print_status "Setting up Let's Encrypt..."
            read -p "Enter your email address: " EMAIL
            read -p "Enter your domain (applylens.app): " DOMAIN
            DOMAIN=${DOMAIN:-applylens.app}
            
            # Stop nginx if running
            docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
            
            # Install certbot if not present
            if ! command -v certbot &> /dev/null; then
                print_status "Installing certbot..."
                sudo apt update
                sudo apt install -y certbot
            fi
            
            # Obtain certificate
            sudo certbot certonly --standalone \
                -d $DOMAIN \
                -d www.$DOMAIN \
                --email $EMAIL \
                --agree-tos \
                --non-interactive
            
            # Copy certificates
            sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $SSL_DIR/
            sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $SSL_DIR/
            sudo chown -R $USER:$USER $SSL_DIR
            chmod 600 $SSL_DIR/privkey.pem
            
            print_success "SSL certificates installed"
            ;;
        2)
            print_status "Please copy your SSL certificates to:"
            echo "  $SSL_DIR/fullchain.pem"
            echo "  $SSL_DIR/privkey.pem"
            read -p "Press Enter when certificates are in place..."
            ;;
        3)
            print_warning "Skipping SSL setup. Only use this for testing!"
            ;;
    esac
else
    print_success "SSL certificates found"
fi

# =============================================================================
# Step 6: Setup Google OAuth Secrets
# =============================================================================
echo ""
print_status "Checking Google OAuth credentials..."

SECRETS_DIR="infra/secrets"
mkdir -p $SECRETS_DIR

if [ ! -f "$SECRETS_DIR/google.json" ]; then
    print_warning "Google OAuth credentials not found"
    echo "Please download your OAuth credentials JSON from:"
    echo "https://console.cloud.google.com/apis/credentials"
    echo ""
    echo "Save it to: $SECRETS_DIR/google.json"
    echo ""
    read -p "Press Enter when ready..."
    
    if [ ! -f "$SECRETS_DIR/google.json" ]; then
        print_error "Google credentials still not found. Please add them before starting."
    fi
else
    print_success "Google OAuth credentials found"
fi

# =============================================================================
# Step 7: Setup Basic Auth for Monitoring Tools
# =============================================================================
echo ""
print_status "Setting up basic auth for monitoring tools..."

HTPASSWD_FILE="infra/nginx/.htpasswd"

if [ ! -f "$HTPASSWD_FILE" ]; then
    if command -v htpasswd &> /dev/null; then
        read -p "Enter username for monitoring access: " MONITOR_USER
        MONITOR_USER=${MONITOR_USER:-admin}
        htpasswd -c $HTPASSWD_FILE $MONITOR_USER
        print_success "Created basic auth credentials"
    else
        print_warning "htpasswd not found. Install with: sudo apt install apache2-utils"
        print_warning "Then create $HTPASSWD_FILE manually"
    fi
else
    print_success "Basic auth file already exists"
fi

# =============================================================================
# Step 8: Build Docker Images
# =============================================================================
echo ""
print_status "Building Docker images..."

docker-compose -f docker-compose.prod.yml build --no-cache

print_success "Docker images built"

# =============================================================================
# Step 9: Start Services
# =============================================================================
echo ""
print_status "Starting services..."

docker-compose -f docker-compose.prod.yml up -d

print_success "Services started"

# =============================================================================
# Step 10: Run Database Migrations
# =============================================================================
echo ""
print_status "Running database migrations..."

sleep 10  # Wait for database to be ready

docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head

print_success "Database migrations complete"

# =============================================================================
# Step 11: Health Check
# =============================================================================
echo ""
print_status "Performing health checks..."

sleep 5

# Check database
if docker-compose -f docker-compose.prod.yml exec -T db pg_isready &> /dev/null; then
    print_success "Database: Healthy"
else
    print_error "Database: Unhealthy"
fi

# Check API
if curl -sf http://localhost:8003/healthz &> /dev/null; then
    print_success "API: Healthy"
else
    print_warning "API: Not responding (may still be starting)"
fi

# Check Web
if curl -sf http://localhost:5175 &> /dev/null; then
    print_success "Web: Healthy"
else
    print_warning "Web: Not responding (may still be starting)"
fi

# =============================================================================
# Final Summary
# =============================================================================
echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Production Setup Complete!                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "🌐 Service URLs:"
echo "   Frontend:     https://applylens.app/web/"
echo "   API:          https://applylens.app/"
echo "   API Docs:     https://applylens.app/docs/"
echo ""
echo "📊 Monitoring (Basic Auth Required):"
echo "   Grafana:      https://applylens.app/grafana/"
echo "   Kibana:       https://applylens.app/kibana/"
echo "   Prometheus:   https://applylens.app/prometheus/"
echo ""
echo "🔧 Management Commands:"
echo "   View logs:    docker-compose -f docker-compose.prod.yml logs -f"
echo "   Stop:         docker-compose -f docker-compose.prod.yml stop"
echo "   Restart:      docker-compose -f docker-compose.prod.yml restart"
echo "   Status:       docker-compose -f docker-compose.prod.yml ps"
echo ""
echo "📚 Documentation:"
echo "   Setup Guide:  PRODUCTION_DOMAIN_SETUP.md"
echo "   Deployment:   PRODUCTION_DEPLOYMENT.md"
echo ""

print_warning "Important Next Steps:"
echo "1. Verify DNS points to this server: applylens.app"
echo "2. Update Google OAuth redirect URIs to include:"
echo "   https://applylens.app/auth/google/callback"
echo "3. Test the application at https://applylens.app/web/"
echo "4. Setup automated backups (see PRODUCTION_DOMAIN_SETUP.md)"
echo "5. Configure monitoring alerts"
echo ""

print_status "Setup complete! 🎉"
