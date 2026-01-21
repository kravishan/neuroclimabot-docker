# ============================================================================
# NeuroClima Initial Deployment Script - PowerShell
# ============================================================================
# This script deploys the NeuroClima application to Kubernetes in the correct order
# with 1 replica per service for initial deployment.
#
# Prerequisites:
#   - kubectl installed and configured
#   - KUBECONFIG environment variable set
#   - Access to uoulu namespace
#
# Usage:
#   .\k8s\deploy-initial.ps1
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NeuroClima Initial Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if KUBECONFIG is set
if (-not $env:KUBECONFIG) {
    Write-Host "ERROR: KUBECONFIG environment variable is not set!" -ForegroundColor Red
    Write-Host "Set it with: `$env:KUBECONFIG='C:\path\to\kubeconfig.yaml'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using kubeconfig: $env:KUBECONFIG" -ForegroundColor Green
Write-Host ""

# Check kubectl connectivity
Write-Host "Checking cluster connectivity..." -ForegroundColor Yellow
kubectl cluster-info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cannot connect to Kubernetes cluster!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Connected to cluster" -ForegroundColor Green
Write-Host ""

# Function to wait for deployment
function Wait-ForDeployment {
    param(
        [string]$Name,
        [string]$Namespace = "uoulu",
        [int]$TimeoutSeconds = 300
    )

    Write-Host "Waiting for $Name to be ready..." -ForegroundColor Yellow
    kubectl wait --for=condition=available --timeout=${TimeoutSeconds}s deployment/$Name -n $Namespace

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $Name is ready!" -ForegroundColor Green
    } else {
        Write-Host "✗ $Name failed to become ready within ${TimeoutSeconds}s" -ForegroundColor Red
        return $false
    }
    return $true
}

# Function to check pod status
function Show-PodStatus {
    param(
        [string]$Component,
        [string]$Namespace = "uoulu"
    )

    Write-Host "Pod status for $Component`:" -ForegroundColor Cyan
    kubectl get pods -n $Namespace -l component=$Component -o wide
    Write-Host ""
}

# ============================================================================
# Deployment Order
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 1: Deploy Processor & Unstructured" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Deploying processor service..." -ForegroundColor Yellow
kubectl apply -f k8s/processor/service.yaml
Write-Host ""

Write-Host "Deploying processor & unstructured deployments..." -ForegroundColor Yellow
kubectl apply -f k8s/processor/deployment.yaml
Write-Host ""

# Wait for unstructured first (processor depends on it)
if (-not (Wait-ForDeployment -Name "neuroclima-unstructured" -TimeoutSeconds 180)) {
    Write-Host "Deployment failed at unstructured. Exiting." -ForegroundColor Red
    exit 1
}
Show-PodStatus -Component "unstructured"

# Wait for processor
if (-not (Wait-ForDeployment -Name "neuroclima-processor" -TimeoutSeconds 300)) {
    Write-Host "Deployment failed at processor. Exiting." -ForegroundColor Red
    exit 1
}
Show-PodStatus -Component "processor"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 2: Deploy Redis" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Deploying Redis service..." -ForegroundColor Yellow
kubectl apply -f k8s/server/service.yaml
Write-Host ""

# Deploy only Redis from server/deployment.yaml
# Since Redis and Server are in the same file, we'll apply the whole file
# but Redis will start first as it's defined first in the file
Write-Host "Deploying Redis & Server (Redis will start first)..." -ForegroundColor Yellow
kubectl apply -f k8s/server/deployment.yaml
Write-Host ""

# Wait for Redis
if (-not (Wait-ForDeployment -Name "neuroclima-redis" -TimeoutSeconds 120)) {
    Write-Host "Deployment failed at Redis. Exiting." -ForegroundColor Red
    exit 1
}
Show-PodStatus -Component "redis"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 3: Verify Server is Ready" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Server should already be starting since it's in the same file as Redis
# Just wait for it to be ready
if (-not (Wait-ForDeployment -Name "neuroclima-server" -TimeoutSeconds 180)) {
    Write-Host "Deployment failed at server. Exiting." -ForegroundColor Red
    exit 1
}
Show-PodStatus -Component "server"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 4: Deploy Client" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Deploying client service..." -ForegroundColor Yellow
kubectl apply -f k8s/client/service.yaml
Write-Host ""

Write-Host "Deploying client nginx config..." -ForegroundColor Yellow
kubectl apply -f k8s/client/nginx-config.yaml
Write-Host ""

Write-Host "Deploying client deployment..." -ForegroundColor Yellow
kubectl apply -f k8s/client/deployment.yaml
Write-Host ""

# Wait for client
if (-not (Wait-ForDeployment -Name "neuroclima-client" -TimeoutSeconds 120)) {
    Write-Host "Deployment failed at client. Exiting." -ForegroundColor Red
    exit 1
}
Show-PodStatus -Component "client"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 5: Deploy Traefik IngressRoute" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Deploying Traefik IngressRoute..." -ForegroundColor Yellow
kubectl apply -f k8s/base/traefik-ingressroute.yaml
Write-Host ""

Write-Host "Checking IngressRoute status..." -ForegroundColor Yellow
kubectl get ingressroute -n uoulu
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "All pods:" -ForegroundColor Yellow
kubectl get pods -n uoulu -l app=neuroclima
Write-Host ""

Write-Host "All services:" -ForegroundColor Yellow
kubectl get svc -n uoulu -l app=neuroclima
Write-Host ""

Write-Host "IngressRoute:" -ForegroundColor Yellow
kubectl get ingressroute -n uoulu
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Initial Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Your application should now be accessible at:" -ForegroundColor Cyan
Write-Host "  https://bot.neuroclima.eu/" -ForegroundColor White
Write-Host ""

Write-Host "To scale to 2 replicas for production (after verifying deployment):" -ForegroundColor Yellow
Write-Host "  kubectl scale deployment neuroclima-client --replicas=2 -n uoulu" -ForegroundColor White
Write-Host "  kubectl scale deployment neuroclima-server --replicas=2 -n uoulu" -ForegroundColor White
Write-Host ""

Write-Host "To monitor the deployment:" -ForegroundColor Yellow
Write-Host "  kubectl get pods -n uoulu -w" -ForegroundColor White
Write-Host ""

Write-Host "To check logs:" -ForegroundColor Yellow
Write-Host "  kubectl logs -n uoulu -l component=server --tail=50" -ForegroundColor White
Write-Host "  kubectl logs -n uoulu -l component=processor --tail=50" -ForegroundColor White
Write-Host "  kubectl logs -n uoulu -l component=client --tail=50" -ForegroundColor White
Write-Host ""
