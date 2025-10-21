# Reindex existing emails through pipeline v2 to add smart flags
# This creates a new index with all v2 flags populated

$ES_URL = "http://localhost:9200"
$SOURCE_INDEX = "gmail_emails"
$DEST_INDEX = "gmail_emails_v2_migrated"
$PIPELINE = "applylens_emails_v2"

Write-Host "`n╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                  ║" -ForegroundColor Cyan
Write-Host "║        📧 Reindex Emails Through Pipeline v2                    ║" -ForegroundColor Cyan
Write-Host "║                                                                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Source Index: " -NoNewline
Write-Host $SOURCE_INDEX -ForegroundColor White
Write-Host "  Destination Index: " -NoNewline
Write-Host $DEST_INDEX -ForegroundColor White
Write-Host "  Pipeline: " -NoNewline
Write-Host $PIPELINE -ForegroundColor Green
Write-Host ""

# Step 1: Check source index count
Write-Host "Step 1: Checking source index..." -ForegroundColor Yellow
try {
    $sourceCount = (Invoke-RestMethod -Uri "$ES_URL/$SOURCE_INDEX/_count" -Method Get).count
    Write-Host "  ✅ Found $sourceCount documents in source index" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ Failed to read source index: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Check if destination exists (don't overwrite)
Write-Host "`nStep 2: Checking destination index..." -ForegroundColor Yellow
try {
    $destExists = Invoke-RestMethod -Uri "$ES_URL/$DEST_INDEX" -Method Head -ErrorAction Stop
    Write-Host "  ⚠️  Destination index already exists!" -ForegroundColor Yellow
    Write-Host "  To proceed, delete it first:" -ForegroundColor White
    Write-Host "    curl -X DELETE $ES_URL/$DEST_INDEX" -ForegroundColor Gray
    exit 1
}
catch {
    Write-Host "  ✅ Destination index doesn't exist (ready to create)" -ForegroundColor Green
}

# Step 3: Create destination index
Write-Host "`nStep 3: Creating destination index..." -ForegroundColor Yellow
$indexSettings = @{
    settings = @{
        number_of_shards = 1
        number_of_replicas = 0
        index = @{
            default_pipeline = $PIPELINE
        }
    }
} | ConvertTo-Json -Depth 10

try {
    Invoke-RestMethod -Uri "$ES_URL/$DEST_INDEX" -Method Put -Body $indexSettings -ContentType "application/json" | Out-Null
    Write-Host "  ✅ Created destination index with pipeline $PIPELINE" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ Failed to create destination index: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Start reindex operation
Write-Host "`nStep 4: Starting reindex operation..." -ForegroundColor Yellow
Write-Host "  ⏳ This may take several minutes for large indices..." -ForegroundColor Gray

$reindexBody = @{
    source = @{
        index = $SOURCE_INDEX
    }
    dest = @{
        index = $DEST_INDEX
        pipeline = $PIPELINE
    }
} | ConvertTo-Json -Depth 10

try {
    $reindexResult = Invoke-RestMethod -Uri "$ES_URL/_reindex?wait_for_completion=true" -Method Post -Body $reindexBody -ContentType "application/json"
    
    Write-Host "  ✅ Reindex complete!" -ForegroundColor Green
    Write-Host "    Created: " -NoNewline
    Write-Host $reindexResult.created -ForegroundColor White
    Write-Host "    Updated: " -NoNewline
    Write-Host $reindexResult.updated -ForegroundColor White
    Write-Host "    Total: " -NoNewline
    Write-Host $reindexResult.total -ForegroundColor White
    Write-Host "    Time: " -NoNewline
    Write-Host "$($reindexResult.took)ms" -ForegroundColor White
}
catch {
    Write-Host "  ❌ Reindex failed: $_" -ForegroundColor Red
    exit 1
}

# Step 5: Verify document counts
Write-Host "`nStep 5: Verifying document counts..." -ForegroundColor Yellow
try {
    $destCount = (Invoke-RestMethod -Uri "$ES_URL/$DEST_INDEX/_count" -Method Get).count
    
    if ($destCount -eq $sourceCount) {
        Write-Host "  ✅ Counts match! Source: $sourceCount, Destination: $destCount" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠️  Count mismatch! Source: $sourceCount, Destination: $destCount" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  ❌ Failed to verify counts: $_" -ForegroundColor Red
}

# Step 6: Sample document verification
Write-Host "`nStep 6: Verifying pipeline v2 flags..." -ForegroundColor Yellow
try {
    $sampleDoc = (Invoke-RestMethod -Uri "$ES_URL/$DEST_INDEX/_search?size=1" -Method Get).hits.hits[0]._source
    
    Write-Host "  Sample document from destination:" -ForegroundColor Cyan
    Write-Host "    From: " -NoNewline -ForegroundColor Gray
    Write-Host $sampleDoc.from -ForegroundColor White
    Write-Host "    Subject: " -NoNewline -ForegroundColor Gray
    Write-Host $sampleDoc.subject -ForegroundColor White
    
    # Check for v2 flags
    $v2Flags = @("is_recruiter", "has_calendar_invite", "has_attachment", "company_guess")
    $foundFlags = 0
    
    foreach ($flag in $v2Flags) {
        if ($sampleDoc.PSObject.Properties.Name -contains $flag) {
            $foundFlags++
            $value = $sampleDoc.$flag
            if ($value) {
                Write-Host "    ✅ $flag" -NoNewline -ForegroundColor Green
                Write-Host ": $value" -ForegroundColor White
            }
        }
    }
    
    if ($foundFlags -eq $v2Flags.Count) {
        Write-Host "`n  ✅ All pipeline v2 flags present!" -ForegroundColor Green
    }
    else {
        Write-Host "`n  ⚠️  Only $foundFlags/$($v2Flags.Count) v2 flags found" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  ⚠️  Could not verify flags: $_" -ForegroundColor Yellow
}

# Summary and next steps
Write-Host "`n╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                                  ║" -ForegroundColor Green
Write-Host "║                    ✅ REINDEX COMPLETE                           ║" -ForegroundColor Green
Write-Host "║                                                                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "📊 Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Test queries on the new index:" -ForegroundColor Yellow
Write-Host "   .\scripts\test_pipeline_v2_queries.ps1" -ForegroundColor White
Write-Host ""
Write-Host "2. Compare old vs new index in Kibana:" -ForegroundColor Yellow
Write-Host "   • Create data view for $DEST_INDEX" -ForegroundColor White
Write-Host "   • Run KQL queries to test smart flags" -ForegroundColor White
Write-Host ""
Write-Host "3. If satisfied, you can:" -ForegroundColor Yellow
Write-Host "   a) Query the new index directly" -ForegroundColor White
Write-Host "   b) Update your application to use $DEST_INDEX" -ForegroundColor White
Write-Host "   c) Create an alias pointing to $DEST_INDEX" -ForegroundColor White
Write-Host ""
Write-Host "ℹ️  The source index ($SOURCE_INDEX) is unchanged and safe to keep" -ForegroundColor Gray
Write-Host ""
