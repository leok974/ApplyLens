#!/bin/bash
# Production Deployment Script for ApplyLens
# Uses docker-compose.prod.yml with Cloudflare in front
# Domain: applylens.app

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║     ApplyLens Production Deployment (Cloudflare)          ║"
echo "║                                                            ║"
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

# =============================================================================
# Step 1: Pre-deployment checks
# =============================================================================
echo ""
print_status "Running pre-deployment checks..."

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    print_error "docker-compose.prod.yml not found! Are you in the right directory?"
    exit 1
fi

if [ ! -f "services/api/Dockerfile.prod" ]; then
    print_error "services/api/Dockerfile.prod not found!"
    exit 1
fi

if [ ! -f "apps/web/Dockerfile.prod" ]; then
    print_error "apps/web/Dockerfile.prod not found!"
    exit 1
fi

if [ ! -f "apps/web/nginx.conf" ]; then
    print_error "apps/web/nginx.conf not found!"
    exit 1
fi

print_success "All required files present"

# Check Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed!"
    exit 1
fi

print_success "Docker $(docker --version | cut -d' ' -f3) found"
print_success "Docker Compose $(docker compose version | grep -oP 'v\d+\.\d+\.\d+' || echo 'found')"

# Validate docker-compose.prod.yml
print_status "Validating docker-compose.prod.yml..."
if docker compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
    print_success "docker-compose.prod.yml is valid"
else
    print_error "docker-compose.prod.yml has syntax errors!"
    docker compose -f docker-compose.prod.yml config
    exit 1
fi

# =============================================================================
# Step 2: Pull latest code
# =============================================================================
echo ""
print_status "Pulling latest code from GitHub..."

# Check if we're on a git repository
if [ -d ".git" ]; then
    git fetch --all
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    print_status "Current branch: $CURRENT_BRANCH"
    
    # Pull with rebase
    if git pull --rebase; then
        print_success "Code updated successfully"
        CURRENT_COMMIT=$(git rev-parse --short HEAD)
        print_status "Current commit: $CURRENT_COMMIT"
    else
        print_error "Failed to pull latest code!"
        exit 1
    fi
else
    print_warning "Not a git repository, skipping pull"
fi

# =============================================================================
# Step 3: Build production images
# =============================================================================
echo ""
print_status "Building production Docker images..."
print_warning "This may take several minutes..."

export IMAGE_TAG="${IMAGE_TAG:-latest}"

if docker compose -f docker-compose.prod.yml build api web; then
    print_success "Production images built successfully"
else
    print_error "Failed to build production images!"
    exit 1
fi

# =============================================================================
# Step 4: Stop old containers (if any)
# =============================================================================
echo ""
print_status "Stopping old containers (if any)..."

if docker compose -f docker-compose.prod.yml ps --quiet | grep -q .; then
    print_warning "Stopping existing containers..."
    docker compose -f docker-compose.prod.yml stop
    print_success "Old containers stopped"
else
    print_status "No running containers to stop"
fi

# =============================================================================
# Step 5: Start the production stack
# =============================================================================
echo ""
print_status "Starting production stack..."
print_status "Services: db, es, kibana, api, web, nginx, prometheus, grafana"

if docker compose -f docker-compose.prod.yml up -d; then
    print_success "Production stack started"
else
    print_error "Failed to start production stack!"
    print_status "Checking logs..."
    docker compose -f docker-compose.prod.yml logs --tail=50
    exit 1
fi

# =============================================================================
# Step 6: Wait for services to be ready
# =============================================================================
echo ""
print_status "Waiting for services to be ready..."

sleep 10

# Check database
print_status "Checking database..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres &> /dev/null; then
        print_success "Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Database failed to start!"
        exit 1
    fi
    sleep 2
done

# Check API
print_status "Checking API..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T api curl -sf http://localhost:8003/healthz &> /dev/null; then
        print_success "API is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "API health check timed out (may still be starting)"
    fi
    sleep 2
done

# =============================================================================
# Step 7: Run database migrations
# =============================================================================
echo ""
print_status "Running database migrations..."

if docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head; then
    print_success "Database migrations completed"
else
    print_error "Database migrations failed!"
    docker compose -f docker-compose.prod.yml logs api --tail=100
    exit 1
fi

# =============================================================================
# Step 8: Health checks
# =============================================================================
echo ""
print_status "Running health checks..."

# Check nginx
print_status "Checking nginx..."
if curl -fsSL http://localhost/ > /dev/null 2>&1; then
    print_success "Nginx is responding"
else
    print_warning "Nginx not responding on http://localhost/"
fi

# Check API through nginx
print_status "Checking API health endpoint..."
if curl -fsSL http://localhost/health > /dev/null 2>&1; then
    print_success "API health endpoint responding"
else
    print_warning "API health endpoint not responding"
fi

# =============================================================================
# Step 9: Display service status
# =============================================================================
echo ""
print_status "Service Status:"
docker compose -f docker-compose.prod.yml ps

# =============================================================================
# Step 10: Display Cloudflare instructions
# =============================================================================
echo ""
echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Deployment Complete!                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${GREEN}✓ Production stack is running${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo ""
echo "1. Verify Cloudflare Tunnel routes to nginx:"
echo "   ${CYAN}cloudflared tunnel list${NC}"
echo "   ${CYAN}cloudflared tunnel route dns <TUNNEL_NAME> applylens.app${NC}"
echo ""
echo "2. Expected mapping:"
echo "   ${BLUE}applylens.app → Cloudflare Tunnel → nginx:80${NC}"
echo ""
echo "3. Test the deployment:"
echo "   ${CYAN}curl -I https://applylens.app/${NC}"
echo "   ${CYAN}curl -I https://applylens.app/docs/${NC}"
echo ""
echo "4. Monitor logs:"
echo "   ${CYAN}docker compose -f docker-compose.prod.yml logs -f${NC}"
echo ""
echo -e "${YELLOW}🌐 Service URLs (internal):${NC}"
echo "   Nginx:        http://localhost:80"
echo "   API:          http://localhost:8003"
echo "   Web:          http://localhost:5175"
echo "   Database:     localhost:5432"
echo "   Elasticsearch: http://localhost:9200"
echo "   Kibana:       http://localhost:5601"
echo "   Prometheus:   http://localhost:9090"
echo "   Grafana:      http://localhost:3000"
echo ""
echo -e "${YELLOW}🌐 Public URLs (via Cloudflare):${NC}"
echo "   Frontend:     https://applylens.app/web/"
echo "   API:          https://applylens.app/"
echo "   API Docs:     https://applylens.app/docs/"
echo ""
echo -e "${YELLOW}📊 Management Commands:${NC}"
echo "   View logs:    ${CYAN}docker compose -f docker-compose.prod.yml logs -f${NC}"
echo "   Restart:      ${CYAN}docker compose -f docker-compose.prod.yml restart${NC}"
echo "   Stop:         ${CYAN}docker compose -f docker-compose.prod.yml stop${NC}"
echo "   Status:       ${CYAN}docker compose -f docker-compose.prod.yml ps${NC}"
echo ""
echo -e "${GREEN}Deployment completed successfully! 🚀${NC}"
echo ""
