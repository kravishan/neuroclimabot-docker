# TruLens Evaluation Flags Guide

## 📍 Location

All evaluation flags are in: **`Server/app/constants.py`**

This allows you to enable/disable specific evaluations **without restarting** and **without editing .env files**.

---

## 🎛️ Available Flags

### Main Evaluation Metrics

```python
# In Server/app/constants.py

# Enable/Disable individual evaluation metrics
TRULENS_EVAL_CONTEXT_RELEVANCE = True    # Evaluate retrieval quality
TRULENS_EVAL_GROUNDEDNESS = True         # Detect hallucinations
TRULENS_EVAL_ANSWER_RELEVANCE = True     # Evaluate response quality
```

### Per-Source Evaluation

```python
# Enable/Disable per-source context evaluation
TRULENS_EVAL_MILVUS_CONTEXT = True       # Evaluate Milvus separately
TRULENS_EVAL_GRAPHRAG_CONTEXT = True     # Evaluate GraphRAG separately
```

### Performance Settings

```python
# Evaluation performance settings
TRULENS_EVAL_PARALLEL = True             # Run evaluations in parallel
TRULENS_EVAL_TIMEOUT_SECONDS = 30.0      # Total timeout for all evaluations
```

---

## 🎯 What Each Flag Does

### TRULENS_EVAL_CONTEXT_RELEVANCE

**What it evaluates:** Retrieval quality - Are retrieved documents relevant to the query?

**When enabled:**
- ✅ Scores how well Milvus + GraphRAG retrieved relevant content
- ✅ Helps tune `SIMILARITY_THRESHOLD` and retrieval settings
- ✅ Identifies when retrieval is pulling irrelevant docs

**When to disable:**
- ⏱️ Reduce cost/time if you only care about hallucinations
- 📊 Your retrieval is already well-tuned

**Cost per query:** ~150-300ms, ~100 tokens

---

### TRULENS_EVAL_GROUNDEDNESS

**What it evaluates:** Hallucination detection - Is the answer supported by retrieved context?

**When enabled:**
- ✅ Detects when LLM makes up information
- ✅ Triggers warnings when score < threshold (default 0.7)
- ✅ Most critical evaluation for factual accuracy

**When to disable:**
- ⚠️ **NOT RECOMMENDED** - This is the most important metric
- Only disable if you have other hallucination detection

**Cost per query:** ~200-800ms, ~200 tokens

**This is usually the MOST IMPORTANT evaluation to keep enabled.**

---

### TRULENS_EVAL_ANSWER_RELEVANCE

**What it evaluates:** Response quality - Does the answer address the user's question?

**When enabled:**
- ✅ Checks if response is on-topic
- ✅ Identifies when LLM goes off-track
- ✅ End-to-end quality check

**When to disable:**
- ⏱️ Reduce cost if you only care about hallucinations
- 📊 Your prompts already keep responses on-topic

**Cost per query:** ~150-300ms, ~100 tokens

---

### TRULENS_EVAL_MILVUS_CONTEXT

**What it evaluates:** Milvus retrieval quality separately

**When enabled:**
- ✅ Compare Milvus vs GraphRAG quality
- ✅ Tune Milvus-specific settings independently

**When to disable:**
- 📊 Don't need per-source breakdown
- ⏱️ Save ~150-300ms per query

---

### TRULENS_EVAL_GRAPHRAG_CONTEXT

**What it evaluates:** GraphRAG retrieval quality separately

**When enabled:**
- ✅ Compare GraphRAG vs Milvus quality
- ✅ Tune GraphRAG-specific settings independently

**When to disable:**
- 📊 Don't need per-source breakdown
- ⏱️ Save ~150-300ms per query

---

### TRULENS_EVAL_PARALLEL

**What it does:** Runs all enabled evaluations in parallel (async)

**When True (default):**
- ⚡ Faster - All evaluations run at once
- 📊 Total time ≈ slowest individual evaluation

**When False:**
- 🐢 Slower - Evaluations run one after another
- 📊 Total time = sum of all evaluations
- 🔍 Easier to debug individual evaluation failures

---

## 🎨 Pre-Built Presets

The constants file includes 4 pre-built presets. Uncomment one to use:

### Preset 1: Full Evaluation (Default)

```python
TRULENS_EVAL_CONTEXT_RELEVANCE = True
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = True
```

**Use when:**
- Development and testing
- Comprehensive quality monitoring
- Tuning all aspects of your RAG

**Cost:** ~500-1400ms per query, ~400 tokens

---

### Preset 2: Hallucination Detection Only

```python
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = True      # ← ONLY THIS
TRULENS_EVAL_ANSWER_RELEVANCE = False
```

**Use when:**
- Production with budget constraints
- Hallucinations are your main concern
- Retrieval is already well-tuned

**Cost:** ~200-800ms per query, ~200 tokens
**Savings:** 60% cheaper than full evaluation

---

### Preset 3: Retrieval Quality Only

```python
TRULENS_EVAL_CONTEXT_RELEVANCE = True  # ← ONLY THIS
TRULENS_EVAL_GROUNDEDNESS = False
TRULENS_EVAL_ANSWER_RELEVANCE = False
```

**Use when:**
- Tuning retrieval parameters
- Testing new embedding models
- Optimizing Milvus/GraphRAG settings

**Cost:** ~150-300ms per query, ~100 tokens
**Savings:** 70% cheaper than full evaluation

---

### Preset 4: End-to-End Quality

```python
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = True
```

**Use when:**
- Production monitoring
- Focus on output quality
- Don't need detailed retrieval analysis

**Cost:** ~350-1100ms per query, ~300 tokens
**Savings:** 30% cheaper than full evaluation

---

## 🚀 How to Use

### Step 1: Edit Constants

Open `Server/app/constants.py` and find the TruLens section:

```python
# =============================================================================
# TruLens Evaluation Flags
# =============================================================================

# Change these values
TRULENS_EVAL_CONTEXT_RELEVANCE = True    # ← Set to False to disable
TRULENS_EVAL_GROUNDEDNESS = True         # ← Set to False to disable
TRULENS_EVAL_ANSWER_RELEVANCE = True     # ← Set to False to disable
```

### Step 2: No Restart Needed!

Changes take effect on the **next query** - no application restart required.

### Step 3: Monitor Logs

Check what's running:

```
# When all enabled:
📊 TruLens Scores: Context=0.85, Groundedness=0.92, Answer=0.88, Overall=0.88

# When only groundedness enabled:
📊 TruLens Scores: Groundedness=0.92, Overall=0.92

# When none enabled:
📊 TruLens: No evaluations enabled
```

---

## 💰 Cost Optimization Examples

### Example 1: Production (Budget Mode)

**Goal:** Minimize cost while catching hallucinations

```python
# In constants.py
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = True      # Critical for factual accuracy
TRULENS_EVAL_ANSWER_RELEVANCE = False

TRULENS_EVAL_MILVUS_CONTEXT = False   # Skip per-source analysis
TRULENS_EVAL_GRAPHRAG_CONTEXT = False
```

**Result:**
- ✅ Detects hallucinations
- ✅ 60% cheaper than full evaluation
- ✅ Still tracks the most critical metric

---

### Example 2: Development (Full Analysis)

**Goal:** Comprehensive quality monitoring

```python
# In constants.py
TRULENS_EVAL_CONTEXT_RELEVANCE = True
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = True

TRULENS_EVAL_MILVUS_CONTEXT = True    # Compare sources
TRULENS_EVAL_GRAPHRAG_CONTEXT = True

TRULENS_EVAL_PARALLEL = True          # Fast evaluation
```

**Result:**
- ✅ Full quality visibility
- ✅ Per-source comparison
- ✅ Optimal for tuning system

---

### Example 3: Retrieval Tuning

**Goal:** Optimize Milvus and GraphRAG settings

```python
# In constants.py
TRULENS_EVAL_CONTEXT_RELEVANCE = True   # Focus on retrieval
TRULENS_EVAL_GROUNDEDNESS = False
TRULENS_EVAL_ANSWER_RELEVANCE = False

TRULENS_EVAL_MILVUS_CONTEXT = True      # Compare sources
TRULENS_EVAL_GRAPHRAG_CONTEXT = True

TRULENS_EVAL_PARALLEL = True
```

**Result:**
- ✅ Detailed retrieval analysis
- ✅ Source-by-source comparison
- ✅ 70% cheaper than full evaluation

---

### Example 4: A/B Testing Prompts

**Goal:** Test different prompts for hallucination rate

```python
# In constants.py
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = True        # Focus on prompt quality
TRULENS_EVAL_ANSWER_RELEVANCE = True

TRULENS_EVAL_MILVUS_CONTEXT = False
TRULENS_EVAL_GRAPHRAG_CONTEXT = False
```

**Result:**
- ✅ Hallucination detection
- ✅ Answer quality tracking
- ✅ Skip retrieval (already constant)

---

## 🔧 Advanced Use Cases

### Temporarily Disable All Evaluations

```python
# Quick way to disable all without changing .env
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = False
TRULENS_EVAL_ANSWER_RELEVANCE = False
```

**Or use the .env flag:**
```bash
TRULENS_ENABLED=false
```

---

### Sequential Evaluation (Debugging)

```python
# Run evaluations one at a time (easier to debug)
TRULENS_EVAL_PARALLEL = False
```

**Useful when:**
- Debugging evaluation failures
- Investigating timeout issues
- Understanding which evaluation is slow

---

### Source Comparison Analysis

```python
# Enable both per-source evaluations
TRULENS_EVAL_CONTEXT_RELEVANCE = True
TRULENS_EVAL_MILVUS_CONTEXT = True
TRULENS_EVAL_GRAPHRAG_CONTEXT = True

# Disable others to focus on retrieval
TRULENS_EVAL_GROUNDEDNESS = False
TRULENS_EVAL_ANSWER_RELEVANCE = False
```

**Result:**
- Compare Milvus vs GraphRAG quality
- Optimize each source independently

---

## 📊 Performance Impact

### All Enabled (Default)

```python
TRULENS_EVAL_CONTEXT_RELEVANCE = True
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = True
TRULENS_EVAL_PARALLEL = True
```

- ⏱️ **Time:** ~500-1400ms per query
- 💰 **Cost:** ~$0.0012 per query (with GPT-4)
- 📊 **Tokens:** ~400 tokens

---

### Groundedness Only

```python
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = False
```

- ⏱️ **Time:** ~200-800ms per query
- 💰 **Cost:** ~$0.0006 per query (with GPT-4)
- 📊 **Tokens:** ~200 tokens
- 🎯 **Savings:** 50% cheaper

---

### No Evaluation

```python
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = False
TRULENS_EVAL_ANSWER_RELEVANCE = False
```

- ⏱️ **Time:** 0ms (no overhead)
- 💰 **Cost:** $0
- 📊 **Tokens:** 0

---

## 🎓 Best Practices

### 1. Start with Full Evaluation

During development, enable all:
```python
TRULENS_EVAL_CONTEXT_RELEVANCE = True
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = True
```

### 2. Move to Targeted Evaluation

In production, focus on critical metrics:
```python
TRULENS_EVAL_GROUNDEDNESS = True  # Always keep this
TRULENS_EVAL_ANSWER_RELEVANCE = True  # Nice to have
TRULENS_EVAL_CONTEXT_RELEVANCE = False  # Disable if retrieval is tuned
```

### 3. Temporarily Enable for Tuning

When optimizing a specific component:
```python
# Tuning retrieval? Enable context relevance
TRULENS_EVAL_CONTEXT_RELEVANCE = True

# Tuning prompts? Enable groundedness
TRULENS_EVAL_GROUNDEDNESS = True

# Both tuned? Disable to save cost
# (change back to False when done)
```

### 4. Use Presets for Common Scenarios

Copy one of the preset blocks from constants.py instead of manually changing each flag.

---

## 🔍 Troubleshooting

### No Scores in Response

**Check:**
1. Is `TRULENS_ENABLED=true` in `.env`?
2. Are ANY flags set to `True` in `constants.py`?
3. Check logs for: `"Running TruLens evaluations: none"`

### Unexpected Scores

**Check logs:**
```
Running TruLens evaluations: context_relevance, groundedness, answer_relevance
```

Verify which evaluations actually ran.

### Slow Evaluation

**Try:**
1. Disable some metrics
2. Set `TRULENS_EVAL_PARALLEL = True`
3. Use `TRULENS_OPENAI_MODEL=gpt-3.5-turbo` (20x cheaper, faster)

---

## 📚 Summary

**Location:** `Server/app/constants.py`

**Main Flags:**
- `TRULENS_EVAL_CONTEXT_RELEVANCE` - Retrieval quality
- `TRULENS_EVAL_GROUNDEDNESS` - Hallucination detection
- `TRULENS_EVAL_ANSWER_RELEVANCE` - Response quality

**Per-Source:**
- `TRULENS_EVAL_MILVUS_CONTEXT` - Milvus quality
- `TRULENS_EVAL_GRAPHRAG_CONTEXT` - GraphRAG quality

**Performance:**
- `TRULENS_EVAL_PARALLEL` - Parallel execution
- `TRULENS_EVAL_TIMEOUT_SECONDS` - Total timeout

**Key Benefits:**
- ✅ No restart required to change flags
- ✅ Fine-grained cost control
- ✅ Optimize for different scenarios
- ✅ Easy presets for common use cases

---

**Need Help?**

- See `QUICKSTART.md` for basic setup
- See `README.md` for complete documentation
- See `INTEGRATION_GUIDE.md` for integration examples
