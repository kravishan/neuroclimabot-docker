# Grafana + Prometheus Setup Guide for NeuroClima Bot

This guide will help you set up Grafana to visualize metrics from your NeuroClima Bot application.

## 📊 What Metrics Are Available?

Your NeuroClima Bot already has Prometheus metrics built-in! Here's what you can monitor:

### HTTP Metrics
- **neuroclima_requests_total** - Total number of HTTP requests (by method, endpoint, status code)
- **neuroclima_request_duration_seconds** - HTTP request duration histogram
- **neuroclima_active_requests** - Number of currently active requests

### Application Metrics
- **neuroclima_active_sessions** - Number of active user sessions
- **neuroclima_cache_hit_rate** - Cache hit rate (0.0 to 1.0)

### Performance Metrics
- **neuroclima_llm_duration_seconds** - LLM response generation time
- **neuroclima_retrieval_duration_seconds** - Document retrieval time from vector DB

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Install and Run Prometheus

#### Option A: Using Docker (Recommended)
```bash
# From the project root directory
docker run -d \
  --name prometheus \
  --network host \
  -v $(pwd)/grafana/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest
```

#### Option B: Using Local Installation
1. Download Prometheus from https://prometheus.io/download/
2. Extract and navigate to the directory
3. Copy the `prometheus.yml` from `./grafana/prometheus.yml` to Prometheus config directory
4. Run Prometheus:
```bash
./prometheus --config.file=prometheus.yml
```

Prometheus will be available at: **http://localhost:9090**

### Step 2: Configure Grafana Data Source

Since you already have Grafana installed on your PC:

1. Open Grafana in your browser (usually http://localhost:3000)
2. Login (default: admin/admin)
3. Go to **Configuration** → **Data Sources** → **Add data source**
4. Select **Prometheus**
5. Configure:
   - **Name**: NeuroClima Prometheus
   - **URL**: `http://localhost:9090`
   - **Access**: Browser (if Grafana is on same machine)
6. Click **Save & Test**

### Step 3: Import the Dashboard

1. In Grafana, go to **Dashboards** → **Import**
2. Click **Upload JSON file**
3. Select the file: `./grafana/dashboards/neuroclima-dashboard.json`
4. Select the **NeuroClima Prometheus** data source
5. Click **Import**

🎉 **Done!** Your dashboard should now display real-time metrics!

---

## 📈 Dashboard Features

The pre-configured dashboard includes:

### Overview Panels (Top Row)
- **Total Requests** - Request volume over last 5 minutes
- **Active Requests** - Currently processing requests
- **Active Sessions** - Number of active user sessions
- **Cache Hit Rate** - Cache performance gauge

### Performance Graphs
- **Request Rate** - Requests per second by HTTP method
- **HTTP Status Codes** - Status code distribution over time
- **Request Duration** - P50, P95, P99 percentiles
- **LLM Response Time** - AI model response latency
- **Document Retrieval Time** - Vector DB query performance
- **Requests by Endpoint** - Traffic breakdown by API endpoint

---

## 🔧 Configuration

### Metrics Server Configuration

Your application exposes metrics on two endpoints:

1. **Main API**: `http://localhost:8000/metrics`
2. **Dedicated Metrics Port**: `http://localhost:8001` (configurable)

To change the metrics port, update your `.env` file:
```env
ENABLE_METRICS=True
METRICS_PORT=8001
```

### Enable/Disable Metrics

In your `.env` file:
```env
# Enable Prometheus metrics
ENABLE_METRICS=True

# Track various performance metrics
TRACK_RESPONSE_TIMES=True
TRACK_GRAPHRAG_API_PERFORMANCE=True
TRACK_RELEVANCE_FILTERING=True
TRACK_BUCKET_USAGE=True
TRACK_STP_PERFORMANCE=True
```

---

## 🧪 Testing Your Setup

### 1. Verify Prometheus is Scraping
```bash
# Check if metrics endpoint is working
curl http://localhost:8000/metrics

# You should see output like:
# neuroclima_requests_total{method="GET",endpoint="/",status_code="200"} 15.0
# neuroclima_active_sessions 5.0
# etc.
```

### 2. Query Metrics in Prometheus
1. Open Prometheus UI: http://localhost:9090
2. Go to **Graph** tab
3. Try queries like:
   - `neuroclima_requests_total`
   - `rate(neuroclima_requests_total[5m])`
   - `neuroclima_active_sessions`

### 3. Generate Some Traffic
```bash
# Send test requests to generate metrics
for i in {1..10}; do
  curl http://localhost:8000/
  sleep 1
done
```

### 4. Check Grafana Dashboard
- Open Grafana dashboard
- You should see graphs updating with data
- If no data appears, check:
  - Is your NeuroClima Bot running?
  - Is Prometheus running and scraping?
  - Is the data source connected properly?

---

## 🎯 Useful Prometheus Queries

Here are some useful queries to explore your metrics:

### Request Rate
```promql
# Overall request rate (requests per second)
sum(rate(neuroclima_requests_total[5m]))

# Request rate by endpoint
sum(rate(neuroclima_requests_total[5m])) by (endpoint)

# Request rate by status code
sum(rate(neuroclima_requests_total[5m])) by (status_code)
```

### Latency Analysis
```promql
# 95th percentile request duration
histogram_quantile(0.95, sum(rate(neuroclima_request_duration_seconds_bucket[5m])) by (le))

# Average LLM response time
rate(neuroclima_llm_duration_seconds_sum[5m]) / rate(neuroclima_llm_duration_seconds_count[5m])
```

### Error Rate
```promql
# 5xx error rate
sum(rate(neuroclima_requests_total{status_code=~"5.."}[5m]))

# Error rate as percentage
sum(rate(neuroclima_requests_total{status_code=~"5.."}[5m])) / sum(rate(neuroclima_requests_total[5m])) * 100
```

### Cache Performance
```promql
# Cache hit rate percentage
neuroclima_cache_hit_rate * 100
```

---

## 🐛 Troubleshooting

### Metrics Not Appearing in Grafana

1. **Check if NeuroClima Bot is running**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify metrics endpoint**
   ```bash
   curl http://localhost:8000/metrics | head -20
   ```

3. **Check Prometheus targets**
   - Go to http://localhost:9090/targets
   - All targets should show as "UP"
   - If "DOWN", check the endpoint URLs

4. **Check Prometheus is scraping**
   - Go to http://localhost:9090/graph
   - Try query: `up{job="neuroclima-api"}`
   - Should return `1` if scraping successfully

5. **Verify Grafana data source**
   - Go to Grafana → Configuration → Data Sources
   - Click on your Prometheus data source
   - Click "Save & Test"
   - Should show "Data source is working"

### No Data in Dashboard

- **Wait a few minutes** - Prometheus needs time to collect data
- **Generate traffic** - Send some requests to your API
- **Check time range** - Ensure dashboard is showing "Last 15 minutes"
- **Refresh dashboard** - Click refresh icon in top right

### High Memory Usage

If Prometheus uses too much memory:
1. Reduce retention time in `prometheus.yml`:
   ```yaml
   global:
     scrape_interval: 30s  # Increase from 15s
   ```
2. Restart Prometheus

---

## 📦 Docker Compose Setup (Future Enhancement)

For production, you can add Prometheus and Grafana to your `docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: neuroclima-prometheus
    volumes:
      - ./grafana/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - neuroclima-network

  grafana:
    image: grafana/grafana:latest
    container_name: neuroclima-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    networks:
      - neuroclima-network
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
```

---

## 🔍 Monitoring Best Practices

1. **Set up alerts** - Configure Prometheus alerts for critical metrics
2. **Regular review** - Check dashboards weekly to identify trends
3. **Performance budgets** - Set thresholds for acceptable latencies
4. **Correlate metrics** - Look at multiple panels together to find root causes
5. **Save custom queries** - Star useful queries in Prometheus for quick access

---

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/best-practices-for-creating-dashboards/)

---

## 🤝 Need Help?

If you encounter issues:
1. Check the logs: `docker logs neuroclima-api`
2. Verify environment variables in `.env`
3. Ensure all services are running
4. Check firewall/network settings

Happy monitoring! 📊✨
