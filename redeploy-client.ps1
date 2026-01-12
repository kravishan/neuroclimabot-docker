# ============================================================================
# Redeploy NeuroClima Client to Kubernetes (PowerShell)
# ============================================================================
# This script forces K8s to pull the latest client image and restart pods
# ============================================================================

# Configuration
$Namespace = "uoulu"
$Deployment = "neuroclima-client"
$KubeconfigPath = "k8s\kubeconfig.yaml"

Write-Host "============================================================================" -ForegroundColor Blue
Write-Host "NeuroClima Client - Kubernetes Redeployment" -ForegroundColor Blue
Write-Host "============================================================================" -ForegroundColor Blue
Write-Host ""

# Check if kubeconfig exists
if (-not (Test-Path $KubeconfigPath)) {
    Write-Host "Error: kubeconfig not found at $KubeconfigPath" -ForegroundColor Red
    Write-Host "Please specify the correct path to your kubeconfig file." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/4] Checking current pods..." -ForegroundColor Green
kubectl --kubeconfig $KubeconfigPath get pods -n $Namespace -l component=client

Write-Host ""
Write-Host "[2/4] Forcing pod restart to pull latest image..." -ForegroundColor Green
kubectl --kubeconfig $KubeconfigPath rollout restart deployment/$Deployment -n $Namespace
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Rollout restart failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/4] Waiting for rollout to complete..." -ForegroundColor Green
kubectl --kubeconfig $KubeconfigPath rollout status deployment/$Deployment -n $Namespace --timeout=5m
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Rollout failed to complete!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[4/4] Verifying new pods are running..." -ForegroundColor Green
kubectl --kubeconfig $KubeconfigPath get pods -n $Namespace -l component=client

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Blue
Write-Host "✅ Client successfully redeployed!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Monitor pods with:" -ForegroundColor Yellow
Write-Host "kubectl --kubeconfig $KubeconfigPath get pods -n $Namespace -w"
Write-Host ""
Write-Host "Check logs with:" -ForegroundColor Yellow
Write-Host "kubectl --kubeconfig $KubeconfigPath logs -f -n $Namespace -l component=client"
Write-Host ""
