# ngrok Tunnel Setup for 24/7 Access

This directory contains the configuration to run ngrok inside your Kubernetes cluster, providing permanent public access to your NeuroClima application.

## Prerequisites

1. **ngrok account** - Sign up at https://dashboard.ngrok.com/signup (free tier works!)
2. **ngrok authtoken** - Get it from https://dashboard.ngrok.com/get-started/your-authtoken

## Setup Steps

### Step 1: Create the ngrok secret

Copy the secret template and add your authtoken:

```powershell
# Copy the template
Copy-Item secret-template.yaml secret.yaml

# Edit secret.yaml and replace YOUR_NGROK_AUTHTOKEN_HERE with your actual authtoken
# Then apply it:
kubectl --kubeconfig ../kubeconfig.yaml apply -f secret.yaml
```

**Important:** Don't commit `secret.yaml` to git! It contains your authtoken.

### Step 2: Deploy ALL ngrok tunnels

You need three tunnels: one for frontend (client), one for backend (server), and one for processor:

```powershell
# Deploy all three ngrok tunnels
kubectl --kubeconfig ../kubeconfig.yaml apply -f deployment.yaml
kubectl --kubeconfig ../kubeconfig.yaml apply -f deployment-server.yaml
kubectl --kubeconfig ../kubeconfig.yaml apply -f deployment-processor.yaml
```

### Step 3: Get your permanent ngrok URLs

```powershell
# Wait for all pods to be running
kubectl --kubeconfig ../kubeconfig.yaml get pods -n uoulu | findstr ngrok

# Get CLIENT URL (frontend)
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=ngrok --tail=50 | findstr "started tunnel"

# Get SERVER URL (backend API)
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=ngrok-server --tail=50 | findstr "started tunnel"

# Get PROCESSOR URL (document processing)
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=ngrok-processor --tail=50 | findstr "started tunnel"
```

Look for lines like:
```
started tunnel: url=https://xxxx-client.ngrok-free.app
started tunnel: url=https://yyyy-server.ngrok-free.app
started tunnel: url=https://zzzz-processor.ngrok-free.app
```

These are your permanent URLs! They will work 24/7, even when your PC is off.

### Step 4: Update client deployment with backend URLs

Edit `../client/deployment.yaml` and replace:
- `VITE_API_BASE_URL`: Use your **SERVER** ngrok URL + `/api` (e.g., `https://yyyy-server.ngrok-free.app/api`)
- `VITE_API_DOCUMENT_URL`: Use your **PROCESSOR** ngrok URL (e.g., `https://zzzz-processor.ngrok-free.app`)
- `VITE_TRANSLATE_API_URL`: Use your **PROCESSOR** ngrok URL (e.g., `https://zzzz-processor.ngrok-free.app`)
- `VITE_STP_SERVICE_URL`: Use your **PROCESSOR** ngrok URL (e.g., `https://zzzz-processor.ngrok-free.app`)

Then redeploy the client:
```powershell
kubectl --kubeconfig ../kubeconfig.yaml apply -f ../client/deployment.yaml
kubectl --kubeconfig ../kubeconfig.yaml rollout restart deployment neuroclima-client -n uoulu
```

## Troubleshooting

### Check pod status
```powershell
kubectl --kubeconfig ../kubeconfig.yaml get pods -n uoulu -l component=ngrok
```

### View logs
```powershell
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=ngrok
```

### Restart ngrok
```powershell
kubectl --kubeconfig ../kubeconfig.yaml rollout restart deployment neuroclima-ngrok -n uoulu
```

## Cleanup

To remove ngrok:
```powershell
kubectl --kubeconfig ../kubeconfig.yaml delete -f deployment.yaml
kubectl --kubeconfig ../kubeconfig.yaml delete secret ngrok-secret -n uoulu
```
