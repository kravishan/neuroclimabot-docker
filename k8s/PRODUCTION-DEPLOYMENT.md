# Production Deployment Guide

## Overview

This guide covers deploying NeuroClima for production with high availability and auto-scaling capabilities.

## Architecture

```
Internet → Traefik LB (TLS with Let's Encrypt)
              ↓
    bot.neuroclima.eu/          → neuroclima-client (2 replicas)
    bot.neuroclima.eu/server    → neuroclima-server (2 replicas)
    bot.neuroclima.eu/processor → neuroclima-processor (1 replica, scalable to 2)
```

## Current Configuration

### Replicas & Resources

| Service | Replicas | Memory Request | Memory Limit | CPU Request | CPU Limit |
|---------|----------|----------------|--------------|-------------|-----------|
| Client | 2 | 128Mi × 2 = 256Mi | 256Mi × 2 = 512Mi | 100m × 2 = 200m | 200m × 2 = 400m |
| Server | 2 | 1Gi × 2 = 2Gi | 2Gi × 2 = 4Gi | 250m × 2 = 500m | 1000m × 2 = 2000m |
| Processor | 1 | 1.5Gi | 5Gi | 500m | 2000m |
| Unstructured | 1 | 1Gi | 2Gi | 250m | 1000m |
| Redis | 1 | 512Mi | 1Gi | 250m | 500m |
| **TOTAL** | **7 pods** | **~5.3Gi** | **~12.5Gi** | **~1.7 cores** | **~5.9 cores** |

### Current Cluster Capacity
- **2 nodes** × (4vCPUs + 8GB RAM) = **8 vCPUs, 16GB RAM total**
- **Usable** (after system overhead): ~**7 vCPUs, ~14GB RAM**
- **Status**: ✅ Fits comfortably with current configuration

## High Availability Features

### 1. Multiple Replicas
- **Client**: 2 replicas for load distribution
- **Server**: 2 replicas for HA and load balancing
- **Processor**: 1 replica (ready to scale to 2)

### 2. Pod Anti-Affinity
All services configured with `preferredDuringSchedulingIgnoredDuringExecution` anti-affinity to spread replicas across different nodes, preventing single node failure from taking down entire service.

### 3. Health Checks
- **Readiness probes**: Ensure pods only receive traffic when ready
- **Liveness probes**: Automatically restart unhealthy pods

### 4. Pod Disruption Budgets
- **2-replica services** (client, server): `minAvailable: 1` ensures at least 1 pod always running
- **1-replica services** (processor, redis, unstructured): `maxUnavailable: 0` prevents voluntary disruption

### 5. Horizontal Pod Autoscaling
- **Client**: Auto-scale 2-4 replicas based on CPU (70% target)
- **Server**: Auto-scale 2-4 replicas based on CPU (70% target)
- **Processor**: Auto-scale 1-2 replicas based on CPU (70% target)

## Deployment Steps

### Prerequisites
1. Traefik IngressRoute configured (already done: `k8s/base/traefik-ingressroute.yaml`)
2. DNS pointing to Traefik LoadBalancer (already done: `bot.neuroclima.eu`)
3. Metrics Server installed for HPA (optional but recommended)

### Step 1: Deploy Updated Services

```bash
# Apply deployments with HA features
kubectl apply -f k8s/client/deployment.yaml
kubectl apply -f k8s/server/deployment.yaml
kubectl apply -f k8s/processor/deployment.yaml

# Apply services (if not already applied)
kubectl apply -f k8s/client/service.yaml
kubectl apply -f k8s/server/service.yaml
kubectl apply -f k8s/processor/service.yaml
```

### Step 2: Deploy Pod Disruption Budgets

```bash
kubectl apply -f k8s/base/poddisruptionbudgets.yaml
```

### Step 3: Deploy Horizontal Pod Autoscalers (Optional)

**Check if metrics-server is installed:**
```bash
kubectl get apiservice v1beta1.metrics.k8s.io
```

**If not installed:**
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

**Apply HPAs:**
```bash
kubectl apply -f k8s/base/hpa.yaml
```

### Step 4: Verify Deployment

```bash
# Check pod status
kubectl get pods -n uoulu -l app=neuroclima

# Check replica counts
kubectl get deployments -n uoulu

# Check PDBs
kubectl get pdb -n uoulu

# Check HPAs (if enabled)
kubectl get hpa -n uoulu

# Check Traefik routing
kubectl get ingressroute -n uoulu
```

## Monitoring & Validation

### Check Pod Distribution Across Nodes
```bash
kubectl get pods -n uoulu -l app=neuroclima -o wide
```

Verify that replicas are spread across different nodes (NODE column should show different nodes for replicas of the same service).

### Test Health Endpoints
```bash
# Test client
curl https://bot.neuroclima.eu/

# Test server
curl https://bot.neuroclima.eu/server/health

# Test processor
curl https://bot.neuroclima.eu/processor/health
```

### Monitor Resource Usage
```bash
# Overall resource usage
kubectl top nodes

# Pod resource usage
kubectl top pods -n uoulu
```

### Check Pod Events
```bash
kubectl get events -n uoulu --sort-by='.lastTimestamp' | head -20
```

## Scaling Recommendations

### Current Cluster (2 nodes × 4vCPU/8GB)
✅ **Sufficient for:**
- Client: 2 replicas
- Server: 2 replicas
- Processor: 1 replica
- Total: ~5.3Gi request, ~12.5Gi limit

### Option 1: Add 1 More Basic Node (Budget-Friendly)
**Total**: 3 nodes × 4vCPU/8GB = 12 vCPUs, 24GB RAM

✅ **Allows:**
- Client: 2-4 replicas (with HPA)
- Server: 2-4 replicas (with HPA)
- Processor: 2 replicas (10Gi for 2 replicas)
- **Cost**: Lowest increment
- **Recommendation**: Good for current needs + growth headroom

### Option 2: Memory-Optimized Nodes (Future-Proof)
**Recommended**: 3 nodes × 4vCPU/16GB = 12 vCPUs, 48GB RAM

✅ **Allows:**
- Client: 2-4 replicas
- Server: 2-4 replicas
- Processor: 3-4 replicas (15-20Gi total)
- **Future-proof**: Easy scaling beyond current needs
- **Recommendation**: Best for long-term growth

## Troubleshooting

### Pods Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n uoulu

# Check events
kubectl get events -n uoulu --field-selector involvedObject.name=<pod-name>

# Check logs
kubectl logs <pod-name> -n uoulu
```

### Health Checks Failing
```bash
# Check health endpoint directly
kubectl port-forward -n uoulu pod/<pod-name> 8080:8000
curl http://localhost:8080/health

# Check readiness/liveness probe configuration
kubectl describe pod <pod-name> -n uoulu | grep -A 10 "Liveness\|Readiness"
```

### HPA Not Scaling
```bash
# Check HPA status
kubectl describe hpa <hpa-name> -n uoulu

# Check metrics server
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -n uoulu

# Check current resource usage
kubectl get hpa -n uoulu
```

### PDB Blocking Node Drains
```bash
# Check PDB status
kubectl get pdb -n uoulu

# Check which pods are protected
kubectl describe pdb <pdb-name> -n uoulu

# Force drain (use with caution)
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force
```

## Rolling Updates

### Update Docker Images
```bash
# Update client
kubectl set image deployment/neuroclima-client client=docker.io/raviyah/neuroclima-client:v2 -n uoulu

# Update server
kubectl set image deployment/neuroclima-server server=docker.io/raviyah/neuroclima-server:v2 -n uoulu

# Update processor
kubectl set image deployment/neuroclima-processor processor=docker.io/raviyah/neuroclima-processor:v2 -n uoulu

# Check rollout status
kubectl rollout status deployment/neuroclima-client -n uoulu
```

### Rollback if Needed
```bash
# Check rollout history
kubectl rollout history deployment/neuroclima-client -n uoulu

# Rollback to previous version
kubectl rollout undo deployment/neuroclima-client -n uoulu

# Rollback to specific revision
kubectl rollout undo deployment/neuroclima-client --to-revision=2 -n uoulu
```

## Best Practices

1. **Always test in staging first** before deploying to production
2. **Monitor resource usage** and adjust requests/limits accordingly
3. **Set up alerts** for pod failures, high resource usage, and health check failures
4. **Use semantic versioning** for Docker images (avoid `:latest` in production)
5. **Regular backups** of persistent volumes (Redis, server data, processor data)
6. **Document all changes** and maintain runbooks for common issues
7. **Test disaster recovery** procedures regularly

## Current Status

- ✅ Traefik IngressRoute configured with TLS
- ✅ Client scaled to 2 replicas with HA features
- ✅ Server scaled to 2 replicas with HA features
- ✅ Processor configured with HA features (1 replica, ready to scale)
- ✅ Pod Disruption Budgets configured
- ✅ Horizontal Pod Autoscalers configured
- ✅ Health probes configured for all services
- ✅ Pod anti-affinity configured for replica distribution

## Next Steps

1. **Monitor resource usage** for 1-2 weeks to understand actual needs
2. **Decide on cluster scaling** (Option 1 or Option 2 above)
3. **Enable metrics-server and HPAs** if not already enabled
4. **Set up monitoring/alerting** (Prometheus, Grafana, or cloud provider monitoring)
5. **Consider adding more replicas** for processor when cluster resources allow
6. **Implement automated backups** for persistent volumes
7. **Create disaster recovery plan** and test it

## Support

For issues or questions, refer to:
- Kubernetes documentation: https://kubernetes.io/docs/
- Traefik documentation: https://doc.traefik.io/traefik/
- Project repository: https://github.com/kravishan/neuroclimabot-docker
