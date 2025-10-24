#!/bin/bash
# Deployment Script for ApplyLens v0.4.26
# Actions Page Implementation with Real Backend

set -e

echo "🚀 Deploying ApplyLens v0.4.26..."
echo "Features: Actions page with real backend endpoints"
echo ""

# Navigate to project directory
cd /root/ApplyLens || exit 1

# Pull latest code
echo "📥 Pulling latest code from git..."
git pull origin demo

# Pull new Docker images
echo "🐳 Pulling Docker images..."
docker compose -f docker-compose.prod.yml pull api web

# Recreate containers with new images
echo "🔄 Recreating API and Web containers..."
docker compose -f docker-compose.prod.yml up -d --force-recreate api web

# Wait for containers to be ready
echo "⏳ Waiting for containers to start..."
sleep 5

# Check container health
echo "🏥 Checking container health..."
docker ps --filter "name=applylens-api-prod" --filter "name=applylens-web-prod"

# Restart nginx to clear DNS cache
echo "♻️  Restarting nginx to clear DNS cache..."
docker restart applylens-nginx-prod

# Wait for nginx to be ready
sleep 3

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔍 Verify deployment:"
echo "   - API health: https://applylens.app/api/ready"
echo "   - Actions page: https://applylens.app/inbox-actions"
echo ""
echo "📊 Check logs:"
echo "   docker logs applylens-api-prod --tail 50 -f"
echo "   docker logs applylens-web-prod --tail 50 -f"
echo "   docker logs applylens-nginx-prod --tail 50 -f"
echo ""
echo "🔙 Rollback if needed:"
echo "   docker tag leoklemet/applylens-api:v0.4.25 leoklemet/applylens-api:rollback"
echo "   docker tag leoklemet/applylens-web:v0.4.25 leoklemet/applylens-web:rollback"
echo "   Update docker-compose.prod.yml to use v0.4.25"
echo "   docker compose -f docker-compose.prod.yml up -d --force-recreate api web"
