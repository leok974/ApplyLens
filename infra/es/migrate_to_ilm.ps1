# Immediate ILM Migration Script (PowerShell)
# Retrofits existing gmail_emails index to ILM-managed structure

param(
    [string]$ES_URL = "http://localhost:9200"
)

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Elasticsearch ILM - Immediate Migration (Retrofit)            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  WARNING: This will migrate your existing gmail_emails index to ILM management" -ForegroundColor Yellow
Write-Host "    - Creates new index: gmail_emails-000001" -ForegroundColor Gray
Write-Host "    - Reindexes all documents" -ForegroundColor Gray
Write-Host "    - Deletes old index: gmail_emails" -ForegroundColor Gray
Write-Host "    - Creates alias: gmail_emails → gmail_emails-000001" -ForegroundColor Gray
Write-Host ""

# Check if running from inside Docker container or host
$isDocker = $false
if ($ES_URL -eq "http://elasticsearch:9200") {
    $isDocker = $true
    Write-Host "Running from Docker container context" -ForegroundColor Cyan
}

$confirmation = Read-Host "Continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Migration cancelled." -ForegroundColor Yellow
    exit 0
}

try {
    Write-Host ""
    Write-Host "Step 1: Create ILM-managed target index..." -ForegroundColor Yellow
    
    $createIndexBody = @{
        settings = @{
            "index.lifecycle.name" = "emails-rolling-90d"
            "index.lifecycle.rollover_alias" = "gmail_emails"
        }
    } | ConvertTo-Json -Depth 10
    
    $response = Invoke-RestMethod -Uri "$ES_URL/gmail_emails-000001" -Method Put -Body $createIndexBody -ContentType "application/json"
    Write-Host "✅ Created gmail_emails-000001 with ILM policy" -ForegroundColor Green

    Write-Host ""
    Write-Host "Step 2: Reindexing existing data..." -ForegroundColor Yellow
    Write-Host "   (This may take a few minutes depending on data size)" -ForegroundColor Gray
    
    $reindexBody = @{
        source = @{ index = "gmail_emails" }
        dest   = @{ index = "gmail_emails-000001" }
    } | ConvertTo-Json -Depth 10
    
    $reindexResponse = Invoke-RestMethod -Uri "$ES_URL/_reindex?wait_for_completion=true" -Method Post -Body $reindexBody -ContentType "application/json"
    Write-Host "✅ Reindexed $($reindexResponse.created)/$($reindexResponse.total) documents in $($reindexResponse.took)ms" -ForegroundColor Green

    Write-Host ""
    Write-Host "Step 3: Deleting old index..." -ForegroundColor Yellow
    $null = Invoke-RestMethod -Uri "$ES_URL/gmail_emails" -Method Delete
    Write-Host "✅ Deleted old gmail_emails index" -ForegroundColor Green

    Write-Host ""
    Write-Host "Step 4: Creating write alias..." -ForegroundColor Yellow
    
    $aliasBody = @{
        actions = @(
            @{
                add = @{
                    index = "gmail_emails-000001"
                    alias = "gmail_emails"
                    is_write_index = $true
                }
            }
        )
    } | ConvertTo-Json -Depth 10
    
    $null = Invoke-RestMethod -Uri "$ES_URL/_aliases" -Method Post -Body $aliasBody -ContentType "application/json"
    Write-Host "✅ Created alias: gmail_emails → gmail_emails-000001 (write_index: true)" -ForegroundColor Green

    Write-Host ""
    Write-Host "Step 5: Applying index template for future rollovers..." -ForegroundColor Yellow
    
    $templateBody = @{
        index_patterns = @("gmail_emails-*")
        template = @{
            settings = @{
                "index.lifecycle.name" = "emails-rolling-90d"
                "index.lifecycle.rollover_alias" = "gmail_emails"
                "index.refresh_interval" = "1s"
                "index.number_of_shards" = 1
                "index.number_of_replicas" = 1
            }
            mappings = @{
                properties = @{
                    owner_email = @{ type = "keyword" }
                    received_at = @{ type = "date" }
                }
            }
        }
        priority = 500
    } | ConvertTo-Json -Depth 10
    
    $null = Invoke-RestMethod -Uri "$ES_URL/_index_template/gmail-emails-template" -Method Put -Body $templateBody -ContentType "application/json"
    Write-Host "✅ Applied index template for future rollovers" -ForegroundColor Green

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Verification:" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "ILM Status:" -ForegroundColor Yellow
    $ilmExplain = Invoke-RestMethod -Uri "$ES_URL/gmail_emails-000001/_ilm/explain?human"
    $firstIndex = $ilmExplain.indices.PSObject.Properties.Name | Select-Object -First 1
    $ilmInfo = $ilmExplain.indices.$firstIndex
    
    Write-Host "  Index: $firstIndex" -ForegroundColor Gray
    Write-Host "  Managed: $($ilmInfo.managed)" -ForegroundColor Gray
    Write-Host "  Policy: $($ilmInfo.policy)" -ForegroundColor Gray
    Write-Host "  Phase: $($ilmInfo.phase)" -ForegroundColor Gray
    Write-Host "  Action: $($ilmInfo.action)" -ForegroundColor Gray

    Write-Host ""
    Write-Host "Alias Configuration:" -ForegroundColor Yellow
    if ($isDocker) {
        docker exec applylens-api-prod curl -s "$ES_URL/_cat/aliases/gmail_emails?v"
    } else {
        $aliases = Invoke-RestMethod -Uri "$ES_URL/_cat/aliases/gmail_emails?v&format=json"
        $aliases | Format-Table -AutoSize
    }

    Write-Host ""
    Write-Host "Index Stats:" -ForegroundColor Yellow
    if ($isDocker) {
        docker exec applylens-api-prod curl -s "$ES_URL/_cat/indices/gmail_emails-*?v&h=index,docs.count,store.size,health"
    } else {
        $indices = Invoke-RestMethod -Uri "$ES_URL/_cat/indices/gmail_emails-*?v&format=json"
        $indices | Select-Object index,@{N='docs';E={$_.'docs.count'}},@{N='size';E={$_.'store.size'}},health | Format-Table -AutoSize
    }

    Write-Host ""
    Write-Host "✅ Migration Complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🧠 What happens next:" -ForegroundColor White
    Write-Host "  • ILM will automatically rollover at 30 days or 20 GB" -ForegroundColor Gray
    Write-Host "  • Old indices delete after 90 days" -ForegroundColor Gray
    Write-Host "  • Disk footprint drops 70-80% year-over-year" -ForegroundColor Gray
    Write-Host "  • Your API continues writing to alias 'gmail_emails' transparently" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "❌ Migration failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Rollback instructions:" -ForegroundColor Yellow
    Write-Host "  1. If gmail_emails-000001 exists: curl -X DELETE `"$ES_URL/gmail_emails-000001`"" -ForegroundColor Gray
    Write-Host "  2. Check if old index was deleted: curl `"$ES_URL/_cat/indices/gmail_emails?v`"" -ForegroundColor Gray
    Write-Host "  3. If needed, restore from backup" -ForegroundColor Gray
    exit 1
}
