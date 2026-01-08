# NeuroClima Monitoring Setup

This folder contains configurations for monitoring the NeuroClima backend with Prometheus and Grafana.

## 📁 Folder Structure

```
monitoring/
├── README.md                          # This file
├── LOCAL_SETUP_GUIDE.md              # Complete guide for local development
├── prometheus.yml                     # Prometheus configuration for local setup
├── grafana/
│   ├── dashboards/
│   │   └── neuroclima-dashboard.json # Pre-built Grafana dashboard
│   └── provisioning/
│       ├── dashboards/
│       │   └── default.yml           # Dashboard provisioning config
│       └── datasources/
│           ├── prometheus.yml        # For Docker (uses hostname 'prometheus')
│           └── prometheus-local.yml  # For local dev (uses localhost)
```

## 🚀 Quick Start

### For Local Development (No Docker)

**Follow the complete guide:** [LOCAL_SETUP_GUIDE.md](./LOCAL_SETUP_GUIDE.md)

**Quick Steps:**
1. Start your Python backend with metrics enabled
2. Download & run Prometheus with `prometheus.yml`
3. Download & run Grafana
4. Import the dashboard from `grafana/dashboards/neuroclima-dashboard.json`

### For Docker (Production)

Coming soon - Docker Compose configuration will be added in the future.

## 📊 Available Dashboards

### NeuroClima Dashboard
- **Location:** `grafana/dashboards/neuroclima-dashboard.json`
- **Metrics:**
  - Request rate (requests/second)
  - Request duration (response time)
  - Active requests
  - Status code distribution
  - LLM generation time
  - Document retrieval time
  - Active sessions
  - Cache hit rate

## 🔧 Configuration Files

### prometheus.yml
Configures Prometheus to scrape metrics from:
- **Python Backend:** `localhost:8001/metrics`
- **Prometheus itself:** `localhost:9090/metrics`

**Key settings:**
- Scrape interval: 15 seconds
- Metrics retention: 15 days (default)

### Grafana Provisioning

**Data Sources:**
- `prometheus.yml` - For Docker (hostname-based)
- `prometheus-local.yml` - For local development (localhost)

**Dashboards:**
- Auto-loads from `grafana/dashboards/` directory
- Dashboards are editable and updateable from UI

## 📈 Metrics Endpoints

Your NeuroClima backend exposes metrics at:

```
http://localhost:8001/metrics
```

Example metrics:
```prometheus
# HELP neuroclima_requests_total Total HTTP requests
# TYPE neuroclima_requests_total counter
neuroclima_requests_total{endpoint="/api/v1/chat",method="POST",status_code="200"} 42.0

# HELP neuroclima_request_duration_seconds HTTP request duration in seconds
# TYPE neuroclima_request_duration_seconds histogram
neuroclima_request_duration_seconds_bucket{endpoint="/api/v1/chat",method="POST",le="0.1"} 10.0
```

## 🛠️ Troubleshooting

### Issue: "No data" in Grafana

**Check:**
1. Is Python backend running? → `curl http://localhost:8000/health`
2. Are metrics exposed? → `curl http://localhost:8001/metrics`
3. Is Prometheus running? → Visit `http://localhost:9090`
4. Is Prometheus scraping? → Check `http://localhost:9090/targets`

### Issue: Prometheus target is "DOWN"

**Solutions:**
1. Verify backend metrics server is running
2. Check `.env` has `ENABLE_METRICS=true`
3. Verify `METRICS_PORT=8001` matches prometheus.yml
4. Test metrics endpoint: `curl http://localhost:8001/metrics`

### Issue: Grafana can't connect to Prometheus

**Solutions:**
1. Verify Prometheus URL in Grafana datasource
2. For local: Use `http://localhost:9090`
3. For Docker: Use `http://prometheus:9090`
4. Check Prometheus is running: `curl http://localhost:9090/-/healthy`

## 📚 Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## 🔄 Next Steps

1. **Local Testing:** Follow [LOCAL_SETUP_GUIDE.md](./LOCAL_SETUP_GUIDE.md)
2. **Customize Dashboard:** Modify panels to track your specific needs
3. **Add Alerts:** Configure alerting for critical metrics
4. **Docker Setup:** Create docker-compose.yml for production deployment

## 💡 Tips

- **Time Range:** In Grafana, set time range to "Last 5 minutes" for testing
- **Refresh Rate:** Set dashboard auto-refresh to 5s or 10s for real-time monitoring
- **Generate Traffic:** Use `curl` or your frontend to create metrics
- **Explore Metrics:** Use Prometheus web UI to discover available metrics

## 🤝 Contributing

To add new metrics to the dashboard:
1. Add metric collection in `Server/app/core/middleware.py`
2. Test locally at `/metrics` endpoint
3. Add panel to `neuroclima-dashboard.json`
4. Update this README with new metrics
