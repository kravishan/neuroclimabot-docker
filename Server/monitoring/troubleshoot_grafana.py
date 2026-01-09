#!/usr/bin/env python3
"""
Interactive troubleshooting script for Grafana "No Data" issues.
This script helps diagnose and fix common problems with the monitoring setup.
"""

import sys
import time
import requests
from typing import Dict, Tuple, Optional


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")


def print_step(number: int, text: str):
    """Print a step header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step {number}] {text}{Colors.END}")
    print(f"{Colors.BLUE}{'-'*70}{Colors.END}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


def print_command(text: str):
    """Print a command to run."""
    print(f"{Colors.CYAN}  $ {text}{Colors.END}")


def check_url(url: str, timeout: int = 3) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Check if a URL is accessible.

    Returns:
        Tuple of (success: bool, content: Optional[str], status_code: Optional[int])
    """
    try:
        response = requests.get(url, timeout=timeout)
        return True, response.text, response.status_code
    except requests.exceptions.ConnectionError:
        return False, None, None
    except requests.exceptions.Timeout:
        return False, "TIMEOUT", None
    except Exception as e:
        return False, str(e), None


def check_backend():
    """Check if the Python backend is running and exposing metrics."""
    print_step(1, "Checking Python Backend")

    # Check main API
    print_info("Checking main API endpoint...")
    success, content, status = check_url("http://localhost:8000/health")

    if not success:
        print_error("Backend is NOT running on port 8000")
        print_warning("\nThe Python backend must be running for metrics to work.")
        print_info("\nTo start the backend:")
        print_command("cd Server")
        print_command("python -m app.main")
        print_info("\nOR if using uvicorn directly:")
        print_command("cd Server")
        print_command("uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print_info("\nMake sure your .env file exists and is configured properly.")
        return False

    print_success(f"Backend is running (status: {status})")

    # Check metrics endpoint
    print_info("\nChecking metrics endpoint...")
    success, content, status = check_url("http://localhost:8001/metrics")

    if not success:
        print_error("Metrics endpoint is NOT accessible on port 8001")
        print_warning("\nThe backend is running but metrics are not exposed.")
        print_info("\nPossible causes:")
        print_info("1. ENABLE_METRICS is not set to 'true' in .env")
        print_info("2. METRICS_PORT is not set to 8001 in .env")
        print_info("3. Another service is using port 8001")
        print_info("\nCheck your .env file has:")
        print_command("ENABLE_METRICS=true")
        print_command("METRICS_PORT=8001")
        print_info("\nThen restart the backend:")
        print_command("# Stop the backend (Ctrl+C) and restart it")
        return False

    if status != 200:
        print_error(f"Metrics endpoint returned status {status}")
        return False

    # Check metrics content
    if content and 'neuroclima_requests_total' in content:
        print_success("Metrics endpoint is working correctly")

        # Count metrics
        metric_lines = [line for line in content.split('\n') if line and not line.startswith('#')]
        print_info(f"Found {len(metric_lines)} metric data points")

        # Show sample metrics
        print_info("\nSample metrics:")
        for line in content.split('\n')[:10]:
            if line and not line.startswith('#'):
                print(f"    {line[:80]}")
                break

        return True
    else:
        print_error("Metrics endpoint is accessible but contains no NeuroClima metrics")
        print_warning("The metrics may not be properly initialized.")
        return False


def check_prometheus():
    """Check if Prometheus is running and scraping the backend."""
    print_step(2, "Checking Prometheus")

    # Check if Prometheus is running
    print_info("Checking if Prometheus is running...")
    success, content, status = check_url("http://localhost:9090/-/healthy")

    if not success:
        print_error("Prometheus is NOT running on port 9090")
        print_warning("\nPrometheus is required to collect metrics from the backend.")
        print_info("\nTo install and run Prometheus:")
        print_info("\n[Windows]")
        print_command("# Download from https://prometheus.io/download/")
        print_command("# Extract to C:\\prometheus")
        print_command("# Copy prometheus.yml:")
        print_command("Copy-Item Server\\monitoring\\prometheus.yml C:\\prometheus\\")
        print_command("cd C:\\prometheus")
        print_command(".\\prometheus.exe --config.file=prometheus.yml")

        print_info("\n[Linux]")
        print_command("wget https://github.com/prometheus/prometheus/releases/download/v2.52.0/prometheus-2.52.0.linux-amd64.tar.gz")
        print_command("tar xvfz prometheus-*.tar.gz")
        print_command("cd prometheus-*")
        print_command("./prometheus --config.file=../Server/monitoring/prometheus.yml")

        print_info("\n[Mac with Homebrew]")
        print_command("brew install prometheus")
        print_command("cp Server/monitoring/prometheus.yml /opt/homebrew/etc/prometheus.yml")
        print_command("prometheus --config.file=/opt/homebrew/etc/prometheus.yml")

        return False

    print_success("Prometheus is running")

    # Check Prometheus targets
    print_info("\nChecking Prometheus targets...")
    success, content, status = check_url("http://localhost:9090/api/v1/targets")

    if not success:
        print_error("Cannot access Prometheus API")
        return False

    import json
    try:
        data = json.loads(content)
        active_targets = data.get('data', {}).get('activeTargets', [])

        if not active_targets:
            print_error("No targets configured in Prometheus")
            print_warning("\nPrometheus has no scrape targets configured.")
            print_info("Make sure you're using the correct prometheus.yml:")
            print_command("prometheus --config.file=Server/monitoring/prometheus.yml")
            return False

        print_success(f"Found {len(active_targets)} target(s)")

        # Check for neuroclima target
        neuroclima_target = None
        for target in active_targets:
            job = target.get('labels', {}).get('job', '')
            if 'neuroclima' in job.lower():
                neuroclima_target = target
                break

        if not neuroclima_target:
            print_error("NeuroClima backend target not found in Prometheus")
            print_warning("\nPrometheus is not configured to scrape the backend.")
            print_info("Check that prometheus.yml contains:")
            print_command("scrape_configs:")
            print_command("  - job_name: 'neuroclima-backend'")
            print_command("    static_configs:")
            print_command("      - targets: ['localhost:8001']")
            return False

        # Check target health
        health = neuroclima_target.get('health', 'unknown')
        scrape_url = neuroclima_target.get('scrapeUrl', 'unknown')
        last_error = neuroclima_target.get('lastError', '')

        print_info(f"\nNeuroClima target status:")
        print_info(f"  URL: {scrape_url}")
        print_info(f"  Health: {health}")

        if health == 'up':
            print_success("✓ Prometheus is successfully scraping the backend!")

            # Check if there's actual data
            print_info("\nChecking for metric data in Prometheus...")
            success, content, status = check_url(
                "http://localhost:9090/api/v1/query?query=neuroclima_requests_total"
            )

            if success:
                data = json.loads(content)
                results = data.get('data', {}).get('result', [])
                if results:
                    print_success(f"Found {len(results)} metric series")
                    return True
                else:
                    print_warning("Target is UP but no metrics data found yet")
                    print_info("This is normal if the backend just started.")
                    print_info("Generate some traffic to create metrics:")
                    print_command("curl http://localhost:8000/health")
                    print_command("curl http://localhost:8000/api/v1/health")
                    return True
        else:
            print_error(f"Target is {health.upper()}")
            if last_error:
                print_error(f"Last error: {last_error}")
            print_warning("\nPrometheus cannot scrape the backend.")
            print_info("Common causes:")
            print_info("1. Backend metrics endpoint not accessible")
            print_info("2. Wrong port in prometheus.yml (should be 8001)")
            print_info("3. Firewall blocking the connection")
            return False

    except Exception as e:
        print_error(f"Error parsing Prometheus response: {e}")
        return False

    return True


def check_grafana():
    """Check if Grafana is running and configured correctly."""
    print_step(3, "Checking Grafana")

    # Check if Grafana is running
    print_info("Checking if Grafana is running...")
    success, content, status = check_url("http://localhost:3000/api/health")

    if not success:
        print_error("Grafana is NOT running on port 3000")
        print_warning("\nGrafana is required for visualization.")
        print_info("\nTo install and run Grafana:")
        print_info("\n[Windows]")
        print_command("# Download from https://grafana.com/grafana/download?platform=windows")
        print_command("# Install and run Grafana")

        print_info("\n[Linux]")
        print_command("sudo apt-get install grafana")
        print_command("sudo systemctl start grafana-server")

        print_info("\n[Mac with Homebrew]")
        print_command("brew install grafana")
        print_command("brew services start grafana")

        print_info("\nThen access Grafana at: http://localhost:3000")
        print_info("Default login: admin / admin")
        return False

    print_success("Grafana is running")

    # Check datasources (requires auth, so we'll skip detailed check)
    print_info("\nTo configure Grafana:")
    print_info("1. Open http://localhost:3000 in your browser")
    print_info("2. Login (default: admin/admin)")
    print_info("3. Go to: Connections → Data sources → Add data source")
    print_info("4. Select 'Prometheus'")
    print_info("5. Set URL to: http://localhost:9090")
    print_info("6. Click 'Save & Test'")
    print_info("\nThen import the dashboard:")
    print_info("1. Go to: Dashboards → Import")
    print_info("2. Upload: Server/monitoring/grafana/dashboards/neuroclima-dashboard.json")
    print_info("3. Select 'Prometheus' as the datasource")

    return True


def check_dashboard_queries():
    """Provide information about dashboard queries."""
    print_step(4, "Dashboard Queries")

    print_info("The NeuroClima dashboard uses these queries:")
    print_info("")
    print_info("1. Request Rate:")
    print_command("   rate(neuroclima_requests_total[5m])")
    print_info("")
    print_info("2. Request Duration (p95):")
    print_command("   histogram_quantile(0.95, rate(neuroclima_request_duration_seconds_bucket[5m]))")
    print_info("")
    print_info("3. Active Requests:")
    print_command("   neuroclima_active_requests")
    print_info("")

    print_info("\nTo test queries in Prometheus:")
    print_info("1. Open http://localhost:9090")
    print_info("2. Go to 'Graph' tab")
    print_info("3. Enter a query, e.g.: neuroclima_requests_total")
    print_info("4. Click 'Execute'")
    print_info("")
    print_info("If you see data in Prometheus but not in Grafana:")
    print_info("• Check the time range in Grafana (top right)")
    print_info("• Set it to 'Last 5 minutes' or 'Last 15 minutes'")
    print_info("• Click the refresh button or enable auto-refresh")


def generate_traffic():
    """Generate some traffic to create metrics."""
    print_step(5, "Generate Traffic (Optional)")

    print_info("Generating traffic to create metrics...")

    endpoints = [
        "http://localhost:8000/",
        "http://localhost:8000/health",
        "http://localhost:8000/api/v1/health",
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            print_success(f"✓ {endpoint} → {response.status_code}")
        except Exception as e:
            print_warning(f"✗ {endpoint} → {e}")

    print_info("\nWait 15-30 seconds for Prometheus to scrape the metrics...")
    print_info("Then check Grafana again.")


def main():
    """Run all troubleshooting checks."""
    print_header("Grafana 'No Data' Troubleshooting")

    print(f"{Colors.BOLD}This script will check your monitoring setup and help fix issues.{Colors.END}")
    print()

    # Check backend
    backend_ok = check_backend()

    if not backend_ok:
        print_header("Summary")
        print_error("Backend is not running or not exposing metrics.")
        print_info("\nFix this first, then run this script again:")
        print_command("python Server/monitoring/troubleshoot_grafana.py")
        return 1

    # Check Prometheus
    prometheus_ok = check_prometheus()

    if not prometheus_ok:
        print_header("Summary")
        print_error("Prometheus is not running or not configured correctly.")
        print_info("\nFix Prometheus, then run this script again.")
        return 1

    # Check Grafana
    grafana_ok = check_grafana()

    # Show dashboard query info
    check_dashboard_queries()

    # Offer to generate traffic
    if backend_ok and prometheus_ok:
        print()
        response = input(f"{Colors.YELLOW}Generate test traffic to create metrics? (y/n): {Colors.END}").lower()
        if response == 'y':
            generate_traffic()

    # Final summary
    print_header("Summary")

    if backend_ok and prometheus_ok and grafana_ok:
        print_success("All services are running!")
        print_info("\nIf Grafana still shows 'No Data':")
        print_info("1. Check the time range in Grafana (top right)")
        print_info("2. Set it to 'Last 15 minutes'")
        print_info("3. Enable auto-refresh (5s or 10s)")
        print_info("4. Verify Prometheus datasource is configured:")
        print_info("   • Go to Connections → Data sources")
        print_info("   • Click 'Prometheus'")
        print_info("   • URL should be: http://localhost:9090")
        print_info("   • Click 'Save & Test'")
        print_info("")
        print_info("5. Test queries in Prometheus first:")
        print_info("   • Open http://localhost:9090")
        print_info("   • Run: neuroclima_requests_total")
        print_info("   • If you see data, the issue is in Grafana config")
        return 0
    else:
        print_error("Some services are not working correctly.")
        print_info("Fix the issues above and run this script again.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Troubleshooting cancelled{Colors.END}")
        sys.exit(1)
