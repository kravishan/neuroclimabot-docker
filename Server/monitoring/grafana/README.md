# NeuroClima Bot - Grafana & Prometheus Monitoring

This directory contains all the configuration files needed to set up monitoring for your NeuroClima Bot using Prometheus and Grafana.

## 📁 Directory Structure

```
Server/monitoring/grafana/
├── README.md                          # This file
├── GRAFANA_SETUP.md                   # Detailed setup guide
├── prometheus.yml                     # Prometheus configuration
├── test-metrics.sh                    # Quick test script
├── dashboards/
│   └── neuroclima-dashboard.json     # Pre-built Grafana dashboard
└── datasources/
    └── prometheus-datasource.yml     # Grafana datasource config
```

## 🚀 Quick Start

### 1. Start Prometheus
```bash
# Run from project root directory
docker run -d \
  --name prometheus \
  --network host \
  -v $(pwd)/Server/monitoring/grafana/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest
```

### 2. Test Your Setup
```bash
./Server/monitoring/grafana/test-metrics.sh
```

### 3. Import Dashboard to Grafana
1. Open Grafana (http://localhost:3000)
2. Add Prometheus data source (http://localhost:9090)
3. Import dashboard: `./Server/monitoring/grafana/dashboards/neuroclima-dashboard.json`

## 📊 Available Metrics

Your NeuroClima Bot exposes these metrics:

- **HTTP Metrics**: Request count, duration, active requests
- **Performance Metrics**: LLM response time, retrieval time
- **Application Metrics**: Active sessions, cache hit rate

Access metrics at: **http://localhost:8000/metrics**

## 📖 Documentation

See [GRAFANA_SETUP.md](./GRAFANA_SETUP.md) for detailed instructions including:
- Complete setup guide
- Troubleshooting tips
- Custom queries
- Best practices

## 🧪 Testing

Run the test script to verify everything is working:
```bash
./Server/monitoring/grafana/test-metrics.sh
```

## 🔗 Access Points

- **Metrics Endpoint**: http://localhost:8000/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## ⚙️ Configuration

Metrics are controlled by these environment variables in `.env`:

```env
ENABLE_METRICS=True
METRICS_PORT=8001
TRACK_RESPONSE_TIMES=True
```

---

**Need help?** Check [GRAFANA_SETUP.md](./GRAFANA_SETUP.md) for detailed troubleshooting.
