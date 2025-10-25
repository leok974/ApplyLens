# Create an Elasticsearch API key for ApplyLens via the cluster REST API
#
# Prerequisites:
#   - Set environment variables:
#       $env:ES_ENDPOINT = "https://YOUR-DEPLOYMENT.es.us-east-1.aws.elastic-cloud.com:9243"
#       $env:ES_USER = "elastic"
#       $env:ES_PASS = "your-password"
#   - Requires 'manage_api_key' cluster privilege
#
# Usage:
#   .\scripts\create-es-api-key.ps1

# Check prerequisites
if (-not $env:ES_ENDPOINT) {
    Write-Error "ES_ENDPOINT is not set"
    Write-Host "Example: `$env:ES_ENDPOINT = 'https://YOUR-DEPLOYMENT.es.us-east-1.aws.elastic-cloud.com:9243'"
    exit 1
}

if (-not $env:ES_USER) {
    Write-Error "ES_USER is not set"
    Write-Host "Example: `$env:ES_USER = 'elastic'"
    exit 1
}

if (-not $env:ES_PASS) {
    Write-Error "ES_PASS is not set"
    Write-Host "Example: `$env:ES_PASS = 'your-password'"
    exit 1
}

Write-Host "Creating Elasticsearch API key for ApplyLens..." -ForegroundColor Cyan
Write-Host "Endpoint: $env:ES_ENDPOINT"
Write-Host ""

# Create basic auth header
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($env:ES_USER):$($env:ES_PASS)"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Content-Type" = "application/json"
}

# API key request body
$body = @{
    name = "applylens-api"
    role_descriptors = @{
        applylens_writer = @{
            cluster = @("monitor")
            index = @(
                @{
                    names = @("gmail_emails-*")
                    privileges = @("read", "write", "create", "create_index", "manage")
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

    Write-Host "API Key created successfully:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Write-Host
    Write-Host ""

    $encoded = $response.encoded
    $apiKeyId = $response.id

    if (-not $encoded) {
        Write-Error "Could not extract encoded API key from response"
        exit 1
    }

    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "API Key Details:" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "ID:      $apiKeyId"
    Write-Host "Encoded: $encoded"
    Write-Host ""

    # Append to .env file
    Write-Host "Adding ELASTICSEARCH_API_KEY to .env file..."
    $envFile = ".env"

    if (Test-Path $envFile) {
        # Remove existing ELASTICSEARCH_API_KEY if present
        $content = Get-Content $envFile | Where-Object { $_ -notmatch '^ELASTICSEARCH_API_KEY=' }
        $content | Set-Content $envFile
    }

    Add-Content -Path $envFile -Value "ELASTICSEARCH_API_KEY=$encoded"
    Write-Host "✓ Added to .env file" -ForegroundColor Green
    Write-Host ""

    # Verify the key works
    Write-Host "Verifying API key..."
    $verifyHeaders = @{
        "Authorization" = "ApiKey $encoded"
    }

    try {
        $health = Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_cluster/health?pretty" `
            -Headers $verifyHeaders `
            -ErrorAction Stop

        Write-Host "✓ API Key verification successful!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Cluster Health:"
        $health | ConvertTo-Json -Depth 10 | Write-Host

    } catch {
        Write-Warning "API Key verification failed:"
        Write-Host $_.Exception.Message
        exit 1
    }

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "Setup Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "The ELASTICSEARCH_API_KEY has been added to .env"
    Write-Host ""
    Write-Host "To use in docker-compose.prod.yml, add:"
    Write-Host "  environment:"
    Write-Host "    - ELASTICSEARCH_API_KEY=`${ELASTICSEARCH_API_KEY}"
    Write-Host ""
    Write-Host "To revoke this key later:"
    Write-Host "  `$headers = @{'Authorization'='Basic $base64Auth'; 'Content-Type'='application/json'}"
    Write-Host "  Invoke-RestMethod -Uri '$env:ES_ENDPOINT/_security/api_key' ``"
    Write-Host "    -Method Delete ``"
    Write-Host "    -Headers `$headers ``"
    Write-Host "    -Body '{\"ids\": [\"$apiKeyId\"]}'"

} catch {
    Write-Error "Error creating API key:"
    Write-Host $_.Exception.Message
    Write-Host $_.ErrorDetails.Message
    exit 1
}
