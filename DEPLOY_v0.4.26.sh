#!/usr/bin/env bash
# Deployment Script for ApplyLens v0.4.26
# Actions Page Implementation with Real Backend
#
# IMPORTANT: Run this script on the production host where docker-compose.prod.yml already exists.
# This script does NOT use SSH or git pull - it only pulls Docker images and recreates containers.

set -euo pipefail

echo "🚀 Deploying ApplyLens v0.4.26..."
echo "Features: Actions page with real backend endpoints"
echo ""

echo "[1/4] Pull latest production images"
docker compose -f docker-compose.prod.yml pull api web

echo "[2/4] Recreate API and Web containers with new tags"
docker compose -f docker-compose.prod.yml up -d --force-recreate api web

echo "[3/4] Restart nginx to pick up any config/static changes"
docker restart applylens-nginx-prod

echo "[4/4] Smoke check"
sleep 3
curl -sS https://applylens.app/api/healthz || echo "⚠️  WARNING: healthz check failed"

echo ""
echo "✅ Deployment complete! v0.4.26 should now be live."
echo ""
echo "🔍 Verify deployment:"
echo "   curl https://applylens.app/api/healthz"
echo "   Visit https://applylens.app/web/inbox-actions in browser"
echo "   Check that only 'Explain why' button shows (no 403 errors)"
echo ""
echo "📊 Check logs:"
echo "   docker logs applylens-api-prod --tail 50 -f"
echo "   docker logs applylens-web-prod --tail 50 -f"
echo "   docker logs applylens-nginx-prod --tail 50 -f"
echo ""
echo "🔙 Rollback if needed:"
echo "   Edit docker-compose.prod.yml to use v0.4.25"
echo "   docker compose -f docker-compose.prod.yml pull api web"
echo "   docker compose -f docker-compose.prod.yml up -d --force-recreate api web"
echo "   docker restart applylens-nginx-prod"
