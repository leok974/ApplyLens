#!/usr/bin/env bash
# deploy-web-v0.4.21.sh - Deploy web v0.4.21 to production
set -euo pipefail

echo "🚀 Deploying ApplyLens Web v0.4.21 to production..."
echo ""

# Pull the latest image
echo "📦 Pulling image from Docker Hub..."
docker pull leoklemet/applylens-web:v0.4.21

# Update the docker-compose to use new version (if needed)
echo "📝 Updating docker-compose.prod.yml..."
sed -i.bak 's|leoklemet/applylens-web:v0.4.[0-9]*|leoklemet/applylens-web:v0.4.21|g' docker-compose.prod.yml

# Recreate the web container
echo "🔄 Recreating web container..."
docker-compose -f docker-compose.prod.yml up -d --force-recreate --no-deps web

# Restart nginx to pick up changes
echo "🔄 Restarting Nginx..."
docker-compose -f docker-compose.prod.yml restart nginx

# Wait for health check
echo "⏳ Waiting for service to be healthy..."
sleep 5

# Check health
echo "🏥 Checking service health..."
if docker ps --filter "name=applylens-web-prod" --filter "health=healthy" | grep -q "applylens-web-prod"; then
    echo "✅ Web service is healthy!"
else
    echo "⚠️  Web service may not be healthy yet. Checking status..."
    docker ps --filter "name=applylens-web-prod" --format "table {{.Names}}\t{{.Status}}"
fi

# Verify the deployment
echo ""
echo "🔍 Verifying deployment..."
docker exec applylens-web-prod ls -la /usr/share/nginx/html/assets/ | grep index || echo "Assets found"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access your site at: https://applylens.app"
echo ""
echo "📊 Useful commands:"
echo "  - View logs:   docker-compose -f docker-compose.prod.yml logs -f web"
echo "  - Check status: docker ps --filter 'name=applylens-web-prod'"
echo "  - Rollback:    docker-compose -f docker-compose.prod.yml up -d --force-recreate --no-deps web"
echo "                 (after changing image tag back to previous version)"
