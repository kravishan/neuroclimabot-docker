# Create Grafana dashboard ConfigMap from the JSON file
# This script creates a Kubernetes ConfigMap containing the NeuroClima Grafana dashboard

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DashboardFile = Join-Path $ScriptDir "..\..\Server\monitoring\grafana\dashboards\neuroclima-dashboard.json"

if (-not (Test-Path $DashboardFile)) {
    Write-Error "Dashboard file not found at $DashboardFile"
    exit 1
}

Write-Host "Creating ConfigMap 'grafana-dashboards' from dashboard JSON file..." -ForegroundColor Cyan

# Create the ConfigMap
kubectl create configmap grafana-dashboards `
    --from-file=neuroclima-dashboard.json="$DashboardFile" `
    --namespace=uoulu `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "✅ Dashboard ConfigMap created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Now restart Grafana to load the dashboard:" -ForegroundColor Yellow
Write-Host "kubectl rollout restart deployment/neuroclima-grafana -n uoulu" -ForegroundColor White
