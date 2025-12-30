#!/bin/bash

echo "🛑 Stopping NeuroClima Client..."
docker-compose -f docker-compose.client.yml down

echo ""
echo "✅ Client container stopped"
echo ""
echo "💡 To start again, run: ./start-client.sh"
