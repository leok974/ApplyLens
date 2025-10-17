#!/bin/bash
# =============================================================================
# ApplyLens Production Stack Builder
# =============================================================================
# This script builds and optionally starts the production stack
#
# Usage:
#   ./build-prod.sh                    # Build only
#   ./build-prod.sh --deploy           # Build and deploy
#   ./build-prod.sh --deploy --restart # Build, deploy and restart all
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="infra/.env.prod"
DEPLOY=false
RESTART=false
MIGRATE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --deploy)
            DEPLOY=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        --migrate)
            MIGRATE=true
            shift
            ;;
        --help|-h)
            cat << EOF

ApplyLens Production Stack Builder

Usage:
  ./build-prod.sh [OPTIONS]

Options:
  --deploy      Build and start the production stack
  --restart     Force restart all services after deployment
  --migrate     Run database migrations after deployment
  --help, -h    Show this help message

Examples:
  ./build-prod.sh                       # Build only
  ./build-prod.sh --deploy              # Build and start
  ./build-prod.sh --deploy --migrate    # Build, start, and migrate
  ./build-prod.sh --deploy --restart    # Build and force restart

Environment:
  Requires: infra/.env.prod with all secrets configured

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# =============================================================================
# Header
# =============================================================================
echo -e "${CYAN}"
echo "====================================================================="
echo "  ApplyLens Production Stack Builder"
echo "====================================================================="
echo -e "${NC}"

# =============================================================================
# Pre-flight Checks
# =============================================================================
echo -e "${YELLOW}[1/5] Pre-flight checks...${NC}"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: $ENV_FILE not found!${NC}"
    echo -e "${RED}   Copy infra/.env.example to infra/.env.prod and configure all secrets${NC}"
    exit 1
fi

echo -e "${GREEN}   ✓ Environment file found: $ENV_FILE${NC}"

# Check for required secrets
REQUIRED_SECRETS=(
    "POSTGRES_PASSWORD"
    "CLOUDFLARED_TUNNEL_TOKEN"
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
)

MISSING_SECRETS=()
for secret in "${REQUIRED_SECRETS[@]}"; do
    if grep -q "${secret}=CHANGE_ME" "$ENV_FILE" || grep -q "${secret}=your-" "$ENV_FILE"; then
        MISSING_SECRETS+=("$secret")
    fi
done

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo -e "${YELLOW}"
    echo "⚠️  WARNING: The following secrets need to be configured:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "   - $secret"
    done
    echo ""
    echo "   Edit $ENV_FILE before deploying to production!"
    echo -e "${NC}"
    
    if [ "$DEPLOY" = true ]; then
        echo -e "${YELLOW}   Continue anyway? (y/N): ${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${RED}   Deployment cancelled.${NC}"
            exit 1
        fi
    fi
fi

# =============================================================================
# Build Images
# =============================================================================
echo -e "${YELLOW}[2/5] Building production images...${NC}"

echo -e "${GRAY}   Command: docker compose -f $COMPOSE_FILE --env-file $ENV_FILE build --no-cache${NC}"

if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache; then
    echo -e "${GREEN}   ✓ Build completed successfully${NC}"
else
    echo -e "${RED}   ❌ Build failed${NC}"
    exit 1
fi

# =============================================================================
# Deployment
# =============================================================================
if [ "$DEPLOY" = true ]; then
    echo -e "${YELLOW}[3/5] Deploying production stack...${NC}"
    
    if [ "$RESTART" = true ]; then
        echo -e "${GRAY}   Stopping existing containers...${NC}"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    fi
    
    echo -e "${GRAY}   Starting services...${NC}"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    echo -e "${GREEN}   ✓ Services started${NC}"
    
    # Wait for services to be ready
    echo -e "${GRAY}   Waiting for services to be healthy...${NC}"
    sleep 10
else
    echo -e "${GRAY}[3/5] Skipping deployment (build only)${NC}"
fi

# =============================================================================
# Database Migrations
# =============================================================================
if [ "$DEPLOY" = true ] && [ "$MIGRATE" = true ]; then
    echo -e "${YELLOW}[4/5] Running database migrations...${NC}"
    
    if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T api alembic upgrade head; then
        echo -e "${GREEN}   ✓ Migrations completed${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Warning: Migrations failed${NC}"
        echo -e "${YELLOW}   You may need to run migrations manually:${NC}"
        echo -e "${GRAY}   docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec api alembic upgrade head${NC}"
    fi
else
    echo -e "${GRAY}[4/5] Skipping database migrations${NC}"
fi

# =============================================================================
# Status Check
# =============================================================================
echo -e "${YELLOW}[5/5] Status check...${NC}"

if [ "$DEPLOY" = true ]; then
    echo -e "${GRAY}"
    echo "   Service Status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo -e "${NC}"
    
    echo -e "${GRAY}   Testing endpoints...${NC}"
    
    # Test health endpoint
    if curl -f -s -o /dev/null -w "" http://localhost/health 2>/dev/null; then
        echo -e "${GREEN}   ✓ Health Check: OK${NC}"
    else
        echo -e "${RED}   ❌ Health Check: Failed${NC}"
    fi
    
    # Test API health
    if curl -f -s -o /dev/null -w "" http://localhost/api/healthz 2>/dev/null; then
        echo -e "${GREEN}   ✓ API Health: OK${NC}"
    else
        echo -e "${RED}   ❌ API Health: Failed${NC}"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "${CYAN}"
echo "====================================================================="
echo "  Build Complete!"
echo "====================================================================="
echo -e "${NC}"

if [ "$DEPLOY" = true ]; then
    echo -e "${GREEN}✅ Production stack is running!${NC}"
    echo -e "${CYAN}"
    echo "Access URLs:"
    echo -e "${NC}"
    echo "  • Web:        http://localhost/web/"
    echo "  • API Docs:   http://localhost/docs"
    echo "  • Health:     http://localhost/health"
    echo "  • Prometheus: http://localhost/prometheus/"
    echo "  • Grafana:    http://localhost/grafana/"
    echo "  • Kibana:     http://localhost/kibana/"
    
    echo -e "${CYAN}"
    echo "Useful Commands:"
    echo -e "${NC}"
    echo -e "${GRAY}  • View logs:    docker compose -f $COMPOSE_FILE logs -f${NC}"
    echo -e "${GRAY}  • Stop stack:   docker compose -f $COMPOSE_FILE down${NC}"
    echo -e "${GRAY}  • Migrations:   docker compose -f $COMPOSE_FILE exec api alembic upgrade head${NC}"
    
    if [ "$MIGRATE" = false ]; then
        echo -e "${YELLOW}"
        echo "⚠️  Don't forget to run migrations!"
        echo -e "${GRAY}   docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec api alembic upgrade head${NC}"
    fi
else
    echo -e "${GREEN}✅ Images built successfully!${NC}"
    echo -e "${CYAN}"
    echo "To deploy:"
    echo -e "${NC}  ./build-prod.sh --deploy"
    echo -e "${CYAN}"
    echo "Or manually:"
    echo -e "${GRAY}  docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d${NC}"
fi

echo ""
