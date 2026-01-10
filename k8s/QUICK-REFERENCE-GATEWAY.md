# Nginx Gateway Quick Reference

## Architecture At A Glance

```
YOUR_URL → Nginx Gateway → Path-based routing
              ↓
    /          → Frontend (React)
    /server/*  → Backend API (FastAPI)
    /processor/* → Document Processor (FastAPI)
```

## URL Patterns

| Path | Service | Example |
|------|---------|---------|
| `/` | Frontend | `https://app.com/` |
| `/server/*` | Backend API | `https://app.com/server/api/v1/chat/start` |
| `/processor/*` | Document Processor | `https://app.com/processor/process/document` |

## Frontend Configuration

**File**: `Client/src/constants/config.js`

```javascript
// Default configuration (production-ready)
export const API_CONFIG = {
  BASE_URL: '/server',           // Routes to backend API
  DOCUMENT_URL: '/processor',    // Routes to processor
}

// Frontend code just uses relative paths
fetch('/server/api/v1/chat/start', { ... })     // Works!
fetch('/processor/process/document', { ... })   // Works!
```

## Quick Commands

### Check Status
```bash
# Check all pods
kubectl get pods -n uoulu

# Check nginx gateway
kubectl logs -f deployment/nginx-gateway -n uoulu

# Check gateway config
kubectl get configmap nginx-gateway-config -n uoulu -o yaml
```

### Deploy/Update
```bash
# Deploy gateway
kubectl apply -f k8s/gateway/nginx-gateway.yaml -n uoulu

# Update gateway config
kubectl apply -f k8s/gateway/nginx-gateway.yaml -n uoulu
kubectl rollout restart deployment/nginx-gateway -n uoulu

# Deploy client
kubectl apply -f k8s/client/deployment.yaml -n uoulu
```

### Expose Gateway
```bash
# Option 1: ngrok (development)
ngrok http nginx-gateway:80

# Option 2: Get NodePort
kubectl get service nginx-gateway -n uoulu

# Option 3: LoadBalancer
kubectl expose service nginx-gateway --type=LoadBalancer -n uoulu
```

### Test Endpoints
```bash
# Health checks (replace YOUR_URL with your actual URL)
curl https://YOUR_URL/server/api/v1/health/
curl https://YOUR_URL/processor/health

# API calls
curl -X POST https://YOUR_URL/server/api/v1/chat/start \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "language": "en"}'
```

## Troubleshooting

### 404 Not Found
```bash
# Check nginx logs
kubectl logs deployment/nginx-gateway -n uoulu --tail=50

# Check if service exists
kubectl get svc -n uoulu

# Verify path in request
# Correct: /server/api/v1/health
# Wrong:   /api/v1/health (missing /server prefix)
```

### 502 Bad Gateway
```bash
# Check backend pods
kubectl get pods -n uoulu | grep server
kubectl describe pod neuroclima-server-xxx -n uoulu

# Check backend service
kubectl get svc neuroclima-server -n uoulu
```

### Connection Timeout
```bash
# Check nginx config timeouts
kubectl describe configmap nginx-gateway-config -n uoulu

# Increase timeout in nginx.conf:
# proxy_read_timeout 1200;  # 20 minutes
```

## Configuration Files

| File | Purpose |
|------|---------|
| `k8s/gateway/nginx-gateway.yaml` | Nginx gateway deployment & config |
| `k8s/client/deployment.yaml` | Frontend deployment |
| `Client/src/constants/config.js` | Frontend API configuration |
| `Client/docker-entrypoint.sh` | Runtime env injection script |

## Environment Variables (Optional)

Override defaults in `k8s/client/deployment.yaml`:

```yaml
env:
- name: VITE_API_BASE_URL
  value: "/server"        # Default - can change if needed
- name: VITE_API_DOCUMENT_URL
  value: "/processor"     # Default - can change if needed
```

**Note**: These are already set as defaults in `config.js`. Only change if you need custom routing.

## Adding a New Service

1. **Add to nginx-gateway.yaml**:
```yaml
upstream my_service {
    server neuroclima-my-service:8080;
}

location /myservice/ {
    proxy_pass http://my_service/;
    # ... proxy headers ...
}
```

2. **Update client config**:
```javascript
export const API_CONFIG = {
  MY_SERVICE_URL: '/myservice',
}
```

3. **Deploy**:
```bash
kubectl apply -f k8s/gateway/nginx-gateway.yaml -n uoulu
kubectl rollout restart deployment/nginx-gateway -n uoulu
```

## Common Patterns

### Health Check
```javascript
// Frontend code
const checkHealth = async () => {
  const response = await fetch('/server/api/v1/health')
  return response.json()
}
```

### API Call with Auth
```javascript
// Frontend code
const apiCall = async () => {
  const response = await fetch('/server/api/v1/chat/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ message: 'Hello' }),
  })
  return response.json()
}
```

### Document Processing
```javascript
// Frontend code
const processDoc = async () => {
  const response = await fetch('/processor/process/document', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bucket: 'docs', filename: 'test.pdf' }),
  })
  return response.json()
}
```

## Security Headers (Add to nginx.conf)

```nginx
location /server/ {
    proxy_pass http://server/;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;
}
```

## Monitoring

### View Logs
```bash
# Gateway logs
kubectl logs -f deployment/nginx-gateway -n uoulu

# Backend logs
kubectl logs -f deployment/neuroclima-server -n uoulu

# Processor logs
kubectl logs -f deployment/neuroclima-processor -n uoulu

# Client logs
kubectl logs -f deployment/neuroclima-client -n uoulu
```

### Check Resources
```bash
# Resource usage
kubectl top pods -n uoulu

# Describe gateway
kubectl describe deployment nginx-gateway -n uoulu
```

## Best Practices

✅ **DO**:
- Use relative paths (`/server/api`, `/processor/upload`)
- Set defaults in `config.js`
- Add trailing slashes in `proxy_pass` to strip prefixes
- Use descriptive location block comments
- Monitor nginx gateway logs
- Set appropriate timeouts

❌ **DON'T**:
- Hardcode absolute URLs (`https://api.example.com`)
- Put API URLs in `.env` files (use config.js defaults)
- Forget trailing slashes in `proxy_pass`
- Skip health checks
- Ignore nginx errors

## Need Help?

1. Check logs: `kubectl logs deployment/nginx-gateway -n uoulu`
2. Read full docs: `k8s/NGINX-GATEWAY-ARCHITECTURE.md`
3. Check nginx docs: https://nginx.org/en/docs/

---

**Remember**: This is the same pattern used by Netflix, Spotify, Airbnb, and major platforms! 🚀
