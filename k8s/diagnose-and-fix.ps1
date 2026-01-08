# NeuroClima Kubernetes Configuration Diagnostic and Fix Script
# This script helps diagnose and fix configuration issues

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "NeuroClima Configuration Diagnostic" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if kubectl is available
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

Write-Host "1. Checking current ConfigMap values in cluster..." -ForegroundColor Yellow
Write-Host ""

# Get the actual values from the cluster
Write-Host "Milvus Configuration:" -ForegroundColor Green
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MILVUS_HOST}' 2>$null
Write-Host " = MILVUS_HOST"
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MILVUS_PORT}' 2>$null
Write-Host " = MILVUS_PORT"
Write-Host ""

Write-Host "MinIO Configuration:" -ForegroundColor Green
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MINIO_ENDPOINT}' 2>$null
Write-Host " = MINIO_ENDPOINT"
kubectl get configmap server-config -n uoulu -o jsonpath='{.data.MINIO_SECURE}' 2>$null
Write-Host " = MINIO_SECURE (from server-config)"
Write-Host ""

Write-Host "Ollama Configuration:" -ForegroundColor Green
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.OLLAMA_API_URL}' 2>$null
Write-Host " = OLLAMA_API_URL"
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.OLLAMA_HOST}' 2>$null
Write-Host " = OLLAMA_HOST"
Write-Host ""

Write-Host "2. Checking Secret..." -ForegroundColor Yellow
$secretExists = kubectl get secret neuroclima-secrets -n uoulu -o jsonpath='{.metadata.name}' 2>$null
if ($secretExists -eq "neuroclima-secrets") {
    Write-Host "✓ Secret 'neuroclima-secrets' exists" -ForegroundColor Green

    # Check if MILVUS_USER and MILVUS_PASSWORD keys exist
    $keys = kubectl get secret neuroclima-secrets -n uoulu -o jsonpath='{.data}' | ConvertFrom-Json | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name

    if ($keys -contains "MILVUS_USER") {
        Write-Host "✓ MILVUS_USER key exists in secret" -ForegroundColor Green
    } else {
        Write-Host "✗ MILVUS_USER key MISSING in secret" -ForegroundColor Red
    }

    if ($keys -contains "MILVUS_PASSWORD") {
        Write-Host "✓ MILVUS_PASSWORD key exists in secret" -ForegroundColor Green
    } else {
        Write-Host "✗ MILVUS_PASSWORD key MISSING in secret" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Secret 'neuroclima-secrets' NOT FOUND" -ForegroundColor Red
}

Write-Host ""
Write-Host "3. Checking if values contain placeholders..." -ForegroundColor Yellow

$milvusHost = kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MILVUS_HOST}' 2>$null
$minioEndpoint = kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MINIO_ENDPOINT}' 2>$null
$ollamaUrl = kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.OLLAMA_API_URL}' 2>$null

$hasPlaceholders = $false

if ($milvusHost -like "*your*" -or $milvusHost -like "*here*") {
    Write-Host "✗ MILVUS_HOST still has placeholder value: $milvusHost" -ForegroundColor Red
    $hasPlaceholders = $true
}

if ($minioEndpoint -like "*your*" -or $minioEndpoint -like "*here*") {
    Write-Host "✗ MINIO_ENDPOINT still has placeholder value: $minioEndpoint" -ForegroundColor Red
    $hasPlaceholders = $true
}

if ($ollamaUrl -like "*your*" -or $ollamaUrl -like "*here*") {
    Write-Host "✗ OLLAMA_API_URL still has placeholder value: $ollamaUrl" -ForegroundColor Red
    $hasPlaceholders = $true
}

if (-not $hasPlaceholders) {
    Write-Host "✓ No placeholder values detected" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Diagnosis Complete" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

if ($hasPlaceholders) {
    Write-Host "PROBLEM FOUND: ConfigMap contains placeholder values" -ForegroundColor Red
    Write-Host ""
    Write-Host "To fix this, you need to edit k8s/base/configmap.yaml with your actual VM endpoints:" -ForegroundColor Yellow
    Write-Host "1. Open k8s/base/configmap.yaml in a text editor" -ForegroundColor White
    Write-Host "2. Update these values in the 'neuroclima-config' section:" -ForegroundColor White
    Write-Host "   MILVUS_HOST: 'YOUR_VM_IP_OR_HOSTNAME'" -ForegroundColor White
    Write-Host "   MILVUS_PORT: '19530'" -ForegroundColor White
    Write-Host "   MINIO_ENDPOINT: 'YOUR_VM_IP_OR_HOSTNAME:9000'" -ForegroundColor White
    Write-Host "   OLLAMA_API_URL: 'http://YOUR_VM_IP_OR_HOSTNAME:11434'" -ForegroundColor White
    Write-Host "   OLLAMA_HOST: 'YOUR_VM_IP_OR_HOSTNAME'" -ForegroundColor White
    Write-Host "3. Save the file" -ForegroundColor White
    Write-Host "4. Run: kubectl apply -f k8s/base/configmap.yaml" -ForegroundColor White
    Write-Host "5. Run: kubectl rollout restart deployment/neuroclima-server -n uoulu" -ForegroundColor White
} else {
    Write-Host "ConfigMap values look correct." -ForegroundColor Green
    Write-Host "If the server is still failing, check the logs:" -ForegroundColor Yellow
    Write-Host "kubectl logs -f -l component=server -n uoulu" -ForegroundColor White
}
