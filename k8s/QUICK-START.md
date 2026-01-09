# 🚀 Quick Start - Deploy NeuroClima to Kubernetes

## Prerequisites Checklist

- [x] kubeconfig.yaml saved in `k8s/` directory
- [ ] kubectl installed on your machine
- [ ] Access to Ollama, MinIO, and Milvus services
- [ ] Updated configuration files (see below)

## Step 1: Update Configuration (Required!)

Edit `k8s/base/configmap.yaml` and replace these values:

```yaml
OLLAMA_API_URL: "http://YOUR_OLLAMA_SERVER:11434"
MINIO_ENDPOINT: "YOUR_MINIO_SERVER:9000"
MILVUS_HOST: "YOUR_MILVUS_SERVER"
```

Also update the 4 GraphRAG URLs in the same file (lines 110-123).

## Step 2: Deploy Everything

Open PowerShell in the `k8s` directory:

```powershell
cd k8s
.\deploy-k8s.ps1 -Action all
```

This will:
1. ✅ Clean up existing deployments
2. ✅ Deploy all services fresh
3. ✅ Show status

## Step 3: Verify

Check all pods are running:

```powershell
kubectl --kubeconfig kubeconfig.yaml get pods -n uoulu
```

Expected: All pods should show `Running` status.

## Step 4: Access the Application

Port forward to your local machine:

```powershell
kubectl --kubeconfig kubeconfig.yaml port-forward svc/neuroclima-client 8080:80 -n uoulu
```

Then open: http://localhost:8080

## Troubleshooting

### If server is crashing:

```powershell
# Check logs
kubectl --kubeconfig kubeconfig.yaml logs -f deployment/neuroclima-server -n uoulu

# Verify config is correct
kubectl --kubeconfig kubeconfig.yaml get configmap neuroclima-config -n uoulu -o yaml

# Restart after fixing config
kubectl --kubeconfig kubeconfig.yaml apply -f base/configmap.yaml
kubectl --kubeconfig kubeconfig.yaml rollout restart deployment/neuroclima-server -n uoulu
```

### If images won't pull:

Check the deployment files use the correct registry:
- `docker.io/raviyah/neuroclima-client:latest`
- `docker.io/raviyah/neuroclima-server:latest`
- `docker.io/raviyah/neuroclima-processor:latest`

## What Gets Deployed

| Service | Purpose | Port |
|---------|---------|------|
| neuroclima-client | Web UI | 80 |
| neuroclima-server | API Backend | 8000 |
| neuroclima-processor | Document Processing | 5000 |
| neuroclima-redis | Cache & Queue | 6379 |
| neuroclima-unstructured | Document Parsing | 8000 |

## Need More Help?

See the full guide: [DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md)
