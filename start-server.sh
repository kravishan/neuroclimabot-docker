#!/bin/bash

echo "🚀 Starting NeuroClima Server + Redis..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if .env file exists
if [ ! -f "Server/.env" ]; then
    echo "⚠️  Warning: Server/.env not found!"
    echo "Please configure Server/.env with your external service endpoints."
    exit 1
fi

# Check for REDIS_PASSWORD
if grep -q "REDIS_PASSWORD=your-secure-redis-password-change-this" Server/.env; then
    echo "⚠️  Please update REDIS_PASSWORD in Server/.env before starting"
    echo "Current placeholder value detected. Use a strong password."
    exit 1
fi

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p Server/data
echo "✅ Directories created"
echo ""

# Start services
echo "🐳 Starting Server and Redis containers..."
docker-compose -f docker-compose.server.yml up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.server.yml ps

echo ""
echo "🎉 Server services are running!"
echo ""
echo "📝 Services started:"
echo "   ✓ Redis (with password authentication)"
echo "   ✓ FastAPI Backend"
echo ""
echo "🌐 Access points:"
echo "   • API docs: http://localhost:8000/docs"
echo "   • Health check: http://localhost:8000/api/v1/health"
echo "   • Metrics: http://localhost:8001"
echo ""
echo "⚙️  External services (configured in Server/.env):"
echo "   • Milvus (vector database)"
echo "   • MinIO (object storage)"
echo "   • Ollama (LLM service)"
echo ""
echo "💡 Useful commands:"
echo "   • Stop server: ./stop-server.sh"
echo "   • View logs: docker-compose -f docker-compose.server.yml logs -f"
echo "   • View server logs: docker-compose -f docker-compose.server.yml logs -f server"
echo "   • View redis logs: docker-compose -f docker-compose.server.yml logs -f redis"
