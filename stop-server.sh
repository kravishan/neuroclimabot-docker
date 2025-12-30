#!/bin/bash

echo "🛑 Stopping NeuroClima Server + Redis..."
docker-compose -f docker-compose.server.yml down

echo ""
echo "✅ Server containers stopped"
echo ""
echo "💡 To remove all data, run: docker-compose -f docker-compose.server.yml down -v"
echo "💡 To start again, run: ./start-server.sh"
