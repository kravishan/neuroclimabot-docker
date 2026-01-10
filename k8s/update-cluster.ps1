# Quick Update Script for Kubernetes Cluster (PowerShell)
# Run this after pulling latest changes from git

Write-Host "========================================" -ForegroundColor Green
Write-Host "Kubernetes Cluster Update Script" -ForegroundColor Green
Write-Host "Phase 1: Security & Nginx Gateway" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if KUBECONFIG is set
if (-not $env:KUBECONFIG) {
    Write-Host "Warning: KUBECONFIG not set. Using default." -ForegroundColor Yellow
    Write-Host "Set it with: `$env:KUBECONFIG='C:\path\to\kubeconfig.yaml'" -ForegroundColor Yellow
    Write-Host ""
}

$namespace = "uoulu"

function Wait-ForRollout {
    param($deployment)
    Write-Host "Waiting for $deployment to roll out..." -ForegroundColor Yellow
    kubectl rollout status deployment/$deployment -n $namespace --timeout=5m
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $deployment updated successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ $deployment rollout failed" -ForegroundColor Red
        return $false
    }
    return $true
}

Write-Host "Step 1: Updating ConfigMaps..." -ForegroundColor Yellow
kubectl apply -f k8s/gateway/nginx-gateway.yaml
kubectl apply -f k8s/client/nginx-config.yaml
Write-Host "✓ ConfigMaps updated" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Updating Deployments..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Updating Server deployment (Redis + Server)..."
kubectl apply -f k8s/server/deployment.yaml
Wait-ForRollout "neuroclima-redis"
Wait-ForRollout "neuroclima-server"
Write-Host ""

Write-Host "Updating Processor deployment (Unstructured + Processor)..."
kubectl apply -f k8s/processor/deployment.yaml
Wait-ForRollout "neuroclima-unstructured"
Wait-ForRollout "neuroclima-processor"
Write-Host ""

Write-Host "Updating Client deployment..."
kubectl apply -f k8s/client/deployment.yaml
Wait-ForRollout "neuroclima-client"
Write-Host ""

Write-Host "Updating Nginx Gateway..."
kubectl apply -f k8s/gateway/nginx-gateway.yaml
Wait-ForRollout "nginx-gateway"
Write-Host ""

Write-Host "Updating Monitoring (Grafana + Prometheus)..."
kubectl apply -f k8s/monitoring/grafana-deployment.yaml
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml
Wait-ForRollout "neuroclima-grafana"
Wait-ForRollout "neuroclima-prometheus"
Write-Host ""

Write-Host "Step 3: Updating Ingress..." -ForegroundColor Yellow
kubectl apply -f k8s/base/ingress-production.yaml
Write-Host "✓ Ingress updated" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Update Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Checking pod status..."
kubectl get pods -n $namespace
Write-Host ""

Write-Host "All updates applied successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Test your application via ngrok URL"
Write-Host "2. Verify all routes work: /, /server/*, /processor/*"
Write-Host "3. Check logs if anything is not working:"
Write-Host "   kubectl logs deployment/<name> -n $namespace"
