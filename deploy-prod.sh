#!/usr/bin/env bash
# deploy-prod.sh - One-command production deployment script for ApplyLens
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="infra/.env"
SECRETS_DIR="infra/secrets"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         ApplyLens Production Stack Deployment             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

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

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Docker and Docker Compose found"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f "infra/.env.example" ]; then
        cp infra/.env.example "$ENV_FILE"
        print_success "Created $ENV_FILE from template"
        print_warning "Please edit $ENV_FILE with your production values before continuing!"
        read -p "Press Enter when ready to continue..."
    else
        print_error "Template file infra/.env.example not found!"
        exit 1
    fi
fi

# Check for required secrets
print_status "Checking for required secrets..."
if [ ! -d "$SECRETS_DIR" ]; then
    mkdir -p "$SECRETS_DIR"
    print_success "Created secrets directory"
fi

if [ ! -f "$SECRETS_DIR/google.json" ]; then
    print_warning "Google OAuth credentials not found at $SECRETS_DIR/google.json"
    print_warning "Gmail integration will not work without this file."
    print_warning "Download from Google Cloud Console and save to $SECRETS_DIR/google.json"
fi

# Ask for deployment mode
echo ""
print_status "Select deployment mode:"
echo "  1) Fresh deployment (stop existing, remove volumes, start fresh)"
echo "  2) Update deployment (rebuild and restart services, keep data)"
echo "  3) Quick restart (restart services only, no rebuild)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        print_warning "This will DELETE ALL EXISTING DATA!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            print_error "Deployment cancelled"
            exit 0
        fi
        
        print_status "Stopping existing services..."
        docker-compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
        print_success "Stopped and removed volumes"
        
        print_status "Building images..."
        docker-compose -f "$COMPOSE_FILE" build --no-cache
        print_success "Built images"
        
        print_status "Starting services..."
        docker-compose -f "$COMPOSE_FILE" up -d
        print_success "Services started"
        
        FRESH_DEPLOY=true
        ;;
    2)
        print_status "Stopping services..."
        docker-compose -f "$COMPOSE_FILE" down
        print_success "Stopped services"
        
        print_status "Rebuilding images..."
        docker-compose -f "$COMPOSE_FILE" build
        print_success "Rebuilt images"
        
        print_status "Starting services..."
        docker-compose -f "$COMPOSE_FILE" up -d
        print_success "Services started"
        
        FRESH_DEPLOY=false
        ;;
    3)
        print_status "Restarting services..."
        docker-compose -f "$COMPOSE_FILE" restart
        print_success "Services restarted"
        
        FRESH_DEPLOY=false
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Wait for services to be ready
echo ""
print_status "Waiting for services to be ready..."
sleep 5

# Check service health
print_status "Checking service health..."
HEALTHY=true

check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            print_success "$service is healthy"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_error "$service failed to become healthy"
    HEALTHY=false
    return 1
}

check_service "Database" "http://localhost:5432" || true
check_service "Elasticsearch" "http://localhost:9200/_cluster/health"
check_service "API" "http://localhost:8003/healthz"
check_service "Frontend" "http://localhost:5175/"
check_service "Kibana" "http://localhost:5601/api/status"
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"

# Run migrations if fresh deployment
if [ "$FRESH_DEPLOY" = true ]; then
    echo ""
    print_status "Running database migrations..."
    if docker-compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head; then
        print_success "Migrations completed"
    else
        print_error "Migration failed"
        HEALTHY=false
    fi
fi

# Display status
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Deployment Summary                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$HEALTHY" = true ]; then
    print_success "All services are healthy!"
else
    print_warning "Some services may have issues. Check logs with:"
    echo "  docker-compose -f $COMPOSE_FILE logs -f"
fi

echo ""
print_status "Service URLs:"
echo "  🌐 Frontend:      http://localhost:5175"
echo "  🔧 API:           http://localhost:8003"
echo "  📊 API Docs:      http://localhost:8003/docs"
echo "  🔍 Elasticsearch: http://localhost:9200"
echo "  📈 Kibana:        http://localhost:5601"
echo "  📉 Prometheus:    http://localhost:9090"
echo "  📊 Grafana:       http://localhost:3000"
echo "  🔀 Nginx:         http://localhost:80"

echo ""
print_status "Useful commands:"
echo "  📋 View logs:     docker-compose -f $COMPOSE_FILE logs -f"
echo "  🔄 Restart:       docker-compose -f $COMPOSE_FILE restart"
echo "  ⏹️  Stop:          docker-compose -f $COMPOSE_FILE down"
echo "  💾 Backup DB:     docker-compose -f $COMPOSE_FILE exec db pg_dump -U postgres applylens > backup.sql"

echo ""
print_status "Documentation:"
echo "  📖 Deployment guide: PRODUCTION_DEPLOYMENT.md"
echo "  🎤 Demo guide:       README.md (Judge Demo section)"

echo ""
if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            ✓ Deployment completed successfully!           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║        ⚠ Deployment completed with warnings               ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
fi

echo ""
