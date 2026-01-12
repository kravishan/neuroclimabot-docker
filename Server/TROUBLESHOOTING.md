# Troubleshooting Guide

## Common Issues and Solutions

This guide helps you fix common issues with TruLens evaluation and external services.

---

## Issue 1: TruLens Protobuf Error ❌

### Error Message:
```
Failed to import transformers.pipelines because of the following error:
cannot import name 'runtime_version' from 'google.protobuf'
```

### Root Cause:
TruLens depends on TensorFlow/Transformers which require protobuf 3.x, but a newer incompatible version (4.x+) is installed.

### Solution:

**Option A: Quick Fix (Recommended)**
```bash
cd Server
python scripts/fix_dependencies.py
```

**Option B: Manual Fix**
```bash
cd Server

# Uninstall current protobuf
pip uninstall protobuf -y

# Install compatible version
pip install protobuf==3.20.3

# Reinstall TruLens
pip install trulens-eval==0.33.0 --force-reinstall
```

**Verify the Fix:**
```bash
python -c "from trulens_eval.feedback.provider.openai import OpenAI; print('✅ TruLens working!')"
```

**Expected Output:**
```
✅ TruLens working!
```

---

## Issue 1b: gRPC Module Not Found ❌

### Error Message:
```
ModuleNotFoundError: No module named 'grpc'
```

This error occurs when importing pymilvus after downgrading protobuf.

### Root Cause:
The protobuf downgrade (required for TruLens) can break the gRPC installation that pymilvus depends on. gRPC and protobuf versions must be compatible.

### Solution:

**Option A: Quick Fix (Recommended)**
```bash
cd Server
python scripts/fix_dependencies.py
```

**Option B: Manual Fix**
```bash
cd Server

# Install compatible gRPC version
pip install grpcio==1.48.0 grpcio-tools==1.48.0 --force-reinstall

# Reinstall pymilvus if needed
pip install pymilvus==2.5.8 --force-reinstall
```

**Verify the Fix:**
```bash
python -c "from pymilvus import connections; print('✅ pymilvus working!')"
```

**Expected Output:**
```
✅ pymilvus working!
```

---

## Issue 2: Milvus Connection Error ❌

### Error Messages:
```
ConnectionNotExistException: (code=1, message=should create connection first.)
Parallel chunk searches timed out after 10s
```

### Root Causes:
1. Milvus service is not running
2. Wrong MILVUS_HOST or MILVUS_PORT in .env
3. Milvus requires authentication but credentials are missing
4. Firewall blocking connection

### Solution:

**Step 1: Check if Milvus is Running**

```bash
# For Docker:
docker ps | grep milvus

# For standalone:
curl http://localhost:19530/healthz
```

**Expected:** HTTP 200 response or running container

**Step 2: Verify .env Configuration**

Open `Server/.env` and check:

```bash
MILVUS_HOST=localhost        # or IP address of Milvus server
MILVUS_PORT=19530           # default Milvus port
MILVUS_USER=                # username (if authentication enabled)
MILVUS_PASSWORD=            # password (if authentication enabled)
```

**For Docker Compose:**
```bash
MILVUS_HOST=milvus-standalone   # service name in docker-compose.yml
MILVUS_PORT=19530
```

**For Remote Milvus:**
```bash
MILVUS_HOST=192.168.1.100   # actual IP
MILVUS_PORT=19530
MILVUS_USER=your_username
MILVUS_PASSWORD=your_password
```

**Step 3: Test Connection**

```bash
python tests/test_external_services.py
```

Look for:
```
[MILVUS] ✅ Connection successful
[MILVUS] ✅ Found collections: mvp_latest_chunks, mvp_latest_summaries
```

**Step 4: Start Milvus if Not Running**

```bash
# Using Docker Compose (recommended):
docker-compose up -d milvus-standalone

# Or download standalone:
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

**Step 5: Check Milvus Logs**

```bash
# Docker logs:
docker logs milvus-standalone

# Look for startup messages:
# "Milvus Proxy successfully started"
```

---

## Issue 3: MinIO Connection Error ❌

### Error Messages:
```
'NoneType' object has no attribute 'bucket_exists'
Failed to generate shareable URL for [...].pdf
```

### Root Causes:
1. MinIO service is not running
2. Wrong MINIO_ENDPOINT in .env
3. Invalid MINIO_ACCESS_KEY or MINIO_SECRET_KEY
4. MinIO client not initialized properly

### Solution:

**Step 1: Check if MinIO is Running**

```bash
# For Docker:
docker ps | grep minio

# For standalone:
curl http://localhost:9000/minio/health/live
```

**Expected:** HTTP 200 response or running container

**Step 2: Verify .env Configuration**

Open `Server/.env` and check:

```bash
MINIO_ENDPOINT=localhost:9000           # MinIO server endpoint
MINIO_ACCESS_KEY=minioadmin            # Access key
MINIO_SECRET_KEY=minioadmin            # Secret key
MINIO_SECURE=false                     # Use HTTPS? (true/false)
MINIO_BUCKET_NAME=data                 # Default bucket name
```

**For Docker Compose:**
```bash
MINIO_ENDPOINT=minio:9000              # service name in docker-compose.yml
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
```

**For Remote MinIO:**
```bash
MINIO_ENDPOINT=192.168.1.100:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_SECURE=true                      # if using HTTPS
```

**Step 3: Test Connection**

```bash
python tests/test_external_services.py
```

Look for:
```
[MINIO] ✅ Connection successful
[MINIO] ✅ Bucket 'data' exists
```

**Step 4: Start MinIO if Not Running**

```bash
# Using Docker:
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Access MinIO Console:
# http://localhost:9001
# Login: minioadmin / minioadmin
```

**Step 5: Create Required Buckets**

```bash
# Option 1: Via MinIO Console (http://localhost:9001)
# Create buckets: news, policy, researchpapers, scientificdata

# Option 2: Via mc (MinIO Client)
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc mb myminio/news
mc mb myminio/policy
mc mb myminio/researchpapers
mc mb myminio/scientificdata
```

---

## Issue 4: Redis Connection Error ❌

### Error Messages:
```
Failed to connect to Redis
Connection refused on localhost:6379
```

### Solution:

**Step 1: Check if Redis is Running**

```bash
# For Docker:
docker ps | grep redis

# For standalone:
redis-cli ping
```

**Expected:** `PONG` response

**Step 2: Verify .env Configuration**

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=            # if authentication enabled
REDIS_DB=0
```

**Step 3: Start Redis if Not Running**

```bash
# Using Docker:
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Using system package:
sudo systemctl start redis
```

---

## Issue 5: Ollama Not Available ❌

### Error Messages:
```
Failed to connect to Ollama API
Connection refused on localhost:11434
```

### Solution:

**Step 1: Check if Ollama is Running**

```bash
curl http://localhost:11434/api/tags
```

**Expected:** JSON response with model list

**Step 2: Verify .env Configuration**

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mixtral:latest
```

**Step 3: Start Ollama**

**For Linux:**
```bash
# Install Ollama:
curl -fsSL https://ollama.com/install.sh | sh

# Start service:
systemctl start ollama

# Pull required model:
ollama pull mixtral
```

**For Windows:**
```bash
# Download from: https://ollama.com/download/windows
# Install and run Ollama Desktop
# Open terminal:
ollama pull mixtral
```

---

## Issue 6: GraphRAG API Not Available ❌

### Error Messages:
```
Failed to connect to GraphRAG API
Connection refused
```

### Solution:

**Step 1: Verify .env Configuration**

```bash
GRAPHRAG_LOCAL_SEARCH_API_URL=http://localhost:8001/api/local-search
GRAPHRAG_GLOBAL_SEARCH_API_URL=http://localhost:8001/api/global-search
```

**Step 2: Check GraphRAG Service**

```bash
curl http://localhost:8001/health
```

**Step 3: Start GraphRAG Service**

```bash
# If using Docker Compose:
docker-compose up -d graphrag

# Check logs:
docker-compose logs graphrag
```

---

## Issue 7: TruLens Evaluation Disabled 📊

### Symptoms:
- No `evaluation` or `quality_flags` in API response
- Logs show: "RAG evaluation disabled"

### Solution:

**Step 1: Check .env File**

```bash
# Must be exactly 'true' (lowercase)
TRULENS_ENABLED=true
```

**Step 2: Check Evaluation Flags in constants.py**

Edit `Server/app/constants.py`:

```python
# At least ONE must be True:
TRULENS_EVAL_CONTEXT_RELEVANCE = True
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = True
```

**Step 3: Restart Application**

```bash
# Stop the app (Ctrl+C)
# Restart:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Step 4: Verify in Logs**

Look for:
```
✅ RAG evaluator initialized with TruLens (TRULENS_ENABLED=true)
✅ TruLens using dedicated OpenAI provider (model: gpt-4, endpoint: https://api.openai.com/v1)
```

---

## Full System Health Check 🔍

Run the comprehensive health check script:

```bash
cd Server
python tests/test_external_services.py
```

This checks:
- ✅ Milvus connection and collections
- ✅ MinIO connection and buckets
- ✅ Redis connection
- ✅ Ollama API and models
- ✅ GraphRAG API
- ✅ OpenAI API (if configured)
- ✅ TruLens initialization

**Expected Output:**

```
=============================================================
External Services Health Check
=============================================================

[MILVUS] ✅ Connection successful (localhost:19530)
[MILVUS] ✅ Collection 'mvp_latest_chunks' (45123 entities)
[MILVUS] ✅ Collection 'mvp_latest_summaries' (3421 entities)

[MINIO] ✅ Connection successful (localhost:9000)
[MINIO] ✅ Bucket 'news' exists
[MINIO] ✅ Bucket 'policy' exists

[REDIS] ✅ Connection successful (localhost:6379)
[REDIS] ✅ Read/write test passed

[OLLAMA] ✅ API available (http://localhost:11434)
[OLLAMA] ✅ Model 'mixtral:latest' available

[GRAPHRAG] ✅ API available (http://localhost:8001)

[OPENAI] ✅ API key configured

[TRULENS] ✅ Initialized successfully

=============================================================
✅ All services healthy!
=============================================================
```

---

## Quick Fix Script 🛠️

Run the automated fix script:

```bash
cd Server
python scripts/fix_dependencies.py
```

This script:
1. ✅ Fixes protobuf compatibility
2. ✅ Reinstalls TruLens
3. ✅ Verifies imports
4. ✅ Checks .env configuration
5. ✅ Provides next steps

---

## Common .env Configuration Template

Copy this template to your `.env` file and adjust values:

```bash
# =============================================================================
# External Services Configuration
# =============================================================================

# Milvus Vector Database
MILVUS_HOST=localhost                    # or milvus-standalone (Docker)
MILVUS_PORT=19530
MILVUS_USER=                            # optional
MILVUS_PASSWORD=                        # optional

# MinIO Object Storage
MINIO_ENDPOINT=localhost:9000           # or minio:9000 (Docker)
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# Redis Cache
REDIS_HOST=localhost                    # or redis (Docker)
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Ollama LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mixtral:latest

# GraphRAG API
GRAPHRAG_LOCAL_SEARCH_API_URL=http://localhost:8001/api/local-search
GRAPHRAG_GLOBAL_SEARCH_API_URL=http://localhost:8001/api/global-search

# =============================================================================
# TruLens RAG Evaluation
# =============================================================================

TRULENS_ENABLED=true
TRULENS_DB_PATH=./data/trulens_evaluations.db
TRULENS_GROUNDEDNESS_THRESHOLD=0.7

# TruLens OpenAI Configuration (Dedicated for Evaluation Only)
TRULENS_OPENAI_API_KEY=sk-your-key-here  # or leave empty for Ollama
TRULENS_OPENAI_MODEL=gpt-4
TRULENS_OPENAI_BASE_URL=https://api.openai.com/v1
TRULENS_OPENAI_ORGANIZATION=

# =============================================================================
# Main Application OpenAI (Separate from TruLens)
# =============================================================================

OPENAI_API_KEY=sk-your-main-app-key-here
OPENAI_MODEL=gpt-4
```

---

## Step-by-Step Startup Guide 🚀

### 1. Start External Services

```bash
# Start Milvus
docker-compose up -d milvus-standalone

# Start MinIO
docker-compose up -d minio

# Start Redis
docker-compose up -d redis

# Start Ollama (if using Docker)
docker-compose up -d ollama
# OR use Ollama Desktop on Windows

# Start GraphRAG
docker-compose up -d graphrag
```

### 2. Fix Dependencies

```bash
cd Server
python scripts/fix_dependencies.py
```

### 3. Verify Services

```bash
python tests/test_external_services.py
```

### 4. Test TruLens

```bash
python tests/test_trulens_integration.py
```

### 5. Start Application

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Test RAG Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are social tipping points?",
    "language": "en",
    "session_id": "test-001"
  }'
```

### 7. Launch TruLens Dashboard (Optional)

```bash
python scripts/launch_trulens_dashboard.py
# Open browser: http://localhost:8501
```

---

## Need More Help?

- **TruLens Setup**: See `Server/app/services/evaluation/QUICKSTART.md`
- **Running Guide**: See `Server/app/services/evaluation/RUNNING_GUIDE.md`
- **Evaluation Flags**: See `Server/app/services/evaluation/EVALUATION_FLAGS.md`
- **Integration**: See `Server/app/services/evaluation/INTEGRATION_GUIDE.md`

---

## Contact & Support

If issues persist:
1. Check application logs for detailed error messages
2. Verify all external services are running (`docker ps`)
3. Test each service individually with health check script
4. Check firewall settings (ports 8000, 9000, 19530, 6379, 11434)
5. Review .env configuration against template above

**Happy troubleshooting!** 🎯
