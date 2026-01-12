#!/bin/bash
# ============================================================================
# Redeploy NeuroClima Client to Kubernetes
# ============================================================================
# This script forces K8s to pull the latest client image and restart pods
# ============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}NeuroClima Client - Kubernetes Redeployment${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Configuration
NAMESPACE="uoulu"
DEPLOYMENT="neuroclima-client"
KUBECONFIG_PATH="k8s/kubeconfig.yaml"

# Check if kubeconfig exists
if [ ! -f "${KUBECONFIG_PATH}" ]; then
    echo -e "${RED}Error: kubeconfig not found at ${KUBECONFIG_PATH}${NC}"
    echo -e "${YELLOW}Please specify the correct path to your kubeconfig file.${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4] Checking current pods...${NC}"
kubectl --kubeconfig ${KUBECONFIG_PATH} get pods -n ${NAMESPACE} -l component=client

echo ""
echo -e "${GREEN}[2/4] Forcing pod restart to pull latest image...${NC}"
kubectl --kubeconfig ${KUBECONFIG_PATH} rollout restart deployment/${DEPLOYMENT} -n ${NAMESPACE}

echo ""
echo -e "${GREEN}[3/4] Waiting for rollout to complete...${NC}"
kubectl --kubeconfig ${KUBECONFIG_PATH} rollout status deployment/${DEPLOYMENT} -n ${NAMESPACE} --timeout=5m

echo ""
echo -e "${GREEN}[4/4] Verifying new pods are running...${NC}"
kubectl --kubeconfig ${KUBECONFIG_PATH} get pods -n ${NAMESPACE} -l component=client

echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}✅ Client successfully redeployed!${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Monitor pods with:${NC}"
echo -e "kubectl --kubeconfig ${KUBECONFIG_PATH} get pods -n ${NAMESPACE} -w"
echo ""
echo -e "${YELLOW}Check logs with:${NC}"
echo -e "kubectl --kubeconfig ${KUBECONFIG_PATH} logs -f -n ${NAMESPACE} -l component=client"
echo ""
