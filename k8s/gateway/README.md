# Nginx Gateway - Industry Standard Reverse Proxy

This is an **industry-standard** approach to exposing multiple services through a single entry point, just like production systems use.

## Architecture

```
Internet → ngrok → Nginx Gateway → Routes to services based on path
                        ↓
        /          → neuroclima-client (Frontend)
        /api/*     → neuroclima-server (Backend API)
        /processor/* → neuroclima-processor (Document Processing)
```

## Why This Approach?

This is **exactly** how production Kubernetes deployments work:

✅ **Single entry point** - One URL, multiple services
✅ **Path-based routing** - Industry standard for microservices
✅ **No CORS issues** - All services on same domain
✅ **Easy to scale** - Add more services by adding paths
✅ **Production-ready** - Same pattern as nginx-ingress, API Gateway
✅ **Works without domain** - Use with ngrok, NodePort, or LoadBalancer
✅ **Easy migration** - When you get a domain, just update DNS!

## How It Works

1. **Nginx Gateway** acts as a reverse proxy (like nginx-ingress in production)
2. Routes traffic based on URL path to the appropriate backend service
3. Frontend uses **relative paths** (`/api`, `/processor`) - best practice!
4. No need for CORS configuration - everything is on the same domain

## Deployment

Deploy the gateway:

```powershell
kubectl --kubeconfig ../kubeconfig.yaml apply -f nginx-gateway.yaml
```

Verify it's running:

```powershell
kubectl --kubeconfig ../kubeconfig.yaml get pods -n uoulu -l component=gateway
kubectl --kubeconfig ../kubeconfig.yaml get svc nginx-gateway -n uoulu
```

## Testing Locally

Port-forward to test the gateway:

```powershell
kubectl --kubeconfig ../kubeconfig.yaml port-forward svc/nginx-gateway 8080:80 -n uoulu
```

Then open: http://localhost:8080

- Frontend: http://localhost:8080/
- Backend API: http://localhost:8080/api
- Processor: http://localhost:8080/processor

## Public Access with ngrok

The ngrok deployment is already configured to use the gateway. Just follow the instructions in `../ngrok/README.md`.

You'll get ONE URL that serves everything:
- `https://your-ngrok-url.ngrok-free.app/` - Frontend
- `https://your-ngrok-url.ngrok-free.app/api` - Backend
- `https://your-ngrok-url.ngrok-free.app/processor` - Processor

## Future: Adding a Domain

When you get a domain, you have two options:

### Option 1: Point domain to ngrok (easiest)
1. Get ngrok paid plan with custom domain support
2. Configure domain DNS to point to ngrok
3. Done! No code changes needed

### Option 2: Point domain directly to cluster (production)
1. Configure DNS: `your-domain.com` → cluster LoadBalancer or NodePort
2. Deploy the Ingress from `../base/ingress-production.yaml`
3. Remove ngrok deployment
4. Done! No code changes needed - gateway stays the same

## Comparison to Other Approaches

| Approach | Entry Points | CORS Issues | Production-Ready | Works Without Domain |
|----------|-------------|-------------|------------------|---------------------|
| **This (Gateway)** | ✅ One | ✅ None | ✅ Yes | ✅ Yes |
| 3 Separate ngrok | ❌ Three | ❌ Yes | ❌ No | ✅ Yes |
| LoadBalancer per service | ❌ Multiple | ❌ Yes | ⚠️ Costly | ❌ No |
| Ingress Controller | ✅ One | ✅ None | ✅ Yes | ⚠️ Needs setup |

## Troubleshooting

### Check gateway logs
```powershell
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=gateway
```

### Check if services are reachable from gateway
```powershell
# Exec into gateway pod
kubectl --kubeconfig ../kubeconfig.yaml exec -it -n uoulu deployment/nginx-gateway -- sh

# Test connectivity
wget -O- http://neuroclima-client
wget -O- http://neuroclima-server:8000/api/health
wget -O- http://neuroclima-processor:5000/health
```

### Restart gateway
```powershell
kubectl --kubeconfig ../kubeconfig.yaml rollout restart deployment nginx-gateway -n uoulu
```
