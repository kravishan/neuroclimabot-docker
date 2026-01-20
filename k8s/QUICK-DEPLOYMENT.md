# NeuroClima Quick Deployment Guide

This guide will help you deploy your NeuroClima application to Kubernetes in just a few steps.

## Prerequisites ✅

- [x] Docker images built and pushed:
  - `docker.io/raviyah/neuroclima-client:latest`
  - `docker.io/raviyah/neuroclima-server:latest`
  - `docker.io/raviyah/neuroclima-processor:latest`
- [x] kubectl installed
- [x] kubeconfig.yaml configured
- [ ] External services running (Ollama, MinIO, Milvus)

## Quick Start (3 Steps)

### Step 1: Configure Your Deployment

Run the configuration wizard:

**On Windows (PowerShell):**
```powershell
cd k8s
.\Setup-Config.ps1
```

**On Linux/Mac:**
```bash
cd k8s
./setup-config.sh
```

The wizard will ask you for:
- VM IP address where Ollama, MinIO, and Milvus are running
- MinIO credentials (access key and secret key)
- Admin credentials
- Other optional settings

This will automatically create:
- `base/configmap.yaml` - Configuration for all services
- `base/secrets-ready.yaml` - Secrets (credentials)

### Step 2: Deploy to Kubernetes

**On Windows (PowerShell):**
```powershell
.\deploy-k8s.ps1 -Action all
```

**On Linux/Mac:**
```bash
./quick-deploy.sh
```

This will:
1. Clean up any existing deployments (asks for confirmation)
2. Deploy ConfigMaps and Secrets
3. Deploy Processor service with PVCs
4. Deploy Server service (includes Redis) with PVCs
5. Deploy Client service
6. Show deployment status

### Step 3: Verify and Access

**Check deployment status:**
```powershell
kubectl --kubeconfig kubeconfig.yaml get pods -n uoulu
```

Expected output (all pods should be `Running`):
```
NAME                                      READY   STATUS    RESTARTS   AGE
neuroclima-client-xxx                     1/1     Running   0          2m
neuroclima-processor-xxx                  1/1     Running   0          3m
neuroclima-redis-xxx                      1/1     Running   0          3m
neuroclima-server-xxx                     1/1     Running   0          3m
neuroclima-unstructured-xxx               1/1     Running   0          3m
```

**Access the application:**
```powershell
kubectl --kubeconfig kubeconfig.yaml port-forward svc/neuroclima-client 8080:80 -n uoulu
```

Then open your browser at: **http://localhost:8080**

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                      (namespace: uoulu)                      │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Client     │    │   Server     │    │  Processor   │  │
│  │  (Port 80)   │◄───┤  (Port 8000) │◄───┤  (Port 5000) │  │
│  │              │    │              │    │              │  │
│  │  React +     │    │  FastAPI +   │    │  FastAPI +   │  │
│  │  Nginx       │    │  SQLite      │    │  GraphRAG    │  │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘  │
│                             │                    │          │
│                       ┌─────▼─────┐    ┌────────▼───────┐  │
│                       │   Redis   │    │  Unstructured  │  │
│                       │ (Port 6379)│   │  (Port 8000)   │  │
│                       └───────────┘    └────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Persistent Volumes (55Gi total)                      │  │
│  │  • processor-data-pvc (10Gi)                         │  │
│  │  • graphrag-data-pvc (20Gi)                          │  │
│  │  • lancedb-data-pvc (10Gi)                           │  │
│  │  • redis-data-pvc (5Gi)                              │  │
│  │  • server-data-pvc (10Gi)                            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────────────────────┘
                   │
         ┌─────────▼─────────────┐
         │   External Services    │
         │  (On your VM)         │
         │                       │
         │  • Ollama (11434)    │
         │  • MinIO (9000)      │
         │  • Milvus (19530)    │
         └───────────────────────┘
```

## Manual Configuration (Alternative to Wizard)

If you prefer to manually create the configuration files:

### 1. Create configmap.yaml

Copy `base/configmap-example.yaml` to `base/configmap.yaml` and update:

```yaml
# Replace YOUR_VM_IP with your actual VM IP
OLLAMA_API_URL: "http://YOUR_VM_IP:11434"
OLLAMA_HOST: "YOUR_VM_IP"
MINIO_ENDPOINT: "YOUR_VM_IP:9000"
MILVUS_HOST: "YOUR_VM_IP"
```

Also update the GraphRAG URLs (4 locations):
```yaml
GRAPHRAG_QUERY_CHAT_MODEL_API_BASE: "http://YOUR_VM_IP:11434/v1"
GRAPHRAG_QUERY_EMBEDDING_MODEL_API_BASE: "http://YOUR_VM_IP:11434/api"
GRAPHRAG_INDEXING_CHAT_MODEL_API_BASE: "http://YOUR_VM_IP:11434/v1"
GRAPHRAG_EMBEDDING_MODEL_API_BASE: "http://YOUR_VM_IP:11434/api"
```

### 2. Create secrets-ready.yaml

Copy `base/secrets.yaml.template` to `base/secrets-ready.yaml` and update:

```yaml
stringData:
  MINIO_ACCESS_KEY: "your_minio_access_key"
  MINIO_SECRET_KEY: "your_minio_secret_key"
  MILVUS_USER: "root"
  MILVUS_PASSWORD: "Milvus"
  REDIS_PASSWORD: "your_redis_password"
  SECRET_KEY: "generate_a_random_key_here"  # Use: openssl rand -hex 32
  ADMIN_USERNAME: "admin"
  ADMIN_PASSWORD: "your_admin_password"
```

## Useful Commands

### Check deployment status
```powershell
kubectl --kubeconfig kubeconfig.yaml get all -n uoulu
```

### Watch pods
```powershell
kubectl --kubeconfig kubeconfig.yaml get pods -n uoulu -w
```

### Check logs
```powershell
# Server logs
kubectl --kubeconfig kubeconfig.yaml logs -f deployment/neuroclima-server -n uoulu

# Processor logs
kubectl --kubeconfig kubeconfig.yaml logs -f deployment/neuroclima-processor -n uoulu

# Client logs
kubectl --kubeconfig kubeconfig.yaml logs -f deployment/neuroclima-client -n uoulu
```

### Check pod details
```powershell
kubectl --kubeconfig kubeconfig.yaml describe pod <pod-name> -n uoulu
```

### Restart a deployment
```powershell
kubectl --kubeconfig kubeconfig.yaml rollout restart deployment/neuroclima-server -n uoulu
```

### Delete everything
```powershell
kubectl --kubeconfig kubeconfig.yaml delete all --all -n uoulu
kubectl --kubeconfig kubeconfig.yaml delete pvc --all -n uoulu
```

## Troubleshooting

### Pods stuck in Pending
**Cause:** PVCs not bound (storage not available)

**Solution:**
```powershell
# Check PVC status
kubectl --kubeconfig kubeconfig.yaml get pvc -n uoulu

# Check storage class
kubectl get storageclass
```

Your cluster needs a default storage class. Contact your cluster administrator.

### Pods in CrashLoopBackOff
**Cause:** Configuration error or cannot connect to external services

**Solution:**
```powershell
# Check logs
kubectl --kubeconfig kubeconfig.yaml logs <pod-name> -n uoulu

# Verify configmap
kubectl --kubeconfig kubeconfig.yaml get configmap neuroclima-config -n uoulu -o yaml

# Test connectivity to your VM from a pod
kubectl run test --image=curlimages/curl --rm -it -n uoulu -- curl http://YOUR_VM_IP:11434
```

### Image pull errors
**Cause:** Images not found or registry authentication required

**Solution:**
```powershell
# Verify images exist on Docker Hub
# docker.io/raviyah/neuroclima-client:latest
# docker.io/raviyah/neuroclima-server:latest
# docker.io/raviyah/neuroclima-processor:latest

# If private registry, create secret:
kubectl create secret docker-registry regcred `
  --docker-server=docker.io `
  --docker-username=YOUR_USERNAME `
  --docker-password=YOUR_PASSWORD `
  -n uoulu
```

### Cannot access application after port-forward
**Cause:** Service not running or wrong port

**Solution:**
```powershell
# Check services
kubectl --kubeconfig kubeconfig.yaml get svc -n uoulu

# Try different port
kubectl --kubeconfig kubeconfig.yaml port-forward svc/neuroclima-client 3000:80 -n uoulu
```

## Advanced Options

### Using Nginx Gateway (Optional)

Deploy the Nginx gateway for unified routing:

```powershell
kubectl --kubeconfig kubeconfig.yaml apply -f gateway/nginx-gateway.yaml -n uoulu
```

Then access via:
```powershell
kubectl --kubeconfig kubeconfig.yaml port-forward svc/nginx-gateway 8080:80 -n uoulu
```

Routes:
- `/` → Client
- `/server/*` → Server API
- `/processor/*` → Processor API

### Using Ingress (Production)

For production with a domain name:

1. Update `base/ingress.yaml` with your domain
2. Apply:
```powershell
kubectl --kubeconfig kubeconfig.yaml apply -f base/ingress.yaml -n uoulu
```

### Scaling

Scale deployments:
```powershell
# Scale processor to 2 replicas
kubectl --kubeconfig kubeconfig.yaml scale deployment/neuroclima-processor --replicas=2 -n uoulu

# Scale server to 3 replicas
kubectl --kubeconfig kubeconfig.yaml scale deployment/neuroclima-server --replicas=3 -n uoulu
```

## Next Steps

1. ✅ Deploy application
2. ✅ Verify all pods are running
3. ✅ Access via port-forward
4. 🔄 Test application functionality
5. 🔄 Set up ingress for production access
6. 🔄 Configure monitoring and logging
7. 🔄 Set up backups for PVCs

## Support

For issues or questions:
1. Check the logs of the failing service
2. Verify external services (Ollama, MinIO, Milvus) are accessible
3. Ensure your kubeconfig is properly configured
4. Check that your VM firewall allows connections from the K8s cluster

## Summary

You now have all the tools needed to deploy NeuroClima:

1. **Setup-Config.ps1** - Interactive configuration wizard
2. **deploy-k8s.ps1** - Automated deployment script
3. **DEPLOYMENT-GUIDE.md** - Comprehensive deployment guide

Start with the configuration wizard, then run the deployment script!
