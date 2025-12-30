#!/bin/bash

echo "🚀 Starting NeuroClima Client..."
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

# Check if .env file exists (optional for client)
if [ ! -f "Client/.env" ]; then
    echo "⚠️  Warning: Client/.env not found! Using default configuration."
    echo ""
fi

# Start client service
echo "🐳 Starting Client container..."
docker-compose -f docker-compose.client.yml up -d

echo ""
echo "⏳ Waiting for client to start..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.client.yml ps

echo ""
echo "🎉 Client is running!"
echo ""
echo "📝 Service started:"
echo "   ✓ React Frontend (nginx)"
echo ""
echo "🌐 Access points:"
echo "   • Frontend: http://localhost"
echo ""
echo "⚠️  Make sure the backend server is running!"
echo "   • Run ./start-server.sh to start the backend"
echo "   • Or ensure backend is accessible at http://localhost:8000"
echo ""
echo "💡 Useful commands:"
echo "   • Stop client: ./stop-client.sh"
echo "   • View logs: docker-compose -f docker-compose.client.yml logs -f"
echo "   • Rebuild: docker-compose -f docker-compose.client.yml up -d --build"
