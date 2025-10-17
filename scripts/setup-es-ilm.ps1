# Elasticsearch ILM Setup for ApplyLens (PowerShell)
# 90-day retention with monthly rollover

$ErrorActionPreference = "Stop"

$ES_URL = if ($env:ES_URL) { $env:ES_URL } else { "http://localhost:9200" }

Write-Host "=== Elasticsearch ILM Policy Setup ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target: $ES_URL"
Write-Host ""

# A. Create ILM policy emails-rolling-90d
Write-Host "1. Creating ILM policy 'emails-rolling-90d'..." -ForegroundColor Yellow

$ilmPolicy = @{
    policy = @{
        phases = @{
            hot = @{
                min_age = "0d"
                actions = @{
                    rollover = @{
                        max_age = "30d"
                        max_size = "20gb"
                    }
                    set_priority = @{
                        priority = 100
                    }
                }
            }
            delete = @{
                min_age = "90d"
                actions = @{
                    delete = @{}
                }
            }
        }
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "$ES_URL/_ilm/policy/emails-rolling-90d" -Method Put -ContentType "application/json" -Body $ilmPolicy | ConvertTo-Json

Write-Host ""
Write-Host "✓ ILM policy created" -ForegroundColor Green
Write-Host ""

# B. Create index template for alias gmail_emails
Write-Host "2. Creating index template 'gmail-emails-template'..." -ForegroundColor Yellow

$indexTemplate = @{
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
                sender = @{ type = "keyword" }
                sender_domain = @{ type = "keyword" }
                subject = @{ type = "text" }
                body = @{ type = "text" }
                labels = @{ type = "keyword" }
                thread_id = @{ type = "keyword" }
                message_id = @{ type = "keyword" }
            }
        }
        aliases = @{
            gmail_emails = @{
                is_write_index = $false
            }
        }
    }
    priority = 500
    composed_of = @()
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "$ES_URL/_index_template/gmail-emails-template" -Method Put -ContentType "application/json" -Body $indexTemplate | ConvertTo-Json

Write-Host ""
Write-Host "✓ Index template created" -ForegroundColor Green
Write-Host ""

# C. Check if we need to bootstrap the first rollover index
Write-Host "3. Checking existing indices..." -ForegroundColor Yellow

try {
    $indices = Invoke-RestMethod -Uri "$ES_URL/_cat/indices/gmail_emails?format=json" -ErrorAction SilentlyContinue
    $existingIndex = $indices[0].index
    
    if ($existingIndex -eq "gmail_emails") {
        Write-Host "   Found concrete 'gmail_emails' index" -ForegroundColor Yellow
        Write-Host "   Migration required:"
        Write-Host ""
        Write-Host "   ⚠️  MANUAL STEPS REQUIRED:" -ForegroundColor Red
        Write-Host "   1. Stop API ingestion temporarily"
        Write-Host "   2. Create first write index:"
        Write-Host "      `$body = '{`"aliases`":{`"gmail_emails`":{`"is_write_index`":true}}}' | Invoke-RestMethod -Uri '$ES_URL/gmail_emails-000001' -Method Put -ContentType 'application/json' -Body `$body"
        Write-Host "   3. Reindex data (optional):"
        Write-Host "      `$body = '{`"source`":{`"index`":`"gmail_emails`"},`"dest`":{`"index`":`"gmail_emails-000001`"}}' | Invoke-RestMethod -Uri '$ES_URL/_reindex' -Method Post -ContentType 'application/json' -Body `$body"
        Write-Host "   4. Delete old index:"
        Write-Host "      Invoke-RestMethod -Uri '$ES_URL/gmail_emails' -Method Delete"
        Write-Host "   5. Restart API ingestion"
        Write-Host ""
    } elseif ($existingIndex -like "gmail_emails-*") {
        Write-Host "   ✓ Rollover index already exists: $existingIndex" -ForegroundColor Green
        Write-Host ""
    }
} catch {
    Write-Host "   No existing index found. Creating first write index..." -ForegroundColor Yellow
    
    $firstIndex = @{
        aliases = @{
            gmail_emails = @{
                is_write_index = $true
            }
        }
    } | ConvertTo-Json -Depth 10
    
    Invoke-RestMethod -Uri "$ES_URL/gmail_emails-000001" -Method Put -ContentType "application/json" -Body $firstIndex | ConvertTo-Json
    
    Write-Host ""
    Write-Host "   ✓ First write index created: gmail_emails-000001" -ForegroundColor Green
    Write-Host ""
}

# D. Verify setup
Write-Host "4. Verifying ILM setup..." -ForegroundColor Yellow
Write-Host ""

Write-Host "   Policy status:"
$policyStatus = Invoke-RestMethod -Uri "$ES_URL/_ilm/policy/emails-rolling-90d"
$policyStatus.'emails-rolling-90d'.policy.phases.PSObject.Properties.Name | ForEach-Object {
    Write-Host "     - $_" -ForegroundColor Gray
}

Write-Host ""
Write-Host "   Index status:"
try {
    $ilmStatus = Invoke-RestMethod -Uri "$ES_URL/gmail_emails/_ilm/explain?human"
    $ilmStatus.indices.PSObject.Properties | ForEach-Object {
        Write-Host "     $($_.Name): phase=$($_.Value.phase), action=$($_.Value.action)" -ForegroundColor Gray
    }
} catch {
    Write-Host "     No indices found yet" -ForegroundColor Gray
}

Write-Host ""
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To manually test rollover:"
Write-Host "  Invoke-RestMethod -Uri '$ES_URL/gmail_emails/_rollover' -Method Post -ContentType 'application/json' -Body '{}'"
Write-Host ""
Write-Host "To monitor ILM status:"
Write-Host "  Invoke-RestMethod -Uri '$ES_URL/gmail_emails/_ilm/explain?human' | ConvertTo-Json"
Write-Host ""
