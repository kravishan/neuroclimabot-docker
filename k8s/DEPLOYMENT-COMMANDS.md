# Kubernetes Deployment Commands

## Overview
This guide provides PowerShell commands to deploy the NeuroClima application to the DigitalOcean Kubernetes cluster with:
- **Redis**: emptyDir (temporary storage)
- **MongoDB**: StatefulSet with persistent SSD storage
- **All services**: Node affinity and tolerations for memory-optimized nodes
- **Multi-replica support**: All Server, Processor, and Client replicas connect to the same MongoDB

## Prerequisites
```powershell
# Set kubeconfig
$env:KUBECONFIG = "D:/Projects/docker/bot/k8s/kubeconfig.yaml"

# Verify connection
kubectl get nodes
```

## Step 1: Clean up failed processor pods
```powershell
# Delete all failed processor pods
kubectl delete pod -l component=processor --field-selector=status.phase=Failed

# Or delete them individually
kubectl delete pod neuroclima-processor-645d7d4b8-4sjpx
kubectl delete pod neuroclima-processor-645d7d4b8-fhbtj
kubectl delete pod neuroclima-processor-645d7d4b8-k4d47
kubectl delete pod neuroclima-processor-645d7d4b8-q6w72
kubectl delete pod neuroclima-processor-645d7d4b8-xw6p4
```

## Step 2: Deploy MongoDB StatefulSet
```powershell
# Deploy MongoDB with persistent SSD storage
kubectl apply -f k8s/server/mongodb-statefulset.yaml

# Wait for MongoDB to be ready
kubectl wait --for=condition=ready pod -l component=mongodb --timeout=300s

# Verify MongoDB is running
kubectl get statefulset neuroclima-mongodb
kubectl get pod -l component=mongodb
kubectl logs -l component=mongodb
```

## Step 3: Update Redis deployment (emptyDir)
```powershell
# Apply updated Redis deployment with emptyDir
kubectl apply -f k8s/server/deployment.yaml

# Wait for Redis to restart
kubectl rollout status deployment neuroclima-redis

# Verify Redis is running
kubectl get pod -l component=redis
```

## Step 4: Update Server deployment (with MongoDB connection)
```powershell
# Apply updated Server deployment with MongoDB env vars
kubectl apply -f k8s/server/deployment.yaml

# Wait for rollout to complete
kubectl rollout status deployment neuroclima-server

# Verify Server is running and connected to MongoDB
kubectl get pod -l component=server
kubectl logs -l component=server --tail=50
```

## Step 5: Update Processor deployment
```powershell
# Apply updated Processor deployment with node affinity
kubectl apply -f k8s/processor/deployment.yaml

# Wait for rollout to complete
kubectl rollout status deployment neuroclima-processor
kubectl rollout status deployment neuroclima-unstructured

# Verify Processor is running
kubectl get pod -l component=processor
kubectl logs -l component=processor --tail=50
```

## Step 6: Update Client deployment
```powershell
# Apply updated Client deployment with node affinity
kubectl apply -f k8s/client/deployment.yaml

# Wait for rollout to complete
kubectl rollout status deployment neuroclima-client

# Verify Client is running
kubectl get pod -l component=client
```

## Step 7: Verify all services
```powershell
# Check all pods
kubectl get pods -o wide

# Check all services
kubectl get svc

# Check StatefulSet
kubectl get statefulset

# Check PVCs
kubectl get pvc

# Check which nodes pods are running on
kubectl get pods -o wide | Select-String "memory-optimized-pool"
```

## Scaling (Optional)
Once everything is running, you can scale up replicas:

```powershell
# Scale Server to 2 replicas
kubectl scale deployment neuroclima-server --replicas=2

# Scale Processor to 2 replicas (if cluster has enough memory)
kubectl scale deployment neuroclima-processor --replicas=2

# Scale Client to 2 replicas
kubectl scale deployment neuroclima-client --replicas=2

# Verify all replicas are running
kubectl get pods -o wide
```

## Troubleshooting

### Check pod logs
```powershell
# Server logs
kubectl logs -l component=server --tail=100

# Processor logs
kubectl logs -l component=processor --tail=100

# MongoDB logs
kubectl logs -l component=mongodb --tail=100

# Redis logs
kubectl logs -l component=redis --tail=100
```

### Check MongoDB connection
```powershell
# Get MongoDB pod name
kubectl get pod -l component=mongodb

# Connect to MongoDB shell
kubectl exec -it neuroclima-mongodb-0 -- mongosh

# Inside mongosh:
# show dbs
# use neuroclima
# show collections
```

### Check events
```powershell
# Check cluster events
kubectl get events --sort-by='.lastTimestamp'

# Check specific pod events
kubectl describe pod <pod-name>
```

### Restart deployments
```powershell
# Restart Server
kubectl rollout restart deployment neuroclima-server

# Restart Processor
kubectl rollout restart deployment neuroclima-processor

# Restart Client
kubectl rollout restart deployment neuroclima-client
```

## Notes

### Storage Configuration
- **Redis**: Uses `emptyDir` - data is lost on pod restart (session data is temporary)
- **MongoDB**: Uses persistent volume - data persists across pod restarts (analytics, feedback, session stats)
- **Processor PVCs**: Still using persistent volumes for GraphRAG, LanceDB data

### Node Affinity
All pods now have:
- Node affinity for `memory-optimized-pool`
- Tolerations for `type=memory-optimized:NoSchedule`

This ensures they run on the 2 new memory-optimized nodes you requested.

### MongoDB Connection
All Server replicas connect to the same MongoDB instance:
- Service: `neuroclima-mongodb`
- StatefulSet pod: `neuroclima-mongodb-0.neuroclima-mongodb.uoulu.svc.cluster.local`
- Port: `27017`
- Database: `neuroclima`
- No authentication (for initial setup)

To add authentication later, update the MongoDB StatefulSet with `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD`, then update the Server deployment with the credentials.
