#!/bin/bash
# Quick Update Script for Kubernetes Cluster
# Run this after pulling latest changes from git

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Kubernetes Cluster Update Script${NC}"
echo -e "${GREEN}Phase 1: Security & Nginx Gateway${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if kubeconfig is set
if [ -z "$KUBECONFIG" ]; then
    echo -e "${YELLOW}Warning: KUBECONFIG not set. Using default.${NC}"
    echo -e "${YELLOW}Set it with: export KUBECONFIG=/path/to/kubeconfig.yaml${NC}"
    echo ""
fi

NAMESPACE="uoulu"

# Function to wait for rollout
wait_for_rollout() {
    local deployment=$1
    echo -e "${YELLOW}Waiting for $deployment to roll out...${NC}"
    kubectl rollout status deployment/$deployment -n $NAMESPACE --timeout=5m
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $deployment updated successfully${NC}"
    else
        echo -e "${RED}✗ $deployment rollout failed${NC}"
        return 1
    fi
}

echo -e "${YELLOW}Step 1: Updating ConfigMaps...${NC}"
kubectl apply -f k8s/gateway/nginx-gateway.yaml
kubectl apply -f k8s/client/nginx-config.yaml
echo -e "${GREEN}✓ ConfigMaps updated${NC}"
echo ""

echo -e "${YELLOW}Step 2: Updating Deployments...${NC}"
echo ""

echo "Updating Server deployment (Redis + Server)..."
kubectl apply -f k8s/server/deployment.yaml
wait_for_rollout neuroclima-redis
wait_for_rollout neuroclima-server
echo ""

echo "Updating Processor deployment (Unstructured + Processor)..."
kubectl apply -f k8s/processor/deployment.yaml
wait_for_rollout neuroclima-unstructured
wait_for_rollout neuroclima-processor
echo ""

echo "Updating Client deployment..."
kubectl apply -f k8s/client/deployment.yaml
wait_for_rollout neuroclima-client
echo ""

echo "Updating Nginx Gateway..."
kubectl apply -f k8s/gateway/nginx-gateway.yaml
wait_for_rollout nginx-gateway
echo ""

echo "Updating Monitoring (Grafana + Prometheus)..."
kubectl apply -f k8s/monitoring/grafana-deployment.yaml
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml
wait_for_rollout neuroclima-grafana
wait_for_rollout neuroclima-prometheus
echo ""

echo -e "${YELLOW}Step 3: Updating Ingress...${NC}"
kubectl apply -f k8s/base/ingress-production.yaml
echo -e "${GREEN}✓ Ingress updated${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Update Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo "Checking pod status..."
kubectl get pods -n $NAMESPACE
echo ""

echo -e "${GREEN}All updates applied successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Test your application via ngrok URL"
echo "2. Verify all routes work: /, /server/*, /processor/*"
echo "3. Check logs if anything is not working:"
echo "   kubectl logs deployment/<name> -n $NAMESPACE"
