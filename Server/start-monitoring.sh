#!/bin/bash
# NeuroClima Monitoring Stack Startup Script

set -e

echo "🚀 Starting NeuroClima with Monitoring Stack..."
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ .env file created. Please configure it before starting."
    exit 1
fi

# Start all services
echo "📦 Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are running
if [ "$(docker ps -q -f name=neuroclima-server)" ]; then
    echo "✅ NeuroClima Server is running"
else
    echo "❌ NeuroClima Server failed to start"
fi

if [ "$(docker ps -q -f name=neuroclima-prometheus)" ]; then
    echo "✅ Prometheus is running"
else
    echo "❌ Prometheus failed to start"
fi

if [ "$(docker ps -q -f name=neuroclima-grafana)" ]; then
    echo "✅ Grafana is running"
else
    echo "❌ Grafana failed to start"
fi

echo ""
echo "🎉 Monitoring stack is ready!"
echo ""
echo "📍 Access your services:"
echo "   • NeuroClima API:     http://localhost:8000"
echo "   • API Metrics:        http://localhost:8001/metrics"
echo "   • Prometheus:         http://localhost:9090"
echo "   • Grafana Dashboard:  http://localhost:3000"
echo ""
echo "🔑 Grafana Login:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "📖 For more information, see MONITORING.md"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down"
