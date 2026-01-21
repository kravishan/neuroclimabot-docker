# NeuroClima Bot - Public Deployment Guide

## 🎯 Overview

This guide walks you through deploying the NeuroClima Bot application to production with **2-replica high availability** configuration on your Kubernetes cluster.

**Target Environment:**
- **Domain:** `bot.neuroclima.eu`
- **Ingress:** Traefik with Let's Encrypt TLS
- **Namespace:** `uoulu`
- **Replicas:** 2 per service (4 services × 2 = 8 pods total)

---

## 📋 Pre-Deployment Checklist

### 1. Cluster Requirements

#### Current Cluster (INSUFFICIENT):
- ❌ 2 nodes × (4 vCPUs + 8GB RAM) = 8 vCPUs, 16GB RAM
- ❌ Cannot handle 2-replica deployment (requires 19.8Gi memory limits)

#### **REQUIRED Cluster (Option 1 - RECOMMENDED):**
- ✅ **3 nodes × (4 vCPUs + 16GB RAM) = 12 vCPUs, 48GB RAM**
- ✅ Total capacity: 48GB memory (2.4x required limits)
- ✅ Survives single node failure
- ✅ Room for autoscaling to 3-4 replicas

#### Alternative Cluster Options:

**Option 2: More nodes, standard memory**
- 4 nodes × (4 vCPUs + 8GB RAM) = 16 vCPUs, 32GB RAM
- Tighter memory fit but more redundancy

**Option 3: Premium setup**
- 3 nodes × (8 vCPUs + 16GB RAM) = 24 vCPUs, 48GB RAM
- Best performance, higher cost

### 2. Required Components

Verify these components are installed in your cluster:

```bash
# Check Traefik ingress controller
kubectl get pods -n kube-system | grep traefik

# Check metrics-server (required for HPA)
kubectl get deployment metrics-server -n kube-system

# If metrics-server is missing, install it:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 3. DNS Configuration

Ensure `bot.neuroclima.eu` points to your Traefik Load Balancer:

```bash
# Get your Load Balancer IP/hostname
kubectl get svc -n kube-system traefik

# Verify DNS resolution
nslookup bot.neuroclima.eu
```

### 4. External Services

Verify external VM services are accessible from the cluster:

- **Ollama:** LLM inference service
- **MinIO:** Object storage
- **Milvus:** Vector database

```bash
# Check connectivity from a test pod
kubectl run -it --rm test --image=curlimages/curl --restart=Never -n uoulu -- sh
# Inside pod:
curl -I http://<OLLAMA_IP>:11434
curl -I http://<MINIO_IP>:9000
curl http://<MILVUS_IP>:19530
```

---

## 🚀 Deployment Steps

### Step 1: Add Cluster Node (If Needed)

**If you haven't already, add a memory-optimized node to your cluster:**

Contact your cluster administrator to add:
- **1 node** with **4 vCPUs + 16GB RAM**

Total cluster after addition: **3 nodes with 48GB RAM**

### Step 2: Verify Namespace and Secrets

```bash
# Verify namespace exists
kubectl get namespace uoulu

# Verify secrets are configured
kubectl get secret neuroclima-secrets -n uoulu

# Check secret keys (without revealing values)
kubectl describe secret neuroclima-secrets -n uoulu
```

Required secret keys:
- `REDIS_PASSWORD`
- `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- `MILVUS_USER`, `MILVUS_PASSWORD`
- `SECRET_KEY` (JWT secret)
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- `MAILEROO_API_KEY`, `MAILEROO_FROM_EMAIL`
- `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST`
- `OPENAI_API_KEY`

### Step 3: Deploy Persistent Volume Claims (PVCs)

```bash
# Deploy PVCs for data persistence (55Gi total)
kubectl apply -f k8s/processor/pvc.yaml
kubectl apply -f k8s/server/pvc.yaml

# Verify PVCs are bound
kubectl get pvc -n uoulu
```

Expected PVCs:
- `processor-data-pvc` (10Gi)
- `graphrag-data-pvc` (20Gi)
- `lancedb-data-pvc` (10Gi)
- `server-data-pvc` (10Gi)
- `redis-data-pvc` (5Gi)

### Step 4: Deploy ConfigMaps

```bash
# Deploy shared configuration
kubectl apply -f k8s/base/configmap-example.yaml
kubectl apply -f k8s/processor/graphrag-settings-configmap.yaml
kubectl apply -f k8s/processor/graphrag-prompts-configmap.yaml

# Verify ConfigMaps
kubectl get configmap -n uoulu
```

### Step 5: Deploy Services

```bash
# Deploy all Kubernetes services
kubectl apply -f k8s/processor/service.yaml
kubectl apply -f k8s/server/service.yaml
kubectl apply -f k8s/client/service.yaml

# Verify services
kubectl get svc -n uoulu
```

### Step 6: Deploy Application Components

**Deploy in order to handle dependencies:**

```bash
# 1. Deploy Redis (cache/session store)
kubectl apply -f k8s/server/deployment.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l component=redis -n uoulu --timeout=120s

# 2. Deploy Unstructured API (document parser)
kubectl apply -f k8s/processor/deployment.yaml

# 3. Deploy Server (backend API)
# (This is already in k8s/server/deployment.yaml, already applied)

# 4. Deploy Client (frontend)
kubectl apply -f k8s/client/deployment.yaml

# Verify all deployments
kubectl get deployments -n uoulu
```

Expected deployments:
```
NAME                      READY   UP-TO-DATE   AVAILABLE
neuroclima-redis          1/1     1            1
neuroclima-server         2/2     2            2
neuroclima-processor      2/2     2            2
neuroclima-unstructured   2/2     2            2
neuroclima-client         2/2     2            2
```

### Step 7: Deploy Traefik IngressRoute

```bash
# Deploy Traefik ingress routing
kubectl apply -f k8s/base/traefik-ingressroute.yaml

# Verify IngressRoute is created
kubectl get ingressroute -n uoulu

# Check Traefik configuration
kubectl describe ingressroute neuroclima-ingressroute -n uoulu
```

### Step 8: Deploy Horizontal Pod Autoscaler (HPA)

```bash
# Deploy HPA for automatic scaling
kubectl apply -f k8s/base/hpa.yaml

# Verify HPAs are created
kubectl get hpa -n uoulu

# Check HPA status
kubectl describe hpa -n uoulu
```

Expected HPAs:
```
NAME                         REFERENCE                       TARGETS         MINPODS   MAXPODS
neuroclima-server-hpa        neuroclima-server               <cpu>/<memory>  2         4
neuroclima-processor-hpa     neuroclima-processor            <cpu>/<memory>  2         3
neuroclima-unstructured-hpa  neuroclima-unstructured         <cpu>/<memory>  2         3
neuroclima-client-hpa        neuroclima-client               <cpu>/<memory>  2         4
```

---

## ✅ Verification & Testing

### 1. Check Pod Distribution

Verify pods are spread across different nodes (anti-affinity):

```bash
# Show pods with their node assignments
kubectl get pods -n uoulu -o wide

# Expected: Each service's 2 replicas should be on different nodes
```

### 2. Test Health Checks

```bash
# Check readiness/liveness probes
kubectl get pods -n uoulu

# All pods should show "2/2 READY" (both containers running)
# If any show "1/2" or "0/2", check logs:
kubectl logs -n uoulu <pod-name>
kubectl describe pod -n uoulu <pod-name>
```

### 3. Test Application Endpoints

```bash
# Test frontend (should return HTML)
curl -I https://bot.neuroclima.eu/

# Test server API health check
curl https://bot.neuroclima.eu/server/health

# Test processor health check
curl https://bot.neuroclima.eu/processor/health
```

### 4. Check TLS Certificate

```bash
# Verify Let's Encrypt certificate
echo | openssl s_client -connect bot.neuroclima.eu:443 -servername bot.neuroclima.eu 2>/dev/null | openssl x509 -noout -dates -issuer

# Should show:
# issuer= /C=US/O=Let's Encrypt/...
```

### 5. Monitor Resource Usage

```bash
# Check current CPU/memory usage
kubectl top nodes
kubectl top pods -n uoulu

# Watch HPA metrics in real-time
kubectl get hpa -n uoulu --watch
```

### 6. End-to-End User Testing

1. **Open application:** https://bot.neuroclima.eu/
2. **Create account** or **login**
3. **Upload a document** for processing
4. **Start a chat** with the bot
5. **Verify responses** are working correctly

---

## 📊 Monitoring & Observability

### Check Logs

```bash
# Server logs
kubectl logs -f deployment/neuroclima-server -n uoulu

# Processor logs
kubectl logs -f deployment/neuroclima-processor -n uoulu

# Client logs
kubectl logs -f deployment/neuroclima-client -n uoulu

# All logs for a specific service
kubectl logs -l component=server -n uoulu --tail=100 -f
```

### Monitor Pod Events

```bash
# Watch all events in the namespace
kubectl get events -n uoulu --watch

# Check specific pod events
kubectl describe pod <pod-name> -n uoulu
```

### Check Service Endpoints

```bash
# View service endpoints (shows which pods are backing each service)
kubectl get endpoints -n uoulu
```

### Resource Consumption

```bash
# Check node capacity vs allocation
kubectl describe nodes | grep -A 5 "Allocated resources"

# Check pod resource requests vs limits
kubectl describe pod <pod-name> -n uoulu | grep -A 10 "Requests:"
```

---

## 🔧 Troubleshooting

### Pods Not Starting

**Symptoms:** Pods stuck in `Pending`, `CrashLoopBackOff`, or `ImagePullBackOff`

**Solutions:**

```bash
# Check pod status
kubectl describe pod <pod-name> -n uoulu

# Common issues:
# 1. Insufficient resources → Add more nodes
# 2. Image pull errors → Check image name and registry access
# 3. Config/Secret missing → Verify ConfigMaps and Secrets exist
# 4. PVC not bound → Check PVC status: kubectl get pvc -n uoulu
```

### Health Checks Failing

**Symptoms:** Pods showing `0/2` or `1/2` ready

**Solutions:**

```bash
# Check liveness/readiness probe failures
kubectl describe pod <pod-name> -n uoulu

# Check application logs for errors
kubectl logs <pod-name> -n uoulu

# Common issues:
# 1. Application not listening on correct port
# 2. Health endpoint path incorrect
# 3. Application startup takes longer than initialDelaySeconds
#    → Increase initialDelaySeconds in deployment.yaml
```

### Ingress Not Working

**Symptoms:** `404 Not Found` or connection timeout at https://bot.neuroclima.eu/

**Solutions:**

```bash
# Check IngressRoute status
kubectl get ingressroute -n uoulu
kubectl describe ingressroute neuroclima-ingressroute -n uoulu

# Check Traefik logs
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik

# Verify DNS
nslookup bot.neuroclima.eu

# Check TLS certificate
kubectl get certificate -n uoulu  # If using cert-manager
```

### High Memory Usage

**Symptoms:** Pods being OOMKilled (Out Of Memory)

**Solutions:**

```bash
# Check which pods are using most memory
kubectl top pods -n uoulu --sort-by=memory

# Check pod events for OOMKilled
kubectl get events -n uoulu | grep OOMKilled

# Solution: Increase memory limits or add more nodes
```

### HPA Not Scaling

**Symptoms:** HPA shows `<unknown>` for metrics

**Solutions:**

```bash
# Check if metrics-server is running
kubectl get pods -n kube-system | grep metrics-server

# Check HPA status
kubectl describe hpa <hpa-name> -n uoulu

# Test metrics manually
kubectl top pods -n uoulu

# If metrics-server is missing, install it:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

---

## 🔄 Scaling & Updates

### Manual Scaling

```bash
# Scale a deployment manually
kubectl scale deployment neuroclima-server --replicas=3 -n uoulu

# Check scaling status
kubectl get deployment neuroclima-server -n uoulu
```

### Rolling Updates

```bash
# Update image version
kubectl set image deployment/neuroclima-server server=docker.io/raviyah/neuroclima-server:v2.0 -n uoulu

# Watch rollout status
kubectl rollout status deployment/neuroclima-server -n uoulu

# Rollback if needed
kubectl rollout undo deployment/neuroclima-server -n uoulu
```

### Adjust HPA Thresholds

Edit the HPA configuration and reapply:

```bash
# Edit HPA
kubectl edit hpa neuroclima-server-hpa -n uoulu

# Or update the file and reapply
kubectl apply -f k8s/base/hpa.yaml
```

---

## 🛡️ Security Checklist

- [ ] All secrets stored in Kubernetes Secrets (not in ConfigMaps or code)
- [ ] TLS enabled for all external traffic (Traefik + Let's Encrypt)
- [ ] Redis password protected
- [ ] MinIO access keys rotated regularly
- [ ] Network policies configured (optional but recommended)
- [ ] RBAC permissions follow least-privilege principle
- [ ] Regular security updates for container images
- [ ] Backup strategy in place for PVCs

---

## 💾 Backup & Recovery

### Backup Strategy

**Persistent Data:**
```bash
# Backup PVC data (example for server-data-pvc)
kubectl exec -it deployment/neuroclima-server -n uoulu -- tar czf /tmp/backup.tar.gz /app/data
kubectl cp uoulu/<pod-name>:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz
```

**Configuration Backup:**
```bash
# Export all ConfigMaps
kubectl get configmap -n uoulu -o yaml > configmaps-backup.yaml

# Export all Secrets (encrypted)
kubectl get secret -n uoulu -o yaml > secrets-backup.yaml
```

### Recovery Procedure

1. Restore PVCs from backup
2. Deploy PVCs: `kubectl apply -f k8s/*/pvc.yaml`
3. Restore ConfigMaps and Secrets
4. Deploy services and deployments
5. Verify application functionality

---

## 📈 Performance Optimization

### 1. Monitor and Tune Resource Limits

```bash
# Check actual usage vs requests/limits
kubectl top pods -n uoulu

# Adjust based on real usage patterns
# Edit deployment.yaml resource values and reapply
```

### 2. Database Optimization

- **Redis:** Monitor memory usage, adjust maxmemory policy if needed
- **Milvus:** Index optimization for vector search performance
- **MinIO:** Configure bucket lifecycle policies for old data

### 3. Application-Level Optimizations

- Enable caching at application level
- Optimize GraphRAG model selection (smaller/faster models if acceptable)
- Implement request queuing for heavy processing tasks
- Use connection pooling for external services

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks

**Weekly:**
- [ ] Check resource utilization: `kubectl top nodes` and `kubectl top pods -n uoulu`
- [ ] Review pod logs for errors
- [ ] Verify all HPAs are functioning
- [ ] Check disk usage for PVCs

**Monthly:**
- [ ] Update container images to latest versions
- [ ] Review and optimize resource requests/limits
- [ ] Rotate secrets (API keys, passwords)
- [ ] Review and clean up old data in MinIO/Milvus

**Quarterly:**
- [ ] Perform load testing
- [ ] Review cluster capacity and plan scaling
- [ ] Security audit (scan images for vulnerabilities)
- [ ] Backup verification (test restore procedures)

### Useful Commands Reference

```bash
# Get all resources in namespace
kubectl get all -n uoulu

# Describe full deployment
kubectl describe deployment neuroclima-server -n uoulu

# Get pod logs (last 100 lines)
kubectl logs --tail=100 <pod-name> -n uoulu

# Get pod logs (follow/stream)
kubectl logs -f <pod-name> -n uoulu

# Execute command in pod
kubectl exec -it <pod-name> -n uoulu -- /bin/sh

# Port forward for local testing
kubectl port-forward svc/neuroclima-server 8000:8000 -n uoulu

# Delete and recreate a pod (for testing)
kubectl delete pod <pod-name> -n uoulu
# (Deployment will automatically create a new one)

# Check resource quotas
kubectl describe resourcequota -n uoulu

# Get deployment rollout history
kubectl rollout history deployment/neuroclima-server -n uoulu
```

---

## 🎉 Conclusion

Your NeuroClima Bot is now deployed with:

✅ **High Availability:** 2 replicas per service across multiple nodes
✅ **Auto-Scaling:** HPA configured for traffic spikes
✅ **Health Monitoring:** Liveness/readiness probes for all services
✅ **Secure Access:** HTTPS with Let's Encrypt TLS
✅ **Production-Ready:** Pod anti-affinity, resource limits, persistent storage

**Next Steps:**
1. Monitor application performance over first week
2. Tune HPA thresholds based on actual traffic patterns
3. Set up external monitoring (Prometheus/Grafana) if not already configured
4. Plan capacity scaling based on user growth

**Application URL:** https://bot.neuroclima.eu/

Good luck with your public release! 🚀
