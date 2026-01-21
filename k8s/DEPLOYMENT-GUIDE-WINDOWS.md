# Windows PowerShell Deployment Guide

## Prerequisites

1. **kubectl installed** - Download from https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
2. **Kubeconfig file** - Located at `C:\Users\ravis\Downloads\kubeconfigs\kubeconfig-uoulu\kubeconfig.yaml`
3. **Access to uoulu namespace** - Verify with cluster administrator

## Setup

### Set KUBECONFIG Environment Variable

```powershell
# Set for current PowerShell session
$env:KUBECONFIG="C:\Users\ravis\Downloads\kubeconfigs\kubeconfig-uoulu\kubeconfig.yaml"

# Verify it's set
echo $env:KUBECONFIG

# Test connection
kubectl cluster-info
kubectl get nodes
```

### Navigate to Project Directory

```powershell
cd C:\path\to\neuroclimabot-docker
```

## Deployment Options

### Option 1: Automated Deployment (Recommended)

Use the provided PowerShell script for automated deployment:

```powershell
# Run the deployment script
.\k8s\deploy-initial.ps1
```

The script will:
- Deploy services in the correct order
- Wait for each component to be ready
- Show pod status after each step
- Provide a summary at the end

### Option 2: Manual Step-by-Step Deployment

Follow these steps to deploy manually in the correct order:

---

## Step-by-Step Manual Deployment

### Step 1: Deploy Processor & Unstructured

```powershell
# Deploy processor service
kubectl apply -f k8s/processor/service.yaml

# Deploy processor & unstructured deployments
kubectl apply -f k8s/processor/deployment.yaml

# Wait for unstructured to be ready (required for processor)
kubectl wait --for=condition=available --timeout=180s deployment/neuroclima-unstructured -n uoulu

# Check status
kubectl get pods -n uoulu -l component=unstructured

# Wait for processor to be ready
kubectl wait --for=condition=available --timeout=300s deployment/neuroclima-processor -n uoulu

# Check status
kubectl get pods -n uoulu -l component=processor

# Check logs if needed
kubectl logs -n uoulu -l component=processor --tail=50
```

**Expected Output:**
```
NAME                                      READY   STATUS    RESTARTS   AGE
neuroclima-unstructured-xxxx              1/1     Running   0          2m
neuroclima-processor-xxxx                 1/1     Running   0          2m
```

---

### Step 2: Deploy Redis

```powershell
# Deploy PVC for Redis (if not already exists)
kubectl apply -f k8s/server/pvc.yaml

# Deploy server services (includes Redis and Server services)
kubectl apply -f k8s/server/service.yaml

# Deploy Redis & Server deployments
# Note: Both are in the same file, Redis will start first
kubectl apply -f k8s/server/deployment.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=available --timeout=120s deployment/neuroclima-redis -n uoulu

# Check Redis status
kubectl get pods -n uoulu -l component=redis

# Check Redis logs
kubectl logs -n uoulu -l component=redis --tail=50
```

**Expected Output:**
```
NAME                                READY   STATUS    RESTARTS   AGE
neuroclima-redis-xxxx               1/1     Running   0          1m
```

---

### Step 3: Wait for Server

```powershell
# Server should already be deploying (same file as Redis)
# Wait for it to be ready
kubectl wait --for=condition=available --timeout=180s deployment/neuroclima-server -n uoulu

# Check server status
kubectl get pods -n uoulu -l component=server

# Check server logs
kubectl logs -n uoulu -l component=server --tail=50

# Test server health endpoint (optional, using port-forward)
kubectl port-forward -n uoulu svc/neuroclima-server 8000:8000
# In another terminal: curl http://localhost:8000/health
```

**Expected Output:**
```
NAME                                READY   STATUS    RESTARTS   AGE
neuroclima-server-xxxx              1/1     Running   0          2m
```

---

### Step 4: Deploy Client

```powershell
# Deploy client nginx config
kubectl apply -f k8s/client/nginx-config.yaml

# Deploy client service
kubectl apply -f k8s/client/service.yaml

# Deploy client deployment
kubectl apply -f k8s/client/deployment.yaml

# Wait for client to be ready
kubectl wait --for=condition=available --timeout=120s deployment/neuroclima-client -n uoulu

# Check client status
kubectl get pods -n uoulu -l component=client

# Check client logs
kubectl logs -n uoulu -l component=client --tail=50
```

**Expected Output:**
```
NAME                                READY   STATUS    RESTARTS   AGE
neuroclima-client-xxxx              1/1     Running   0          1m
```

---

### Step 5: Deploy Traefik IngressRoute

```powershell
# Deploy the Traefik IngressRoute
kubectl apply -f k8s/base/traefik-ingressroute.yaml

# Check IngressRoute status
kubectl get ingressroute -n uoulu

# Describe IngressRoute for details
kubectl describe ingressroute neuroclima-ingressroute -n uoulu
```

**Expected Output:**
```
NAME                        AGE
neuroclima-ingressroute     10s
```

---

## Verification

### Check All Pods

```powershell
# Check all pods in uoulu namespace
kubectl get pods -n uoulu -l app=neuroclima

# Check with more details
kubectl get pods -n uoulu -l app=neuroclima -o wide

# Watch pods in real-time
kubectl get pods -n uoulu -l app=neuroclima -w
```

**Expected Output:**
```
NAME                                      READY   STATUS    RESTARTS   AGE
neuroclima-client-xxxx                    1/1     Running   0          5m
neuroclima-server-xxxx                    1/1     Running   0          7m
neuroclima-processor-xxxx                 1/1     Running   0          10m
neuroclima-redis-xxxx                     1/1     Running   0          7m
neuroclima-unstructured-xxxx              1/1     Running   0          10m
```

### Check Services

```powershell
# Check all services
kubectl get svc -n uoulu -l app=neuroclima

# Check specific service
kubectl describe svc neuroclima-server -n uoulu
```

### Check IngressRoute

```powershell
# Check IngressRoute
kubectl get ingressroute -n uoulu

# Get detailed information
kubectl describe ingressroute neuroclima-ingressroute -n uoulu
```

### Test Application

Open your browser and navigate to:
- **Frontend**: https://bot.neuroclima.eu/
- **Server Health**: https://bot.neuroclima.eu/server/health
- **Processor Health**: https://bot.neuroclima.eu/processor/health

Or test with PowerShell:

```powershell
# Test frontend
Invoke-WebRequest -Uri "https://bot.neuroclima.eu/" -UseBasicParsing

# Test server health
Invoke-WebRequest -Uri "https://bot.neuroclima.eu/server/health" -UseBasicParsing

# Test processor health
Invoke-WebRequest -Uri "https://bot.neuroclima.eu/processor/health" -UseBasicParsing
```

---

## Troubleshooting

### Pod Not Starting

```powershell
# Check pod status
kubectl get pods -n uoulu

# Describe pod to see events
kubectl describe pod <pod-name> -n uoulu

# Check pod logs
kubectl logs <pod-name> -n uoulu

# Check previous logs if pod restarted
kubectl logs <pod-name> -n uoulu --previous
```

### Health Check Failing

```powershell
# Port-forward to pod and test directly
kubectl port-forward -n uoulu pod/<pod-name> 8080:8000

# In another terminal, test the health endpoint
Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing

# Check readiness/liveness probe configuration
kubectl describe pod <pod-name> -n uoulu | Select-String -Pattern "Liveness|Readiness" -Context 0,5
```

### Cannot Connect to Application

```powershell
# Check if IngressRoute is configured
kubectl get ingressroute -n uoulu

# Check Traefik service
kubectl get svc -n kube-system | Select-String "traefik"

# Check if services have endpoints
kubectl get endpoints -n uoulu

# Describe IngressRoute
kubectl describe ingressroute neuroclima-ingressroute -n uoulu
```

### Check Resource Usage

```powershell
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n uoulu

# Check events
kubectl get events -n uoulu --sort-by='.lastTimestamp' | Select-Object -First 20
```

---

## Scaling to Production (After Verification)

Once you've verified the initial deployment works correctly, scale to 2 replicas for production:

```powershell
# Scale client to 2 replicas
kubectl scale deployment neuroclima-client --replicas=2 -n uoulu

# Scale server to 2 replicas
kubectl scale deployment neuroclima-server --replicas=2 -n uoulu

# Wait for new pods to be ready
kubectl wait --for=condition=available --timeout=180s deployment/neuroclima-client -n uoulu
kubectl wait --for=condition=available --timeout=180s deployment/neuroclima-server -n uoulu

# Verify scaled deployments
kubectl get pods -n uoulu -l app=neuroclima -o wide
```

Expected output after scaling:
```
NAME                                      READY   STATUS    RESTARTS   AGE
neuroclima-client-xxxx                    1/1     Running   0          2m
neuroclima-client-yyyy                    1/1     Running   0          5s
neuroclima-server-xxxx                    1/1     Running   0          2m
neuroclima-server-yyyy                    1/1     Running   0          5s
neuroclima-processor-xxxx                 1/1     Running   0          10m
neuroclima-redis-xxxx                     1/1     Running   0          7m
neuroclima-unstructured-xxxx              1/1     Running   0          10m
```

### Deploy Pod Disruption Budgets (Optional)

```powershell
# Deploy PodDisruptionBudgets for HA
kubectl apply -f k8s/base/poddisruptionbudgets.yaml

# Verify PDBs
kubectl get pdb -n uoulu
```

### Deploy Horizontal Pod Autoscalers (Optional)

**First, check if metrics-server is installed:**

```powershell
kubectl get apiservice v1beta1.metrics.k8s.io
```

**If installed, deploy HPAs:**

```powershell
# Deploy HPAs
kubectl apply -f k8s/base/hpa.yaml

# Verify HPAs
kubectl get hpa -n uoulu

# Check HPA status
kubectl describe hpa -n uoulu
```

---

## Useful Commands

### Monitoring

```powershell
# Watch all pods
kubectl get pods -n uoulu -w

# Follow logs for all server pods
kubectl logs -n uoulu -l component=server -f --tail=50

# Check resource usage
kubectl top pods -n uoulu

# Check node resource usage
kubectl top nodes
```

### Updates

```powershell
# Update an image
kubectl set image deployment/neuroclima-server server=docker.io/raviyah/neuroclima-server:v2 -n uoulu

# Check rollout status
kubectl rollout status deployment/neuroclima-server -n uoulu

# Rollback if needed
kubectl rollout undo deployment/neuroclima-server -n uoulu
```

### Cleanup (Use with caution!)

```powershell
# Delete specific deployment
kubectl delete deployment neuroclima-client -n uoulu

# Delete all resources with label
kubectl delete all -n uoulu -l app=neuroclima

# Delete IngressRoute
kubectl delete ingressroute neuroclima-ingressroute -n uoulu
```

---

## Common Issues

### Issue: "connection refused" when accessing application

**Solution:**
1. Check if all pods are running: `kubectl get pods -n uoulu`
2. Check IngressRoute: `kubectl get ingressroute -n uoulu`
3. Check if DNS is pointing to Traefik LoadBalancer
4. Verify Traefik is running: `kubectl get pods -n kube-system | Select-String "traefik"`

### Issue: Pods stuck in "Pending" state

**Solution:**
1. Check node resources: `kubectl top nodes`
2. Describe pod to see reason: `kubectl describe pod <pod-name> -n uoulu`
3. Check if PVCs are bound: `kubectl get pvc -n uoulu`

### Issue: Pods in "CrashLoopBackOff"

**Solution:**
1. Check pod logs: `kubectl logs <pod-name> -n uoulu`
2. Check previous logs: `kubectl logs <pod-name> -n uoulu --previous`
3. Verify environment variables and secrets are configured
4. Check if dependent services are running (e.g., server needs Redis)

---

## Support

For more information, see:
- Main deployment guide: `k8s/PRODUCTION-DEPLOYMENT.md`
- Traefik IngressRoute: `k8s/base/traefik-ingressroute.yaml`
- Project repository: https://github.com/kravishan/neuroclimabot-docker
