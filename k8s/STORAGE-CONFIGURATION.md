# Kubernetes Storage Configuration

## Overview
This document describes the storage architecture for the NeuroClima application running on DigitalOcean Kubernetes.

## Storage Strategy

### Persistent Storage (Node SSD) - Data persists across pod restarts
- **MongoDB**: Database for analytics, feedback, session statistics (20Gi)
- **GraphRAG Data**: Pre-computed knowledge graph data (20Gi)
- **LanceDB**: Vector database for document embeddings (10Gi)
- **Processor Data**: General processor working directory (10Gi)
- **Server Data**: Server working directory (10Gi)

### Temporary Storage (emptyDir) - Data lost on pod restart
- **Redis**: Session cache and temporary data (cleared on restart)

---

## Storage Details

### 1. MongoDB (Persistent - StatefulSet)
```yaml
Type: StatefulSet with volumeClaimTemplate
Storage: 20Gi persistent volume (node SSD)
Location: k8s/server/mongodb-statefulset.yaml
Mount Path: /data/db
Purpose: Persistent database for analytics, feedback, session stats
```

**Why persistent?**
- Analytics data must persist across restarts
- Feedback submissions are valuable and must be retained
- Session statistics accumulate over time

### 2. GraphRAG Data (Persistent - PVC)
```yaml
PVC Name: graphrag-data-pvc
Storage: 20Gi persistent volume (node SSD)
Location: k8s/processor/pvc.yaml (lines 13-23)
Mount Path: /app/graphrag (in Processor pod)
Purpose: Pre-computed knowledge graph, entities, relationships
```

**Files stored:**
- `entities.parquet` - Knowledge graph entities
- `relationships.parquet` - Entity relationships
- `communities/` - Community detection results
- Other GraphRAG output artifacts

**Why persistent?**
- GraphRAG data is expensive to compute (takes hours)
- Data must persist across pod restarts and scaling
- Shared across multiple Processor replicas (ReadWriteOnce with single writer)

**Init strategy:**
- Init container copies data from Docker image on first run
- Subsequent restarts reuse existing data from PVC
- See: `k8s/processor/deployment.yaml` lines 114-138

### 3. LanceDB (Persistent - PVC)
```yaml
PVC Name: lancedb-data-pvc
Storage: 10Gi persistent volume (node SSD)
Location: k8s/processor/pvc.yaml (lines 25-35)
Mount Path: /app/lancedb (in Processor pod)
Purpose: Vector database for document embeddings
```

**Why persistent?**
- Document embeddings are expensive to compute
- Vector index must persist for consistent search results
- Required for document retrieval and semantic search

### 4. Processor Data (Persistent - PVC)
```yaml
PVC Name: processor-data-pvc
Storage: 10Gi persistent volume (node SSD)
Location: k8s/processor/pvc.yaml (lines 1-11)
Mount Path: /app/data (in Processor pod)
Purpose: Working directory for document processing
```

### 5. Server Data (Persistent - PVC)
```yaml
PVC Name: server-data-pvc
Storage: 10Gi persistent volume (node SSD)
Location: k8s/server/pvc.yaml (lines 4-12)
Mount Path: /app/data (in Server pod)
Purpose: Working directory for server operations
```

### 6. Redis (Temporary - emptyDir)
```yaml
Type: emptyDir (temporary storage)
Location: k8s/server/deployment.yaml (lines 48-49)
Mount Path: /data (in Redis pod)
Purpose: Session cache and temporary data
```

**Why emptyDir?**
- Redis is used for session caching and temporary data
- Data can be safely cleared on pod restart
- Reduces storage costs and simplifies management
- Recommended by DigitalOcean team for temporary storage

---

## PowerShell Commands to Verify Storage

### Check PVCs
```powershell
# Set kubeconfig
$env:KUBECONFIG = "D:/Projects/docker/bot/k8s/kubeconfig.yaml"

# List all PVCs
kubectl get pvc

# Expected output:
# NAME                  STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS       AGE
# graphrag-data-pvc     Bound    pvc-xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx      20Gi       RWO            do-block-storage   Xd
# lancedb-data-pvc      Bound    pvc-xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx      10Gi       RWO            do-block-storage   Xd
# processor-data-pvc    Bound    pvc-xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx      10Gi       RWO            do-block-storage   Xd
# server-data-pvc       Bound    pvc-xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx      10Gi       RWO            do-block-storage   Xd
# mongodb-data-xxx      Bound    pvc-xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx      20Gi       RWO            do-block-storage   Xd

# Check PVC details
kubectl describe pvc graphrag-data-pvc
kubectl describe pvc lancedb-data-pvc
```

### Check Persistent Volumes
```powershell
# List all PVs (you might not have permissions, but try)
kubectl get pv

# Check storage class (should be do-block-storage for DigitalOcean SSD)
kubectl get storageclass
```

### Verify Data in Pods
```powershell
# Check GraphRAG data in Processor pod
kubectl exec -it deployment/neuroclima-processor -- ls -lh /app/graphrag/output/

# Expected files:
# entities.parquet
# relationships.parquet
# communities/
# ...

# Check LanceDB data
kubectl exec -it deployment/neuroclima-processor -- ls -lh /app/lancedb/

# Check MongoDB data
kubectl exec -it neuroclima-mongodb-0 -- ls -lh /data/db/

# Check Redis is using emptyDir (temporary)
kubectl exec -it deployment/neuroclima-redis -- df -h /data
```

### Monitor Storage Usage
```powershell
# Check disk usage in Processor pod
kubectl exec -it deployment/neuroclima-processor -- df -h

# Check disk usage in MongoDB pod
kubectl exec -it neuroclima-mongodb-0 -- df -h

# Check pod storage metrics
kubectl top pods
```

---

## Storage Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    DigitalOcean Kubernetes Cluster               │
│                                                                   │
│  ┌────────────────┐      ┌────────────────┐                     │
│  │ Processor Pod  │      │ Processor Pod  │  (when scaled)       │
│  │                │      │                │                     │
│  │  ┌──────────┐  │      │  ┌──────────┐  │                     │
│  │  │ GraphRAG │◄─┼──────┼─►│ GraphRAG │  │  Shared PVC         │
│  │  └──────────┘  │      │  └──────────┘  │  (ReadWriteOnce)    │
│  │  ┌──────────┐  │      │  ┌──────────┐  │                     │
│  │  │ LanceDB  │◄─┼──────┼─►│ LanceDB  │  │  Shared PVC         │
│  │  └──────────┘  │      │  └──────────┘  │  (ReadWriteOnce)    │
│  └────────────────┘      └────────────────┘                     │
│           ▲                       ▲                              │
│           │                       │                              │
│           │   ┌───────────────────┴──────┐                      │
│           │   │ Persistent Volumes (SSD)  │                      │
│           │   │ - graphrag-data-pvc (20Gi)│                      │
│           │   │ - lancedb-data-pvc (10Gi) │                      │
│           │   └───────────────────────────┘                      │
│           │                                                      │
│  ┌────────▼────────┐                                             │
│  │ Server Pod(s)   │                                             │
│  │                 │      ┌────────────────┐                     │
│  │  MongoDB Client ├─────►│ MongoDB StatefulSet │               │
│  │                 │      │  - 20Gi PVC     │                    │
│  │  Redis Client   │      │  - Persistent   │                    │
│  └────────┬────────┘      └────────────────┘                     │
│           │                                                      │
│           │   ┌─────────────────┐                               │
│           └──►│ Redis Pod       │                               │
│               │ - emptyDir      │  Temporary storage            │
│               │ - Cleared on    │  (data lost on restart)       │
│               │   restart       │                               │
│               └─────────────────┘                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration from Old Configuration

### What Changed
1. **Redis**: Changed from PVC to emptyDir
   - Old: `redis-data-pvc` (5Gi persistent)
   - New: `emptyDir` (temporary)
   - Impact: Redis data will be cleared on pod restart (acceptable for cache)

2. **MongoDB**: Added StatefulSet with persistent storage
   - New: `mongodb-data-xxx` (20Gi persistent)
   - Purpose: Centralized database for all Server replicas

### Migration Steps (if needed)
```powershell
# 1. Backup Redis data before switching to emptyDir (optional, if you have important data)
kubectl exec -it deployment/neuroclima-redis -- redis-cli SAVE
kubectl cp neuroclima-redis-xxxxx:/data/dump.rdb ./redis-backup.rdb

# 2. Delete old Redis PVC (after switching to emptyDir)
kubectl delete pvc redis-data-pvc

# 3. Apply new configurations
kubectl apply -f k8s/server/mongodb-statefulset.yaml
kubectl apply -f k8s/server/deployment.yaml
kubectl apply -f k8s/processor/deployment.yaml
```

---

## Scaling Considerations

### Multiple Processor Replicas
- **GraphRAG Data**: ReadWriteOnce PVC can only be mounted by one pod at a time
- **Solution 1**: Use ReadWriteMany PVC (requires NFS or similar)
- **Solution 2**: Keep 1 Processor replica (current configuration)
- **Solution 3**: Copy GraphRAG data to each pod's local storage (inefficient)

**Current approach**: 1 Processor replica with anti-affinity rules ready for scaling when storage solution is implemented.

### Multiple Server Replicas
- **MongoDB**: All Server replicas connect to the same MongoDB StatefulSet
- **No issues**: Multiple pods can connect to the same MongoDB instance
- **Ready to scale**: Server can scale to multiple replicas without changes

---

## Troubleshooting

### PVC Not Binding
```powershell
# Check PVC status
kubectl get pvc
kubectl describe pvc <pvc-name>

# Check events
kubectl get events --sort-by='.lastTimestamp' | Select-String "pvc"

# Check storage class
kubectl get storageclass
```

### Out of Storage
```powershell
# Check PVC usage
kubectl exec -it deployment/neuroclima-processor -- df -h

# Resize PVC (if supported by storage class)
kubectl patch pvc graphrag-data-pvc -p '{"spec":{"resources":{"requests":{"storage":"30Gi"}}}}'
```

### Data Loss After Pod Restart
```powershell
# Check if volume is emptyDir (temporary) or PVC (persistent)
kubectl get pod <pod-name> -o yaml | Select-String -Pattern "emptyDir|persistentVolumeClaim" -Context 2

# Check PVC is bound
kubectl get pvc
```

---

## Cost Optimization

### Current Storage Costs (DigitalOcean Block Storage)
- GraphRAG: 20Gi × $0.10/GB/month = $2.00/month
- LanceDB: 10Gi × $0.10/GB/month = $1.00/month
- MongoDB: 20Gi × $0.10/GB/month = $2.00/month
- Processor: 10Gi × $0.10/GB/month = $1.00/month
- Server: 10Gi × $0.10/GB/month = $1.00/month
- **Total: ~$7.00/month**

### Savings from emptyDir
- Removed Redis PVC: 5Gi × $0.10/GB/month = **$0.50/month saved**

---

## Summary

✅ **GraphRAG data** → 20Gi persistent SSD storage (already configured)
✅ **LanceDB** → 10Gi persistent SSD storage (already configured)
✅ **MongoDB** → 20Gi persistent SSD storage (newly added StatefulSet)
✅ **Redis** → emptyDir temporary storage (changed from PVC)
✅ **All pods** → Node affinity for memory-optimized nodes

Your GraphRAG and LanceDB data are **safe and persistent** across pod restarts!
