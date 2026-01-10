# Deployment Update Guide

This guide walks you through updating your running Kubernetes cluster with the latest Phase 1 improvements and Nginx Gateway architecture.

## Prerequisites

1. Your kubeconfig file (you already have this)
2. Git repository updated with latest changes
3. Access to your Kubernetes cluster

## What's Being Updated

### Phase 1 - Security & Stability:
- ✅ All image tags changed from `:latest` to specific versions
- ✅ Security contexts added (non-root users)
- ✅ Liveness/readiness probes added
- ✅ Storage class added to all PVCs

### Nginx Gateway Architecture:
- ✅ Nginx gateway updated with security improvements
- ✅ Ingress routes through nginx-gateway
- ✅ Client configured to use `/server` instead of `/api`

## Update Strategy

You have two options:

### Option 1: Rolling Update (Recommended - Zero Downtime)
Updates pods one by one, no service interruption.

### Option 2: Recreate (Faster but Brief Downtime)
Delete old pods, create new ones.

## Step-by-Step Update Process

### Step 1: Backup Current State (Optional but Recommended)

```bash
# Set your kubeconfig path
export KUBECONFIG=C:\Users\ravis\Downloads\kubeconfigs\kubeconfig-uoulu\kubeconfig.yaml

# Export current deployments
kubectl get deployments -n uoulu -o yaml > backup-deployments.yaml
kubectl get pvc -n uoulu -o yaml > backup-pvcs.yaml
kubectl get ingress -n uoulu -o yaml > backup-ingress.yaml
```

### Step 2: Pull Latest Changes

```bash
# In your local repository
cd /path/to/neuroclimabot-docker
git pull origin claude/k8s-security-stability-QaeQ0
```

### Step 3: Apply Updates

#### 3.1 Update ConfigMaps First (No Downtime)

```bash
# Update nginx gateway config
kubectl apply -f k8s/gateway/nginx-gateway.yaml --kubeconfig kubeconfig.yaml

# Update client nginx config
kubectl apply -f k8s/client/nginx-config.yaml --kubeconfig kubeconfig.yaml
```

#### 3.2 Update Deployments (Rolling Update - No Downtime)

**Important:** PVCs cannot be updated after creation (storageClassName is immutable).
Only new PVCs will use the storage class. Existing PVCs will continue to work.

```bash
# Update Server deployment (Redis + Server)
kubectl apply -f k8s/server/deployment.yaml --kubeconfig kubeconfig.yaml

# Update Processor deployment (Unstructured + Processor)
kubectl apply -f k8s/processor/deployment.yaml --kubeconfig kubeconfig.yaml

# Update Client deployment
kubectl apply -f k8s/client/deployment.yaml --kubeconfig kubeconfig.yaml

# Update Nginx Gateway deployment
kubectl apply -f k8s/gateway/nginx-gateway.yaml --kubeconfig kubeconfig.yaml

# Update Ngrok deployment (if using)
kubectl apply -f k8s/ngrok/deployment.yaml --kubeconfig kubeconfig.yaml

# Update Monitoring deployments
kubectl apply -f k8s/monitoring/grafana-deployment.yaml --kubeconfig kubeconfig.yaml
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml --kubeconfig kubeconfig.yaml
```

#### 3.3 Update Ingress (No Downtime)

```bash
# Update production ingress
kubectl apply -f k8s/base/ingress-production.yaml --kubeconfig kubeconfig.yaml

# OR if using the TLS version
kubectl apply -f k8s/base/ingress.yaml --kubeconfig kubeconfig.yaml
```

### Step 4: Monitor Rollout

```bash
# Watch all pods updating
kubectl get pods -n uoulu -w --kubeconfig kubeconfig.yaml

# Check specific deployment rollout status
kubectl rollout status deployment/neuroclima-server -n uoulu --kubeconfig kubeconfig.yaml
kubectl rollout status deployment/neuroclima-processor -n uoulu --kubeconfig kubeconfig.yaml
kubectl rollout status deployment/neuroclima-client -n uoulu --kubeconfig kubeconfig.yaml
kubectl rollout status deployment/nginx-gateway -n uoulu --kubeconfig kubeconfig.yaml
kubectl rollout status deployment/neuroclima-grafana -n uoulu --kubeconfig kubeconfig.yaml
kubectl rollout status deployment/neuroclima-prometheus -n uoulu --kubeconfig kubeconfig.yaml
```

### Step 5: Verify Updates

```bash
# Check all pods are running
kubectl get pods -n uoulu --kubeconfig kubeconfig.yaml

# Verify image versions
kubectl get deployments -n uoulu -o wide --kubeconfig kubeconfig.yaml

# Check specific deployment details
kubectl describe deployment neuroclima-server -n uoulu --kubeconfig kubeconfig.yaml | grep Image
kubectl describe deployment neuroclima-processor -n uoulu --kubeconfig kubeconfig.yaml | grep Image
kubectl describe deployment nginx-gateway -n uoulu --kubeconfig kubeconfig.yaml | grep Image

# Verify security contexts
kubectl get pod <pod-name> -n uoulu -o yaml --kubeconfig kubeconfig.yaml | grep -A 5 securityContext

# Check probes are configured
kubectl describe deployment neuroclima-server -n uoulu --kubeconfig kubeconfig.yaml | grep -A 3 Liveness
```

### Step 6: Test Application

```bash
# Port forward to test locally
kubectl port-forward -n uoulu svc/nginx-gateway 8080:80 --kubeconfig kubeconfig.yaml

# Test routes
curl http://localhost:8080/              # Should return client
curl http://localhost:8080/server/health # Should return server health
curl http://localhost:8080/processor/    # Should return processor response
```

Or access via your ngrok URL and test the application.

## One-Command Update (All at Once)

If you want to update everything at once:

```bash
# Update all deployments
kubectl apply -f k8s/server/deployment.yaml \
              -f k8s/processor/deployment.yaml \
              -f k8s/client/deployment.yaml \
              -f k8s/gateway/nginx-gateway.yaml \
              -f k8s/ngrok/deployment.yaml \
              -f k8s/monitoring/grafana-deployment.yaml \
              -f k8s/monitoring/prometheus-deployment.yaml \
              -f k8s/base/ingress-production.yaml \
              --kubeconfig kubeconfig.yaml

# Watch the rollout
kubectl get pods -n uoulu -w --kubeconfig kubeconfig.yaml
```

## Troubleshooting

### If Pods Fail to Start

```bash
# Check pod status
kubectl get pods -n uoulu --kubeconfig kubeconfig.yaml

# Check pod logs
kubectl logs <pod-name> -n uoulu --kubeconfig kubeconfig.yaml

# Describe pod to see events
kubectl describe pod <pod-name> -n uoulu --kubeconfig kubeconfig.yaml
```

### Common Issues

**Issue: ImagePullBackOff**
- The specific version tags might not exist on Docker Hub
- Solution: Check if images exist or use `:latest` tag

**Issue: CrashLoopBackOff**
- Security context might prevent the container from starting
- Solution: Check logs, may need to adjust runAsUser

**Issue: Pods stuck in Pending**
- PVCs might not be bound
- Solution: Check PVC status with `kubectl get pvc -n uoulu`

## Rollback Instructions

If something goes wrong, you can rollback:

```bash
# Rollback specific deployment
kubectl rollout undo deployment/neuroclima-server -n uoulu --kubeconfig kubeconfig.yaml

# Rollback to specific revision
kubectl rollout history deployment/neuroclima-server -n uoulu --kubeconfig kubeconfig.yaml
kubectl rollout undo deployment/neuroclima-server --to-revision=2 -n uoulu --kubeconfig kubeconfig.yaml

# Restore from backup
kubectl apply -f backup-deployments.yaml --kubeconfig kubeconfig.yaml
```

## Expected Results

After successful update, you should see:

1. **All pods running** with new image versions
2. **Security contexts** applied (non-root users)
3. **Probes** configured and passing
4. **Nginx gateway** routing traffic correctly
5. **Application working** as before, but more secure

## Verification Checklist

- [ ] All pods are in `Running` state
- [ ] All deployments show `READY 1/1`
- [ ] Probes are passing (check with `kubectl describe`)
- [ ] Application accessible via ngrok/ingress
- [ ] API calls work (frontend can communicate with backend)
- [ ] Document processing works
- [ ] No error logs in pods

## Notes

- **PVC Storage Class**: Existing PVCs cannot be updated (immutable field). Only new PVCs will use `do-block-storage`.
- **Image Tags**: Make sure the specific version tags exist in your Docker registry. If v1.0.0 doesn't exist, you may need to build and push those images, or use `:latest`.
- **Zero Downtime**: Kubernetes rolling update ensures at least one pod is always running during the update.

## Need Help?

Check the logs:
```bash
kubectl logs deployment/neuroclima-server -n uoulu --kubeconfig kubeconfig.yaml
kubectl logs deployment/nginx-gateway -n uoulu --kubeconfig kubeconfig.yaml
```

Check events:
```bash
kubectl get events -n uoulu --sort-by='.lastTimestamp' --kubeconfig kubeconfig.yaml
```
