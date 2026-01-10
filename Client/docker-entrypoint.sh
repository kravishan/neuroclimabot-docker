#!/bin/sh
set -e

echo "🚀 Starting NeuroClima Client..."

# Optional: Inject runtime environment variables into JS files
# This allows overriding the default /server and /processor paths if needed
if [ -n "$VITE_API_BASE_URL" ] || [ -n "$VITE_API_DOCUMENT_URL" ]; then
  echo "🔧 Injecting runtime environment variables..."

  find /usr/share/nginx/html/assets -name "*.js" -type f 2>/dev/null | while read -r file; do
    if [ -n "$VITE_API_BASE_URL" ]; then
      echo "   Replacing /server with $VITE_API_BASE_URL in $(basename "$file")"
      sed -i "s|['\"]\/server['\"]|\"$VITE_API_BASE_URL\"|g" "$file" 2>/dev/null || true
    fi

    if [ -n "$VITE_API_DOCUMENT_URL" ]; then
      echo "   Replacing /processor with $VITE_API_DOCUMENT_URL in $(basename "$file")"
      sed -i "s|['\"]\/processor['\"]|\"$VITE_API_DOCUMENT_URL\"|g" "$file" 2>/dev/null || true
    fi
  done

  echo "✅ Runtime environment variables injected successfully"
else
  echo "ℹ️  Using default Nginx Gateway paths:"
  echo "   - API Server: /server/*"
  echo "   - Processor: /processor/*"
  echo "   - Frontend: /*"
fi

echo "✅ Client ready - starting Nginx..."

# Start nginx
exec nginx -g "daemon off;"
