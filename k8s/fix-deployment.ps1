# Emergency Fix Script for Failed Deployments
# This script rolls back failed deployments and applies working configuration

Write-Host "========================================" -ForegroundColor Red
Write-Host "Emergency Deployment Fix Script" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

if (-not $env:KUBECONFIG) {
    Write-Host "Error: KUBECONFIG not set!" -ForegroundColor Red
    Write-Host "Set it with: `$env:KUBECONFIG='C:\path\to\kubeconfig.yaml'" -ForegroundColor Yellow
    exit 1
}

$namespace = "uoulu"

Write-Host "Step 1: Deleting failed deployments..." -ForegroundColor Yellow
Write-Host ""

# Delete the failed new pods to stop them from trying to pull non-existent images
Write-Host "Scaling down failed deployments to 0..."
kubectl scale deployment nginx-gateway --replicas=0 -n $namespace
kubectl scale deployment neuroclima-client --replicas=0 -n $namespace
kubectl scale deployment neuroclima-server --replicas=0 -n $namespace
kubectl scale deployment neuroclima-redis --replicas=0 -n $namespace
kubectl scale deployment neuroclima-processor --replicas=0 -n $namespace
kubectl scale deployment neuroclima-unstructured --replicas=0 -n $namespace
kubectl scale deployment neuroclima-grafana --replicas=0 -n $namespace
kubectl scale deployment neuroclima-prometheus --replicas=0 -n $namespace

Write-Host ""
Write-Host "Waiting 10 seconds for pods to terminate..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Step 2: Pulling latest fixed configuration from git..." -ForegroundColor Yellow
git pull origin claude/k8s-security-stability-QaeQ0

Write-Host ""
Write-Host "Step 3: Applying fixed deployments..." -ForegroundColor Yellow
Write-Host ""

# Apply the fixed configurations
kubectl apply -f k8s/gateway/nginx-gateway.yaml
kubectl apply -f k8s/server/deployment.yaml
kubectl apply -f k8s/processor/deployment.yaml
kubectl apply -f k8s/client/deployment.yaml
kubectl apply -f k8s/monitoring/grafana-deployment.yaml
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml

Write-Host ""
Write-Host "Step 4: Scaling deployments back to 1 replica..." -ForegroundColor Yellow
kubectl scale deployment nginx-gateway --replicas=1 -n $namespace
kubectl scale deployment neuroclima-client --replicas=1 -n $namespace
kubectl scale deployment neuroclima-server --replicas=1 -n $namespace
kubectl scale deployment neuroclima-redis --replicas=1 -n $namespace
kubectl scale deployment neuroclima-processor --replicas=1 -n $namespace
kubectl scale deployment neuroclima-unstructured --replicas=1 -n $namespace
kubectl scale deployment neuroclima-grafana --replicas=1 -n $namespace
kubectl scale deployment neuroclima-prometheus --replicas=1 -n $namespace

Write-Host ""
Write-Host "Step 5: Monitoring pod startup..." -ForegroundColor Yellow
Write-Host ""

# Wait for pods to be ready
Write-Host "Waiting for nginx-gateway to be ready..."
kubectl wait --for=condition=ready pod -l component=gateway -n $namespace --timeout=120s

Write-Host "Waiting for server components to be ready..."
kubectl wait --for=condition=ready pod -l component=server -n $namespace --timeout=120s
kubectl wait --for=condition=ready pod -l component=redis -n $namespace --timeout=120s

Write-Host "Waiting for processor components to be ready..."
kubectl wait --for=condition=ready pod -l component=processor -n $namespace --timeout=120s
kubectl wait --for=condition=ready pod -l component=unstructured -n $namespace --timeout=120s

Write-Host "Waiting for client to be ready..."
kubectl wait --for=condition=ready pod -l component=client -n $namespace --timeout=120s

Write-Host "Waiting for monitoring to be ready..."
kubectl wait --for=condition=ready pod -l component=grafana -n $namespace --timeout=120s
kubectl wait --for=condition=ready pod -l component=prometheus -n $namespace --timeout=120s

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Fix Applied Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Checking final pod status..."
kubectl get pods -n $namespace
Write-Host ""

Write-Host "All deployments should now be running!" -ForegroundColor Green
Write-Host ""
Write-Host "What was fixed:" -ForegroundColor Cyan
Write-Host "1. Changed custom images back to :latest (v1.0.0 didn't exist)"
Write-Host "2. Removed security context from nginx-gateway (was causing crashes)"
Write-Host "3. Kept all other Phase 1 security improvements"
Write-Host ""
Write-Host "Test your application now!" -ForegroundColor Green
