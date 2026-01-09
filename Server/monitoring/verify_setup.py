#!/usr/bin/env python3
"""
Verification script for Prometheus/Grafana monitoring setup.
Tests that the backend is exposing metrics correctly.
"""

import sys
import requests
from typing import Dict, List, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


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
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def check_endpoint(url: str, description: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Check if an endpoint is accessible.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return True, f"{description} is accessible"
        else:
            return False, f"{description} returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to {description}. Is the service running?"
    except requests.exceptions.Timeout:
        return False, f"{description} timed out"
    except Exception as e:
        return False, f"{description} error: {str(e)}"


def check_metrics_content(url: str = "http://localhost:8001/metrics") -> Tuple[bool, List[str]]:
    """
    Check if metrics endpoint contains expected NeuroClima metrics.

    Returns:
        Tuple of (success: bool, found_metrics: List[str])
    """
    expected_metrics = [
        'neuroclima_requests_total',
        'neuroclima_request_duration_seconds',
        'neuroclima_active_requests',
    ]

    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return False, []

        content = response.text
        found = [metric for metric in expected_metrics if metric in content]

        return len(found) > 0, found
    except Exception:
        return False, []


def main():
    """Run all verification checks."""
    print_header("NeuroClima Monitoring Setup Verification")

    all_passed = True

    # Check 1: Backend API
    print_info("Checking backend API...")
    success, message = check_endpoint("http://localhost:8000/health", "Backend API")
    if success:
        print_success(message)
    else:
        print_error(message)
        all_passed = False

    # Check 2: Metrics endpoint
    print_info("Checking metrics endpoint...")
    success, message = check_endpoint("http://localhost:8001/metrics", "Metrics endpoint")
    if success:
        print_success(message)

        # Check 3: Metrics content
        print_info("Verifying metrics content...")
        has_metrics, found_metrics = check_metrics_content()
        if has_metrics:
            print_success(f"Found {len(found_metrics)} NeuroClima metrics:")
            for metric in found_metrics:
                print(f"  • {metric}")
        else:
            print_error("No NeuroClima metrics found in response")
            print_warning("Metrics may not be enabled. Check .env file:")
            print_warning("  ENABLE_METRICS=true")
            print_warning("  METRICS_PORT=8001")
            all_passed = False
    else:
        print_error(message)
        print_warning("Make sure your backend is running with:")
        print_warning("  cd Server && python -m app.main")
        all_passed = False

    # Check 4: Prometheus (optional)
    print_info("Checking Prometheus (optional)...")
    success, message = check_endpoint("http://localhost:9090/-/healthy", "Prometheus")
    if success:
        print_success(message)

        # Check if Prometheus is scraping our backend
        print_info("Checking Prometheus targets...")
        try:
            response = requests.get("http://localhost:9090/api/v1/targets", timeout=5)
            if response.status_code == 200:
                data = response.json()
                active_targets = data.get('data', {}).get('activeTargets', [])
                neuroclima_target = next(
                    (t for t in active_targets if 'neuroclima' in t.get('labels', {}).get('job', '')),
                    None
                )
                if neuroclima_target:
                    health = neuroclima_target.get('health', 'unknown')
                    if health == 'up':
                        print_success("Prometheus is successfully scraping backend metrics")
                    else:
                        print_warning(f"Prometheus target is {health}")
                else:
                    print_warning("NeuroClima target not found in Prometheus")
                    print_info("Add to prometheus.yml under scrape_configs")
        except Exception as e:
            print_warning(f"Could not verify Prometheus targets: {e}")
    else:
        print_warning(message)
        print_info("Prometheus is optional for backend, but required for Grafana")
        print_info("Install from: https://prometheus.io/download/")

    # Check 5: Grafana (optional)
    print_info("Checking Grafana (optional)...")
    success, message = check_endpoint("http://localhost:3000/api/health", "Grafana")
    if success:
        print_success(message)
    else:
        print_warning(message)
        print_info("Grafana is optional but recommended for visualization")
        print_info("Install from: https://grafana.com/grafana/download")

    # Final summary
    print_header("Summary")

    if all_passed:
        print_success("All required checks passed! ✨")
        print_info("\nNext steps:")
        print("  1. Install Prometheus: https://prometheus.io/download/")
        print("  2. Run Prometheus with: prometheus --config.file=Server/monitoring/prometheus.yml")
        print("  3. Install Grafana: https://grafana.com/grafana/download")
        print("  4. Import dashboard from: Server/monitoring/grafana/dashboards/neuroclima-dashboard.json")
        print(f"\n📖 Full guide: {Colors.BOLD}Server/monitoring/LOCAL_SETUP_GUIDE.md{Colors.END}")
        return 0
    else:
        print_error("Some checks failed. Please fix the issues above.")
        print_info("\n💡 Common fixes:")
        print("  • Ensure backend is running: cd Server && python -m app.main")
        print("  • Check .env file has ENABLE_METRICS=true")
        print("  • Verify no other service is using port 8001")
        print(f"\n📖 Full guide: {Colors.BOLD}Server/monitoring/LOCAL_SETUP_GUIDE.md{Colors.END}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Verification cancelled{Colors.END}")
        sys.exit(1)
