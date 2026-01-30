# Clean Deployment Guide - Deploy in Correct Order

This guide will help you delete all existing deployments and redeploy them in the correct order to ensure all dependencies are satisfied.

## Deployment Order
1. **MongoDB** - Database (no dependencies)
2. **Processor** - Document processing (depends on external services only)
3. **Redis** - Cache (no dependencies)
4. **Server** - API server (depends on Redis + MongoDB)
5. **Client** - Web UI (depends on Server)

---

## Step 1: Delete All Deployments

```powershell
# Set kubeconfig
$env:KUBECONFIG = "D:/Projects/docker/bot/k8s/kubeconfig.yaml"

# Delete all deployments (this will NOT delete PVCs - your data is safe!)
kubectl delete deployment --all -n uoulu

# Also delete StatefulSets (if MongoDB was already deployed)
kubectl delete statefulset --all -n uoulu

# Verify all pods are terminated
kubectl get pods

# Wait until no pods are running (except system pods)
# This may take 30-60 seconds
```

**IMPORTANT**: This command does NOT delete:
- ❌ PersistentVolumeClaims (PVCs) - Your data is safe!
- ❌ Services - Networking is preserved
- ❌ ConfigMaps - Configuration is preserved
- ❌ Secrets - Credentials are preserved

---

## Step 2: Deploy MongoDB StatefulSet

MongoDB must be deployed first since Server depends on it.

```powershell
# Apply MongoDB StatefulSet
kubectl apply -f k8s/server/mongodb-statefulset.yaml

# Wait for MongoDB to be ready (this may take 2-3 minutes)
kubectl wait --for=condition=ready pod -l component=mongodb --timeout=300s

# Verify MongoDB is running
kubectl get statefulset neuroclima-mongodb
kubectl get pod -l component=mongodb

# Check MongoDB logs to ensure it started successfully
kubectl logs -l component=mongodb --tail=50

# Test MongoDB connection
kubectl exec -it neuroclima-mongodb-0 -- mongosh --eval "db.adminCommand('ping')"
```

**Expected output:**
```
statefulset.apps/neuroclima-mongodb created
service/neuroclima-mongodb created
pod/neuroclima-mongodb-0 condition met
NAME                  READY   AGE
neuroclima-mongodb-0  1/1     Running   0          2m
```

---

## Step 3: Deploy Processor (Unstructured + Processor)

Processor includes both the Unstructured API and the main Processor service.

```powershell
# Apply Processor deployment (includes Unstructured)
kubectl apply -f k8s/processor/deployment.yaml

# Wait for Unstructured to be ready (fast startup ~30s)
kubectl wait --for=condition=ready pod -l component=unstructured --timeout=180s

# Wait for Processor to be ready (slow startup ~2-3 minutes due to model loading)
kubectl wait --for=condition=ready pod -l component=processor --timeout=300s

# Verify both are running
kubectl get deployment neuroclima-unstructured neuroclima-processor
kubectl get pod -l component=unstructured
kubectl get pod -l component=processor

# Check Processor logs
kubectl logs -l component=processor --tail=50

# Check if GraphRAG data was initialized
kubectl exec -it deployment/neuroclima-processor -- ls -lh /app/graphrag/output/
```

**Expected output:**
```
deployment.apps/neuroclima-unstructured created
deployment.apps/neuroclima-processor created
pod/neuroclima-unstructured-xxx condition met
pod/neuroclima-processor-xxx condition met
NAME                      READY   UP-TO-DATE   AVAILABLE   AGE
neuroclima-unstructured   1/1     1            1           2m
neuroclima-processor      1/1     1            1           3m
```

---

## Step 4: Deploy Redis

Redis provides caching for the Server.

```powershell
# Apply Server deployment (this includes Redis)
# We're applying the full file but only Redis will start first
kubectl apply -f k8s/server/deployment.yaml

# Wait for Redis to be ready (fast startup ~10-20s)
kubectl wait --for=condition=ready pod -l component=redis --timeout=120s

# Verify Redis is running
kubectl get deployment neuroclima-redis
kubectl get pod -l component=redis

# Test Redis connection
kubectl exec -it deployment/neuroclima-redis -- redis-cli -a '$REDIS_PASSWORD' ping
```

**Expected output:**
```
deployment.apps/neuroclima-redis created
pod/neuroclima-redis-xxx condition met
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
neuroclima-redis   1/1     1            1           30s
PONG
```

---

## Step 5: Deploy Server

Server depends on both Redis and MongoDB.

```powershell
# Redis and MongoDB should already be running from previous steps
# The Server deployment is already applied from Step 4, just wait for it

# Wait for Server to be ready (startup ~30-60s)
kubectl wait --for=condition=ready pod -l component=server --timeout=300s

# Verify Server is running
kubectl get deployment neuroclima-server
kubectl get pod -l component=server

# Check Server logs for MongoDB and Redis connections
kubectl logs -l component=server --tail=100

# Look for successful connections:
# - "Connected to Redis"
# - "Connected to MongoDB" or similar messages
```

**Expected output:**
```
NAME                 READY   UP-TO-DATE   AVAILABLE   AGE
neuroclima-server    1/1     1            1           1m
```

---

## Step 6: Deploy Client

Client is the web UI that depends on Server.

```powershell
# Apply Client deployment
kubectl apply -f k8s/client/deployment.yaml

# Wait for Client to be ready (fast startup ~20-30s)
kubectl wait --for=condition=ready pod -l component=client --timeout=180s

# Verify Client is running
kubectl get deployment neuroclima-client
kubectl get pod -l component=client

# Check Client logs
kubectl logs -l component=client --tail=50
```

**Expected output:**
```
deployment.apps/neuroclima-client created
pod/neuroclima-client-xxx condition met
NAME                READY   UP-TO-DATE   AVAILABLE   AGE
neuroclima-client   1/1     1            1           30s
```

---

## Step 7: Verify All Services

```powershell
# Check all pods are running
kubectl get pods -o wide

# Expected output (all Running):
# NAME                                       READY   STATUS    RESTARTS   AGE
# neuroclima-mongodb-0                       1/1     Running   0          5m
# neuroclima-unstructured-xxx                1/1     Running   0          4m
# neuroclima-processor-xxx                   1/1     Running   0          3m
# neuroclima-redis-xxx                       1/1     Running   0          2m
# neuroclima-server-xxx                      1/1     Running   0          2m
# neuroclima-client-xxx                      1/1     Running   0          1m

# Check all services
kubectl get svc

# Check deployments
kubectl get deployment

# Check StatefulSets
kubectl get statefulset

# Check PVCs (data should still be there!)
kubectl get pvc
```

---

## Step 8: Test the Application

```powershell
# Get the LoadBalancer external IP (for client)
kubectl get svc neuroclima-client-lb

# Access the application at:
# https://bot.neuroclima.eu/

# Or use port-forward for testing
kubectl port-forward svc/neuroclima-client 8080:80

# Then access: http://localhost:8080
```

---

## Troubleshooting

### MongoDB Not Starting
```powershell
# Check MongoDB logs
kubectl logs -l component=mongodb --tail=100

# Check MongoDB pod events
kubectl describe pod -l component=mongodb

# Check PVC is bound
kubectl get pvc | Select-String "mongodb"
```

### Processor Failing to Start
```powershell
# Check Processor logs (look for model loading errors)
kubectl logs -l component=processor --tail=200

# Check init container logs (GraphRAG data initialization)
kubectl logs -l component=processor -c init-graphrag-data

# Check PVCs are bound
kubectl get pvc | Select-String "processor\|graphrag\|lancedb"

# Verify GraphRAG data exists
kubectl exec -it deployment/neuroclima-processor -- ls -lh /app/graphrag/output/
```

### Server Can't Connect to MongoDB
```powershell
# Check Server logs for connection errors
kubectl logs -l component=server --tail=100 | Select-String "MongoDB\|mongo"

# Test MongoDB connectivity from Server pod
kubectl exec -it deployment/neuroclima-server -- nc -zv neuroclima-mongodb-0.neuroclima-mongodb.uoulu.svc.cluster.local 27017

# Check MongoDB service
kubectl get svc neuroclima-mongodb
kubectl describe svc neuroclima-mongodb
```

### Server Can't Connect to Redis
```powershell
# Check Server logs for Redis errors
kubectl logs -l component=server --tail=100 | Select-String "Redis\|redis"

# Test Redis connectivity from Server pod
kubectl exec -it deployment/neuroclima-server -- nc -zv neuroclima-redis 6379

# Check Redis service
kubectl get svc neuroclima-redis
```

### Pods Not Scheduling (Pending)
```powershell
# Check pod status
kubectl get pods

# If pods are Pending, check events
kubectl describe pod <pod-name>

# Common issues:
# - Insufficient memory/CPU on nodes
# - Taints on nodes (need tolerations)
# - Node affinity not matching any nodes

# Check node resources
kubectl top nodes

# Check node taints
kubectl describe nodes | Select-String "Taints" -Context 0,1
```

---

## Clean Up (if needed)

If you need to start completely fresh and delete EVERYTHING including data:

```powershell
# WARNING: This will DELETE ALL DATA! Use with caution!

# Delete all deployments and StatefulSets
kubectl delete deployment --all -n uoulu
kubectl delete statefulset --all -n uoulu

# Delete all PVCs (THIS DELETES YOUR DATA!)
kubectl delete pvc --all -n uoulu

# Delete all services
kubectl delete svc --all -n uoulu

# Delete all ConfigMaps
kubectl delete configmap --all -n uoulu

# Delete all Secrets
kubectl delete secret --all -n uoulu

# Verify everything is deleted
kubectl get all -n uoulu
kubectl get pvc -n uoulu
```

---

## Summary

**Deployment order matters!**

1. ✅ MongoDB first (Server depends on it)
2. ✅ Processor second (independent, slow startup)
3. ✅ Redis third (Server depends on it)
4. ✅ Server fourth (depends on Redis + MongoDB)
5. ✅ Client last (depends on Server)

**Total deployment time: ~5-7 minutes**

- MongoDB: 2-3 minutes
- Processor: 2-3 minutes (model loading)
- Redis: 10-20 seconds
- Server: 30-60 seconds
- Client: 20-30 seconds

**Your data is safe!**
- Deleting deployments does NOT delete PVCs
- GraphRAG, LanceDB, and MongoDB data persist
- Only Redis data is lost (by design - emptyDir)
