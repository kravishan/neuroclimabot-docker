#!/bin/bash
# Create Grafana dashboard ConfigMap from the JSON file

# This script creates a Kubernetes ConfigMap containing the NeuroClima Grafana dashboard

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_FILE="$SCRIPT_DIR/../../Server/monitoring/grafana/dashboards/neuroclima-dashboard.json"

if [ ! -f "$DASHBOARD_FILE" ]; then
    echo "Error: Dashboard file not found at $DASHBOARD_FILE"
    exit 1
fi

echo "Creating ConfigMap 'grafana-dashboards' from dashboard JSON file..."

kubectl create configmap grafana-dashboards \
    --from-file=neuroclima-dashboard.json="$DASHBOARD_FILE" \
    --namespace=uoulu \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Dashboard ConfigMap created successfully!"
echo ""
echo "Now restart Grafana to load the dashboard:"
echo "kubectl rollout restart deployment/neuroclima-grafana -n uoulu"
