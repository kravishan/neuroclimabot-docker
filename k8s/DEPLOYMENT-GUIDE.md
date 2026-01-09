# NeuroClima Kubernetes Deployment Guide

This guide will help you deploy NeuroClima applications to your Kubernetes cluster from scratch.

## Prerequisites

1. **kubectl** installed on your Windows machine
   - Download from: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/

2. **kubeconfig file** saved at `k8s/kubeconfig.yaml`
   - ✅ Already created with your cluster credentials

3. **External Services** - You need access to:
   - Ollama server (LLM service)
   - MinIO (Object storage)
   - Milvus (Vector database)

## Step 1: Update Configuration

Before deploying, you must update the configuration files with your actual service URLs.

### 1.1 Update ConfigMap (`k8s/base/configmap.yaml`)

Open `k8s/base/configmap.yaml` and replace the following placeholders:

```yaml
# Line 12-17: Shared configuration
OLLAMA_API_URL: "http://your-ollama-server:11434"  # Replace with your Ollama URL
OLLAMA_HOST: "your-ollama-server"                  # Replace with your Ollama host
MINIO_ENDPOINT: "your-minio-server:9000"           # Replace with your MinIO endpoint
MILVUS_HOST: "your-milvus-server"                  # Replace with your Milvus host

# Line 110-123: GraphRAG configuration (4 locations to update)
GRAPHRAG_QUERY_CHAT_MODEL_API_BASE: "http://your-ollama-server:11434"
GRAPHRAG_QUERY_EMBEDDING_MODEL_API_BASE: "http://your-ollama-server:11434"
GRAPHRAG_INDEXING_CHAT_MODEL_API_BASE: "http://your-ollama-server:11434"
GRAPHRAG_EMBEDDING_MODEL_API_BASE: "http://your-ollama-server:11434"
```

### 1.2 Update Secrets (Optional)

The file `k8s/base/secrets-ready.yaml` contains default credentials. For production, you should update:

- `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`
- `MILVUS_USER` and `MILVUS_PASSWORD`
- `REDIS_PASSWORD`
- `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- `SECRET_KEY` (for JWT tokens)
- Other optional keys if you use those services

### 1.3 Update Client Domain (Optional)

If you want to access the client externally, update `k8s/client/deployment.yaml`:

```yaml
# Line 29-35: Replace YOUR_DOMAIN with your actual domain
- name: VITE_API_BASE_URL
  value: "https://your-domain.com/api"
- name: VITE_API_DOCUMENT_URL
  value: "https://your-domain.com/processor"
```

For now, you can leave these as-is for internal cluster communication.

## Step 2: Deploy Using PowerShell Script

We've created an automated deployment script for you. Open PowerShell in the `k8s` directory and run:

### Option A: Full Cleanup and Deploy (Recommended)

```powershell
cd k8s
.\deploy-k8s.ps1 -Action all
```

This will:
1. Delete all existing deployments
2. Optionally delete PVCs (you'll be prompted)
3. Deploy base configuration (ConfigMaps and Secrets)
4. Deploy Processor service
5. Deploy Server service (includes Redis)
6. Deploy Client service
7. Show deployment status

### Option B: Only Cleanup

```powershell
.\deploy-k8s.ps1 -Action cleanup
```

### Option C: Only Deploy

```powershell
.\deploy-k8s.ps1 -Action deploy
```

### Option D: Check Status

```powershell
.\deploy-k8s.ps1 -Action status
```

## Step 3: Verify Deployment

After deployment, check the status:

```powershell
kubectl --kubeconfig kubeconfig.yaml get pods -n uoulu
```

Expected output (all pods should show `Running`):

```
NAME                                      READY   STATUS    RESTARTS   AGE
neuroclima-client-xxx                     1/1     Running   0          2m
neuroclima-processor-xxx                  1/1     Running   0          3m
neuroclima-redis-xxx                      1/1     Running   0          3m
neuroclima-server-xxx                     1/1     Running   0          3m
neuroclima-unstructured-xxx               1/1     Running   0          3m
```

## Step 4: Check Logs

If any pod is not running, check its logs:

```powershell
# Server logs
kubectl --kubeconfig kubeconfig.yaml logs -f deployment/neuroclima-server -n uoulu

# Processor logs
kubectl --kubeconfig kubeconfig.yaml logs -f deployment/neuroclima-processor -n uoulu

# Client logs
kubectl --kubeconfig kubeconfig.yaml logs -f deployment/neuroclima-client -n uoulu

# Describe a specific pod to see events
kubectl --kubeconfig kubeconfig.yaml describe pod <pod-name> -n uoulu
```

## Step 5: Access the Application

### Option 1: Port Forwarding (Development)

Forward the client port to your local machine:

```powershell
kubectl --kubeconfig kubeconfig.yaml port-forward svc/neuroclima-client 8080:80 -n uoulu
```

Then access the application at: http://localhost:8080

### Option 2: Using Ingress (Production)

If you have a domain and ingress controller:

1. Update `k8s/base/ingress.yaml` with your domain
2. Deploy ingress:
   ```powershell
   kubectl --kubeconfig kubeconfig.yaml apply -f base/ingress.yaml -n uoulu
   ```

## Common Issues and Solutions

### Issue 1: Server CrashLoopBackOff

**Symptoms:** `neuroclima-server` pod shows `CrashLoopBackOff`

**Causes:**
- Missing or invalid Milvus credentials
- Cannot connect to external services (Ollama, MinIO, Milvus)
- ConfigMap not properly applied

**Solutions:**
1. Check the logs:
   ```powershell
   kubectl --kubeconfig kubeconfig.yaml logs deployment/neuroclima-server -n uoulu
   ```

2. Verify secrets exist:
   ```powershell
   kubectl --kubeconfig kubeconfig.yaml get secret neuroclima-secrets -n uoulu
   ```

3. Verify configmap:
   ```powershell
   kubectl --kubeconfig kubeconfig.yaml get configmap neuroclima-config -n uoulu -o yaml
   ```

4. Update configmap and restart:
   ```powershell
   kubectl --kubeconfig kubeconfig.yaml apply -f base/configmap.yaml
   kubectl --kubeconfig kubeconfig.yaml rollout restart deployment/neuroclima-server -n uoulu
   ```

### Issue 2: Image Pull Errors

**Symptoms:** Pods show `ImagePullBackOff` or `ErrImagePull`

**Solutions:**
1. Check if images exist:
   - `docker.io/raviyah/neuroclima-client:latest`
   - `docker.io/raviyah/neuroclima-server:latest`
   - `docker.io/raviyah/neuroclima-processor:latest`

2. If using a private registry, create image pull secret:
   ```powershell
   kubectl create secret docker-registry regcred `
     --docker-server=docker.io `
     --docker-username=YOUR_USERNAME `
     --docker-password=YOUR_PASSWORD `
     -n uoulu
   ```

### Issue 3: PVC Not Binding

**Symptoms:** PVCs show `Pending` status

**Solutions:**
1. Check storage class:
   ```powershell
   kubectl get storageclass
   ```

2. Check PVC status:
   ```powershell
   kubectl --kubeconfig kubeconfig.yaml describe pvc processor-data-pvc -n uoulu
   ```

3. Your cluster might not have a default storage class. Check with your cluster administrator.

### Issue 4: Cannot Connect to External Services

**Symptoms:** Pods running but application errors about connecting to Ollama/MinIO/Milvus

**Solutions:**
1. Verify the URLs in your configmap are correct and reachable from the cluster
2. Test connectivity from a debug pod:
   ```powershell
   kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n uoulu -- curl http://your-ollama-server:11434/
   ```

## Manual Deployment Steps

If you prefer to deploy manually instead of using the script:

```powershell
cd k8s

# 1. Delete existing resources
kubectl --kubeconfig kubeconfig.yaml delete -f client/ --ignore-not-found=true -n uoulu
kubectl --kubeconfig kubeconfig.yaml delete -f server/ --ignore-not-found=true -n uoulu
kubectl --kubeconfig kubeconfig.yaml delete -f processor/ --ignore-not-found=true -n uoulu

# 2. Deploy base configuration
kubectl --kubeconfig kubeconfig.yaml apply -f base/configmap.yaml -n uoulu
kubectl --kubeconfig kubeconfig.yaml apply -f base/secrets-ready.yaml -n uoulu

# 3. Deploy Processor
kubectl --kubeconfig kubeconfig.yaml apply -f processor/pvc.yaml -n uoulu
kubectl --kubeconfig kubeconfig.yaml apply -f processor/deployment.yaml -n uoulu
kubectl --kubeconfig kubeconfig.yaml apply -f processor/service.yaml -n uoulu

# 4. Deploy Server (includes Redis)
kubectl --kubeconfig kubeconfig.yaml apply -f server/pvc.yaml -n uoulu
kubectl --kubeconfig kubeconfig.yaml apply -f server/deployment.yaml -n uoulu
kubectl --kubeconfig kubeconfig.yaml apply -f server/service.yaml -n uoulu

# 5. Deploy Client
kubectl --kubeconfig kubeconfig.yaml apply -f client/deployment.yaml -n uoulu
kubectl --kubeconfig kubeconfig.yaml apply -f client/service.yaml -n uoulu

# 6. Check status
kubectl --kubeconfig kubeconfig.yaml get pods -n uoulu
```

## Useful Commands

```powershell
# Check all resources
kubectl --kubeconfig kubeconfig.yaml get all -n uoulu

# Watch pod status
kubectl --kubeconfig kubeconfig.yaml get pods -n uoulu -w

# Get pod logs
kubectl --kubeconfig kubeconfig.yaml logs -f <pod-name> -n uoulu

# Describe pod (see events)
kubectl --kubeconfig kubeconfig.yaml describe pod <pod-name> -n uoulu

# Restart deployment
kubectl --kubeconfig kubeconfig.yaml rollout restart deployment/neuroclima-server -n uoulu

# Scale deployment
kubectl --kubeconfig kubeconfig.yaml scale deployment/neuroclima-processor --replicas=2 -n uoulu

# Delete everything
kubectl --kubeconfig kubeconfig.yaml delete all --all -n uoulu
```

## Architecture

Your deployment includes:

1. **Client**: Web UI (Nginx-based, port 80)
2. **Server**: FastAPI backend (port 8000)
3. **Processor**: Document processing service (port 5000)
4. **Redis**: Caching and queue management (port 6379)
5. **Unstructured**: Document parsing service (port 8000)

External dependencies:
- **Ollama**: LLM inference
- **MinIO**: Object storage
- **Milvus**: Vector database

## Next Steps

1. ✅ Configuration files updated
2. ✅ Run deployment script
3. ✅ Verify all pods are running
4. 🔄 Test application functionality
5. 🔄 Set up monitoring and logging (optional)
6. 🔄 Configure ingress for external access (optional)

## Support

If you encounter issues:

1. Check the logs of the failing pod
2. Verify your configmap has correct URLs
3. Ensure external services (Ollama, MinIO, Milvus) are accessible from the cluster
4. Check the events: `kubectl get events -n uoulu --sort-by='.lastTimestamp'`
