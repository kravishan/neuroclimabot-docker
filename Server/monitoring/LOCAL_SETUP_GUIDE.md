# Local Prometheus & Grafana Setup Guide

This guide will help you set up Prometheus and Grafana locally to monitor your NeuroClima Python backend.

## Prerequisites

- Python backend running on `localhost:8000` (with metrics on port `8001`)
- Basic familiarity with command line

## Architecture

```
Python Backend (localhost:8000)
    ↓ exposes /metrics
Metrics Server (localhost:8001)
    ↓ scraped by
Prometheus (localhost:9090)
    ↓ data source for
Grafana (localhost:3000)
```

## Step 1: Verify Backend Metrics

First, ensure your Python backend is running with metrics enabled:

```bash
# Check your .env file has these settings:
# ENABLE_METRICS=true
# METRICS_PORT=8001

# Start your Python backend
cd Server
python -m app.main
```

Verify metrics are accessible:
```bash
# In another terminal, test the metrics endpoint
curl http://localhost:8001/metrics
# OR visit in browser: http://localhost:8001/metrics
```

You should see Prometheus-format metrics like:
```
neuroclima_requests_total{...} 1.0
neuroclima_request_duration_seconds_bucket{...} 0.5
...
```

## Step 2: Install & Run Prometheus

### Windows

1. **Download Prometheus:**
   - Visit: https://prometheus.io/download/
   - Download the latest Windows release (e.g., `prometheus-2.x.x.windows-amd64.zip`)

2. **Extract and configure:**
   ```powershell
   # Extract the zip file to C:\prometheus
   # Copy the prometheus.yml config
   Copy-Item Server\monitoring\prometheus.yml C:\prometheus\prometheus.yml
   ```

3. **Run Prometheus:**
   ```powershell
   cd C:\prometheus
   .\prometheus.exe --config.file=prometheus.yml
   ```

### Linux/Mac

1. **Download and install:**
   ```bash
   # Linux
   wget https://github.com/prometheus/prometheus/releases/download/v2.52.0/prometheus-2.52.0.linux-amd64.tar.gz
   tar xvfz prometheus-*.tar.gz
   cd prometheus-*

   # Mac (using Homebrew)
   brew install prometheus
   ```

2. **Copy configuration:**
   ```bash
   # For Linux (if extracted to ~/prometheus)
   cp Server/monitoring/prometheus.yml ~/prometheus-*/prometheus.yml

   # For Mac (Homebrew)
   cp Server/monitoring/prometheus.yml /opt/homebrew/etc/prometheus.yml
   ```

3. **Run Prometheus:**
   ```bash
   # Linux
   ./prometheus --config.file=prometheus.yml

   # Mac (Homebrew)
   brew services start prometheus
   # OR run directly:
   prometheus --config.file=/opt/homebrew/etc/prometheus.yml
   ```

### Verify Prometheus

- Open browser: http://localhost:9090
- Go to Status → Targets
- You should see `neuroclima-backend` target with status "UP"
- Try a query: `neuroclima_requests_total` in the Expression field

## Step 3: Install & Run Grafana

### Windows

1. **Download Grafana:**
   - Visit: https://grafana.com/grafana/download?platform=windows
   - Download the Windows installer or ZIP

2. **Install and run:**
   ```powershell
   # If using installer, follow installation wizard
   # If using ZIP, extract and run:
   cd C:\grafana\bin
   .\grafana-server.exe
   ```

### Linux

1. **Install Grafana:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y software-properties-common
   sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
   wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
   sudo apt-get update
   sudo apt-get install grafana

   # Start Grafana
   sudo systemctl start grafana-server
   sudo systemctl enable grafana-server
   ```

### Mac

1. **Install using Homebrew:**
   ```bash
   brew install grafana

   # Start Grafana
   brew services start grafana
   # OR run directly:
   grafana-server --config=/opt/homebrew/etc/grafana/grafana.ini
   ```

### Verify Grafana

- Open browser: http://localhost:3000
- Default login: `admin` / `admin` (you'll be prompted to change)

## Step 4: Configure Grafana Data Source

1. **Login to Grafana** (http://localhost:3000)

2. **Add Prometheus Data Source:**
   - Click "Connections" → "Data sources" → "Add data source"
   - Select "Prometheus"
   - Configure:
     - **Name:** Prometheus
     - **URL:** `http://localhost:9090`
     - **Access:** Server (default)
   - Click "Save & Test" - you should see "Data source is working"

## Step 5: Import Dashboard

### Option A: Manual Import (Recommended for Local)

1. In Grafana, click "Dashboards" → "New" → "Import"
2. Click "Upload JSON file"
3. Select: `Server/monitoring/grafana/dashboards/neuroclima-dashboard.json`
4. Select "Prometheus" as the data source
5. Click "Import"

### Option B: Automatic Provisioning (Advanced)

1. **Find Grafana configuration directory:**
   - Windows: `C:\Program Files\GrafanaLabs\grafana\conf\`
   - Linux: `/etc/grafana/`
   - Mac: `/opt/homebrew/etc/grafana/`

2. **Copy provisioning files:**
   ```bash
   # Create provisioning directories if they don't exist
   mkdir -p <grafana-dir>/provisioning/datasources
   mkdir -p <grafana-dir>/provisioning/dashboards

   # Copy datasource config (use local version - see next step)
   cp Server/monitoring/grafana/provisioning/datasources/prometheus-local.yml <grafana-dir>/provisioning/datasources/

   # Copy dashboard config
   cp Server/monitoring/grafana/provisioning/dashboards/default.yml <grafana-dir>/provisioning/dashboards/

   # Copy dashboard JSON
   cp Server/monitoring/grafana/dashboards/neuroclima-dashboard.json <grafana-dir>/provisioning/dashboards/
   ```

3. **Restart Grafana** to load provisioned configs

## Step 6: Test the Setup

1. **Generate some traffic to your backend:**
   ```bash
   # Hit the health endpoint a few times
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/health
   ```

2. **Check Prometheus:**
   - Visit http://localhost:9090
   - Query: `neuroclima_requests_total`
   - You should see metrics with your requests

3. **Check Grafana:**
   - Visit http://localhost:3000
   - Open the NeuroClima dashboard
   - You should see charts updating with request data

## Troubleshooting

### Prometheus can't scrape metrics

**Problem:** Target shows as "DOWN" in Prometheus targets page

**Solutions:**
- Verify Python backend is running: `curl http://localhost:8001/metrics`
- Check `.env` has `ENABLE_METRICS=true` and `METRICS_PORT=8001`
- Verify no firewall blocking port 8001
- Check prometheus.yml has correct target: `localhost:8001`

### Grafana shows "No data"

**Solutions:**
- Verify Prometheus data source is working (click "Save & Test")
- Check Prometheus has data: visit http://localhost:9090 and run query
- Verify time range in Grafana (top right) - set to "Last 5 minutes"
- Generate traffic to your backend to create metrics

### Grafana can't connect to Prometheus

**Problem:** "Data source is not working" error

**Solutions:**
- Verify Prometheus is running: visit http://localhost:9090
- Check Grafana data source URL is `http://localhost:9090` (not `http://prometheus:9090`)
- Try using `http://127.0.0.1:9090` instead

### Metrics server not starting

**Problem:** Python backend logs show metrics server failed

**Solutions:**
- Check port 8001 is not in use: `netstat -an | grep 8001` (Linux/Mac) or `netstat -an | findstr 8001` (Windows)
- Try changing `METRICS_PORT` in `.env` to another port (e.g., 8002)
- Update prometheus.yml targets to match new port

## Available Metrics

Your NeuroClima backend exposes these metrics:

- `neuroclima_requests_total` - Total HTTP requests by method, endpoint, status
- `neuroclima_request_duration_seconds` - Request duration histogram
- `neuroclima_active_requests` - Current active requests
- `neuroclima_active_sessions` - Number of active sessions
- `neuroclima_cache_hit_rate` - Cache hit rate
- `neuroclima_llm_duration_seconds` - LLM generation time
- `neuroclima_retrieval_duration_seconds` - Document retrieval time

## Next Steps

Once local setup is working:

1. **Customize Dashboard:** Edit panels in Grafana to track metrics important to you
2. **Add Alerts:** Configure Grafana alerts for high error rates or slow responses
3. **Docker Setup:** When ready, use docker-compose for production deployment

## Stopping Services

```bash
# Stop Prometheus
# Ctrl+C if running in terminal, or:
pkill prometheus

# Stop Grafana
# Linux:
sudo systemctl stop grafana-server
# Mac:
brew services stop grafana
# Windows: Stop from Services panel or Ctrl+C

# Stop Python backend
# Ctrl+C in the terminal running it
```

## Useful Links

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Backend Metrics: http://localhost:8001/metrics
- Backend Health: http://localhost:8000/health
- Backend API Docs: http://localhost:8000/docs
