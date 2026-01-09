#!/bin/bash
# =============================================================================
# Apply Kubernetes Secrets Helper Script
# =============================================================================
# This script helps you create and apply the Kubernetes secrets needed for
# the NeuroClima application.
# =============================================================================

set -e  # Exit on error

SECRETS_TEMPLATE="k8s/base/secrets.yaml.template"
SECRETS_FILE="k8s/base/secrets.yaml"
NAMESPACE="uoulu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "NeuroClima Kubernetes Secrets Setup"
echo "================================================"
echo ""

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}ERROR: kubectl is not installed or not in PATH${NC}"
    echo "Please install kubectl first: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if template exists
if [ ! -f "$SECRETS_TEMPLATE" ]; then
    echo -e "${RED}ERROR: Template file not found: $SECRETS_TEMPLATE${NC}"
    exit 1
fi

# Check if secrets.yaml already exists
if [ -f "$SECRETS_FILE" ]; then
    echo -e "${YELLOW}WARNING: $SECRETS_FILE already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing $SECRETS_FILE"
    else
        echo "Creating new $SECRETS_FILE from template..."
        cp "$SECRETS_TEMPLATE" "$SECRETS_FILE"
        echo -e "${GREEN}✓ Created $SECRETS_FILE${NC}"
        echo ""
        echo -e "${YELLOW}IMPORTANT: Please edit $SECRETS_FILE and update the placeholder values!${NC}"
        echo "After editing, run this script again to apply the secrets."
        exit 0
    fi
else
    echo "Creating $SECRETS_FILE from template..."
    cp "$SECRETS_TEMPLATE" "$SECRETS_FILE"
    echo -e "${GREEN}✓ Created $SECRETS_FILE${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Please edit $SECRETS_FILE and update the placeholder values!${NC}"
    echo "After editing, run this script again to apply the secrets."
    exit 0
fi

echo ""
echo "Checking connection to Kubernetes cluster..."

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}ERROR: Cannot connect to Kubernetes cluster${NC}"
    echo "Please ensure:"
    echo "  1. Your kubeconfig is set up correctly"
    echo "  2. You have access to the cluster"
    echo "  3. The cluster is running"
    exit 1
fi

echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"
echo ""

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${YELLOW}WARNING: Namespace '$NAMESPACE' does not exist${NC}"
    read -p "Do you want to create it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl create namespace "$NAMESPACE"
        echo -e "${GREEN}✓ Created namespace '$NAMESPACE'${NC}"
    else
        echo -e "${RED}ERROR: Cannot proceed without namespace${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Namespace '$NAMESPACE' exists${NC}"
fi

echo ""
echo "Applying secrets to Kubernetes..."
echo ""

# Apply the secrets
if kubectl apply -f "$SECRETS_FILE"; then
    echo ""
    echo -e "${GREEN}✓ Secrets applied successfully!${NC}"
    echo ""

    # Check if secret was created
    if kubectl get secret neuroclima-secrets -n "$NAMESPACE" &> /dev/null; then
        echo -e "${GREEN}✓ Secret 'neuroclima-secrets' verified in namespace '$NAMESPACE'${NC}"
        echo ""

        # Show secret keys (not values)
        echo "Secret contains the following keys:"
        kubectl get secret neuroclima-secrets -n "$NAMESPACE" -o jsonpath='{.data}' | jq -r 'keys[]' | sed 's/^/  - /'
        echo ""

        echo -e "${YELLOW}Next steps:${NC}"
        echo "  1. Restart the server deployment to pick up the new secrets:"
        echo "     kubectl rollout restart deployment/neuroclima-server -n $NAMESPACE"
        echo ""
        echo "  2. Check the server logs to verify it starts correctly:"
        echo "     kubectl logs -f deployment/neuroclima-server -n $NAMESPACE"
        echo ""
        echo "  3. Verify all pods are running:"
        echo "     kubectl get pods -n $NAMESPACE"

    else
        echo -e "${YELLOW}WARNING: Could not verify secret creation${NC}"
    fi
else
    echo ""
    echo -e "${RED}ERROR: Failed to apply secrets${NC}"
    echo "Please check the error message above and try again."
    exit 1
fi

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
