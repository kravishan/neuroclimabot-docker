#!/bin/bash
# ============================================================================
# Rebuild and Push NeuroClima Client Docker Image
# ============================================================================
# This script rebuilds the client Docker image with updated .env changes
# and pushes it to Docker Hub
# ============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}NeuroClima Client - Docker Image Rebuild${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Configuration
DOCKER_USERNAME="raviyah"
IMAGE_NAME="neuroclima-client"
TAG="latest"
FULL_IMAGE="docker.io/${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Check if .env file exists
if [ ! -f "Client/.env" ]; then
    echo -e "${YELLOW}Warning: Client/.env file not found!${NC}"
    echo -e "${YELLOW}Using .env.example as template...${NC}"
    cp Client/.env.example Client/.env
    echo -e "${YELLOW}Please edit Client/.env with your configuration and run this script again.${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4] Building Docker image...${NC}"
cd Client
docker build -t ${FULL_IMAGE} .
cd ..

echo ""
echo -e "${GREEN}[2/4] Tagging image...${NC}"
docker tag ${FULL_IMAGE} ${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}

echo ""
echo -e "${GREEN}[3/4] Checking Docker login status...${NC}"
if ! docker info | grep -q "Username: ${DOCKER_USERNAME}"; then
    echo -e "${YELLOW}Not logged in to Docker Hub. Please log in:${NC}"
    docker login
fi

echo ""
echo -e "${GREEN}[4/4] Pushing image to Docker Hub...${NC}"
docker push ${FULL_IMAGE}

echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}✅ Image successfully built and pushed!${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "Image: ${FULL_IMAGE}"
echo ""
echo -e "${YELLOW}Next step: Run ./redeploy-client.sh to update K8s pods${NC}"
echo ""
