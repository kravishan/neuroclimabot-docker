#!/usr/bin/env python3
"""
Dependency Fix Script for TruLens and External Services

This script helps fix common dependency and connectivity issues:
1. TruLens protobuf compatibility
2. External service connectivity
3. Environment configuration validation

Usage:
    python scripts/fix_dependencies.py
"""

import subprocess
import sys
import os
from pathlib import Path

def print_header(message: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {message}")
    print("=" * 70 + "\n")

def print_step(step_num: int, message: str):
    """Print a numbered step."""
    print(f"\n{step_num}. {message}")
    print("-" * 70)

def run_command(command: list, description: str) -> bool:
    """Run a shell command and return success status."""
    try:
        print(f"   Running: {' '.join(command)}")
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"   ✅ {description} - SUCCESS")
        if result.stdout:
            print(f"   Output: {result.stdout[:200]}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description} - FAILED")
        if e.stderr:
            print(f"   Error: {e.stderr[:200]}")
        return False
    except Exception as e:
        print(f"   ❌ {description} - ERROR: {str(e)}")
        return False

def main():
    print_header("TruLens & External Services - Dependency Fix Script")

    # Change to Server directory
    script_dir = Path(__file__).parent
    server_dir = script_dir.parent
    os.chdir(server_dir)

    print(f"📂 Working directory: {server_dir}")

    # Step 1: Fix protobuf version
    print_step(1, "Fix Protobuf Compatibility Issue")
    print("   Issue: TruLens requires protobuf 3.x, but newer version may be installed")
    print("   Solution: Downgrade protobuf to 3.20.3")

    success = run_command(
        [sys.executable, "-m", "pip", "install", "protobuf==3.20.3", "--force-reinstall"],
        "Reinstall protobuf 3.20.3"
    )

    if not success:
        print("\n⚠️  Protobuf fix failed. Try manually:")
        print("   pip uninstall protobuf -y")
        print("   pip install protobuf==3.20.3")

    # Step 2: Reinstall TruLens
    print_step(2, "Reinstall TruLens with Fixed Dependencies")

    success = run_command(
        [sys.executable, "-m", "pip", "install", "trulens-eval==0.33.0", "--no-deps"],
        "Reinstall TruLens (no deps)"
    )

    if success:
        run_command(
            [sys.executable, "-m", "pip", "install", "trulens-eval==0.33.0"],
            "Reinstall TruLens dependencies"
        )

    # Step 3: Verify TruLens import
    print_step(3, "Verify TruLens Import")

    try:
        print("   Attempting to import TruLens...")
        import trulens_eval
        from trulens_eval.feedback.provider.openai import OpenAI as TruLensOpenAI
        print("   ✅ TruLens import - SUCCESS")
        print(f"   Version: {trulens_eval.__version__}")
    except ImportError as e:
        print(f"   ❌ TruLens import - FAILED: {str(e)}")
        print("\n   This may require manual intervention:")
        print("   1. pip uninstall transformers tensorflow -y")
        print("   2. pip install protobuf==3.20.3")
        print("   3. pip install transformers tensorflow")

    # Step 4: Check .env file
    print_step(4, "Check Environment Configuration")

    env_file = server_dir / ".env"
    if env_file.exists():
        print(f"   ✅ .env file found: {env_file}")

        # Check critical variables
        critical_vars = [
            "MILVUS_HOST",
            "MILVUS_PORT",
            "MINIO_ENDPOINT",
            "MINIO_ACCESS_KEY",
            "REDIS_HOST",
            "TRULENS_ENABLED"
        ]

        with open(env_file, 'r') as f:
            env_content = f.read()

        print("\n   Checking critical environment variables:")
        for var in critical_vars:
            if var in env_content:
                # Extract value (simple check)
                for line in env_content.split('\n'):
                    if line.startswith(var):
                        print(f"      ✅ {line[:50]}")
                        break
            else:
                print(f"      ❌ {var} - NOT FOUND")
    else:
        print(f"   ❌ .env file not found: {env_file}")
        print("   Please create .env from .env.example:")
        print(f"   cp {server_dir}/.env.example {server_dir}/.env")

    # Step 5: Run health check
    print_step(5, "Run External Services Health Check")

    health_check_script = server_dir / "tests" / "test_external_services.py"
    if health_check_script.exists():
        print(f"   Health check script: {health_check_script}")
        print("\n   To run the health check, execute:")
        print(f"   python tests/test_external_services.py")
        print("\n   This will test connectivity to:")
        print("   - Milvus vector database")
        print("   - MinIO object storage")
        print("   - Redis cache")
        print("   - Ollama LLM service")
        print("   - GraphRAG API")
        print("   - OpenAI API")
    else:
        print(f"   ❌ Health check script not found: {health_check_script}")

    # Summary
    print_header("Summary & Next Steps")

    print("✅ Dependency fixes applied\n")

    print("📋 Next Steps:")
    print("\n1. Verify TruLens is working:")
    print("   python tests/test_trulens_integration.py")

    print("\n2. Check external services:")
    print("   python tests/test_external_services.py")

    print("\n3. Start external services if needed:")
    print("   - Milvus: Check if running on port 19530")
    print("   - MinIO: Check if running on port 9000")
    print("   - Redis: Check if running on port 6379")
    print("   - Ollama: Check if running on port 11434")

    print("\n4. Configure .env file:")
    print("   - Set correct MILVUS_HOST, MILVUS_PORT")
    print("   - Set correct MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY")
    print("   - Set TRULENS_ENABLED=true")
    print("   - Set TRULENS_OPENAI_API_KEY (or leave empty for Ollama)")

    print("\n5. Start the application:")
    print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")

    print("\n" + "=" * 70)
    print("For more help, see: Server/app/services/evaluation/RUNNING_GUIDE.md")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
