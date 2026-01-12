"""
External Services Health Check
Tests connectivity and configuration of all external services used by the application.
Run this to diagnose connection issues with Milvus, MinIO, Redis, GraphRAG, Ollama, etc.

Usage:
    python tests/test_external_services.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import time
from typing import Dict, Any, List
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ServiceHealthChecker:
    """Health checker for all external services."""

    def __init__(self):
        self.results = {}
        self.overall_status = True

    def print_header(self, title: str):
        """Print section header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_test(self, service: str, test_name: str, status: bool, details: str = ""):
        """Print test result."""
        symbol = "✅" if status else "❌"
        status_text = "PASS" if status else "FAIL"
        print(f"{symbol} [{service}] {test_name}: {status_text}")
        if details:
            print(f"   → {details}")

        if not status:
            self.overall_status = False

    async def check_milvus(self) -> Dict[str, Any]:
        """Test Milvus connection and collections."""
        self.print_header("MILVUS DATABASE")

        result = {
            "service": "Milvus",
            "connection": False,
            "collections": {},
            "error": None
        }

        try:
            from pymilvus import connections, utility, Collection

            # Test 1: Environment variables
            host = os.getenv("MILVUS_HOST", settings.MILVUS_HOST if hasattr(settings, 'MILVUS_HOST') else None)
            port = os.getenv("MILVUS_PORT", "19530")
            user = os.getenv("MILVUS_USER", "")
            password = os.getenv("MILVUS_PASSWORD", "")

            print(f"\n📋 Configuration:")
            print(f"   Host: {host}")
            print(f"   Port: {port}")
            print(f"   User: {user if user else '(not set)'}")
            print(f"   Password: {'***' if password else '(not set)'}")

            if not host:
                self.print_test("Milvus", "Configuration", False, "MILVUS_HOST not set in .env")
                result["error"] = "MILVUS_HOST not configured"
                return result

            # Test 2: Connection
            print(f"\n🔌 Testing connection to {host}:{port}...")

            try:
                connections.connect(
                    alias="health_check",
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    timeout=10
                )
                result["connection"] = True
                self.print_test("Milvus", "Connection", True, f"Connected to {host}:{port}")
            except Exception as e:
                self.print_test("Milvus", "Connection", False, f"Failed: {str(e)}")
                result["error"] = str(e)
                return result

            # Test 3: List collections
            print(f"\n📚 Checking collections...")
            try:
                collection_names = utility.list_collections(using="health_check")
                self.print_test("Milvus", "List Collections", True, f"Found {len(collection_names)} collections")

                # Test 4: Check expected collections
                expected_collections = ["mvp_latest_chunks", "mvp_latest_summaries"]

                for coll_name in expected_collections:
                    if coll_name in collection_names:
                        try:
                            collection = Collection(coll_name, using="health_check")
                            collection.load()
                            num_entities = collection.num_entities
                            result["collections"][coll_name] = {
                                "exists": True,
                                "num_entities": num_entities,
                                "loaded": True
                            }
                            self.print_test("Milvus", f"Collection '{coll_name}'", True,
                                          f"{num_entities} entities")
                        except Exception as e:
                            result["collections"][coll_name] = {
                                "exists": True,
                                "error": str(e)
                            }
                            self.print_test("Milvus", f"Collection '{coll_name}'", False, str(e))
                    else:
                        result["collections"][coll_name] = {"exists": False}
                        self.print_test("Milvus", f"Collection '{coll_name}'", False,
                                      "Collection does not exist")

                # List all collections with counts
                print(f"\n📊 All Collections:")
                for coll_name in collection_names:
                    try:
                        collection = Collection(coll_name, using="health_check")
                        num_entities = collection.num_entities
                        print(f"   • {coll_name}: {num_entities} entities")
                    except:
                        print(f"   • {coll_name}: (unable to load)")

            except Exception as e:
                self.print_test("Milvus", "List Collections", False, str(e))
                result["error"] = str(e)

            # Cleanup
            connections.disconnect("health_check")

        except ImportError:
            self.print_test("Milvus", "Import pymilvus", False, "pymilvus not installed")
            result["error"] = "pymilvus not installed"
        except Exception as e:
            self.print_test("Milvus", "General", False, str(e))
            result["error"] = str(e)

        return result

    async def check_minio(self) -> Dict[str, Any]:
        """Test MinIO connection and buckets."""
        self.print_header("MinIO OBJECT STORAGE")

        result = {
            "service": "MinIO",
            "connection": False,
            "buckets": {},
            "error": None
        }

        try:
            from minio import Minio

            # Test 1: Environment variables
            endpoint = os.getenv("MINIO_ENDPOINT", "")
            access_key = os.getenv("MINIO_ACCESS_KEY", "")
            secret_key = os.getenv("MINIO_SECRET_KEY", "")
            secure = os.getenv("MINIO_SECURE", "true").lower() == "true"

            print(f"\n📋 Configuration:")
            print(f"   Endpoint: {endpoint}")
            print(f"   Access Key: {access_key[:10]}... (hidden)" if access_key else "   Access Key: (not set)")
            print(f"   Secure: {secure}")

            if not endpoint or not access_key or not secret_key:
                self.print_test("MinIO", "Configuration", False,
                              "MINIO_ENDPOINT, MINIO_ACCESS_KEY, or MINIO_SECRET_KEY not set")
                result["error"] = "MinIO not configured"
                return result

            # Test 2: Connection
            print(f"\n🔌 Testing connection to {endpoint}...")

            try:
                client = Minio(
                    endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=secure
                )

                # Try to list buckets to verify connection
                buckets = list(client.list_buckets())
                result["connection"] = True
                self.print_test("MinIO", "Connection", True, f"Connected to {endpoint}")
                self.print_test("MinIO", "List Buckets", True, f"Found {len(buckets)} buckets")

            except Exception as e:
                self.print_test("MinIO", "Connection", False, f"Failed: {str(e)}")
                result["error"] = str(e)
                return result

            # Test 3: Check expected buckets
            expected_buckets = ["news", "policy", "researchpapers", "scientificdata", "reports"]

            print(f"\n📦 Checking buckets...")
            for bucket_name in expected_buckets:
                try:
                    exists = client.bucket_exists(bucket_name)
                    if exists:
                        # Try to list objects to verify access
                        objects = list(client.list_objects(bucket_name, max_keys=1))
                        result["buckets"][bucket_name] = {"exists": True, "accessible": True}
                        self.print_test("MinIO", f"Bucket '{bucket_name}'", True, "Exists and accessible")
                    else:
                        result["buckets"][bucket_name] = {"exists": False}
                        self.print_test("MinIO", f"Bucket '{bucket_name}'", False, "Does not exist")
                except Exception as e:
                    result["buckets"][bucket_name] = {"exists": True, "accessible": False, "error": str(e)}
                    self.print_test("MinIO", f"Bucket '{bucket_name}'", False, f"Access error: {str(e)}")

            # List all buckets
            print(f"\n📊 All Buckets:")
            for bucket in buckets:
                print(f"   • {bucket.name} (created: {bucket.creation_date})")

        except ImportError:
            self.print_test("MinIO", "Import minio", False, "minio package not installed")
            result["error"] = "minio not installed"
        except Exception as e:
            self.print_test("MinIO", "General", False, str(e))
            result["error"] = str(e)

        return result

    async def check_redis(self) -> Dict[str, Any]:
        """Test Redis connection."""
        self.print_header("REDIS CACHE")

        result = {
            "service": "Redis",
            "connection": False,
            "error": None
        }

        try:
            import redis

            # Test 1: Environment variables
            host = os.getenv("REDIS_HOST", "redis")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            password = os.getenv("REDIS_PASSWORD", "")

            print(f"\n📋 Configuration:")
            print(f"   Host: {host}")
            print(f"   Port: {port}")
            print(f"   DB: {db}")
            print(f"   Password: {'***' if password else '(not set)'}")

            # Test 2: Connection
            print(f"\n🔌 Testing connection to {host}:{port}...")

            try:
                client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password if password else None,
                    socket_connect_timeout=5,
                    decode_responses=True
                )

                # Test ping
                response = client.ping()
                if response:
                    result["connection"] = True
                    self.print_test("Redis", "Connection", True, f"Connected to {host}:{port}")

                    # Test set/get
                    test_key = "health_check_test"
                    test_value = "test_value"
                    client.setex(test_key, 10, test_value)
                    retrieved = client.get(test_key)

                    if retrieved == test_value:
                        self.print_test("Redis", "Read/Write", True, "Can read and write data")
                    else:
                        self.print_test("Redis", "Read/Write", False, "Data mismatch")

                    client.delete(test_key)

                    # Get info
                    info = client.info()
                    print(f"\n📊 Redis Info:")
                    print(f"   Version: {info.get('redis_version', 'unknown')}")
                    print(f"   Used Memory: {info.get('used_memory_human', 'unknown')}")
                    print(f"   Connected Clients: {info.get('connected_clients', 'unknown')}")

            except Exception as e:
                self.print_test("Redis", "Connection", False, f"Failed: {str(e)}")
                result["error"] = str(e)

        except ImportError:
            self.print_test("Redis", "Import redis", False, "redis package not installed")
            result["error"] = "redis not installed"
        except Exception as e:
            self.print_test("Redis", "General", False, str(e))
            result["error"] = str(e)

        return result

    async def check_ollama(self) -> Dict[str, Any]:
        """Test Ollama connection."""
        self.print_header("OLLAMA LLM SERVICE")

        result = {
            "service": "Ollama",
            "connection": False,
            "models": [],
            "error": None
        }

        try:
            import aiohttp

            # Test 1: Environment variables
            base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

            print(f"\n📋 Configuration:")
            print(f"   Base URL: {base_url}")

            # Test 2: Connection
            print(f"\n🔌 Testing connection to {base_url}...")

            try:
                async with aiohttp.ClientSession() as session:
                    # Test API endpoint
                    async with session.get(f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            models = data.get("models", [])
                            result["connection"] = True
                            result["models"] = [m["name"] for m in models]

                            self.print_test("Ollama", "Connection", True, f"Connected to {base_url}")
                            self.print_test("Ollama", "List Models", True, f"Found {len(models)} models")

                            print(f"\n📊 Available Models:")
                            for model in models:
                                print(f"   • {model['name']} (size: {model.get('size', 'unknown')})")
                        else:
                            self.print_test("Ollama", "Connection", False, f"HTTP {response.status}")
                            result["error"] = f"HTTP {response.status}"

            except asyncio.TimeoutError:
                self.print_test("Ollama", "Connection", False, "Connection timeout")
                result["error"] = "Connection timeout"
            except Exception as e:
                self.print_test("Ollama", "Connection", False, str(e))
                result["error"] = str(e)

        except ImportError:
            self.print_test("Ollama", "Import aiohttp", False, "aiohttp not installed")
            result["error"] = "aiohttp not installed"
        except Exception as e:
            self.print_test("Ollama", "General", False, str(e))
            result["error"] = str(e)

        return result

    async def check_graphrag_api(self) -> Dict[str, Any]:
        """Test GraphRAG API connection."""
        self.print_header("GRAPHRAG API SERVICE")

        result = {
            "service": "GraphRAG",
            "connection": False,
            "error": None
        }

        try:
            import aiohttp

            # Test 1: Environment variables
            api_url = os.getenv("GRAPHRAG_LOCAL_SEARCH_API_URL", "http://processor:8002/local-search")

            print(f"\n📋 Configuration:")
            print(f"   API URL: {api_url}")

            # Test 2: Connection
            print(f"\n🔌 Testing connection to {api_url}...")

            try:
                async with aiohttp.ClientSession() as session:
                    # Test with a simple query
                    test_payload = {
                        "query": "health check",
                        "context_depth": 1
                    }

                    async with session.post(
                        api_url,
                        json=test_payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            result["connection"] = True
                            self.print_test("GraphRAG", "Connection", True, f"API responding")

                            data = await response.json()
                            print(f"\n📊 API Response:")
                            print(f"   Status: {response.status}")
                            print(f"   Response received: {len(str(data))} bytes")
                        else:
                            self.print_test("GraphRAG", "Connection", False, f"HTTP {response.status}")
                            result["error"] = f"HTTP {response.status}"

            except asyncio.TimeoutError:
                self.print_test("GraphRAG", "Connection", False, "Connection timeout (may not be running)")
                result["error"] = "Connection timeout"
            except Exception as e:
                self.print_test("GraphRAG", "Connection", False, str(e))
                result["error"] = str(e)

        except ImportError:
            self.print_test("GraphRAG", "Import aiohttp", False, "aiohttp not installed")
            result["error"] = "aiohttp not installed"
        except Exception as e:
            self.print_test("GraphRAG", "General", False, str(e))
            result["error"] = str(e)

        return result

    async def check_openai(self) -> Dict[str, Any]:
        """Test OpenAI API connection."""
        self.print_header("OPENAI API")

        result = {
            "service": "OpenAI",
            "connection": False,
            "error": None
        }

        # Test 1: Environment variables
        api_key = os.getenv("OPENAI_API_KEY", "")
        trulens_api_key = os.getenv("TRULENS_OPENAI_API_KEY", "")

        print(f"\n📋 Configuration:")
        print(f"   Main API Key: {api_key[:10]}... (hidden)" if api_key else "   Main API Key: (not set)")
        print(f"   TruLens API Key: {trulens_api_key[:10]}... (hidden)" if trulens_api_key else "   TruLens API Key: (not set)")

        if not api_key and not trulens_api_key:
            self.print_test("OpenAI", "Configuration", False, "No OpenAI API keys configured (will use Ollama)")
            result["error"] = "Not configured (optional)"
            return result

        try:
            import openai

            # Test with main key if available
            if api_key:
                print(f"\n🔌 Testing main OpenAI API key...")
                try:
                    client = openai.OpenAI(api_key=api_key)
                    # Simple test - list models
                    models = client.models.list()
                    result["connection"] = True
                    self.print_test("OpenAI", "Main API Key", True, "Valid and working")
                except Exception as e:
                    self.print_test("OpenAI", "Main API Key", False, str(e))
                    result["error"] = str(e)

            # Test TruLens key if available
            if trulens_api_key:
                print(f"\n🔌 Testing TruLens OpenAI API key...")
                try:
                    client = openai.OpenAI(api_key=trulens_api_key)
                    models = client.models.list()
                    self.print_test("OpenAI", "TruLens API Key", True, "Valid and working")
                except Exception as e:
                    self.print_test("OpenAI", "TruLens API Key", False, str(e))

        except ImportError:
            self.print_test("OpenAI", "Import openai", False, "openai package not installed")
            result["error"] = "openai not installed"
        except Exception as e:
            self.print_test("OpenAI", "General", False, str(e))
            result["error"] = str(e)

        return result

    async def run_all_checks(self):
        """Run all health checks."""
        print("\n" + "=" * 80)
        print("  EXTERNAL SERVICES HEALTH CHECK")
        print("  Testing connectivity to all external services")
        print("=" * 80)

        start_time = time.time()

        # Run all checks
        results = {
            "milvus": await self.check_milvus(),
            "minio": await self.check_minio(),
            "redis": await self.check_redis(),
            "ollama": await self.check_ollama(),
            "graphrag": await self.check_graphrag_api(),
            "openai": await self.check_openai(),
        }

        elapsed = time.time() - start_time

        # Print summary
        self.print_header("SUMMARY")

        print(f"\n⏱️  Total Time: {elapsed:.2f}s\n")

        for service_name, result in results.items():
            if result.get("connection"):
                print(f"✅ {result['service']}: Connected")
            elif result.get("error") == "Not configured (optional)":
                print(f"⚪ {result['service']}: Not configured (optional)")
            else:
                print(f"❌ {result['service']}: {result.get('error', 'Failed')}")

        print("\n" + "=" * 80)
        if self.overall_status:
            print("  ✅ ALL CRITICAL SERVICES ARE WORKING")
        else:
            print("  ❌ SOME SERVICES HAVE ISSUES - SEE DETAILS ABOVE")
        print("=" * 80 + "\n")

        return results


async def main():
    """Main entry point."""
    checker = ServiceHealthChecker()
    results = await checker.run_all_checks()

    # Exit with error code if any critical service failed
    if not checker.overall_status:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Health check failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
