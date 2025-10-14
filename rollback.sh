#!/bin/bash
# Rollback Script for ApplyLens Production Deployment
# Quick recovery mechanism if deployment has issues

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${RED}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ApplyLens Rollback Procedures                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

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
# Show rollback options
# =============================================================================
echo ""
print_warning "Rollback Options:"
echo ""
echo "1) Quick Restart (restart services without rebuild)"
echo "2) View Recent Logs (diagnose issues)"
echo "3) Restart Specific Service"
echo "4) Roll Back to Previous Commit"
echo "5) Full Rebuild and Restart"
echo "6) Stop All Services"
echo "7) Exit (no changes)"
echo ""

read -p "Select option [1-7]: " OPTION

case $OPTION in
    1)
        # Quick restart
        echo ""
        print_status "Restarting all services..."
        docker compose -f docker-compose.prod.yml restart
        print_success "Services restarted"
        
        echo ""
        print_status "Waiting for services to stabilize..."
        sleep 10
        
        print_status "Running health checks..."
        ./health-check.sh
        ;;
        
    2)
        # View logs
        echo ""
        print_status "Recent logs from all services:"
        echo ""
        docker compose -f docker-compose.prod.yml logs --tail=200
        
        echo ""
        print_status "Error summary:"
        docker compose -f docker-compose.prod.yml logs --tail=200 2>&1 | grep -i "error" | tail -20
        ;;
        
    3)
        # Restart specific service
        echo ""
        echo "Available services:"
        docker compose -f docker-compose.prod.yml ps --services
        echo ""
        read -p "Enter service name to restart: " SERVICE
        
        print_status "Restarting $SERVICE..."
        docker compose -f docker-compose.prod.yml restart "$SERVICE"
        
        print_success "$SERVICE restarted"
        
        print_status "Checking $SERVICE logs..."
        docker compose -f docker-compose.prod.yml logs --tail=50 "$SERVICE"
        ;;
        
    4)
        # Git rollback
        echo ""
        print_warning "Rolling back to previous commit"
        
        CURRENT_COMMIT=$(git rev-parse --short HEAD)
        print_status "Current commit: $CURRENT_COMMIT"
        
        print_status "Recent commits:"
        git log --oneline -10
        
        echo ""
        read -p "Enter commit hash to rollback to: " TARGET_COMMIT
        
        print_warning "This will reset your working directory!"
        read -p "Are you sure? (yes/no): " CONFIRM
        
        if [ "$CONFIRM" == "yes" ]; then
            print_status "Rolling back to $TARGET_COMMIT..."
            git reset --hard "$TARGET_COMMIT"
            
            print_status "Rebuilding services..."
            docker compose -f docker-compose.prod.yml build api web
            
            print_status "Restarting services..."
            docker compose -f docker-compose.prod.yml up -d
            
            print_status "Running migrations..."
            docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head
            
            print_success "Rollback complete!"
            
            NEW_COMMIT=$(git rev-parse --short HEAD)
            print_status "Now at commit: $NEW_COMMIT"
        else
            print_status "Rollback cancelled"
        fi
        ;;
        
    5)
        # Full rebuild
        echo ""
        print_warning "Full rebuild and restart"
        read -p "Are you sure? This will rebuild all images. (yes/no): " CONFIRM
        
        if [ "$CONFIRM" == "yes" ]; then
            print_status "Stopping services..."
            docker compose -f docker-compose.prod.yml stop
            
            print_status "Rebuilding images (no cache)..."
            docker compose -f docker-compose.prod.yml build --no-cache api web
            
            print_status "Starting services..."
            docker compose -f docker-compose.prod.yml up -d
            
            print_status "Waiting for services..."
            sleep 15
            
            print_status "Running migrations..."
            docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head
            
            print_success "Full rebuild complete!"
            
            print_status "Running health checks..."
            ./health-check.sh
        else
            print_status "Rebuild cancelled"
        fi
        ;;
        
    6)
        # Stop all
        echo ""
        print_warning "Stopping all services"
        read -p "Are you sure? (yes/no): " CONFIRM
        
        if [ "$CONFIRM" == "yes" ]; then
            print_status "Stopping all services..."
            docker compose -f docker-compose.prod.yml stop
            print_success "All services stopped"
            
            print_status "Service status:"
            docker compose -f docker-compose.prod.yml ps
        else
            print_status "Stop cancelled"
        fi
        ;;
        
    7)
        # Exit
        print_status "Exiting without changes"
        exit 0
        ;;
        
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
print_status "Rollback procedure complete"
echo ""
echo -e "${YELLOW}Additional Commands:${NC}"
echo "  View logs:     ${CYAN}docker compose -f docker-compose.prod.yml logs -f${NC}"
echo "  Health check:  ${CYAN}./health-check.sh${NC}"
echo "  Service status: ${CYAN}docker compose -f docker-compose.prod.yml ps${NC}"
echo ""
