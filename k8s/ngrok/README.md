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

### Step 2: Deploy ngrok pod

```powershell
kubectl --kubeconfig ../kubeconfig.yaml apply -f deployment.yaml
```

### Step 3: Get your permanent ngrok URL

```powershell
# Wait for the pod to be running
kubectl --kubeconfig ../kubeconfig.yaml get pods -n uoulu -l component=ngrok

# Check the logs to find your public URL
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=ngrok -f
```

Look for a line like:
```
started tunnel: url=https://xxxx-xxxx-xxxx.ngrok-free.app
```

That's your permanent URL! It will work 24/7, even when your PC is off.

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
