#!/bin/bash

# NeuroClima Kubernetes Deployment Script
# Usage: ./deploy.sh [build|deploy|update|delete|status]

set -e

# Configuration
NAMESPACE="uoulu"
KUBECONFIG_FILE="${KUBECONFIG_FILE:-./kubeconfig.yaml}"
REGISTRY="${REGISTRY:-docker.io/yourusername}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "docker not found. Please install docker."
        exit 1
    fi

    if [ ! -f "$KUBECONFIG_FILE" ]; then
        log_error "kubeconfig.yaml not found at $KUBECONFIG_FILE"
        exit 1
    fi

    log_info "Prerequisites check passed ✓"
}

build_images() {
    log_info "Building Docker images..."

    if [ -z "$REGISTRY" ]; then
        log_error "REGISTRY environment variable not set"
        exit 1
    fi

    # Build Processor
    log_info "Building processor image..."
    docker build -t $REGISTRY/neuroclima-processor:latest ../Processor

    # Build Server
    log_info "Building server image..."
    docker build -t $REGISTRY/neuroclima-server:latest ../Server

    # Build Client
    log_info "Building client image..."
    docker build -t $REGISTRY/neuroclima-client:latest ../Client

    log_info "Images built successfully ✓"
}

push_images() {
    log_info "Pushing Docker images to registry..."

    docker push $REGISTRY/neuroclima-processor:latest
    docker push $REGISTRY/neuroclima-server:latest
    docker push $REGISTRY/neuroclima-client:latest

    log_info "Images pushed successfully ✓"
}

update_manifests() {
    log_info "Updating manifests with registry: $REGISTRY"

    # Create temporary files with updated registry
    sed "s|YOUR_REGISTRY|$REGISTRY|g" processor/deployment.yaml > processor/deployment.yaml.tmp
    sed "s|YOUR_REGISTRY|$REGISTRY|g" server/deployment.yaml > server/deployment.yaml.tmp
    sed "s|YOUR_REGISTRY|$REGISTRY|g" client/deployment.yaml > client/deployment.yaml.tmp

    mv processor/deployment.yaml.tmp processor/deployment.yaml
    mv server/deployment.yaml.tmp server/deployment.yaml
    mv client/deployment.yaml.tmp client/deployment.yaml

    log_info "Manifests updated ✓"
}

deploy_base() {
    log_info "Deploying base configuration..."

    if [ ! -f base/secrets.yaml ]; then
        log_warn "secrets.yaml not found. Creating from template..."
        cp base/secrets.yaml.template base/secrets.yaml
        log_warn "Please edit base/secrets.yaml with your actual credentials!"
        read -p "Press enter when ready to continue..."
    fi

    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f base/configmap.yaml
    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f base/secrets.yaml

    log_info "Base configuration deployed ✓"
}

deploy_processor() {
    log_info "Deploying Processor service..."

    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f processor/pvc.yaml
    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f processor/deployment.yaml
    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f processor/service.yaml

    log_info "Processor deployed ✓"
}

deploy_server() {
    log_info "Deploying Server service..."

    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f server/pvc.yaml
    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f server/deployment.yaml
    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f server/service.yaml

    log_info "Server deployed ✓"
}

deploy_client() {
    log_info "Deploying Client service..."

    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f client/deployment.yaml
    kubectl --kubeconfig=$KUBECONFIG_FILE apply -f client/service.yaml

    log_info "Client deployed ✓"
}

deploy_ingress() {
    log_info "Deploying Ingress..."

    if grep -q "YOUR_DOMAIN" base/ingress.yaml; then
        log_warn "Please update YOUR_DOMAIN in base/ingress.yaml first"
        read -p "Skip ingress deployment? (y/n): " skip
        if [ "$skip" != "y" ]; then
            kubectl --kubeconfig=$KUBECONFIG_FILE apply -f base/ingress.yaml
        fi
    else
        kubectl --kubeconfig=$KUBECONFIG_FILE apply -f base/ingress.yaml
    fi

    log_info "Ingress deployed ✓"
}

deploy_all() {
    log_info "Deploying all services..."

    deploy_base
    sleep 2
    deploy_processor
    sleep 2
    deploy_server
    sleep 2
    deploy_client

    read -p "Deploy ingress? (y/n): " deploy_ing
    if [ "$deploy_ing" = "y" ]; then
        deploy_ingress
    fi

    log_info "All services deployed ✓"
}

check_status() {
    log_info "Checking deployment status..."

    echo ""
    log_info "Pods:"
    kubectl --kubeconfig=$KUBECONFIG_FILE get pods -n $NAMESPACE

    echo ""
    log_info "Services:"
    kubectl --kubeconfig=$KUBECONFIG_FILE get svc -n $NAMESPACE

    echo ""
    log_info "PVCs:"
    kubectl --kubeconfig=$KUBECONFIG_FILE get pvc -n $NAMESPACE

    echo ""
    log_info "Ingress:"
    kubectl --kubeconfig=$KUBECONFIG_FILE get ingress -n $NAMESPACE
}

delete_all() {
    log_warn "This will delete all NeuroClima resources!"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" = "yes" ]; then
        log_info "Deleting all resources..."

        kubectl --kubeconfig=$KUBECONFIG_FILE delete -f client/ --ignore-not-found=true
        kubectl --kubeconfig=$KUBECONFIG_FILE delete -f server/ --ignore-not-found=true
        kubectl --kubeconfig=$KUBECONFIG_FILE delete -f processor/ --ignore-not-found=true
        kubectl --kubeconfig=$KUBECONFIG_FILE delete -f base/ingress.yaml --ignore-not-found=true

        read -p "Delete PVCs (this will delete data)? (yes/no): " delete_pvc
        if [ "$delete_pvc" = "yes" ]; then
            kubectl --kubeconfig=$KUBECONFIG_FILE delete pvc --all -n $NAMESPACE
        fi

        log_info "Resources deleted ✓"
    else
        log_info "Deletion cancelled"
    fi
}

update_deployment() {
    log_info "Updating deployment..."

    read -p "Update which service? (processor/server/client/all): " service

    case $service in
        processor)
            kubectl --kubeconfig=$KUBECONFIG_FILE apply -f processor/deployment.yaml
            ;;
        server)
            kubectl --kubeconfig=$KUBECONFIG_FILE apply -f server/deployment.yaml
            ;;
        client)
            kubectl --kubeconfig=$KUBECONFIG_FILE apply -f client/deployment.yaml
            ;;
        all)
            kubectl --kubeconfig=$KUBECONFIG_FILE apply -f processor/deployment.yaml
            kubectl --kubeconfig=$KUBECONFIG_FILE apply -f server/deployment.yaml
            kubectl --kubeconfig=$KUBECONFIG_FILE apply -f client/deployment.yaml
            ;;
        *)
            log_error "Invalid service: $service"
            exit 1
            ;;
    esac

    log_info "Deployment updated ✓"
}

show_logs() {
    read -p "Show logs for which service? (processor/server/client): " service

    case $service in
        processor)
            kubectl --kubeconfig=$KUBECONFIG_FILE logs -f deployment/neuroclima-processor -n $NAMESPACE
            ;;
        server)
            kubectl --kubeconfig=$KUBECONFIG_FILE logs -f deployment/neuroclima-server -n $NAMESPACE
            ;;
        client)
            kubectl --kubeconfig=$KUBECONFIG_FILE logs -f deployment/neuroclima-client -n $NAMESPACE
            ;;
        *)
            log_error "Invalid service: $service"
            exit 1
            ;;
    esac
}

# Main script
case "${1:-}" in
    build)
        check_prerequisites
        build_images
        push_images
        update_manifests
        ;;
    deploy)
        check_prerequisites
        deploy_all
        ;;
    update)
        check_prerequisites
        update_deployment
        ;;
    status)
        check_prerequisites
        check_status
        ;;
    logs)
        check_prerequisites
        show_logs
        ;;
    delete)
        check_prerequisites
        delete_all
        ;;
    *)
        echo "Usage: $0 {build|deploy|update|status|logs|delete}"
        echo ""
        echo "Commands:"
        echo "  build   - Build and push Docker images"
        echo "  deploy  - Deploy all services to Kubernetes"
        echo "  update  - Update an existing deployment"
        echo "  status  - Check deployment status"
        echo "  logs    - Show logs for a service"
        echo "  delete  - Delete all resources"
        echo ""
        echo "Environment variables:"
        echo "  REGISTRY          - Docker registry (default: docker.io/yourusername)"
        echo "  KUBECONFIG_FILE   - Path to kubeconfig (default: ./kubeconfig.yaml)"
        exit 1
        ;;
esac
