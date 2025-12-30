#!/bin/bash

echo "🛑 Stopping all NeuroClima containers..."
docker-compose -f docker-compose.server.yml -f docker-compose.client.yml down

echo ""
echo "✅ All containers stopped"
echo ""
echo "💡 To remove all data, run: docker-compose -f docker-compose.server.yml down -v"
echo "💡 To start again, run: ./start.sh"
echo "💡 To start server only, run: ./start-server.sh"
echo "💡 To start client only, run: ./start-client.sh"
