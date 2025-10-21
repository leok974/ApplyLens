# Gitleaks wrapper script for Windows (Docker-based)
# Usage: .\gitleaks.ps1 detect --source . --no-git -v

# Pull the latest gitleaks image if not present
$image = "zricethezav/gitleaks:v8.18.4"
docker image inspect $image 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pulling gitleaks Docker image..."
    docker pull $image
}

# Run gitleaks in Docker
$workdir = (Get-Location).Path
docker run --rm -v "${workdir}:/path" $image $args
exit $LASTEXITCODE
