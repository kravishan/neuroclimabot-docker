#!/bin/bash

echo "🚀 Starting NeuroClima Docker Setup..."
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

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p Server/data
echo "✅ Directories created"
echo ""

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 NeuroClima is starting up!"
echo ""
echo "📝 Next Steps:"
echo "   1. Download Ollama model: docker exec -it neuroclima-ollama ollama pull mistral:7b"
echo "   2. Check logs: docker-compose logs -f"
echo "   3. Access frontend: http://localhost"
echo "   4. Access API docs: http://localhost:8000/docs"
echo "   5. MinIO console: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "💡 Run './stop.sh' to stop all services"
echo "💡 Run 'docker-compose logs -f' to view logs"
