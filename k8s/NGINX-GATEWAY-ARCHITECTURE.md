# Nginx Gateway - Industry Standard Reverse Proxy Architecture

## Overview

This deployment uses an **industry-standard reverse proxy pattern** - the same approach used by major cloud platforms and production Kubernetes clusters worldwide.

## Architecture Diagram

```
Internet
    ↓
  ngrok (or LoadBalancer/NodePort)
    ↓
Nginx Gateway (nginx-gateway service)
    ↓
  Path-Based Routing:
    ├─ /          → neuroclima-client:80 (React Frontend)
    ├─ /server/*  → neuroclima-server:8000 (FastAPI Backend)
    └─ /processor/* → neuroclima-processor:5000 (Document Processor)
```

## Why This Approach?

### ✅ **Industry Standard**
- **Same pattern as**: nginx-ingress, AWS API Gateway, Google Cloud Load Balancer
- **Used by**: Netflix, Spotify, Airbnb, and thousands of production systems
- **Battle-tested**: Proven to handle millions of requests

### ✅ **Single Entry Point**
- One URL for your entire application
- Example: `https://your-app.com`
  - Frontend: `https://your-app.com/`
  - Backend API: `https://your-app.com/server/api/v1/...`
  - Processor: `https://your-app.com/processor/process/...`

### ✅ **No CORS Issues**
- All services on the same domain
- No need for complex CORS configuration
- Frontend uses relative paths (`/server/api`, `/processor/upload`)

### ✅ **Production Ready**
- Easy to add SSL/TLS termination
- Built-in load balancing
- Request logging and monitoring
- Health check support

### ✅ **Easy to Scale**
- Add new services by adding new paths
- Scale individual services independently
- No client-side code changes needed

### ✅ **Works Everywhere**
- Local development: Use with localhost
- Cloud: Use with ngrok, NodePort, or LoadBalancer
- Production: Point your domain DNS to the gateway

## How It Works

### 1. Client Makes Request

```javascript
// In React app (Client/src/constants/config.js)
const API_CONFIG = {
  BASE_URL: '/server',           // Relative path!
  DOCUMENT_URL: '/processor',    // Relative path!
}

// Making API calls
fetch('/server/api/v1/chat/start', { ... })  // → http://server:8000/api/v1/chat/start
fetch('/processor/process/document', { ... }) // → http://processor:5000/process/document
```

### 2. Nginx Gateway Routes Request

```nginx
# In k8s/gateway/nginx-gateway.yaml

location /server/ {
    proxy_pass http://server/;     # Routes to neuroclima-server:8000
    # Trailing slash strips /server prefix
}

location /processor/ {
    proxy_pass http://processor/;  # Routes to neuroclima-processor:5000
    # Trailing slash strips /processor prefix
}

location / {
    proxy_pass http://client;      # Routes to neuroclima-client:80
    # Default route - catches everything else
}
```

### 3. Request Flow Example

```
User Browser Request:
  GET https://your-app.com/server/api/v1/chat/start

↓ Nginx Gateway receives request

↓ Matches location /server/

↓ Strips /server prefix

↓ Forwards to backend:
  GET http://neuroclima-server:8000/api/v1/chat/start

↓ Backend processes request

↓ Response flows back through gateway

↓ User receives response
```

## Configuration Files

### 1. Nginx Gateway (`k8s/gateway/nginx-gateway.yaml`)
```yaml
# ConfigMap with nginx.conf
# Deployment running nginx:alpine
# Service exposing port 80
```

**Key Points:**
- Defines upstream services (client, server, processor)
- Configures path-based routing with location blocks
- Sets proxy headers for proper request forwarding
- Handles timeouts for long-running requests

### 2. Client Config (`Client/src/constants/config.js`)
```javascript
export const API_CONFIG = {
  BASE_URL: '/server',           // Relative path - works through gateway
  DOCUMENT_URL: '/processor',    // Relative path - works through gateway
  TIMEOUT: 120000,
}
```

**Key Points:**
- Uses **relative paths** as defaults (best practice!)
- Works automatically through Nginx Gateway
- Can be overridden with environment variables if needed

### 3. Client Deployment (`k8s/client/deployment.yaml`)
```yaml
env:
- name: VITE_API_BASE_URL
  value: "/server"        # Optional - already default in config.js
- name: VITE_API_DOCUMENT_URL
  value: "/processor"     # Optional - already default in config.js
```

**Key Points:**
- Environment variables are optional (defaults already set)
- Runtime injection via docker-entrypoint.sh
- Allows customization without rebuilding

## Deployment Steps

### 1. Deploy the Nginx Gateway
```bash
kubectl apply -f k8s/gateway/nginx-gateway.yaml -n uoulu
```

### 2. Deploy Backend Services
```bash
kubectl apply -f k8s/server/deployment.yaml -n uoulu
kubectl apply -f k8s/processor/deployment.yaml -n uoulu
```

### 3. Deploy Frontend
```bash
kubectl apply -f k8s/client/deployment.yaml -n uoulu
```

### 4. Expose the Gateway
```bash
# Option 1: ngrok (for development/testing)
ngrok http nginx-gateway:80

# Option 2: NodePort (for local access)
kubectl expose service nginx-gateway --type=NodePort

# Option 3: LoadBalancer (for production)
kubectl expose service nginx-gateway --type=LoadBalancer
```

## Request Examples

### Frontend Access
```bash
# Browser
https://your-app.com/

# Result: React app loaded from neuroclima-client
```

### Backend API Access
```bash
# From browser (via frontend)
fetch('/server/api/v1/chat/start', { ... })

# Direct cURL
curl https://your-app.com/server/api/v1/health

# Result: FastAPI backend at neuroclima-server:8000
```

### Processor Access
```bash
# From browser (via frontend)
fetch('/processor/process/document', { ... })

# Direct cURL
curl https://your-app.com/processor/health

# Result: Document processor at neuroclima-processor:5000
```

## Benefits Summary

| Feature | Without Gateway | With Gateway |
|---------|----------------|--------------|
| **URLs** | Multiple (http://api.com, http://processor.com) | Single (https://app.com) |
| **CORS** | Required, complex | Not needed |
| **SSL** | Configure on each service | Configure once |
| **Scalability** | Manual client updates | Just add paths |
| **Monitoring** | Monitor each service | Single entry point |
| **Production Ready** | Needs reverse proxy anyway | Already there |

## Troubleshooting

### Issue: 404 Not Found
**Cause**: Path not matching location blocks
**Solution**: Check nginx logs
```bash
kubectl logs -f deployment/nginx-gateway -n uoulu
```

### Issue: 502 Bad Gateway
**Cause**: Backend service not running
**Solution**: Check backend service status
```bash
kubectl get pods -n uoulu
kubectl describe pod neuroclima-server-xxx -n uoulu
```

### Issue: Request timeout
**Cause**: Long-running request exceeding timeout
**Solution**: Increase timeout in nginx.conf
```nginx
proxy_read_timeout 1200;  # 20 minutes
```

## Adding New Services

To add a new service through the gateway:

1. **Add upstream definition**:
```nginx
upstream new_service {
    server neuroclima-new-service:3000;
}
```

2. **Add location block**:
```nginx
location /newservice/ {
    proxy_pass http://new_service/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

3. **Update client config** (if needed):
```javascript
export const API_CONFIG = {
  NEW_SERVICE_URL: '/newservice',
}
```

4. **Deploy and test**:
```bash
kubectl apply -f k8s/gateway/nginx-gateway.yaml -n uoulu
kubectl rollout restart deployment/nginx-gateway -n uoulu
```

## Migration Path

### From Direct URLs to Gateway

**Before** (Direct URLs):
```javascript
const API_CONFIG = {
  BASE_URL: 'https://api.neuroclima.com',      // Direct URL
  DOCUMENT_URL: 'https://processor.neuroclima.com',  // Direct URL
}
```

**After** (Gateway with Relative Paths):
```javascript
const API_CONFIG = {
  BASE_URL: '/server',      // Through gateway
  DOCUMENT_URL: '/processor',  // Through gateway
}
```

**No backend changes needed!** ✅

## Best Practices

1. **Always use relative paths** in frontend code
2. **Set defaults in config.js** to relative paths
3. **Use environment variables** only for overrides
4. **Add comprehensive logging** in nginx
5. **Monitor gateway health** with health checks
6. **Set appropriate timeouts** for your use case
7. **Use trailing slashes** in proxy_pass to strip prefixes

## Production Checklist

- [ ] SSL/TLS certificate configured
- [ ] Health check endpoints configured
- [ ] Rate limiting enabled (if needed)
- [ ] Request logging enabled
- [ ] Monitoring/alerts set up
- [ ] Timeout values tuned
- [ ] Buffer sizes configured
- [ ] CORS headers set (if needed for external APIs)
- [ ] Security headers added
- [ ] DDoS protection configured

## Learn More

- [Nginx Reverse Proxy Docs](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [12-Factor App](https://12factor.net/) - Industry standard for web apps

---

**This is production-grade architecture** used by major platforms worldwide. You're now following industry best practices! 🚀
