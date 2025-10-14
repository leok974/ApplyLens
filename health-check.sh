#!/bin/bash
# Health Check Script for ApplyLens Production Deployment
# Verifies all services are running correctly

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           ApplyLens Health Check (Production)             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

FAILED_CHECKS=0

# Function to check service
check_service() {
    local service_name="$1"
    local check_command="$2"
    local description="$3"
    
    echo -ne "${BLUE}[*]${NC} Checking ${description}... "
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

echo ""
echo -e "${YELLOW}🔍 Container Status:${NC}"
docker compose -f docker-compose.prod.yml ps

echo ""
echo -e "${YELLOW}🏥 Health Checks:${NC}"
echo ""

# Check internal services (localhost)
check_service "nginx" "curl -fsSL http://localhost/" "Nginx (localhost)"
check_service "api-health" "curl -fsSL http://localhost/health" "API health endpoint (via nginx)"
check_service "api-direct" "docker compose -f docker-compose.prod.yml exec -T api curl -sf http://localhost:8003/healthz" "API direct (port 8003)"
check_service "web-direct" "curl -fsSL http://localhost:5175/" "Web app (port 5175)"
check_service "database" "docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres" "PostgreSQL database"
check_service "elasticsearch" "curl -fsSL http://localhost:9200/_cluster/health" "Elasticsearch"
check_service "kibana" "curl -fsSL http://localhost:5601/api/status" "Kibana"
check_service "prometheus" "curl -fsSL http://localhost:9090/-/healthy" "Prometheus"
check_service "grafana" "curl -fsSL http://localhost:3000/api/health" "Grafana"

echo ""
echo -e "${YELLOW}🌐 External Access (via Cloudflare):${NC}"
echo ""

# Check external access
if check_service "cloudflare-frontend" "curl -I https://applylens.app/ 2>&1 | head -n 1 | grep -q '200\\|301\\|302'" "Frontend (https://applylens.app/)"; then
    HTTP_STATUS=$(curl -I https://applylens.app/ 2>&1 | head -n 1)
    echo "   Status: ${HTTP_STATUS}"
fi

if check_service "cloudflare-docs" "curl -I https://applylens.app/docs/ 2>&1 | head -n 1 | grep -q '200\\|307'" "API Docs (https://applylens.app/docs/)"; then
    HTTP_STATUS=$(curl -I https://applylens.app/docs/ 2>&1 | head -n 1)
    echo "   Status: ${HTTP_STATUS}"
fi

# Check logs for errors
echo ""
echo -e "${YELLOW}📋 Recent Errors (last 50 lines):${NC}"
echo ""

ERROR_COUNT=$(docker compose -f docker-compose.prod.yml logs --tail=50 2>&1 | grep -i "error" | wc -l)

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}Found $ERROR_COUNT error messages:${NC}"
    docker compose -f docker-compose.prod.yml logs --tail=50 2>&1 | grep -i "error" | tail -10
else
    echo -e "${GREEN}No recent errors found${NC}"
fi

# Summary
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        ✓ All Health Checks Passed!                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    exit 0
else
    echo -e "${RED}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        ✗ $FAILED_CHECKS Health Check(s) Failed!                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Check logs: ${CYAN}docker compose -f docker-compose.prod.yml logs -f${NC}"
    echo "2. Check specific service: ${CYAN}docker compose -f docker-compose.prod.yml logs <service>${NC}"
    echo "3. Restart services: ${CYAN}docker compose -f docker-compose.prod.yml restart${NC}"
    echo ""
    
    exit 1
fi
