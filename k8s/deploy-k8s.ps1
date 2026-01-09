# NeuroClima Kubernetes Deployment Script for Windows
# This script will clean up existing deployments and deploy fresh

param(
    [Parameter(Mandatory=$false)]
    [string]$KubeConfig = ".\kubeconfig.yaml",

    [Parameter(Mandatory=$false)]
    [ValidateSet("cleanup", "deploy", "all", "status")]
    [string]$Action = "all"
)

# Configuration
$NAMESPACE = "uoulu"
$KUBECONFIG_PATH = $KubeConfig

# Color functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check prerequisites
function Check-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check kubectl
    $kubectlInstalled = Get-Command kubectl -ErrorAction SilentlyContinue
    if (-not $kubectlInstalled) {
        Write-Error-Message "kubectl not found. Please install kubectl."
        Write-Host "Download from: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/"
        exit 1
    }

    # Check kubeconfig file
    if (-not (Test-Path $KUBECONFIG_PATH)) {
        Write-Error-Message "kubeconfig.yaml not found at $KUBECONFIG_PATH"
        exit 1
    }

    Write-Info "Prerequisites check passed ✓"
}

# Cleanup existing deployments
function Cleanup-Deployments {
    Write-Info "Starting cleanup of existing deployments..."

    # Ask for confirmation
    $confirmation = Read-Host "This will delete all NeuroClima resources. Are you sure? (yes/no)"
    if ($confirmation -ne "yes") {
        Write-Info "Cleanup cancelled"
        return
    }

    Write-Info "Deleting client resources..."
    kubectl --kubeconfig=$KUBECONFIG_PATH delete -f client/deployment.yaml --ignore-not-found=true -n $NAMESPACE
    kubectl --kubeconfig=$KUBECONFIG_PATH delete -f client/service.yaml --ignore-not-found=true -n $NAMESPACE

    Write-Info "Deleting server resources..."
    kubectl --kubeconfig=$KUBECONFIG_PATH delete -f server/deployment.yaml --ignore-not-found=true -n $NAMESPACE
    kubectl --kubeconfig=$KUBECONFIG_PATH delete -f server/service.yaml --ignore-not-found=true -n $NAMESPACE

    Write-Info "Deleting processor resources..."
    kubectl --kubeconfig=$KUBECONFIG_PATH delete -f processor/deployment.yaml --ignore-not-found=true -n $NAMESPACE
    kubectl --kubeconfig=$KUBECONFIG_PATH delete -f processor/service.yaml --ignore-not-found=true -n $NAMESPACE

    Write-Info "Deleting ingress..."
    kubectl --kubeconfig=$KUBECONFIG_PATH delete -f base/ingress.yaml --ignore-not-found=true -n $NAMESPACE

    # Ask about PVCs
    Write-Warn "Do you want to delete PVCs (Persistent Volume Claims)? This will DELETE ALL DATA!"
    $deletePVC = Read-Host "Delete PVCs? (yes/no)"
    if ($deletePVC -eq "yes") {
        Write-Info "Deleting PVCs..."
        kubectl --kubeconfig=$KUBECONFIG_PATH delete -f processor/pvc.yaml --ignore-not-found=true -n $NAMESPACE
        kubectl --kubeconfig=$KUBECONFIG_PATH delete -f server/pvc.yaml --ignore-not-found=true -n $NAMESPACE

        # Wait for PVCs to be deleted
        Write-Info "Waiting for PVCs to be deleted..."
        Start-Sleep -Seconds 10
    }

    Write-Info "Cleanup completed ✓"
}

# Deploy base configuration
function Deploy-Base {
    Write-Info "Deploying base configuration..."

    # Check if configmap needs updating
    $configMapContent = Get-Content "base/configmap.yaml" -Raw
    if ($configMapContent -match "your_ollama_server_url_here" -or
        $configMapContent -match "your_minio_server_endpoint_here" -or
        $configMapContent -match "your_milvus_server_host_here") {
        Write-Warn "IMPORTANT: You need to update the following in base/configmap.yaml:"
        Write-Warn "  - OLLAMA_API_URL"
        Write-Warn "  - MINIO_ENDPOINT"
        Write-Warn "  - MILVUS_HOST"
        Write-Warn "  - GRAPHRAG URLs (multiple locations)"
        $continue = Read-Host "Have you updated these values? (yes/no)"
        if ($continue -ne "yes") {
            Write-Error-Message "Please update base/configmap.yaml first"
            exit 1
        }
    }

    # Apply configmaps
    Write-Info "Applying configmaps..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f base/configmap.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to apply configmap"
        exit 1
    }

    # Apply secrets
    Write-Info "Applying secrets..."
    if (Test-Path "base/secrets-ready.yaml") {
        kubectl --kubeconfig=$KUBECONFIG_PATH apply -f base/secrets-ready.yaml -n $NAMESPACE
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Message "Failed to apply secrets"
            exit 1
        }
    } else {
        Write-Error-Message "base/secrets-ready.yaml not found"
        exit 1
    }

    Write-Info "Base configuration deployed ✓"
}

# Deploy Processor
function Deploy-Processor {
    Write-Info "Deploying Processor service..."

    # Apply PVCs first
    Write-Info "Creating Processor PVCs..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f processor/pvc.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Processor PVCs"
        exit 1
    }

    # Wait for PVCs to be bound
    Write-Info "Waiting for PVCs to be bound..."
    Start-Sleep -Seconds 5

    # Apply deployment
    Write-Info "Creating Processor deployment..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f processor/deployment.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Processor deployment"
        exit 1
    }

    # Apply service
    Write-Info "Creating Processor service..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f processor/service.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Processor service"
        exit 1
    }

    Write-Info "Processor deployed ✓"
}

# Deploy Server (includes Redis)
function Deploy-Server {
    Write-Info "Deploying Server service (includes Redis)..."

    # Apply PVCs first
    Write-Info "Creating Server PVCs..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f server/pvc.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Server PVCs"
        exit 1
    }

    # Wait for PVCs to be bound
    Write-Info "Waiting for PVCs to be bound..."
    Start-Sleep -Seconds 5

    # Apply deployment
    Write-Info "Creating Server deployment..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f server/deployment.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Server deployment"
        exit 1
    }

    # Apply service
    Write-Info "Creating Server service..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f server/service.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Server service"
        exit 1
    }

    Write-Info "Server deployed ✓"
}

# Deploy Client
function Deploy-Client {
    Write-Info "Deploying Client service..."

    # Check if client deployment needs updating
    $clientContent = Get-Content "client/deployment.yaml" -Raw
    if ($clientContent -match "YOUR_DOMAIN") {
        Write-Warn "IMPORTANT: You need to update YOUR_DOMAIN in client/deployment.yaml"
        $continue = Read-Host "Have you updated the domain? (yes/no)"
        if ($continue -ne "yes") {
            Write-Warn "Skipping domain update - using placeholder values"
        }
    }

    # Apply deployment
    Write-Info "Creating Client deployment..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f client/deployment.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Client deployment"
        exit 1
    }

    # Apply service
    Write-Info "Creating Client service..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f client/service.yaml -n $NAMESPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to create Client service"
        exit 1
    }

    Write-Info "Client deployed ✓"
}

# Check deployment status
function Check-Status {
    Write-Info "Checking deployment status..."

    Write-Host "`n=== PODS ===" -ForegroundColor Cyan
    kubectl --kubeconfig=$KUBECONFIG_PATH get pods -n $NAMESPACE

    Write-Host "`n=== SERVICES ===" -ForegroundColor Cyan
    kubectl --kubeconfig=$KUBECONFIG_PATH get svc -n $NAMESPACE

    Write-Host "`n=== PVCs ===" -ForegroundColor Cyan
    kubectl --kubeconfig=$KUBECONFIG_PATH get pvc -n $NAMESPACE

    Write-Host "`n=== CONFIGMAPS ===" -ForegroundColor Cyan
    kubectl --kubeconfig=$KUBECONFIG_PATH get configmap -n $NAMESPACE

    Write-Host "`n=== SECRETS ===" -ForegroundColor Cyan
    kubectl --kubeconfig=$KUBECONFIG_PATH get secret -n $NAMESPACE
}

# Main execution
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  NeuroClima Kubernetes Deployment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Check-Prerequisites

switch ($Action) {
    "cleanup" {
        Cleanup-Deployments
    }
    "deploy" {
        Deploy-Base
        Start-Sleep -Seconds 2
        Deploy-Processor
        Start-Sleep -Seconds 3
        Deploy-Server
        Start-Sleep -Seconds 3
        Deploy-Client
        Write-Host ""
        Write-Info "Deployment complete! Checking status..."
        Start-Sleep -Seconds 5
        Check-Status
    }
    "all" {
        Cleanup-Deployments
        Write-Host ""
        Write-Info "Waiting 10 seconds before starting deployment..."
        Start-Sleep -Seconds 10
        Deploy-Base
        Start-Sleep -Seconds 2
        Deploy-Processor
        Start-Sleep -Seconds 3
        Deploy-Server
        Start-Sleep -Seconds 3
        Deploy-Client
        Write-Host ""
        Write-Info "Deployment complete! Checking status..."
        Start-Sleep -Seconds 5
        Check-Status
    }
    "status" {
        Check-Status
    }
}

Write-Host ""
Write-Info "Script completed!"
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  Check logs:    kubectl --kubeconfig=$KUBECONFIG_PATH logs -f deployment/neuroclima-server -n $NAMESPACE" -ForegroundColor Gray
Write-Host "  Check pods:    kubectl --kubeconfig=$KUBECONFIG_PATH get pods -n $NAMESPACE" -ForegroundColor Gray
Write-Host "  Describe pod:  kubectl --kubeconfig=$KUBECONFIG_PATH describe pod <pod-name> -n $NAMESPACE" -ForegroundColor Gray
