#!/bin/bash

echo "🛑 Stopping NeuroClima Docker containers..."
docker-compose down

echo ""
echo "✅ All containers stopped"
echo ""
echo "💡 To remove all data, run: docker-compose down -v"
echo "💡 To start again, run: ./start.sh"
