# NeuroClima Kubernetes Deployment Guide

This guide explains how to deploy the NeuroClima application to a Kubernetes cluster.

## Prerequisites

### Required Tools
- `kubectl` - Kubernetes command-line tool
- `docker` - For building images
- Access to a Docker registry (Docker Hub, GitHub Container Registry, etc.)
- `kubeconfig.yaml` file from your cluster administrator

### Required Services
Your Kubernetes cluster should have access to:
- **MinIO** - Object storage
- **Milvus** - Vector database
- **Ollama** - LLM service

## Quick Start

### 1. Set up kubectl with kubeconfig

```bash
# Export kubeconfig path
export KUBECONFIG=/path/to/kubeconfig.yaml

# Or use the --kubeconfig flag with every command
kubectl --kubeconfig kubeconfig.yaml get pods

# Verify access to your namespace
kubectl get pods -n uoulu
```

### 2. Build and Push Docker Images

You need to build and push your Docker images to a container registry:

```bash
# Set your registry (e.g., docker.io/yourusername, ghcr.io/yourusername)
export REGISTRY="docker.io/yourusername"

# Build and push Processor image
cd Processor
docker build -t $REGISTRY/neuroclima-processor:latest .
docker push $REGISTRY/neuroclima-processor:latest

# Build and push Server image
cd ../Server
docker build -t $REGISTRY/neuroclima-server:latest .
docker push $REGISTRY/neuroclima-server:latest

# Build and push Client image
cd ../Client
docker build -t $REGISTRY/neuroclima-client:latest .
docker push $REGISTRY/neuroclima-client:latest

cd ..
```

### 3. Update Image References

Update the image references in the deployment files:

```bash
# Update processor deployment
sed -i "s|YOUR_REGISTRY|$REGISTRY|g" k8s/processor/deployment.yaml

# Update server deployment
sed -i "s|YOUR_REGISTRY|$REGISTRY|g" k8s/server/deployment.yaml

# Update client deployment
sed -i "s|YOUR_REGISTRY|$REGISTRY|g" k8s/client/deployment.yaml
```

### 4. Configure External Services

Edit `k8s/base/configmap.yaml` to point to your external services:

```yaml
data:
  OLLAMA_API_URL: "http://your-ollama-service:11434"
  MINIO_ENDPOINT: "your-minio-endpoint:9000"
  MILVUS_HOST: "your-milvus-host"
  MILVUS_PORT: "19530"
```

### 5. Create Secrets

```bash
# Copy the template
cp k8s/base/secrets.yaml.template k8s/base/secrets.yaml

# Edit secrets.yaml with your actual credentials
nano k8s/base/secrets.yaml

# Apply secrets
kubectl apply -f k8s/base/secrets.yaml
```

**Important**: Add `k8s/base/secrets.yaml` to `.gitignore`!

### 6. Deploy the Application

Deploy in order: Base → Processor → Server → Client

```bash
# Apply base configuration
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/secrets.yaml

# Deploy Processor
kubectl apply -f k8s/processor/pvc.yaml
kubectl apply -f k8s/processor/deployment.yaml
kubectl apply -f k8s/processor/service.yaml

# Deploy Server
kubectl apply -f k8s/server/pvc.yaml
kubectl apply -f k8s/server/deployment.yaml
kubectl apply -f k8s/server/service.yaml

# Deploy Client
kubectl apply -f k8s/client/deployment.yaml
kubectl apply -f k8s/client/service.yaml

# Deploy Ingress (optional, if you want external access)
# Update YOUR_DOMAIN in ingress.yaml first
kubectl apply -f k8s/base/ingress.yaml
```

### 7. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n uoulu

# Expected output:
# NAME                                     READY   STATUS    RESTARTS   AGE
# neuroclima-unstructured-xxx              1/1     Running   0          5m
# neuroclima-processor-xxx                 1/1     Running   0          5m
# neuroclima-redis-xxx                     1/1     Running   0          3m
# neuroclima-server-xxx                    1/1     Running   0          3m
# neuroclima-client-xxx                    1/1     Running   0          1m

# Check services
kubectl get svc -n uoulu

# Check persistent volume claims
kubectl get pvc -n uoulu
```

### 8. View Logs

```bash
# Processor logs
kubectl logs -f deployment/neuroclima-processor -n uoulu

# Server logs
kubectl logs -f deployment/neuroclima-server -n uoulu

# Client logs
kubectl logs -f deployment/neuroclima-client -n uoulu

# All logs
kubectl logs -f -l app=neuroclima -n uoulu
```

## Accessing the Application

### Option 1: Port Forwarding (Development)

```bash
# Forward client port
kubectl port-forward svc/neuroclima-client 8080:80 -n uoulu

# Forward server port
kubectl port-forward svc/neuroclima-server 8000:8000 -n uoulu

# Forward processor port
kubectl port-forward svc/neuroclima-processor 5000:5000 -n uoulu

# Access at:
# - Client: http://localhost:8080
# - Server: http://localhost:8000
# - Processor: http://localhost:5000
```

### Option 2: Ingress (Production)

If you deployed the ingress:
- Access at: https://YOUR_DOMAIN.com
- Server API: https://YOUR_DOMAIN.com/api
- Processor API: https://YOUR_DOMAIN.com/processor

## Common Operations

### Update an Application

```bash
# Build and push new image
docker build -t $REGISTRY/neuroclima-processor:v2 ./Processor
docker push $REGISTRY/neuroclima-processor:v2

# Update deployment
kubectl set image deployment/neuroclima-processor \
  processor=$REGISTRY/neuroclima-processor:v2 -n uoulu

# Or edit and apply
kubectl apply -f k8s/processor/deployment.yaml
```

### Scale Deployments

```bash
# Scale processor to 2 replicas
kubectl scale deployment neuroclima-processor --replicas=2 -n uoulu

# Scale server to 3 replicas
kubectl scale deployment neuroclima-server --replicas=3 -n uoulu
```

### Restart a Deployment

```bash
kubectl rollout restart deployment/neuroclima-processor -n uoulu
kubectl rollout restart deployment/neuroclima-server -n uoulu
```

### Check Deployment Status

```bash
kubectl rollout status deployment/neuroclima-processor -n uoulu
kubectl rollout history deployment/neuroclima-processor -n uoulu
```

### Rollback a Deployment

```bash
kubectl rollout undo deployment/neuroclima-processor -n uoulu
```

### Update ConfigMap

```bash
# Edit configmap
kubectl edit configmap neuroclima-config -n uoulu

# Or apply changes
kubectl apply -f k8s/base/configmap.yaml

# Restart pods to pick up changes
kubectl rollout restart deployment/neuroclima-processor -n uoulu
```

### Update Secrets

```bash
# Edit secrets file
nano k8s/base/secrets.yaml

# Apply
kubectl apply -f k8s/base/secrets.yaml

# Restart pods
kubectl rollout restart deployment/neuroclima-processor -n uoulu
kubectl rollout restart deployment/neuroclima-server -n uoulu
```

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod to see events
kubectl describe pod neuroclima-processor-xxx -n uoulu

# Check events
kubectl get events -n uoulu --sort-by='.lastTimestamp'

# Check logs
kubectl logs neuroclima-processor-xxx -n uoulu
```

### Image Pull Errors

```bash
# Check if image exists
docker pull $REGISTRY/neuroclima-processor:latest

# Create image pull secret (if using private registry)
kubectl create secret docker-registry regcred \
  --docker-server=$REGISTRY \
  --docker-username=$USERNAME \
  --docker-password=$PASSWORD \
  -n uoulu

# Add to deployment spec:
# spec:
#   template:
#     spec:
#       imagePullSecrets:
#       - name: regcred
```

### PVC Not Binding

```bash
# Check PVC status
kubectl get pvc -n uoulu

# Describe PVC
kubectl describe pvc processor-data-pvc -n uoulu

# Check if storage class exists
kubectl get storageclass
```

### Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints neuroclima-processor -n uoulu

# Check if pods are running
kubectl get pods -l component=processor -n uoulu

# Test service from another pod
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n uoulu \
  -- curl http://neuroclima-processor:5000/health
```

### External Services Not Reachable

```bash
# Check if external services are accessible from a pod
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n uoulu \
  -- curl http://YOUR_OLLAMA_SERVICE:11434/

# Check configmap values
kubectl get configmap neuroclima-config -n uoulu -o yaml
```

## Resource Management

### Check Resource Usage

```bash
# Check pod resource usage
kubectl top pods -n uoulu

# Check node resource usage
kubectl top nodes
```

### Adjust Resource Limits

Edit deployment files and update:
```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

Then apply:
```bash
kubectl apply -f k8s/processor/deployment.yaml
```

## Backup and Restore

### Backup Persistent Volumes

```bash
# Create a backup pod
kubectl run backup --image=ubuntu --restart=Never -n uoulu \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "backup",
      "image": "ubuntu",
      "command": ["sleep", "3600"],
      "volumeMounts": [{
        "name": "data",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {
        "claimName": "processor-data-pvc"
      }
    }]
  }
}'

# Copy data from pod
kubectl cp uoulu/backup:/data ./backup-data

# Clean up
kubectl delete pod backup -n uoulu
```

## Complete Cleanup

To remove everything:

```bash
# Delete all resources
kubectl delete -f k8s/client/
kubectl delete -f k8s/server/
kubectl delete -f k8s/processor/
kubectl delete -f k8s/base/

# Delete PVCs (this will delete data!)
kubectl delete pvc --all -n uoulu
```

## Environment-Specific Deployments

### Development
- Use `latest` tags
- Smaller resource limits
- Port forwarding for access

### Staging
- Use version tags (e.g., `v1.2.3`)
- Medium resource limits
- Ingress with staging domain

### Production
- Use specific version tags
- Full resource limits
- Ingress with production domain
- Enable monitoring and logging
- Set up backups

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2

    - name: Build and push images
      run: |
        docker build -t $REGISTRY/neuroclima-processor:$GITHUB_SHA ./Processor
        docker push $REGISTRY/neuroclima-processor:$GITHUB_SHA

    - name: Deploy to k8s
      run: |
        kubectl set image deployment/neuroclima-processor \
          processor=$REGISTRY/neuroclima-processor:$GITHUB_SHA \
          -n uoulu
```

## Support

For issues:
1. Check pod logs: `kubectl logs -f pod-name -n uoulu`
2. Check events: `kubectl get events -n uoulu`
3. Verify configuration: `kubectl get configmap,secret -n uoulu`
4. Test connectivity: Use debug pod to test connections
