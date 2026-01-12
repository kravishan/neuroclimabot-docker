# ============================================================================
# Rebuild and Push NeuroClima Client Docker Image (PowerShell)
# ============================================================================
# This script rebuilds the client Docker image with updated .env changes
# and pushes it to Docker Hub
# ============================================================================

# Configuration
$DockerUsername = "raviyah"
$ImageName = "neuroclima-client"
$Tag = "latest"
$FullImage = "docker.io/$DockerUsername/${ImageName}:$Tag"

Write-Host "============================================================================" -ForegroundColor Blue
Write-Host "NeuroClima Client - Docker Image Rebuild" -ForegroundColor Blue
Write-Host "============================================================================" -ForegroundColor Blue
Write-Host ""

# Check if .env file exists
if (-not (Test-Path "Client\.env")) {
    Write-Host "Warning: Client\.env file not found!" -ForegroundColor Yellow
    Write-Host "Using .env.example as template..." -ForegroundColor Yellow
    Copy-Item "Client\.env.example" "Client\.env"
    Write-Host "Please edit Client\.env with your configuration and run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/4] Building Docker image..." -ForegroundColor Green
Set-Location Client
docker build -t $FullImage .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker build failed!" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "[2/4] Tagging image..." -ForegroundColor Green
docker tag $FullImage "$DockerUsername/${ImageName}:$Tag"

Write-Host ""
Write-Host "[3/4] Checking Docker login status..." -ForegroundColor Green
$dockerInfo = docker info 2>&1 | Select-String "Username"
if (-not $dockerInfo) {
    Write-Host "Not logged in to Docker Hub. Please log in:" -ForegroundColor Yellow
    docker login
}

Write-Host ""
Write-Host "[4/4] Pushing image to Docker Hub..." -ForegroundColor Green
docker push $FullImage
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker push failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Blue
Write-Host "✅ Image successfully built and pushed!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Image: $FullImage"
Write-Host ""
Write-Host "Next step: Run .\redeploy-client.ps1 to update K8s pods" -ForegroundColor Yellow
Write-Host ""
