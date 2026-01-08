# NeuroClima Monitoring with Prometheus & Grafana

Complete guide to set up and use Prometheus metrics and Grafana dashboards for monitoring your NeuroClima RAG system.

## 🚀 Quick Start

### 1. Start the Monitoring Stack

```bash
# Navigate to the Server directory
cd /home/user/neuroclimabot-docker/Server

# Start all services (server + monitoring)
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### 2. Access the Services

- **NeuroClima API**: http://localhost:8000
- **NeuroClima Metrics**: http://localhost:8001/metrics
- **Prometheus UI**: http://localhost:9090
- **Grafana Dashboard**: http://localhost:3000

### 3. Login to Grafana

- **URL**: http://localhost:3000
- **Username**: `admin`
- **Password**: `admin` (change this in production!)

After login, you'll see the **NeuroClima RAG System - Performance Dashboard** automatically loaded!

---

## 📊 Dashboard Panels Explained

### Panel 1: Request Rate (req/s)
- Shows requests per second to your API
- Broken down by HTTP method, endpoint, and status code
- **Use it to**: Monitor traffic patterns and identify peak usage times

### Panel 2: Active Sessions (Gauge)
- Current number of active chat sessions
- **Thresholds**:
  - Green: 0-50 sessions
  - Yellow: 50-100 sessions
  - Red: 100+ sessions
- **Use it to**: Monitor concurrent users

### Panel 3: Active Requests (Gauge)
- Number of requests currently being processed
- **Thresholds**:
  - Green: 0-5 requests
  - Yellow: 5-10 requests
  - Red: 10+ requests
- **Use it to**: Detect bottlenecks and overload

### Panel 4: Request Latency (Percentiles)
- Shows p50 (median), p95, and p99 latency
- **Good values**:
  - p50: < 1s
  - p95: < 3s
  - p99: < 5s
- **Use it to**: Identify slow requests and performance issues

### Panel 5: LLM & Retrieval Latency
- Separate tracking for LLM generation and vector retrieval
- Shows p50 and p95 for both operations
- **Use it to**: Identify which component is causing delays

### Panel 6: Cache Hit Rate (Gauge)
- Percentage of requests served from cache
- **Thresholds**:
  - Red: 0-50% (poor)
  - Yellow: 50-80% (fair)
  - Green: 80-100% (excellent)
- **Use it to**: Optimize caching strategy

### Panel 7: Error Rate by Status Code
- Shows 2xx (success), 4xx (client errors), 5xx (server errors)
- **Use it to**: Detect and troubleshoot errors

### Panel 8: Total Requests by Endpoint
- Bar chart showing request distribution across endpoints
- **Use it to**: Identify most-used features

### Panel 9: Python Garbage Collection Rate
- Shows Python GC activity by generation
- **Use it to**: Detect memory issues and optimization opportunities

### Panel 10: Total Counters
- Summary of total requests, LLM calls, and retrieval calls
- **Use it to**: Get overall usage statistics

---

## 🔍 Useful Prometheus Queries

Access Prometheus at http://localhost:9090 and try these queries:

### Request Metrics

```promql
# Total requests per second
rate(neuroclima_requests_total[5m])

# Requests by endpoint
sum by (endpoint) (rate(neuroclima_requests_total[5m]))

# Error rate (5xx errors)
rate(neuroclima_requests_total{status_code=~"5.."}[5m])

# Success rate percentage
sum(rate(neuroclima_requests_total{status_code=~"2.."}[5m])) /
sum(rate(neuroclima_requests_total[5m])) * 100
```

### Latency Metrics

```promql
# Average request duration
rate(neuroclima_request_duration_seconds_sum[5m]) /
rate(neuroclima_request_duration_seconds_count[5m])

# 95th percentile request latency
histogram_quantile(0.95, rate(neuroclima_request_duration_seconds_bucket[5m]))

# 99th percentile LLM latency
histogram_quantile(0.99, rate(neuroclima_llm_duration_seconds_bucket[5m]))

# Average retrieval time
rate(neuroclima_retrieval_duration_seconds_sum[5m]) /
rate(neuroclima_retrieval_duration_seconds_count[5m])
```

### Application Metrics

```promql
# Current active sessions
neuroclima_active_sessions

# Current active requests
neuroclima_active_requests

# Cache hit rate
neuroclima_cache_hit_rate

# Requests per minute
sum(rate(neuroclima_requests_total[1m])) * 60
```

---

## 🧪 Generate Test Data

To populate the dashboard with real data, make some test requests:

```bash
# Health check
curl http://localhost:8000/health

# Make a chat query
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is climate change?",
    "use_milvus": true,
    "use_graph": false
  }'

# Load test (requires 'ab' - Apache Bench)
ab -n 100 -c 10 http://localhost:8000/health

# Or use this simple bash loop
for i in {1..50}; do
  curl -s http://localhost:8000/health > /dev/null
  echo "Request $i sent"
  sleep 0.1
done
```

---

## 🎨 Customize Your Dashboard

### Add New Panels

1. Click **"+"** icon → **Add panel**
2. Select **Prometheus** as data source
3. Enter your PromQL query
4. Configure visualization settings
5. Click **Save**

### Modify Existing Panels

1. Hover over panel → Click **title** → **Edit**
2. Modify query, visualization, or thresholds
3. Click **Apply** → **Save dashboard**

### Create Alerts

1. Edit a panel
2. Go to **Alert** tab
3. Set conditions (e.g., "alert if p95 latency > 5s")
4. Configure notification channels

---

## 🛠️ Advanced Configuration

### Change Grafana Admin Password

Edit `docker-compose.monitoring.yml`:

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=your-secure-password
```

Then restart:

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d grafana
```

### Adjust Prometheus Retention

Edit `docker-compose.monitoring.yml`:

```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=90d'  # Keep 90 days instead of 30
```

### Change Scrape Interval

Edit `prometheus.yml`:

```yaml
global:
  scrape_interval: 5s  # Scrape every 5 seconds (more frequent)
```

---

## 📈 Monitoring Best Practices

### 1. Set Up Alerts

Create alerts for:
- Error rate > 5%
- p95 latency > 5 seconds
- Active requests > 20
- Cache hit rate < 50%

### 2. Monitor Resource Usage

Add these to your dashboard:

```promql
# Memory usage (if process metrics are exported)
process_resident_memory_bytes

# CPU usage
rate(process_cpu_seconds_total[5m])
```

### 3. Track Business Metrics

Use the metrics to answer:
- What's our busiest time of day?
- Which endpoints are most popular?
- Are we meeting our SLA (99% of requests < 3s)?
- Is caching effective?

### 4. Performance Optimization

Look for:
- **High LLM latency**: Consider using a faster model or caching
- **High retrieval latency**: Optimize Milvus queries or increase resources
- **Low cache hit rate**: Adjust cache TTL or strategy
- **Memory growth**: Check for memory leaks using GC metrics

---

## 🐛 Troubleshooting

### Grafana shows "No Data"

1. Check Prometheus is scraping:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. Verify metrics endpoint:
   ```bash
   curl http://localhost:8001/metrics | grep neuroclima
   ```

3. Make test requests to generate data

### Prometheus not scraping

1. Check Prometheus logs:
   ```bash
   docker logs neuroclima-prometheus
   ```

2. Verify service connectivity:
   ```bash
   docker exec neuroclima-prometheus wget -O- http://server:8001/metrics
   ```

### Dashboard not loading

1. Check Grafana logs:
   ```bash
   docker logs neuroclima-grafana
   ```

2. Verify provisioning files:
   ```bash
   docker exec neuroclima-grafana ls -la /etc/grafana/provisioning/datasources/
   docker exec neuroclima-grafana ls -la /var/lib/grafana/dashboards/
   ```

---

## 🔄 Maintenance

### Backup Grafana Dashboards

```bash
# Export all dashboards
docker exec neuroclima-grafana grafana-cli admin export-dashboard

# Or manually: Dashboard settings → JSON Model → Copy
```

### Clean Up Old Data

```bash
# Remove old Prometheus data
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down
docker volume rm server_prometheus_data
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### Update Images

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml pull
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

---

## 📚 Additional Resources

- [Prometheus Querying](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [PromQL Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/)

---

## 🎯 Next Steps

1. ✅ Start the monitoring stack
2. ✅ Access Grafana and explore the dashboard
3. ✅ Generate test data
4. 📊 Set up alerts for critical metrics
5. 🎨 Customize dashboards for your needs
6. 📈 Monitor and optimize performance

Happy monitoring! 🚀
