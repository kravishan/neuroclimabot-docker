# FastAPI Async Semaphore Implementation

## Overview

This document describes the async semaphore implementation added to the NeuroClima backend to control concurrent resource usage and prevent system overload.

## What Are Semaphores?

An async semaphore is a concurrency control mechanism that limits the number of concurrent operations. Think of it as a "ticket system" - only N operations can run simultaneously, and others must wait for a ticket to become available.

## Why Add Semaphores?

### Benefits

1. **Resource Protection**
   - Prevents overwhelming external APIs (OpenAI, Translation, GraphRAG, STP)
   - Controls database load (Milvus vector searches)
   - Manages memory usage during traffic bursts

2. **Cost Control**
   - Limits concurrent LLM API calls to control costs
   - Prevents rate limit violations and associated penalties

3. **Predictable Performance**
   - Controlled queue depth = more predictable latencies
   - Prevents "thundering herd" problems
   - Better user experience under load

4. **Better Error Handling**
   - Controlled failure vs cascading failures
   - Graceful degradation during high load

### Drawbacks

1. **Added Complexity**
   - More code to maintain
   - Requires configuration tuning

2. **Request Queuing**
   - Increased latency for queued requests
   - Requests wait for semaphore availability

3. **Not a Silver Bullet**
   - Doesn't replace proper caching, rate limiting, or load balancing
   - Doesn't solve underlying performance issues

## Implementation Details

### Configuration

All semaphore limits are configurable via environment variables in `.env`:

```bash
# Async Semaphore Limits
MAX_CONCURRENT_CHAT_REQUESTS=10
MAX_CONCURRENT_LLM_CALLS=5
MAX_CONCURRENT_MILVUS_QUERIES=10
MAX_CONCURRENT_TRANSLATION_CALLS=10
MAX_CONCURRENT_GRAPHRAG_CALLS=8
MAX_CONCURRENT_STP_CALLS=8
SEMAPHORE_ACQUISITION_TIMEOUT=30.0
```

Configuration location: `Server/app/config/features.py`

### Semaphore Manager

A centralized `SemaphoreManager` class manages all semaphores:

**Location:** `Server/app/core/dependencies.py`

**Semaphores:**
- `chat_semaphore` - Limits concurrent chat request processing
- `llm_semaphore` - Limits concurrent LLM API calls
- `milvus_semaphore` - Limits concurrent vector database queries
- `translation_semaphore` - Limits concurrent translation API calls
- `graphrag_semaphore` - Limits concurrent GraphRAG API calls
- `stp_semaphore` - Limits concurrent STP API calls

**Singleton Pattern:** One instance shared across the entire application.

### Where Semaphores Are Applied

#### 1. Chat Request Processing
**Files:**
- `Server/app/api/v1/helpers/translation.py`

**Functions:**
- `process_with_translation()`
- `process_with_translation_and_tracing()`

**Limit:** `MAX_CONCURRENT_CHAT_REQUESTS` (default: 10)

**Why:** Chat requests are expensive (translation → RAG → LLM → translation) and can take 25-45 seconds. Limiting concurrent requests prevents memory/CPU overload.

#### 2. LLM API Calls
**Files:**
- `Server/app/services/llm/openai.py`
- `Server/app/services/llm/mixtral.py`

**Methods:**
- `OpenAILLM._acall()`
- `MixtralLLM._acall()`

**Limit:** `MAX_CONCURRENT_LLM_CALLS` (default: 5)

**Why:** Prevents overwhelming LLM APIs, controls costs, and avoids rate limits.

#### 3. Milvus Vector Database Queries
**Files:**
- `Server/app/services/external/milvus.py`

**Methods:**
- `MilvusClient.search_chunks()`
- `MilvusClient.search_all_summaries()`

**Limit:** `MAX_CONCURRENT_MILVUS_QUERIES` (default: 10)

**Why:** Prevents overloading the vector database with too many simultaneous searches.

#### 4. Translation API Calls
**Files:**
- `Server/app/services/external/translation_client.py`

**Methods:**
- `TranslationClient._translate_in_request()`
- `TranslationClient._translate_out_request()`

**Limit:** `MAX_CONCURRENT_TRANSLATION_CALLS` (default: 10)

**Why:** Respects translation service rate limits and prevents overload.

#### 5. GraphRAG API Calls
**Files:**
- `Server/app/services/external/graphrag_api_client.py`

**Methods:**
- `GraphRAGAPIClient.local_search()`

**Limit:** `MAX_CONCURRENT_GRAPHRAG_CALLS` (default: 8)

**Why:** Controls load on the GraphRAG service and manages memory usage.

#### 6. Social Tipping Point (STP) API Calls
**Files:**
- `Server/app/services/external/stp_client.py`

**Methods:**
- `STPClient._make_stp_request()`

**Limit:** `MAX_CONCURRENT_STP_CALLS` (default: 8)

**Why:** Respects STP service rate limits and prevents overload.

## Usage Patterns

### Basic Pattern

```python
from app.core.dependencies import get_semaphore_manager

async def my_operation():
    semaphore_manager = get_semaphore_manager()

    async with semaphore_manager.llm_semaphore:
        # Only N concurrent operations reach here
        result = await call_llm_api()
        return result
```

### With Timeout Protection

The `SemaphoreManager` includes built-in timeout protection via `SEMAPHORE_ACQUISITION_TIMEOUT` to prevent indefinite waiting.

### Logging

All semaphore operations are logged:
- 🔒 = Waiting for semaphore
- ✅ = Semaphore acquired
- 🔓 = Semaphore released

## Monitoring

Monitor these metrics to tune semaphore limits:

1. **Request Queue Times**
   - Look for "Waiting for semaphore" log entries
   - High wait times indicate limits may be too low

2. **System Resource Usage**
   - Memory usage
   - CPU usage
   - Database connections

3. **Error Rates**
   - Timeout errors
   - Rate limit errors from external APIs

4. **Response Times**
   - Average response time
   - P95/P99 latency

## Tuning Guidelines

### Increase Limits When:
- Queue wait times are consistently high (>5 seconds)
- System resources are underutilized
- Response times are acceptable under current load
- No rate limit errors from external APIs

### Decrease Limits When:
- System memory/CPU consistently maxed out
- Getting rate limit errors from external APIs
- Database connection pool exhausted
- Costs are too high (for LLM calls)

### Recommended Starting Points:

**Small deployment (1-50 concurrent users):**
```bash
MAX_CONCURRENT_CHAT_REQUESTS=10
MAX_CONCURRENT_LLM_CALLS=5
MAX_CONCURRENT_MILVUS_QUERIES=10
```

**Medium deployment (50-200 concurrent users):**
```bash
MAX_CONCURRENT_CHAT_REQUESTS=20
MAX_CONCURRENT_LLM_CALLS=10
MAX_CONCURRENT_MILVUS_QUERIES=20
```

**Large deployment (200+ concurrent users):**
```bash
MAX_CONCURRENT_CHAT_REQUESTS=50
MAX_CONCURRENT_LLM_CALLS=20
MAX_CONCURRENT_MILVUS_QUERIES=30
```

## Testing

### Unit Testing

Test individual semaphore-protected operations:

```python
import asyncio
import pytest
from app.core.dependencies import get_semaphore_manager

@pytest.mark.asyncio
async def test_semaphore_limits():
    manager = get_semaphore_manager()

    # Verify semaphore limits
    assert manager.chat_semaphore._value == 10

    # Test concurrent acquisition
    async def acquire_and_hold():
        async with manager.chat_semaphore:
            await asyncio.sleep(0.1)

    # Start more tasks than semaphore allows
    tasks = [acquire_and_hold() for _ in range(20)]
    await asyncio.gather(*tasks)

    # All should complete successfully
    assert True
```

### Load Testing

Use tools like `locust` or `k6` to test under load:

```python
# locustfile.py
from locust import HttpUser, task, between

class ChatUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def start_chat(self):
        self.client.post("/api/v1/chat/start", json={
            "message": "What is climate change?",
            "language": "en"
        })
```

Run: `locust -f locustfile.py --users 100 --spawn-rate 10`

## Troubleshooting

### Problem: High queue wait times

**Symptoms:** Logs show many "Waiting for semaphore" messages with long waits.

**Solutions:**
1. Increase semaphore limit for that resource
2. Optimize the underlying operation (caching, etc.)
3. Add horizontal scaling

### Problem: System overload despite semaphores

**Symptoms:** High CPU/memory usage, slow responses.

**Solutions:**
1. Decrease semaphore limits
2. Review resource-intensive operations
3. Add caching
4. Scale horizontally

### Problem: TimeoutError acquiring semaphore

**Symptoms:** Users see "System is currently overloaded" errors.

**Solutions:**
1. Increase `SEMAPHORE_ACQUISITION_TIMEOUT`
2. Increase semaphore limits
3. Add more servers
4. Implement request queuing with proper backpressure

## Related Concepts

### Semaphores vs Rate Limiting

- **Rate Limiting:** "10 requests per minute per user"
- **Semaphores:** "Max 5 concurrent operations total"

Both are useful! Rate limiting protects against abuse per user. Semaphores protect system resources globally.

### Semaphores vs Load Balancing

Semaphores control concurrency on a single instance. Load balancing distributes requests across multiple instances. Use both together for best results.

### Semaphores vs Caching

Semaphores limit concurrent execution. Caching avoids execution entirely. Implement caching first, then use semaphores for non-cacheable operations.

## Future Improvements

1. **Dynamic Semaphore Adjustment**
   - Automatically adjust limits based on system metrics
   - Increase during low load, decrease during high load

2. **Per-User Semaphores**
   - Prevent single user from consuming all resources
   - Fair queueing across users

3. **Priority Queues**
   - Premium users get priority
   - Critical operations bypass queues

4. **Circuit Breakers**
   - Temporarily disable services when error rates spike
   - Automatic recovery when service stabilizes

5. **Distributed Semaphores**
   - Share semaphore limits across multiple instances
   - Use Redis or similar for coordination

## References

- Python asyncio Semaphores: https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore
- FastAPI Concurrency: https://fastapi.tiangolo.com/async/
- The Little Book of Semaphores: https://greenteapress.com/semaphores/

## Contact

For questions or issues related to this implementation, please refer to the project documentation or contact the development team.
