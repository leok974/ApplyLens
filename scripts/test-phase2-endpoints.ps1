# Phase 2 - Email Categorization Test Script
# Tests labeling, profile, and relevance endpoints

Write-Host "🧪 Testing Phase 2 Endpoints" -ForegroundColor Cyan
Write-Host ""

$API_BASE = "http://localhost:8003"
$ES_BASE = "http://localhost:9200"
$INDEX = "emails_v1-000001"

# Helper function for API calls
function Test-Endpoint {
    param(
        [string]$Method = "GET",
        [string]$Url,
        [string]$Name,
        [object]$Body = $null
    )
    
    Write-Host "Testing: $Name" -ForegroundColor Yellow
    Write-Host "  $Method $Url"
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            ContentType = "application/json"
            TimeoutSec = 30
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
        }
        
        $response = Invoke-RestMethod @params
        Write-Host "  ✅ Success" -ForegroundColor Green
        
        # Show sample of response
        if ($response) {
            Write-Host "  Response:" -ForegroundColor Gray
            $json = $response | ConvertTo-Json -Depth 3 -Compress
            if ($json.Length -gt 200) {
                $json = $json.Substring(0, 197) + "..."
            }
            Write-Host "    $json" -ForegroundColor Gray
        }
        
        return $response
    }
    catch {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
    
    Write-Host ""
}

# 1. Check if API is healthy
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "1️⃣  Health Check" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

Test-Endpoint -Url "$API_BASE/health" -Name "API Health"

# Wait for API to fully start
Start-Sleep -Seconds 3

# 2. Check ES document count
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "2️⃣  Elasticsearch Data" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$count_response = Test-Endpoint -Url "$ES_BASE/$INDEX/_count" -Name "Document Count"
$doc_count = $count_response.count

if ($doc_count -eq 0) {
    Write-Host "⚠️  No documents in index. Run gmail backfill first:" -ForegroundColor Yellow
    Write-Host "   python analytics/ingest/gmail_backfill_to_es_bq.py" -ForegroundColor Gray
    Write-Host ""
}

# 3. Test Labels Endpoints
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "3️⃣  Labels Router" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Check stats before applying
Test-Endpoint -Url "$API_BASE/labels/stats" -Name "Label Stats (before)"

if ($doc_count -gt 0) {
    Write-Host ""
    Write-Host "Applying labels to all documents..." -ForegroundColor Yellow
    Write-Host "(This may take a while depending on document count)" -ForegroundColor Gray
    Write-Host ""
    
    # Apply labels (limited to first 100 for testing)
    $apply_body = @{
        query = @{
            match_all = @{}
        }
        batch_size = 100
    }
    
    $apply_response = Test-Endpoint `
        -Method "POST" `
        -Url "$API_BASE/labels/apply" `
        -Name "Apply Labels" `
        -Body $apply_body
    
    if ($apply_response) {
        Write-Host ""
        Write-Host "📊 Labeling Results:" -ForegroundColor Green
        Write-Host "   Updated: $($apply_response.updated) documents" -ForegroundColor Gray
        Write-Host "   Categories:" -ForegroundColor Gray
        foreach ($cat in $apply_response.by_category.PSObject.Properties) {
            Write-Host "     - $($cat.Name): $($cat.Value)" -ForegroundColor Gray
        }
        Write-Host "   Methods:" -ForegroundColor Gray
        foreach ($method in $apply_response.by_method.PSObject.Properties) {
            Write-Host "     - $($method.Name): $($method.Value)" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    # Check stats after applying
    Test-Endpoint -Url "$API_BASE/labels/stats" -Name "Label Stats (after)"
}

# 4. Test Profile Endpoints
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "4️⃣  Profile Router" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$profile_summary = Test-Endpoint -Url "$API_BASE/profile/summary?days=60" -Name "Profile Summary"

if ($profile_summary) {
    Write-Host ""
    Write-Host "📊 Profile Summary:" -ForegroundColor Green
    Write-Host "   Total Emails: $($profile_summary.total)" -ForegroundColor Gray
    Write-Host "   Time Window: $($profile_summary.days) days" -ForegroundColor Gray
    Write-Host "   Avg Per Day: $($profile_summary.avg_per_day)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   Categories:" -ForegroundColor Gray
    foreach ($cat in $profile_summary.by_category) {
        Write-Host "     - $($cat.category): $($cat.count) ($($cat.percent)%)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "   Top Senders:" -ForegroundColor Gray
    $top_5 = $profile_summary.top_senders | Select-Object -First 5
    foreach ($s in $top_5) {
        Write-Host "     - $($s.sender_domain): $($s.count)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Test senders endpoint
Test-Endpoint -Url "$API_BASE/profile/senders?days=60&size=10" -Name "All Senders"
Write-Host ""

# Test category-specific senders
Test-Endpoint -Url "$API_BASE/profile/senders?category=newsletter&days=60" -Name "Newsletter Senders"
Write-Host ""

Test-Endpoint -Url "$API_BASE/profile/senders?category=promo&days=60" -Name "Promo Senders"
Write-Host ""

# Test category details
Test-Endpoint -Url "$API_BASE/profile/categories/newsletter?days=30" -Name "Newsletter Details"
Write-Host ""

# Test time series
Test-Endpoint -Url "$API_BASE/profile/time-series?days=7&interval=1d" -Name "Time Series (7 days)"
Write-Host ""

# 5. Test Sample Document with Categories
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "5️⃣  Sample Categorized Document" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

if ($doc_count -gt 0) {
    # Search for a categorized document
    $search_body = @{
        size = 1
        query = @{
            bool = @{
                must = @(
                    @{ exists = @{ field = "category" } }
                )
            }
        }
        _source = @("subject", "sender_domain", "category", "confidence", "reason", "features", "expires_at")
    }
    
    try {
        $search_response = Invoke-RestMethod `
            -Uri "$ES_BASE/$INDEX/_search" `
            -Method POST `
            -ContentType "application/json" `
            -Body ($search_body | ConvertTo-Json -Depth 10)
        
        if ($search_response.hits.hits.Count -gt 0) {
            $doc = $search_response.hits.hits[0]._source
            
            Write-Host "📧 Sample Email:" -ForegroundColor Green
            Write-Host "   Subject: $($doc.subject)" -ForegroundColor Gray
            Write-Host "   Sender: $($doc.sender_domain)" -ForegroundColor Gray
            Write-Host "   Category: $($doc.category)" -ForegroundColor Cyan
            Write-Host "   Confidence: $($doc.confidence)" -ForegroundColor Gray
            Write-Host "   Reason: $($doc.reason)" -ForegroundColor Gray
            
            if ($doc.features) {
                Write-Host "   Features:" -ForegroundColor Gray
                Write-Host "     - URL Count: $($doc.features.url_count)" -ForegroundColor Gray
                Write-Host "     - Money Hits: $($doc.features.money_hits)" -ForegroundColor Gray
                Write-Host "     - Due Date Hit: $($doc.features.due_date_hit)" -ForegroundColor Gray
            }
            
            if ($doc.expires_at) {
                Write-Host "   Expires: $($doc.expires_at)" -ForegroundColor Yellow
            }
            Write-Host ""
        }
    }
    catch {
        Write-Host "  ❌ Failed to fetch sample document" -ForegroundColor Red
    }
}

# 6. Kibana Query Examples
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "6️⃣  Kibana Query Examples" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

Write-Host "Run these queries in Kibana ESQL:" -ForegroundColor Yellow
Write-Host ""

Write-Host "1. Time to Expire (Promos):" -ForegroundColor Cyan
Write-Host @'
FROM emails_v1-*
| WHERE category == "promo" AND expires_at IS NOT NULL
| EVAL tte_days = TO_LONG(expires_at - NOW()) / 86400000
| STATS avg_tte = AVG(tte_days), 
        soon = COUNT(IF(tte_days <= 3, 1, NULL)),
        expired = COUNT(IF(tte_days < 0, 1, NULL))
'@ -ForegroundColor Gray
Write-Host ""

Write-Host "2. Inactive Subscriptions:" -ForegroundColor Cyan
Write-Host @'
FROM emails_v1-*
| WHERE category IN ("newsletter", "promo") 
  AND received_at >= NOW() - 60 DAY
| STATS cnt = COUNT(*) BY sender_domain
| SORT cnt DESC
| LIMIT 50
'@ -ForegroundColor Gray
Write-Host ""

Write-Host "3. Low Confidence Labels:" -ForegroundColor Cyan
Write-Host @'
FROM emails_v1-*
| WHERE confidence IS NOT NULL AND confidence < 0.5
| STATS cnt = COUNT(*) BY category
| SORT cnt DESC
'@ -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ Phase 2 Testing Complete" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

Write-Host "📚 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Review PHASE_2_IMPLEMENTATION.md for full documentation"
Write-Host "   2. Train ML model (optional): python services/api/app/labeling/train_ml.py"
Write-Host "   3. Build Profile UI page: apps/web/src/pages/Profile.tsx"
Write-Host "   4. Add category filters to Inbox component"
Write-Host "   5. Set up scheduled labeling: cron job for /labels/apply"
Write-Host ""

Write-Host "🔗 Useful Endpoints:" -ForegroundColor Yellow
Write-Host "   Labels API: http://localhost:8000/labels/stats"
Write-Host "   Profile API: http://localhost:8000/profile/summary?days=60"
Write-Host "   API Docs: http://localhost:8000/docs"
Write-Host ""
