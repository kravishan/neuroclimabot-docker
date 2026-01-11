# TruLens Quick Start Guide

## 🚀 Enable/Disable TruLens Evaluation

TruLens evaluation is controlled by environment variables in your `.env` file.

---

## ⚡ Quick Setup

### Step 1: Configure `.env` File

Add these settings to your `Server/.env` file:

```bash
# =============================================================================
# TruLens RAG Evaluation
# =============================================================================

# Enable TruLens evaluation
TRULENS_ENABLED=true

# Database path for storing evaluation results
TRULENS_DB_PATH=./data/trulens_evaluations.db

# Groundedness threshold (scores below this trigger hallucination warnings)
TRULENS_GROUNDEDNESS_THRESHOLD=0.7

# -----------------------------------------------------------------------------
# TruLens OpenAI Configuration (Dedicated for Evaluation Only)
# -----------------------------------------------------------------------------
# IMPORTANT: These settings are ONLY used for TruLens evaluation
# They are separate from your main application's OpenAI configuration

# OpenAI API key for TruLens (leave empty to use Ollama/Mixtral)
TRULENS_OPENAI_API_KEY=sk-your-trulens-api-key-here

# OpenAI model for evaluation
TRULENS_OPENAI_MODEL=gpt-4

# OpenAI API endpoint (use custom for Azure OpenAI)
TRULENS_OPENAI_BASE_URL=https://api.openai.com/v1

# Organization ID (optional)
TRULENS_OPENAI_ORGANIZATION=
```

**Note:** If you don't provide `TRULENS_OPENAI_API_KEY`, TruLens will automatically use Ollama/Mixtral (free, local).

### Step 2: Install Dependencies

```bash
cd Server
pip install -r requirements.txt
```

This installs `trulens-eval==0.33.0`.

### Step 3: Test It Works

```bash
cd Server
python tests/test_trulens_integration.py
```

**Expected Output (when TRULENS_ENABLED=true):**
```
✅ RAG evaluator initialized with TruLens (TRULENS_ENABLED=true)

📊 TruLens Evaluation Scores:
   • Context Relevance:  0.850 ✅
   • Groundedness:       0.920 ✅
   • Answer Relevance:   0.880 ✅
   • Overall Score:      0.883 ✅
```

**Expected Output (when TRULENS_ENABLED=false):**
```
RAG evaluation disabled (TRULENS_ENABLED=false in .env)
❌ No evaluation data found in response
```

---

## 🎛️ Enable TruLens

### Method 1: Environment Variable (Recommended)

Edit `Server/.env`:

```bash
TRULENS_ENABLED=true
```

Restart your application. TruLens will automatically:
- Initialize on first RAG query
- Evaluate every response
- Track metrics
- Log hallucination warnings

### Method 2: Programmatic Control

You can also enable/disable programmatically:

```python
from app.services.evaluation.rag_evaluator import get_rag_evaluator

# Force enable (overrides .env setting)
evaluator = await get_rag_evaluator(enabled=True)

# Force disable (overrides .env setting)
evaluator = await get_rag_evaluator(enabled=False)

# Use .env setting (default behavior)
evaluator = await get_rag_evaluator()  # Uses TRULENS_ENABLED from .env
```

---

## 🛑 Disable TruLens

### Method 1: Environment Variable (Recommended)

Edit `Server/.env`:

```bash
TRULENS_ENABLED=false
```

Restart your application. TruLens will be completely disabled:
- No initialization overhead
- No evaluation calls
- No performance impact
- Your RAG still works normally

### Method 2: Programmatic Control

```python
from app.services.evaluation.rag_evaluator import get_rag_evaluator

# Disable evaluation
evaluator = await get_rag_evaluator(enabled=False)
```

---

## 📊 What Gets Evaluated (When Enabled)

When `TRULENS_ENABLED=true`, every RAG response is evaluated with:

### 1️⃣ Context Relevance (0-1)
- **What:** Are retrieved documents relevant to the query?
- **Evaluates:** Your Milvus + GraphRAG retrieval quality
- **Low score means:** Poor retrieval, irrelevant documents

### 2️⃣ Groundedness (0-1) - Hallucination Detection
- **What:** Is the answer supported by retrieved context?
- **Evaluates:** Whether LLM made up information
- **Low score means:** Potential hallucination
- **Threshold:** Scores < 0.7 trigger warnings

### 3️⃣ Answer Relevance (0-1)
- **What:** Does the answer address the user's question?
- **Evaluates:** End-to-end response quality
- **Low score means:** Answer is off-topic

### Response Format

```python
{
    "content": "Generated answer...",

    # NEW: Evaluation scores (only when TRULENS_ENABLED=true)
    "evaluation": {
        "context_relevance": 0.85,
        "groundedness": 0.92,
        "answer_relevance": 0.88,
        "overall_score": 0.88,
        "milvus_context_relevance": 0.87,
        "graphrag_context_relevance": 0.82,
        "evaluation_time_ms": 1250
    },

    # NEW: Quality flags (only when TRULENS_ENABLED=true)
    "quality_flags": {
        "excellent_response": true,
        "potential_hallucination": false,
        "high_quality": true
    }
}
```

---

## 🎯 Use Cases

### Development & Testing
```bash
# Enable for testing
TRULENS_ENABLED=true
```
- Catch hallucinations early
- Tune retrieval parameters
- Compare prompt variations

### Production - Full Monitoring
```bash
# Enable for comprehensive quality monitoring
TRULENS_ENABLED=true
```
- Real-time quality tracking
- Hallucination detection
- Quality degradation alerts

### Production - Performance Optimized
```bash
# Disable to reduce latency
TRULENS_ENABLED=false
```
- No evaluation overhead (~1-2s saved per query)
- Maximum throughput
- Rely on user feedback instead

### Production - Sampled Evaluation
```bash
# Enable, but sample queries in code
TRULENS_ENABLED=true
```

In your code:
```python
import random

# Evaluate only 10% of queries
if random.random() < 0.1:
    evaluator = await get_rag_evaluator(enabled=True)
else:
    evaluator = await get_rag_evaluator(enabled=False)
```

---

## ⚙️ Configuration Options

### TRULENS_ENABLED
**Type:** Boolean
**Default:** `false`
**Description:** Master switch for TruLens evaluation

```bash
TRULENS_ENABLED=true   # Enable evaluation
TRULENS_ENABLED=false  # Disable evaluation (default)
```

### TRULENS_DB_PATH
**Type:** String
**Default:** `./data/trulens_evaluations.db`
**Description:** SQLite database path for storing evaluation history

```bash
TRULENS_DB_PATH=./data/trulens_evaluations.db
```

**Note:** Create the directory if it doesn't exist:
```bash
mkdir -p ./data
```

### TRULENS_EVALUATION_MODEL
**Type:** String
**Default:** `gpt-4`
**Options:** `gpt-4`, `gpt-3.5-turbo`, `ollama`
**Description:** LLM model used for evaluation

```bash
# Use GPT-4 (most accurate, requires OpenAI API key)
TRULENS_EVALUATION_MODEL=gpt-4

# Use GPT-3.5 (faster, cheaper)
TRULENS_EVALUATION_MODEL=gpt-3.5-turbo

# Use local Ollama/Mixtral (free, no API key needed)
TRULENS_EVALUATION_MODEL=ollama
```

**Note:** If OpenAI API key is not found, automatically falls back to Ollama.

### TRULENS_GROUNDEDNESS_THRESHOLD
**Type:** Float (0.0 - 1.0)
**Default:** `0.7`
**Description:** Threshold for hallucination warnings

```bash
# Strict (more warnings)
TRULENS_GROUNDEDNESS_THRESHOLD=0.8

# Default
TRULENS_GROUNDEDNESS_THRESHOLD=0.7

# Lenient (fewer warnings)
TRULENS_GROUNDEDNESS_THRESHOLD=0.6
```

**When score < threshold:**
```
⚠️ Low groundedness detected: 0.65 (threshold: 0.7, potential hallucination)
```

### TRULENS_OPENAI_API_KEY
**Type:** String
**Default:** `` (empty - uses Ollama)
**Description:** Dedicated OpenAI API key for TruLens evaluation only

```bash
# Use OpenAI for evaluation
TRULENS_OPENAI_API_KEY=sk-your-trulens-specific-key

# Leave empty to use Ollama/Mixtral (free, local)
TRULENS_OPENAI_API_KEY=
```

**IMPORTANT:** This is completely separate from your main application's `OPENAI_API_KEY`.
You can use different API keys for different purposes:
- Main app uses one OpenAI account
- TruLens uses a different OpenAI account (or Ollama)

### TRULENS_OPENAI_MODEL
**Type:** String
**Default:** `gpt-4`
**Options:** `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, `gpt-3.5-turbo-16k`
**Description:** OpenAI model for TruLens evaluation

```bash
# Most accurate (recommended)
TRULENS_OPENAI_MODEL=gpt-4

# Faster, cheaper alternative
TRULENS_OPENAI_MODEL=gpt-3.5-turbo

# High capacity for long contexts
TRULENS_OPENAI_MODEL=gpt-3.5-turbo-16k
```

**Cost Comparison:**
- `gpt-4`: $0.03/1K input tokens, $0.06/1K output tokens
- `gpt-3.5-turbo`: $0.001/1K input tokens, $0.002/1K output tokens (20x cheaper)

### TRULENS_OPENAI_BASE_URL
**Type:** String
**Default:** `https://api.openai.com/v1`
**Description:** OpenAI API endpoint (for custom endpoints like Azure OpenAI)

```bash
# Standard OpenAI API (default)
TRULENS_OPENAI_BASE_URL=https://api.openai.com/v1

# Azure OpenAI example
TRULENS_OPENAI_BASE_URL=https://your-resource.openai.azure.com/

# Custom proxy or gateway
TRULENS_OPENAI_BASE_URL=https://your-proxy.com/v1
```

**Use Cases:**
- **Azure OpenAI**: Enterprise deployments with Azure
- **Proxy/Gateway**: Route through your own infrastructure
- **Regional endpoints**: Use region-specific OpenAI endpoints

### TRULENS_OPENAI_ORGANIZATION
**Type:** String
**Default:** `` (empty)
**Description:** OpenAI organization ID (optional)

```bash
# If you have multiple organizations
TRULENS_OPENAI_ORGANIZATION=org-your-org-id

# Leave empty if not needed
TRULENS_OPENAI_ORGANIZATION=
```

**Note:** Only needed if your API key has access to multiple organizations.

---

## 🎯 OpenAI Configuration Examples

### Example 1: Dedicated OpenAI Account for TruLens

```bash
# Main app uses primary OpenAI account
OPENAI_API_KEY=sk-main-app-key-xxxx

# TruLens uses separate account (different billing)
TRULENS_OPENAI_API_KEY=sk-trulens-key-yyyy
TRULENS_OPENAI_MODEL=gpt-4
TRULENS_OPENAI_BASE_URL=https://api.openai.com/v1
```

**Why?**
- Separate billing/quota for evaluation
- Track evaluation costs independently
- Different rate limits

### Example 2: Azure OpenAI for TruLens

```bash
# Use Azure OpenAI for evaluation
TRULENS_OPENAI_API_KEY=your-azure-key
TRULENS_OPENAI_MODEL=gpt-4
TRULENS_OPENAI_BASE_URL=https://your-resource.openai.azure.com/
```

**Benefits:**
- Enterprise security and compliance
- Data residency requirements
- Private network access

### Example 3: Cost Optimization (GPT-3.5)

```bash
# Use cheaper GPT-3.5 for evaluation
TRULENS_OPENAI_API_KEY=sk-your-key
TRULENS_OPENAI_MODEL=gpt-3.5-turbo
TRULENS_OPENAI_BASE_URL=https://api.openai.com/v1
```

**Savings:**
- 20x cheaper than GPT-4
- Still accurate for most evaluations
- Faster response times

### Example 4: Free Local Evaluation (Ollama)

```bash
# Don't set API key - uses Ollama/Mixtral
TRULENS_OPENAI_API_KEY=
```

**Benefits:**
- Zero API costs
- Complete privacy (no data sent externally)
- No rate limits

---

## 📈 View Results

### Method 1: Check Response JSON

```python
result = await rag_service.query("What are social tipping points?")

if "evaluation" in result:
    print(f"Context Relevance: {result['evaluation']['context_relevance']}")
    print(f"Groundedness: {result['evaluation']['groundedness']}")
    print(f"Answer Relevance: {result['evaluation']['answer_relevance']}")
else:
    print("Evaluation disabled")
```

### Method 2: Launch Dashboard

```bash
python scripts/launch_trulens_dashboard.py
```

Open browser: **http://localhost:8501**

Dashboard shows:
- Real-time scores
- Trend over time
- Hallucination alerts
- Query drill-down

### Method 3: Check Statistics

```python
from app.services.evaluation.rag_evaluator import get_rag_evaluator

evaluator = await get_rag_evaluator()
stats = evaluator.get_statistics()

print(f"Total Evaluations: {stats['total_evaluations']}")
print(f"Avg Groundedness: {stats['avg_groundedness']:.3f}")
print(f"Hallucination Rate: {stats['hallucination_rate']:.2%}")
```

---

## 🔍 Troubleshooting

### Issue: "TruLens not installed"

**Error:**
```
ImportError: No module named 'trulens_eval'
```

**Solution:**
```bash
cd Server
pip install trulens-eval==0.33.0
# or
pip install -r requirements.txt
```

### Issue: "Evaluation disabled" message

**Symptom:**
```
RAG evaluation disabled (TRULENS_ENABLED=false in .env)
```

**Solution:**
Check your `.env` file:
```bash
# Make sure it says true, not false
TRULENS_ENABLED=true
```

### Issue: No evaluation scores in response

**Check:**
1. Is `TRULENS_ENABLED=true` in `.env`?
2. Did you restart the application after changing `.env`?
3. Check logs for initialization message:
   ```
   ✅ RAG evaluator initialized with TruLens (TRULENS_ENABLED=true)
   ```

### Issue: "OpenAI API key not found"

**Symptom:**
TruLens tries to use OpenAI but API key is missing.

**Solution:**
Either:
1. Add OpenAI API key to `.env`:
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

2. Or use Ollama (automatic fallback):
   ```bash
   TRULENS_EVALUATION_MODEL=ollama
   ```

### Issue: Slow evaluation

**Symptom:**
Each query takes 2+ seconds longer with TruLens enabled.

**Solutions:**

1. **Disable in production:**
   ```bash
   TRULENS_ENABLED=false
   ```

2. **Sample queries:**
   ```python
   import random
   if random.random() < 0.1:  # Evaluate 10%
       evaluator = await get_rag_evaluator(enabled=True)
   ```

3. **Use faster model:**
   ```bash
   TRULENS_EVALUATION_MODEL=gpt-3.5-turbo
   ```

---

## 📚 Next Steps

1. ✅ Set `TRULENS_ENABLED=true` in `.env`
2. ✅ Run test: `python tests/test_trulens_integration.py`
3. ✅ Launch dashboard: `python scripts/launch_trulens_dashboard.py`
4. ✅ Integrate with RAG: See [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
5. ✅ Monitor quality: Check dashboard for trends

---

## 💡 Key Takeaways

- **Enable:** `TRULENS_ENABLED=true` in `.env`
- **Disable:** `TRULENS_ENABLED=false` in `.env`
- **Default:** Disabled (false) for no performance impact
- **When enabled:** Every RAG response gets evaluated
- **When disabled:** No overhead, RAG works normally
- **Dashboard:** `python scripts/launch_trulens_dashboard.py`

**That's it! TruLens is now under your control via environment variables.** 🚀
