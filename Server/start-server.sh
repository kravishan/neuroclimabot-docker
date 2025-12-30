#!/bin/sh
# Server startup script - waits for Redis to be ready before starting

set -e

echo "🔄 Waiting for Redis to be ready..."

# Redis connection details from environment
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-changeme}"

# Maximum wait time (seconds)
MAX_WAIT=60
WAIT_INTERVAL=2
ELAPSED=0

# Wait for Redis to be ready
while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Try to ping Redis with authentication
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" --no-auth-warning ping > /dev/null 2>&1; then
        echo "✅ Redis is ready!"
        break
    fi

    echo "⏳ Waiting for Redis... ($ELAPSED/$MAX_WAIT seconds)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

# Check if Redis is ready
if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "❌ Redis failed to become ready within $MAX_WAIT seconds"
    exit 1
fi

# Start the FastAPI server
echo "🚀 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
