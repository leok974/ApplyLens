# Create an enhanced Elasticsearch API key for ApplyLens
# This version includes more comprehensive permissions for production use

if (-not $env:ES_ENDPOINT) {
    Write-Error "ES_ENDPOINT is not set"
    exit 1
}

if (-not $env:ES_USER) {
    Write-Error "ES_USER is not set"
    exit 1
}

if (-not $env:ES_PASS) {
    Write-Error "ES_PASS is not set"
    exit 1
}

Write-Host "Creating Enhanced Elasticsearch API key for ApplyLens..." -ForegroundColor Cyan
Write-Host "Endpoint: $env:ES_ENDPOINT"
Write-Host ""

# Create basic auth header
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($env:ES_USER):$($env:ES_PASS)"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Content-Type" = "application/json"
}

# Enhanced API key request body with comprehensive permissions
$body = @{
    name = "applylens-api-enhanced"
    role_descriptors = @{
        applylens_full_access = @{
            cluster = @(
                "monitor",                      # View cluster health, stats
                "manage_index_templates",       # Manage index templates
                "manage_ilm",                   # Index lifecycle management
                "manage_ingest_pipelines"       # Manage ingest pipelines
            )
            index = @(
                @{
                    names = @(
                        "gmail_emails*",        # Gmail email indices
                        "applylens*",           # Any ApplyLens indices
                        ".applylens*"           # Hidden ApplyLens indices
                    )
                    privileges = @(
                        "all"                   # Full access to these indices
                    )
                }
            )
        }
    }
} | ConvertTo-Json -Depth 10

# Create API key
try {
    $response = Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_security/api_key" `
        -Method Post `
        -Headers $headers `
        -Body $body `
        -ErrorAction Stop

    Write-Host "✓ Enhanced API Key created successfully!" -ForegroundColor Green
    Write-Host ""
    $response | ConvertTo-Json -Depth 10 | Write-Host
    Write-Host ""

    $encoded = $response.encoded
    $apiKeyId = $response.id

    if (-not $encoded) {
        Write-Error "Could not extract encoded API key from response"
        exit 1
    }

    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "Enhanced API Key Details:" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "ID:      $apiKeyId"
    Write-Host "Name:    applylens-api-enhanced"
    Write-Host "Encoded: $encoded"
    Write-Host ""
    Write-Host "Permissions:" -ForegroundColor Cyan
    Write-Host "  Cluster:" -ForegroundColor White
    Write-Host "    • monitor (health, stats, settings)" -ForegroundColor Gray
    Write-Host "    • manage_index_templates (create/update templates)" -ForegroundColor Gray
    Write-Host "    • manage_ilm (index lifecycle policies)" -ForegroundColor Gray
    Write-Host "    • manage_ingest_pipelines (data processing)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Indices (gmail_emails*, applylens*, .applylens*):" -ForegroundColor White
    Write-Host "    • all (full CRUD + admin operations)" -ForegroundColor Gray
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    # Update .env file
    Write-Host "Updating ELASTICSEARCH_API_KEY in .env file..."
    $envFile = ".env"

    if (Test-Path $envFile) {
        $content = Get-Content $envFile | Where-Object { $_ -notmatch '^ELASTICSEARCH_API_KEY=' }
        $content | Set-Content $envFile
    }

    Add-Content -Path $envFile -Value "ELASTICSEARCH_API_KEY=$encoded"
    Write-Host "✓ Updated .env file" -ForegroundColor Green
    Write-Host ""

    # Verify the key works
    Write-Host "Verifying enhanced API key..."
    $verifyHeaders = @{
        "Authorization" = "ApiKey $encoded"
    }

    try {
        $health = Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_cluster/health?pretty" `
            -Headers $verifyHeaders `
            -ErrorAction Stop

        Write-Host "✓ API Key verification successful!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Cluster Status: $($health.status)" -ForegroundColor $(if ($health.status -eq "green") { "Green" } elseif ($health.status -eq "yellow") { "Yellow" } else { "Red" })
        Write-Host "Active Shards: $($health.active_shards) / Total Shards: $($health.active_shards + $health.unassigned_shards)"

    } catch {
        Write-Warning "API Key verification failed:"
        Write-Host $_.Exception.Message
        exit 1
    }

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "Enhanced Setup Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "What changed from basic key:" -ForegroundColor Cyan
    Write-Host "  ✓ Full access ('all') to indices instead of individual privileges" -ForegroundColor Green
    Write-Host "  ✓ Can manage index templates" -ForegroundColor Green
    Write-Host "  ✓ Can manage ILM policies (data retention)" -ForegroundColor Green
    Write-Host "  ✓ Can manage ingest pipelines (data transformation)" -ForegroundColor Green
    Write-Host "  ✓ Covers applylens* and .applylens* patterns (not just gmail)" -ForegroundColor Green
    Write-Host ""
    Write-Host "To revoke this key:"
    Write-Host "  \$headers = @{'Authorization'='Basic $base64Auth'; 'Content-Type'='application/json'}"
    Write-Host "  Invoke-RestMethod -Uri '$env:ES_ENDPOINT/_security/api_key' ``"
    Write-Host "    -Method Delete ``"
    Write-Host "    -Headers `$headers ``"
    Write-Host "    -Body '{\"ids\": [\"$apiKeyId\"]}'"

} catch {
    Write-Error "Error creating enhanced API key:"
    Write-Host $_.Exception.Message
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message
    }
    exit 1
}
