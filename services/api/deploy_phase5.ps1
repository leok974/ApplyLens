# Phase 5.0 Production Deployment Script
# Deploys Phase 5.0 feedback-aware style tuning to production

Write-Host "=== Phase 5.0 Production Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build new Docker image
Write-Host "Step 1: Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.prod -t leoklemet/applylens-api:0.6.0-phase5 -t leoklemet/applylens-api:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker image built successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Push to Docker Hub (optional - uncomment if you want to push)
# Write-Host "Step 2: Pushing to Docker Hub..." -ForegroundColor Yellow
# docker push leoklemet/applylens-api:0.6.0-phase5
# docker push leoklemet/applylens-api:latest
# Write-Host "✓ Pushed to Docker Hub" -ForegroundColor Green
# Write-Host ""

# Step 3: Stop old container
Write-Host "Step 2: Stopping old API container..." -ForegroundColor Yellow
docker stop applylens-api-prod
Write-Host "✓ Old container stopped" -ForegroundColor Green
Write-Host ""

# Step 4: Remove old container
Write-Host "Step 3: Removing old container..." -ForegroundColor Yellow
docker rm applylens-api-prod
Write-Host "✓ Old container removed" -ForegroundColor Green
Write-Host ""

# Step 5: Start new container with Phase 5.0 code
Write-Host "Step 4: Starting new API container with Phase 5.0..." -ForegroundColor Yellow
docker run -d `
  --name applylens-api-prod `
  --network applylens-network `
  -p 8003:8000 `
  -e DATABASE_URL="postgresql://postgres:postgres@applylens-db-prod:5432/applylens" `
  -e ELASTICSEARCH_URL="http://applylens-es-prod:9200" `
  -e REDIS_URL="redis://applylens-redis-prod:6379" `
  -e ENVIRONMENT="production" `
  --restart unless-stopped `
  leoklemet/applylens-api:0.6.0-phase5

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start new container" -ForegroundColor Red
    exit 1
}
Write-Host "✓ New container started" -ForegroundColor Green
Write-Host ""

# Step 6: Wait for container to be healthy
Write-Host "Step 5: Waiting for API to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

$health = curl -s http://localhost:8003/health
if ($health -match "ok") {
    Write-Host "✓ API is healthy" -ForegroundColor Green
} else {
    Write-Host "✗ API health check failed" -ForegroundColor Red
    docker logs applylens-api-prod --tail 50
    exit 1
}
Write-Host ""

# Step 7: Apply Phase 5.0 database migration
Write-Host "Step 6: Applying Phase 5.0 migration..." -ForegroundColor Yellow
docker exec applylens-api-prod alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Migration failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Migration applied successfully" -ForegroundColor Green
Write-Host ""

# Step 8: Verify migration
Write-Host "Step 7: Verifying migration..." -ForegroundColor Yellow
$currentRev = docker exec applylens-api-prod alembic current
Write-Host "Current revision: $currentRev"
Write-Host "✓ Migration verified" -ForegroundColor Green
Write-Host ""

# Step 9: Run aggregator to populate style hints
Write-Host "Step 8: Running aggregator to populate style hints..." -ForegroundColor Yellow
$result = docker exec applylens-api-prod python -c "from app.autofill_aggregator import run_aggregator; updated = run_aggregator(days=30); print(f'Updated {updated} profiles')"
Write-Host $result
Write-Host "✓ Aggregator completed" -ForegroundColor Green
Write-Host ""

# Step 10: Test Phase 5.0 endpoints
Write-Host "Step 9: Testing Phase 5.0 endpoints..." -ForegroundColor Yellow

# Test profile endpoint
Write-Host "  Testing profile endpoint..."
$profile = curl -s "http://localhost:8003/api/extension/learning/profile?host=test&schema_hash=test"
if ($profile -match "host") {
    Write-Host "  ✓ Profile endpoint working" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Profile endpoint returned: $profile" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Phase 5.0 deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Monitor logs: docker logs -f applylens-api-prod"
Write-Host "2. Run backend tests: docker exec applylens-api-prod pytest tests/test_learning_style_tuning.py -v"
Write-Host "3. Build and deploy extension"
Write-Host "4. Set up aggregator cron job (Windows Task Scheduler)"
Write-Host ""
