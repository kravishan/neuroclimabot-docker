# Nginx Gateway - Industry Standard Reverse Proxy Architecture

This document explains the **production-ready** Nginx Gateway architecture used in this Kubernetes deployment.

## Architecture Overview

```
Internet/User
    ↓
ngrok (optional) / Ingress / LoadBalancer
    ↓
Nginx Gateway (Single Entry Point)
    ├─ /           → neuroclima-client:80 (Frontend)
    ├─ /server/*   → neuroclima-server:8000 (Backend API)
    └─ /processor/* → neuroclima-processor:5000 (Document Processing)
```

## Why This Approach?

This is **exactly** how production Kubernetes deployments work and provides several critical benefits:

### ✅ **Single Entry Point**
- One URL serves the entire application
- No need to manage multiple domains or ports
- Simplified SSL/TLS certificate management

### ✅ **Path-Based Routing** (Industry Standard)
- Routes traffic based on URL paths
- Same pattern used by nginx-ingress, API Gateway, Istio
- Microservices architecture best practice

### ✅ **No CORS Issues**
- All services on same domain/origin
- Browser security restrictions eliminated
- Simplified frontend configuration

### ✅ **Easy to Scale**
- Add more services by adding paths to nginx config
- No changes needed to client code
- Independent service deployment

### ✅ **Production-Ready**
- Same pattern as major cloud platforms (AWS ALB, GCP Load Balancer)
- Battle-tested nginx reverse proxy
- High performance and reliability

### ✅ **Works Without Domain**
- Use with ngrok tunnels
- Use with NodePort for development
- Use with LoadBalancer
- Easy migration when you get a domain - just update DNS!

## How It Works

### 1. Nginx Gateway Configuration

The `nginx-gateway` acts as a reverse proxy with path-based routing:

```nginx
location /server/ {
    proxy_pass http://neuroclima-server:8000/;
    # Strips /server prefix: /server/v1/users → /v1/users
}

location /processor/ {
    proxy_pass http://neuroclima-processor:5000/;
    # Strips /processor prefix: /processor/upload → /upload
}

location / {
    proxy_pass http://neuroclima-client:80;
    # Serves frontend for all other paths
}
```

### 2. Request Flow Example

**Frontend Request:**
```
User → https://your-domain.com/
  → Ingress → nginx-gateway → neuroclima-client
  ← Serves React App
```

**API Request from Frontend:**
```
User clicks button → fetch('/server/v1/users')
  → Same domain, no CORS preflight
  → nginx-gateway receives /server/v1/users
  → Routes to neuroclima-server:8000/v1/users
  ← Returns data
```

**Document Processing Request:**
```
User uploads document → fetch('/processor/upload')
  → nginx-gateway receives /processor/upload
  → Routes to neuroclima-processor:5000/upload
  ← Returns processed document
```

### 3. Frontend Configuration

The frontend uses **relative paths** (best practice):

```javascript
// Environment variables
VITE_API_BASE_URL="/server"
VITE_API_DOCUMENT_URL="/processor"

// API calls
fetch('/server/v1/users')        // Routed to server
fetch('/processor/upload')       // Routed to processor
```

No hardcoded domains or absolute URLs needed!

## Deployment Modes

### Mode 1: Development (Ngrok)
```
ngrok → nginx-gateway → services
```
Single ngrok tunnel exposes entire application.

### Mode 2: Production (Ingress)
```
Internet → Kubernetes Ingress → nginx-gateway → services
```
Use nginx-ingress or cloud load balancer with SSL termination.

### Mode 3: NodePort (Local Testing)
```
localhost:30080 → nginx-gateway → services
```
Direct access for development and testing.

## Configuration Files

### Core Components

1. **nginx-gateway.yaml**
   - ConfigMap: nginx routing configuration
   - Deployment: nginx container
   - Service: ClusterIP service

2. **ingress.yaml** / **ingress-production.yaml**
   - Routes ALL traffic to nginx-gateway
   - nginx-gateway handles internal routing

3. **client/deployment.yaml**
   - Environment variables with relative paths
   - `/server` for API
   - `/processor` for document processing

4. **client/nginx-config.yaml**
   - Runtime config for frontend
   - Serves config.js with relative paths

## Security Features

### Phase 1 Improvements Applied
- ✅ Specific nginx version (1.25.3-alpine)
- ✅ Security context (non-root user)
- ✅ No privilege escalation
- ✅ Capabilities dropped
- ✅ Liveness/readiness probes

### Additional Security
- All communication internal to cluster
- SSL/TLS termination at ingress
- No services exposed directly
- Centralized access control point

## Scaling and High Availability

### Horizontal Scaling
```yaml
# Scale nginx-gateway
kubectl scale deployment nginx-gateway --replicas=3

# Scale backend services independently
kubectl scale deployment neuroclima-server --replicas=5
```

### Load Balancing
- Kubernetes Service handles load balancing to nginx-gateway pods
- nginx-gateway load balances to backend service pods
- Two levels of load balancing for high availability

## Migration Path

### Current: No Domain
```
ngrok → nginx-gateway → services
```

### Future: With Domain
```
your-domain.com → Ingress → nginx-gateway → services
```

**No code changes needed!** Just:
1. Point DNS to your Kubernetes cluster
2. Update ingress.yaml with your domain
3. Deploy

## Monitoring and Debugging

### Check nginx-gateway logs
```bash
kubectl logs -n uoulu deployment/nginx-gateway -f
```

### Test routing
```bash
# Access via nginx-gateway service
kubectl port-forward -n uoulu svc/nginx-gateway 8080:80

# Test routes
curl http://localhost:8080/              # Client
curl http://localhost:8080/server/health # Server
curl http://localhost:8080/processor/    # Processor
```

### Common Issues

**404 errors:**
- Check nginx-gateway logs
- Verify service names and ports
- Ensure backend services are running

**CORS errors:**
- Should not happen with this setup
- If they occur, check if requests bypass nginx-gateway

**Slow responses:**
- Check nginx proxy timeouts
- Monitor backend service performance
- Scale nginx-gateway or backend services

## Comparison with Other Approaches

### Direct Service Exposure (❌ Anti-pattern)
```
client.domain.com → client
api.domain.com → server
processor.domain.com → processor
```
Problems:
- Multiple domains to manage
- CORS configuration required
- SSL certificates for each domain
- Complex DNS management

### Nginx Gateway (✅ Best Practice)
```
domain.com/ → client
domain.com/server → server
domain.com/processor → processor
```
Benefits:
- Single domain
- No CORS issues
- One SSL certificate
- Simple DNS

## References

This pattern is used by:
- **nginx-ingress**: Kubernetes ingress controller
- **Istio**: Service mesh
- **AWS ALB**: Application Load Balancer with path routing
- **GCP Load Balancer**: HTTP(S) load balancing
- **Kong**: API Gateway
- **Traefik**: Modern reverse proxy

It's an industry-standard, production-proven architecture for microservices deployments.

## Next Steps

To enhance this setup:
1. Add rate limiting in nginx-gateway
2. Implement caching for static assets
3. Add request/response transformation
4. Integrate with service mesh (optional)
5. Add WAF (Web Application Firewall) rules
6. Implement circuit breakers
7. Add distributed tracing headers
