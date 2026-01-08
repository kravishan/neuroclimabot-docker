# Grafana "No Data" Troubleshooting Guide

## 🔧 Quick Diagnostic Tool

Run this script first to automatically diagnose issues:

```bash
python Server/monitoring/troubleshoot_grafana.py
```

This script will check:
- ✅ Backend is running and exposing metrics
- ✅ Prometheus is running and scraping
- ✅ Grafana is running
- ✅ Metrics are being collected

## 🚨 Common Issues & Solutions

### Issue 1: Backend Not Running

**Symptom:** Can't access http://localhost:8000 or http://localhost:8001/metrics

**Solution:**
```bash
# Start the backend
cd Server
python -m app.main
```

**Check:**
- Verify `.env` file exists in `Server/` directory
- Check console for error messages
- Ensure all dependencies are installed: `pip install -r requirements.txt`

---

### Issue 2: Metrics Not Enabled

**Symptom:** Backend runs but http://localhost:8001/metrics shows nothing

**Solution:**

1. Check your `Server/.env` file contains:
   ```bash
   ENABLE_METRICS=true
   METRICS_PORT=8001
   ```

2. If `.env` doesn't exist, copy from template:
   ```bash
   cp Server/.env.example Server/.env
   ```

3. Edit `.env` and set:
   ```bash
   ENABLE_METRICS=true
   METRICS_PORT=8001
   ```

4. **Restart the backend** (Ctrl+C and run again)

**Verify:**
```bash
curl http://localhost:8001/metrics
```

You should see output like:
```
# HELP neuroclima_requests_total Total HTTP requests
# TYPE neuroclima_requests_total counter
neuroclima_requests_total{endpoint="/health",method="GET",status_code="200"} 1.0
```

---

### Issue 3: Prometheus Not Running

**Symptom:** Can't access http://localhost:9090

**Solution:**

#### Windows:
```powershell
# Download from https://prometheus.io/download/
# Extract to C:\prometheus

# Copy config file
Copy-Item Server\monitoring\prometheus.yml C:\prometheus\

# Run Prometheus
cd C:\prometheus
.\prometheus.exe --config.file=prometheus.yml
```

#### Linux:
```bash
# Download
wget https://github.com/prometheus/prometheus/releases/download/v2.52.0/prometheus-2.52.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Run with config
./prometheus --config.file=../Server/monitoring/prometheus.yml
```

#### Mac (Homebrew):
```bash
brew install prometheus
cp Server/monitoring/prometheus.yml /opt/homebrew/etc/prometheus.yml
prometheus --config.file=/opt/homebrew/etc/prometheus.yml
```

**Verify:**
- Open http://localhost:9090 in browser
- Go to Status → Targets
- Look for `neuroclima-backend` with status "UP"

---

### Issue 4: Prometheus Target is DOWN

**Symptom:** In Prometheus (http://localhost:9090/targets), the neuroclima-backend shows "DOWN"

**Possible Causes & Solutions:**

#### A. Backend not running
```bash
# Check if backend is running
curl http://localhost:8001/metrics

# If not, start it:
cd Server
python -m app.main
```

#### B. Wrong port in prometheus.yml
Check `Server/monitoring/prometheus.yml` has:
```yaml
scrape_configs:
  - job_name: 'neuroclima-backend'
    static_configs:
      - targets: ['localhost:8001']  # ← Should be 8001, not 8000
```

#### C. Firewall blocking port 8001
```bash
# Windows: Check Windows Firewall
# Linux: Check with
sudo ufw status

# Allow port if needed
sudo ufw allow 8001
```

#### D. Prometheus using old config
```bash
# Restart Prometheus after changing prometheus.yml
# Stop Prometheus (Ctrl+C)
# Start it again with the correct config file
```

---

### Issue 5: Grafana Not Running

**Symptom:** Can't access http://localhost:3000

**Solution:**

#### Windows:
- Download from https://grafana.com/grafana/download?platform=windows
- Run the installer or extract ZIP
- Start Grafana server

#### Linux:
```bash
sudo systemctl start grafana-server
# OR
sudo service grafana-server start
```

#### Mac:
```bash
brew services start grafana
```

**Verify:**
- Open http://localhost:3000
- Login with admin/admin

---

### Issue 6: Grafana Datasource Not Configured

**Symptom:** Grafana opens but dashboards show "No Data" or "Data source not found"

**Solution:**

1. **Login to Grafana** at http://localhost:3000 (admin/admin)

2. **Add Prometheus Data Source:**
   - Click **Connections** → **Data sources**
   - Click **Add data source**
   - Select **Prometheus**
   - Configure:
     - **Name:** `Prometheus`
     - **URL:** `http://localhost:9090`
     - **Access:** Server (default)
   - Click **Save & Test**
   - You should see: ✅ "Data source is working"

3. **If "Save & Test" fails:**
   - Verify Prometheus is running: visit http://localhost:9090
   - Try `http://127.0.0.1:9090` instead of `localhost:9090`
   - Check no firewall is blocking port 9090

---

### Issue 7: Dashboard Shows "No Data"

**Symptom:** Grafana datasource works, but dashboard panels show "No data"

**Solutions:**

#### A. Check Time Range
1. In Grafana dashboard, look at **top right corner**
2. Click the time range dropdown
3. Select **Last 15 minutes** or **Last 5 minutes**
4. The time range might be set to a period before you started collecting metrics

#### B. Enable Auto-Refresh
1. Click the refresh icon (top right)
2. Set to **5s** or **10s** for real-time updates

#### C. Generate Traffic
Metrics only appear when your backend receives requests:
```bash
# Generate some requests
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health

# Run a few times
for i in {1..10}; do curl http://localhost:8000/health; done
```

Wait 15-30 seconds for Prometheus to scrape, then refresh Grafana.

#### D. Verify Data in Prometheus First
1. Open http://localhost:9090
2. Go to **Graph** tab
3. Enter query: `neuroclima_requests_total`
4. Click **Execute**
5. If you see data here but not in Grafana:
   - The issue is with Grafana datasource configuration
   - Check datasource URL is correct
   - Re-import the dashboard

#### E. Check Dashboard Queries
1. In Grafana, click **Edit** on a panel
2. Check the query at the bottom
3. Common queries:
   - `rate(neuroclima_requests_total[5m])`
   - `neuroclima_active_requests`
   - `neuroclima_request_duration_seconds`

4. Make sure **Data source** is set to **Prometheus**

---

### Issue 8: Some Panels Show Data, Others Don't

**Symptom:** Some dashboard panels work, but others show "No data"

**Solution:**

Different panels track different metrics. Some metrics only appear after specific actions:

| Metric | When It Appears |
|--------|----------------|
| `neuroclima_requests_total` | After any API request |
| `neuroclima_active_requests` | When requests are being processed |
| `neuroclima_active_sessions` | After a user creates a session |
| `neuroclima_llm_duration_seconds` | After LLM generates a response |
| `neuroclima_retrieval_duration_seconds` | After document retrieval |
| `neuroclima_cache_hit_rate` | After cache operations |

**Generate Comprehensive Traffic:**
```bash
# Make API requests to trigger different metrics
curl -X POST http://localhost:8000/api/v1/chat/start \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "bucket": "researchpapers"}'

# Check health (creates basic metrics)
curl http://localhost:8000/health

# List sessions (if auth is disabled)
curl http://localhost:8000/api/v1/chat/sessions
```

---

## 📊 Step-by-Step Verification

Run these commands in order to verify your setup:

### Step 1: Backend
```bash
# Check backend is running
curl http://localhost:8000/health

# Should return: {"status": "healthy", ...}
```

### Step 2: Metrics
```bash
# Check metrics endpoint
curl http://localhost:8001/metrics

# Should return Prometheus-format metrics
# Look for: neuroclima_requests_total
```

### Step 3: Prometheus
```bash
# Check Prometheus health
curl http://localhost:9090/-/healthy

# Should return: Healthy
```

### Step 4: Prometheus Targets
```bash
# Check targets API
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="neuroclima-backend") | .health'

# Should return: "up"
```

### Step 5: Prometheus Query
```bash
# Query for metrics
curl 'http://localhost:9090/api/v1/query?query=neuroclima_requests_total' | jq '.data.result'

# Should return array with metric data
```

### Step 6: Grafana
1. Open http://localhost:3000
2. Login (admin/admin)
3. Go to Dashboards
4. Open NeuroClima dashboard
5. Set time range to "Last 15 minutes"
6. Enable auto-refresh

---

## 🔍 Automated Troubleshooting

Use the interactive troubleshooting script:

```bash
python Server/monitoring/troubleshoot_grafana.py
```

This will:
- ✅ Check all services are running
- ✅ Verify configuration
- ✅ Test connectivity
- ✅ Show detailed error messages
- ✅ Suggest fixes
- ✅ Optionally generate test traffic

---

## 📝 Still Not Working?

If you've tried everything above and Grafana still shows no data:

### 1. Check Logs

**Backend logs:**
```bash
# Look for errors when starting the backend
cd Server
python -m app.main

# Should see:
# ✅ Metrics server started on port 8001
```

**Prometheus logs:**
```bash
# Prometheus shows logs in the terminal where it's running
# Look for:
# level=info msg="Server is ready to receive web requests."
```

**Grafana logs:**
- Windows: `C:\Program Files\GrafanaLabs\grafana\data\log\grafana.log`
- Linux: `/var/log/grafana/grafana.log`
- Mac: `/opt/homebrew/var/log/grafana/grafana.log`

### 2. Restart Everything in Order

```bash
# 1. Stop all services (Ctrl+C in each terminal)

# 2. Start backend
cd Server
python -m app.main

# 3. Start Prometheus (in new terminal)
prometheus --config.file=Server/monitoring/prometheus.yml

# 4. Start Grafana (in new terminal)
# Linux: sudo systemctl start grafana-server
# Mac: brew services start grafana
# Windows: Start from Services

# 5. Wait 30 seconds

# 6. Generate traffic
curl http://localhost:8000/health

# 7. Open Grafana and check
```

### 3. Verify Ports

Check that ports are not blocked or in use:

```bash
# Windows
netstat -an | findstr "8000 8001 9090 3000"

# Linux/Mac
netstat -an | grep -E "8000|8001|9090|3000"

# You should see LISTEN on all these ports
```

### 4. Check prometheus.yml Location

Make sure Prometheus is using the correct config:

```bash
# When starting Prometheus, use absolute path
prometheus --config.file=/full/path/to/Server/monitoring/prometheus.yml
```

### 5. Browser Cache

- Clear browser cache
- Try incognito/private mode
- Try a different browser

---

## 💡 Quick Checklist

- [ ] Backend running on port 8000
- [ ] Metrics exposed on port 8001
- [ ] `.env` has `ENABLE_METRICS=true`
- [ ] Prometheus running on port 9090
- [ ] Prometheus config points to `localhost:8001`
- [ ] Prometheus target status is "UP"
- [ ] Grafana running on port 3000
- [ ] Grafana datasource configured (`http://localhost:9090`)
- [ ] Grafana datasource test passes
- [ ] Time range in Grafana set to recent period
- [ ] Traffic generated to backend
- [ ] Auto-refresh enabled in Grafana

If all are checked and it still doesn't work, run:
```bash
python Server/monitoring/troubleshoot_grafana.py
```

---

## 🎯 Expected Result

When everything is working:

1. **Prometheus (http://localhost:9090):**
   - Status → Targets → neuroclima-backend → UP (green)
   - Graph → Query: `neuroclima_requests_total` → Shows data

2. **Grafana (http://localhost:3000):**
   - Connections → Data sources → Prometheus → ✅ Working
   - NeuroClima Dashboard → Shows graphs with data
   - Request Rate panel shows requests/second
   - Response Time panel shows latency

3. **Terminal output when starting backend:**
   ```
   ✅ Metrics server started on port 8001
   ✅ All services initialized successfully
   ```
