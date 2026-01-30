# Rebuild and Deploy Client (Without Voice Input)
# This script rebuilds the Client Docker image after removing voice input features

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Rebuilding NeuroClima Client (No Voice Input)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to Client directory
Set-Location -Path "D:\Projects\docker\bot\Client"

Write-Host "[1/4] Building Docker image..." -ForegroundColor Yellow
docker build -t docker.io/raviyah/neuroclima-client:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/4] Pushing to Docker Hub..." -ForegroundColor Yellow
docker push docker.io/raviyah/neuroclima-client:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker push failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/4] Setting kubeconfig..." -ForegroundColor Yellow
$env:KUBECONFIG = "D:/Projects/docker/bot/k8s/kubeconfig.yaml"

Write-Host ""
Write-Host "[4/4] Restarting Client deployment..." -ForegroundColor Yellow
Set-Location -Path "D:\Projects\docker\bot"
kubectl rollout restart deployment neuroclima-client

Write-Host ""
Write-Host "Waiting for new pods to be ready..." -ForegroundColor Yellow
kubectl rollout status deployment neuroclima-client

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "SUCCESS! Client updated successfully" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Changes applied:" -ForegroundColor Cyan
Write-Host "  - Removed voice input (microphone recording)" -ForegroundColor White
Write-Host "  - Removed RecordRTC library" -ForegroundColor White
Write-Host "  - Removed 'local network access' warning" -ForegroundColor White
Write-Host "  - Kept text-to-speech (read responses aloud)" -ForegroundColor White
Write-Host ""
Write-Host "Verify at: https://bot.neuroclima.eu/" -ForegroundColor Cyan
Write-Host ""
