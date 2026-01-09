# ngrok Setup with Gateway (Simplified - Industry Standard)

With the nginx gateway, you only need **ONE ngrok tunnel** for everything! This is the industry-standard approach.

## Quick Start

### Step 1: Deploy the gateway first

```powershell
kubectl --kubeconfig ../kubeconfig.yaml apply -f ../gateway/nginx-gateway.yaml
```

### Step 2: Create ngrok secret (if not already done)

```powershell
# Copy the template
Copy-Item secret-template.yaml secret.yaml

# Edit secret.yaml and add your ngrok authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
notepad secret.yaml

# Apply it
kubectl --kubeconfig ../kubeconfig.yaml apply -f secret.yaml
```

### Step 3: Deploy ONE ngrok tunnel

```powershell
kubectl --kubeconfig ../kubeconfig.yaml apply -f deployment.yaml
```

That's it! You only need ONE tunnel now.

### Step 4: Get your public URL

```powershell
# Check logs for the URL
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=ngrok --tail=50
```

Look for:
```
started tunnel    url=https://xxxxx.ngrok-free.app
```

### Step 5: Access your application

Your ONE URL now serves everything:

- **Frontend**: `https://xxxxx.ngrok-free.app/`
- **Backend API**: `https://xxxxx.ngrok-free.app/api`
- **Processor**: `https://xxxxx.ngrok-free.app/processor`

No CORS issues! No separate URLs! Just like production! ✅

## Update Client Deployment

The client needs to use relative paths:

```powershell
kubectl --kubeconfig ../kubeconfig.yaml apply -f ../client/deployment.yaml
kubectl --kubeconfig ../kubeconfig.yaml rollout restart deployment neuroclima-client -n uoulu
```

## Architecture Diagram

```
Internet
   ↓
https://xxxxx.ngrok-free.app/
   ↓
ngrok pod
   ↓
nginx-gateway service
   ↓
nginx-gateway pod (reverse proxy)
   ↓
   ├─ /          → neuroclima-client:80 (frontend)
   ├─ /api/*     → neuroclima-server:8000 (backend)
   └─ /processor/* → neuroclima-processor:5000 (processor)
```

## Why This is Better

| Old Approach (3 tunnels) | New Approach (1 tunnel + gateway) |
|-------------------------|-----------------------------------|
| ❌ 3 separate URLs | ✅ 1 URL, multiple paths |
| ❌ CORS configuration needed | ✅ No CORS issues |
| ❌ Hard to maintain | ✅ Easy to maintain |
| ❌ Not production-like | ✅ Industry standard |
| ❌ Update client config with 3 URLs | ✅ Uses relative paths |

## Cleanup Old Tunnels (if you deployed them)

If you previously deployed separate server and processor tunnels:

```powershell
kubectl --kubeconfig ../kubeconfig.yaml delete deployment neuroclima-ngrok-server -n uoulu
kubectl --kubeconfig ../kubeconfig.yaml delete deployment neuroclima-ngrok-processor -n uoulu
```

Now you only need the main `neuroclima-ngrok` deployment!
