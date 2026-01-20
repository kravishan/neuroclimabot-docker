#!/bin/bash

# NeuroClima Quick Deployment Script for Linux/Mac
# This script helps you deploy NeuroClima to your Kubernetes cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="uoulu"
KUBECONFIG_PATH="./kubeconfig.yaml"

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check prerequisites
info "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    error "kubectl not found. Please install kubectl first."
fi

if [ ! -f "$KUBECONFIG_PATH" ]; then
    error "kubeconfig.yaml not found at $KUBECONFIG_PATH"
fi

info "Prerequisites check passed ✓"

# Check if namespace exists, create if it doesn't
info "Checking namespace..."
if ! kubectl --kubeconfig=$KUBECONFIG_PATH get namespace $NAMESPACE &> /dev/null; then
    info "Creating namespace: $NAMESPACE"
    kubectl --kubeconfig=$KUBECONFIG_PATH create namespace $NAMESPACE
else
    info "Namespace $NAMESPACE already exists"
fi

# Check if configmap.yaml exists
if [ ! -f "base/configmap.yaml" ]; then
    error "base/configmap.yaml not found. Please create it from configmap-example.yaml"
fi

# Check if secrets-ready.yaml exists
if [ ! -f "base/secrets-ready.yaml" ]; then
    error "base/secrets-ready.yaml not found. Please create it from secrets.yaml.template"
fi

info "Configuration files found ✓"

# Deploy base configuration
info "Deploying base configuration (ConfigMaps and Secrets)..."
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f base/configmap.yaml -n $NAMESPACE
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f base/secrets-ready.yaml -n $NAMESPACE
info "Base configuration deployed ✓"

# Deploy Processor
info "Deploying Processor service..."
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f processor/pvc.yaml -n $NAMESPACE
sleep 2
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f processor/deployment.yaml -n $NAMESPACE
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f processor/service.yaml -n $NAMESPACE
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f processor/graphrag-settings-configmap.yaml -n $NAMESPACE
info "Processor deployed ✓"

# Deploy Server (includes Redis)
info "Deploying Server service (includes Redis)..."
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f server/pvc.yaml -n $NAMESPACE
sleep 2
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f server/deployment.yaml -n $NAMESPACE
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f server/service.yaml -n $NAMESPACE
info "Server deployed ✓"

# Deploy Client
info "Deploying Client service..."
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f client/deployment.yaml -n $NAMESPACE
kubectl --kubeconfig=$KUBECONFIG_PATH apply -f client/service.yaml -n $NAMESPACE
info "Client deployed ✓"

# Optional: Deploy Nginx Gateway
read -p "Do you want to deploy the Nginx Gateway? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info "Deploying Nginx Gateway..."
    kubectl --kubeconfig=$KUBECONFIG_PATH apply -f gateway/nginx-gateway.yaml -n $NAMESPACE
    info "Nginx Gateway deployed ✓"
fi

# Show deployment status
info "Checking deployment status..."
echo ""
echo "==================== PODS ===================="
kubectl --kubeconfig=$KUBECONFIG_PATH get pods -n $NAMESPACE
echo ""
echo "==================== SERVICES ===================="
kubectl --kubeconfig=$KUBECONFIG_PATH get services -n $NAMESPACE
echo ""
echo "==================== PVCs ===================="
kubectl --kubeconfig=$KUBECONFIG_PATH get pvc -n $NAMESPACE
echo ""

info "Deployment completed! ✓"
echo ""
warn "To access the application, you can use port-forwarding:"
echo "  kubectl --kubeconfig=$KUBECONFIG_PATH port-forward svc/neuroclima-client 8080:80 -n $NAMESPACE"
echo ""
warn "Then open your browser at: http://localhost:8080"
echo ""
info "To check logs:"
echo "  kubectl --kubeconfig=$KUBECONFIG_PATH logs -f deployment/neuroclima-server -n $NAMESPACE"
echo "  kubectl --kubeconfig=$KUBECONFIG_PATH logs -f deployment/neuroclima-processor -n $NAMESPACE"
echo "  kubectl --kubeconfig=$KUBECONFIG_PATH logs -f deployment/neuroclima-client -n $NAMESPACE"
