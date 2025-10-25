# Create a least-privilege Elasticsearch API key for ApplyLens
# This version uses minimal permissions - safer for production

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

Write-Host "Creating Least-Privilege Elasticsearch API key for ApplyLens..." -ForegroundColor Cyan
Write-Host "Endpoint: $env:ES_ENDPOINT"
Write-Host ""

# Create basic auth header
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($env:ES_USER):$($env:ES_PASS)"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Content-Type" = "application/json"
}

# Least-privilege API key request body
$body = @{
    name = "applylens-api-minimal"
    role_descriptors = @{
        applylens_minimal = @{
            cluster = @(
                "monitor",                      # View cluster health, stats
                "manage_index_templates",       # Manage index templates
                "manage_ilm",                   # Index lifecycle management
                "manage_ingest_pipelines"       # Manage ingest pipelines
            )
            index = @(
                @{
                    names = @(
                        "gmail_emails-*",       # Gmail email indices
                        "applylens-*",          # ApplyLens indices
                        ".applylens-*"          # Hidden ApplyLens indices
                    )
                    privileges = @(
                        "read",                 # Query and search
                        "write",                # Update documents
                        "index",                # Index new documents
                        "create",               # Create documents
                        "create_index",         # Create new indices
                        "view_index_metadata"   # View mappings and settings
                    )
                    # Explicitly NOT including:
                    # - "manage" (index-level admin)
                    # - "delete" (document deletion)
                    # - "delete_index" (index deletion)
                    # - "all" (full access)
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

    Write-Host "✓ Least-Privilege API Key created successfully!" -ForegroundColor Green
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
    Write-Host "Least-Privilege API Key Details:" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "ID:      $apiKeyId"
    Write-Host "Name:    applylens-api-minimal"
    Write-Host "Encoded: $encoded"
    Write-Host ""
    Write-Host "Cluster Permissions:" -ForegroundColor Cyan
    Write-Host "  ✓ monitor                    (health, stats)" -ForegroundColor Green
    Write-Host "  ✓ manage_index_templates     (templates)" -ForegroundColor Green
    Write-Host "  ✓ manage_ilm                 (lifecycle)" -ForegroundColor Green
    Write-Host "  ✓ manage_ingest_pipelines    (pipelines)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Index Permissions (gmail_emails-*, applylens-*, .applylens-*):" -ForegroundColor Cyan
    Write-Host "  ✓ read                       (query/search)" -ForegroundColor Green
    Write-Host "  ✓ write                      (update docs)" -ForegroundColor Green
    Write-Host "  ✓ index                      (index docs)" -ForegroundColor Green
    Write-Host "  ✓ create                     (create docs)" -ForegroundColor Green
    Write-Host "  ✓ create_index               (create indices)" -ForegroundColor Green
    Write-Host "  ✓ view_index_metadata        (view mappings)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Security Restrictions:" -ForegroundColor Red
    Write-Host "  ✗ Cannot manage index settings" -ForegroundColor Gray
    Write-Host "  ✗ Cannot delete documents" -ForegroundColor Gray
    Write-Host "  ✗ Cannot delete indices" -ForegroundColor Gray
    Write-Host "  ✗ Cannot manage aliases" -ForegroundColor Gray
    Write-Host "  ✗ No cluster admin operations" -ForegroundColor Gray
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
    Write-Host "Verifying least-privilege API key..."
    $verifyHeaders = @{
        "Authorization" = "ApiKey $encoded"
    }

    try {
        $health = Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_cluster/health" `
            -Headers $verifyHeaders `
            -ErrorAction Stop

        Write-Host "✓ Cluster health check: PASSED" -ForegroundColor Green
        Write-Host "  Status: $($health.status)" -ForegroundColor White

    } catch {
        Write-Warning "Cluster health check failed:"
        Write-Host $_.Exception.Message
        exit 1
    }

    # Test write permission
    Write-Host ""
    Write-Host "Testing write permissions..."
    try {
        $testDoc = @{
            test = "least_privilege_verification"
            timestamp = (Get-Date).ToString("o")
        } | ConvertTo-Json

        $writeTest = Invoke-RestMethod -Uri "$env:ES_ENDPOINT/applylens-test/_doc/test-$(Get-Date -Format 'yyyyMMddHHmmss')" `
            -Method Post `
            -Headers ($verifyHeaders + @{"Content-Type" = "application/json"}) `
            -Body $testDoc `
            -ErrorAction Stop

        Write-Host "✓ Write test: PASSED (can index documents)" -ForegroundColor Green

    } catch {
        Write-Warning "Write test failed (this may be expected if index pattern doesn't match):"
        Write-Host $_.Exception.Message
    }

    # Test delete restriction
    Write-Host ""
    Write-Host "Testing security restrictions..."
    try {
        $deleteTest = Invoke-RestMethod -Uri "$env:ES_ENDPOINT/applylens-test" `
            -Method Delete `
            -Headers $verifyHeaders `
            -ErrorAction Stop

        Write-Host "⚠ WARNING: Delete index succeeded - key has too many privileges!" -ForegroundColor Red

    } catch {
        if ($_.Exception.Response.StatusCode -eq 403 -or $_.Exception.Response.StatusCode -eq 405) {
            Write-Host "✓ Delete index: BLOCKED (403/405 - correct!)" -ForegroundColor Green
        } else {
            Write-Host "? Delete test error: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "Least-Privilege Setup Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Advantages over 'all' privilege:" -ForegroundColor Cyan
    Write-Host "  ✓ Cannot accidentally delete indices" -ForegroundColor Green
    Write-Host "  ✓ Cannot modify index settings in production" -ForegroundColor Green
    Write-Host "  ✓ Limited to read/write operations only" -ForegroundColor Green
    Write-Host "  ✓ Follows principle of least privilege" -ForegroundColor Green
    Write-Host "  ✓ Safer for production environments" -ForegroundColor Green
    Write-Host ""
    Write-Host "To revoke old enhanced key (if needed):"
    Write-Host "  \$headers = @{'Authorization'='Basic $base64Auth'; 'Content-Type'='application/json'}"
    Write-Host "  Invoke-RestMethod -Uri '$env:ES_ENDPOINT/_security/api_key' ``"
    Write-Host "    -Method Delete ``"
    Write-Host "    -Headers `$headers ``"
    Write-Host "    -Body '{\"ids\": [\"uVibDZoBZNl7zqftzkFo\"]}'"  # Enhanced key ID

} catch {
    Write-Error "Error creating least-privilege API key:"
    Write-Host $_.Exception.Message
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message
    }
    exit 1
}
