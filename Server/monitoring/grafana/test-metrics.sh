#!/bin/bash
# Quick test script to verify Prometheus metrics are working

echo "🔍 Testing NeuroClima Bot Prometheus Metrics"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if API is running
echo "1. Checking if NeuroClima Bot API is running..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ API is running on port 8000${NC}"
else
    echo -e "${RED}✗ API is not responding on port 8000${NC}"
    echo "  Please start the NeuroClima Bot API first"
    exit 1
fi
echo ""

# Test 2: Check metrics endpoint
echo "2. Checking metrics endpoint..."
if curl -s http://localhost:8000/metrics > /dev/null; then
    echo -e "${GREEN}✓ Metrics endpoint is accessible${NC}"
    echo ""
    echo "Sample metrics:"
    curl -s http://localhost:8000/metrics | grep "neuroclima_" | head -10
else
    echo -e "${RED}✗ Metrics endpoint not accessible${NC}"
    echo "  Check if ENABLE_METRICS=True in your .env file"
    exit 1
fi
echo ""

# Test 3: Check if Prometheus is running
echo "3. Checking if Prometheus is running..."
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo -e "${GREEN}✓ Prometheus is running on port 9090${NC}"
else
    echo -e "${YELLOW}⚠ Prometheus is not running on port 9090${NC}"
    echo "  To start Prometheus with Docker (run from project root):"
    echo "  docker run -d --name prometheus --network host -v \$(pwd)/Server/monitoring/grafana/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus:latest"
fi
echo ""

# Test 4: Check if Grafana is running
echo "4. Checking if Grafana is running..."
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo -e "${GREEN}✓ Grafana is running on port 3000${NC}"
else
    echo -e "${YELLOW}⚠ Grafana is not running on port 3000${NC}"
    echo "  Please start your local Grafana installation"
fi
echo ""

# Test 5: Generate sample traffic
echo "5. Generating sample traffic to create metrics..."
for i in {1..5}; do
    curl -s http://localhost:8000/ > /dev/null
    echo -n "."
    sleep 0.5
done
echo ""
echo -e "${GREEN}✓ Generated 5 test requests${NC}"
echo ""

# Summary
echo "=============================================="
echo "📊 Setup Summary:"
echo "=============================================="
echo ""
echo "Metrics Endpoint:  http://localhost:8000/metrics"
echo "Prometheus UI:     http://localhost:9090"
echo "Grafana UI:        http://localhost:3000"
echo ""
echo "Next steps:"
echo "1. Open Prometheus: http://localhost:9090"
echo "2. Try query: neuroclima_requests_total"
echo "3. Import dashboard in Grafana from: ./Server/monitoring/grafana/dashboards/neuroclima-dashboard.json"
echo ""
echo -e "${GREEN}Happy monitoring! 📈${NC}"
