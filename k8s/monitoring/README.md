# NeuroClima Monitoring - Kubernetes Deployment

This directory contains Kubernetes manifests for deploying Prometheus and Grafana monitoring stack.

## 📦 Components

### Prometheus
- **Purpose**: Metrics collection and storage
- **Scrapes metrics from**:
  - NeuroClima backend: `neuroclima-server:8001/metrics`
  - GPU LLM server: `86.50.23.167:9100/metrics` (Ollama VM)
  - Prometheus itself: `localhost:9090/metrics`
- **Storage**: 10Gi PVC
- **Retention**: 15 days

### Grafana
- **Purpose**: Metrics visualization and dashboards
- **Default login**: `admin` / `${GRAFANA_PASSWORD}` (from secrets)
- **Storage**: 5Gi PVC
- **Datasource**: Auto-provisioned Prometheus connection

## 🚀 Deployment

### Prerequisites

1. **Add Grafana password to secrets**:
   ```bash
   # Add to your secrets file or kubectl command
   GRAFANA_PASSWORD=<your-secure-password>
   ```

2. **Ensure namespace exists**:
   ```bash
   kubectl create namespace uoulu
   ```

### Quick Deploy

```bash
# From the k8s/monitoring directory
kubectl apply -f prometheus-configmap.yaml
kubectl apply -f prometheus-pvc.yaml
kubectl apply -f prometheus-deployment.yaml
kubectl apply -f prometheus-service.yaml

kubectl apply -f grafana-configmap.yaml
kubectl apply -f grafana-pvc.yaml
kubectl apply -f grafana-deployment.yaml
kubectl apply -f grafana-service.yaml
```

### All-in-One Deploy

```bash
# From the k8s/ directory
kubectl apply -f monitoring/
```

### 📊 Create Dashboard ConfigMap

After deploying Grafana, you need to create a ConfigMap with the dashboard JSON:

**Option 1: Use the provided script (Linux/Mac)**
```bash
cd k8s/monitoring
chmod +x create-dashboard-configmap.sh
./create-dashboard-configmap.sh
```

**Option 2: Use PowerShell script (Windows)**
```powershell
cd k8s\monitoring
.\create-dashboard-configmap.ps1
```

**Option 3: Manual kubectl command**
```bash
# From the repository root
kubectl create configmap grafana-dashboards \
  --from-file=neuroclima-dashboard.json=Server/monitoring/grafana/dashboards/neuroclima-dashboard.json \
  --namespace=uoulu \
  --dry-run=client -o yaml | kubectl apply -f -
```

Then restart Grafana to load the dashboard:
```bash
kubectl rollout restart deployment/neuroclima-grafana -n uoulu
```

## 📊 Access Services

### Port Forwarding (for testing)

**Prometheus**:
```bash
kubectl port-forward -n uoulu svc/neuroclima-prometheus 9090:9090
```
Then access: http://localhost:9090

**Grafana**:
```bash
kubectl port-forward -n uoulu svc/neuroclima-grafana 3000:3000
```
Then access: http://localhost:3000

### Production Access

Add Ingress rules or LoadBalancer services for production access.

## 🔧 Configuration

### Update Scrape Targets

Edit `prometheus-configmap.yaml` to add/modify scrape targets:

```yaml
- job_name: 'my-service'
  static_configs:
    - targets: ['my-service:port']
```

Apply changes:
```bash
kubectl apply -f prometheus-configmap.yaml
kubectl rollout restart deployment/neuroclima-prometheus -n uoulu
```

## 📝 Verify Deployment

### Check Pods

```bash
kubectl get pods -n uoulu -l component=prometheus
kubectl get pods -n uoulu -l component=grafana
```

### Check Logs

```bash
kubectl logs -n uoulu -l component=prometheus --tail=50
kubectl logs -n uoulu -l component=grafana --tail=50
```

### Check Services

```bash
kubectl get svc -n uoulu | grep prometheus
kubectl get svc -n uoulu | grep grafana
```

### Verify Prometheus Targets

1. Port-forward Prometheus: `kubectl port-forward -n uoulu svc/neuroclima-prometheus 9090:9090`
2. Visit: http://localhost:9090/targets
3. Check all targets are "UP"

## 🐛 Troubleshooting

### Prometheus Not Scraping Backend

**Check**:
1. Is the server pod running? `kubectl get pods -n uoulu -l component=server`
2. Is port 8001 exposed? Check `k8s/server/deployment.yaml`
3. Can Prometheus reach the server? `kubectl exec -n uoulu deployment/neuroclima-prometheus -- wget -O- http://neuroclima-server:8001/metrics`

### Grafana Can't Connect to Prometheus

**Check**:
1. Is Prometheus service running? `kubectl get svc -n uoulu neuroclima-prometheus`
2. Check Grafana logs: `kubectl logs -n uoulu -l component=grafana`
3. Verify datasource config: `kubectl get configmap -n uoulu grafana-datasources -o yaml`

### Grafana Password Not Working

**Add GRAFANA_PASSWORD to secrets**:
```bash
kubectl create secret generic neuroclima-secrets \
  --from-literal=GRAFANA_PASSWORD=your-password \
  --namespace=uoulu \
  --dry-run=client -o yaml | kubectl apply -f -
```

Or patch existing secret:
```bash
kubectl patch secret neuroclima-secrets -n uoulu \
  -p '{"data":{"GRAFANA_PASSWORD":"'$(echo -n "your-password" | base64)'"}}'
```

Then restart Grafana:
```bash
kubectl rollout restart deployment/neuroclima-grafana -n uoulu
```

## 🔐 Security Notes

- Grafana admin password is stored in Kubernetes secrets
- Prometheus has no authentication (use network policies to restrict access)
- For production, configure:
  - Grafana HTTPS/TLS
  - OAuth/LDAP authentication
  - Network policies to restrict pod-to-pod communication

## 📈 Resource Usage

**Prometheus**:
- Requests: 1Gi RAM, 500m CPU
- Limits: 2Gi RAM, 1000m CPU
- Storage: 10Gi

**Grafana**:
- Requests: 512Mi RAM, 250m CPU
- Limits: 1Gi RAM, 500m CPU
- Storage: 5Gi

Adjust in deployment files as needed for your cluster.

## 🔄 Updates

### Update Prometheus

```bash
kubectl set image deployment/neuroclima-prometheus \
  prometheus=prom/prometheus:v2.XX.X -n uoulu
```

### Update Grafana

```bash
kubectl set image deployment/neuroclima-grafana \
  grafana=grafana/grafana:X.X.X -n uoulu
```

## 📚 Additional Resources

- [Prometheus on Kubernetes](https://prometheus.io/docs/prometheus/latest/installation/)
- [Grafana on Kubernetes](https://grafana.com/docs/grafana/latest/setup-grafana/installation/kubernetes/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
