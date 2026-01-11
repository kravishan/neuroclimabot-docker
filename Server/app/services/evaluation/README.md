# TruLens RAG Evaluation for NeuroClimaBot

## 📚 Table of Contents

1. [Overview](#overview)
2. [How TruLens Works](#how-trulens-works)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [Usage Examples](#usage-examples)
6. [Understanding Scores](#understanding-scores)
7. [Dashboard](#dashboard)
8. [API Reference](#api-reference)

---

## Overview

This module provides **TruLens** integration for evaluating your RAG (Retrieval-Augmented Generation) system in real-time. TruLens uses the **RAG Triad** methodology to comprehensively evaluate retrieval quality, answer groundedness, and relevance.

### What Gets Evaluated

```
Your RAG Pipeline:
┌──────────────────────────────────────────────────────┐
│  User Query                                          │
│     ↓                                                │
│  1. RETRIEVAL (Milvus + GraphRAG)   ← Evaluated     │
│     ↓                                                │
│  2. RERANKING                                        │
│     ↓                                                │
│  3. GENERATION (OpenAI/Mixtral)     ← Evaluated     │
│     ↓                                                │
│  Generated Answer                   ← Evaluated     │
└──────────────────────────────────────────────────────┘
```

### Key Features

✅ **Real-time evaluation** of every RAG response
✅ **Hallucination detection** via groundedness scoring
✅ **Multi-source analysis** (Milvus vs GraphRAG quality comparison)
✅ **Production-ready** with minimal performance overhead
✅ **Dashboard visualization** for monitoring trends
✅ **Seamless integration** with your existing RAG pipeline

---

## How TruLens Works

### The RAG Triad

TruLens evaluates your RAG system using three fundamental metrics:

```
┌─────────────────────────────────────────────────────┐
│                   RAG TRIAD                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1️⃣  CONTEXT RELEVANCE (Retrieval Quality)         │
│      ┌─────────────────────────────────────┐       │
│      │ Input:  User Query                  │       │
│      │ Output: Retrieved Contexts          │       │
│      │ Score:  0.0 - 1.0                   │       │
│      └─────────────────────────────────────┘       │
│      Question: "Did we retrieve relevant docs?"    │
│                                                      │
│      Your System:                                   │
│      • Evaluates Milvus chunks separately          │
│      • Evaluates GraphRAG data separately          │
│      • Identifies which source performs better     │
│                                                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  2️⃣  GROUNDEDNESS (Hallucination Detection)        │
│      ┌─────────────────────────────────────┐       │
│      │ Input:  Retrieved Contexts          │       │
│      │ Output: Generated Answer            │       │
│      │ Score:  0.0 - 1.0                   │       │
│      └─────────────────────────────────────┘       │
│      Question: "Is answer supported by context?"   │
│                                                      │
│      Detection:                                     │
│      • Score < 0.7 = Potential hallucination       │
│      • Automatic warnings logged                   │
│      • Tracked in statistics                       │
│                                                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  3️⃣  ANSWER RELEVANCE (End-to-End Quality)        │
│      ┌─────────────────────────────────────┐       │
│      │ Input:  User Query                  │       │
│      │ Output: Generated Answer            │       │
│      │ Score:  0.0 - 1.0                   │       │
│      └─────────────────────────────────────┘       │
│      Question: "Does answer address the query?"    │
│                                                      │
│      Checks:                                        │
│      • Answer addresses the question               │
│      • Response is on-topic                        │
│      • User's intent is satisfied                  │
│                                                      │
└─────────────────────────────────────────────────────┘

OVERALL SCORE = Average of all three metrics
```

### How It Works in Your Application

**Before TruLens:**
```python
User: "What are social tipping points?"
  ↓
RAG System processes query
  ↓
Response: "Social tipping points are..."
  ↓
❓ But was the answer accurate? Any hallucinations?
```

**With TruLens:**
```python
User: "What are social tipping points?"
  ↓
RAG System processes query
  ↓
TruLens Evaluator analyzes:
  ├─ Context Relevance: 0.85 ✅ (good retrieval)
  ├─ Groundedness: 0.92 ✅ (no hallucinations)
  └─ Answer Relevance: 0.88 ✅ (addresses question)
  ↓
Response: "Social tipping points are..." + Quality Scores
  ↓
✅ High confidence in answer quality!
```

---

## Quick Start

### 1. Enable TruLens in `.env`

**IMPORTANT:** TruLens is disabled by default. Enable it in `Server/.env`:

```bash
# Enable TruLens evaluation
TRULENS_ENABLED=true

# Optional: Configure settings
TRULENS_DB_PATH=./data/trulens_evaluations.db
TRULENS_EVALUATION_MODEL=gpt-4
TRULENS_GROUNDEDNESS_THRESHOLD=0.7
```

**To disable:** Set `TRULENS_ENABLED=false` (default)

See [QUICKSTART.md](./QUICKSTART.md) for detailed enable/disable instructions.

### 2. Installation

```bash
cd Server
pip install -r requirements.txt
```

This installs `trulens-eval==0.33.0` along with other dependencies.

### 3. Run Test

```bash
cd Server
python tests/test_trulens_integration.py
```

Expected output:
```
📊 TruLens Evaluation Scores:
   • Context Relevance:  0.850 ✅
   • Groundedness:       0.920 ✅
   • Answer Relevance:   0.880 ✅
   • Overall Score:      0.883 ✅
```

### 3. Launch Dashboard

```bash
cd Server
python scripts/launch_trulens_dashboard.py
```

Open browser: `http://localhost:8501`

### 4. Integrate with Your RAG Service

See [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) for detailed integration steps.

**Simple Integration:**

```python
# In Server/app/services/rag/chain.py

from app.services.evaluation.rag_evaluator import get_rag_evaluator

class CleanRAGService:
    async def initialize(self):
        # ... existing initialization ...
        self.evaluator = await get_rag_evaluator(enabled=True)

    async def query(self, question: str, **kwargs):
        # ... existing RAG processing ...
        result = await self.orchestrator.process_start_conversation(...)

        # Evaluate response
        if self.evaluator:
            scores = await self.evaluator.evaluate_from_rag_response(
                query=question,
                rag_response=result
            )
            if scores:
                result = self.evaluator.add_scores_to_response(result, scores)

        return result
```

---

## Architecture

### Module Structure

```
app/services/evaluation/
├── __init__.py                    # Package exports
├── README.md                      # This file
├── INTEGRATION_GUIDE.md           # Detailed integration guide
│
├── trulens_service.py             # Core TruLens service
│   ├── TruLensService             # Main evaluation service
│   ├── EvaluationScores           # Score dataclass
│   └── get_trulens_service()      # Singleton getter
│
├── trulens_custom_provider.py    # Custom Ollama/Mixtral provider
│   └── OllamaFeedbackProvider     # For users without OpenAI
│
└── rag_evaluator.py               # RAG-specific evaluator
    ├── RAGEvaluator               # High-level evaluator
    └── get_rag_evaluator()        # Singleton getter
```

### Integration Points

```
Your Application:
├── app/services/rag/chain.py
│   └── CleanRAGService            ← Add evaluator here
│
├── app/services/rag/orchestrator.py
│   └── RAGOrchestrator            ← Or add evaluator here
│
└── app/api/routes/query.py
    └── query_endpoint()           ← Or add evaluator here
```

---

## Usage Examples

### Example 1: Basic Evaluation

```python
from app.services.rag.chain import get_rag_service
from app.services.evaluation.rag_evaluator import get_rag_evaluator

# Initialize
rag_service = await get_rag_service()
evaluator = await get_rag_evaluator(enabled=True)

# Query
result = await rag_service.query(
    question="What are the main causes of climate change?",
    language="en"
)

# Check scores
if "evaluation" in result:
    print(f"Context Relevance: {result['evaluation']['context_relevance']}")
    print(f"Groundedness: {result['evaluation']['groundedness']}")
    print(f"Answer Relevance: {result['evaluation']['answer_relevance']}")

    # Check for issues
    if result['quality_flags']['potential_hallucination']:
        print("⚠️ Warning: Potential hallucination detected!")
```

### Example 2: Compare Data Sources

```python
# After evaluation
eval_data = result['evaluation']

milvus_score = eval_data['milvus_context_relevance']
graphrag_score = eval_data['graphrag_context_relevance']

print(f"Milvus Quality: {milvus_score:.2f}")
print(f"GraphRAG Quality: {graphrag_score:.2f}")

if milvus_score > graphrag_score + 0.1:
    print("→ Milvus is providing better context")
elif graphrag_score > milvus_score + 0.1:
    print("→ GraphRAG is providing better context")
else:
    print("→ Both sources are performing similarly")
```

### Example 3: Quality Monitoring

```python
from app.services.evaluation.rag_evaluator import get_rag_evaluator

evaluator = await get_rag_evaluator()

# Get statistics
stats = evaluator.get_statistics()

print(f"Total Evaluations: {stats['total_evaluations']}")
print(f"Avg Groundedness: {stats['avg_groundedness']:.3f}")
print(f"Hallucination Rate: {stats['hallucination_rate']:.2%}")

# Alert if quality drops
if stats['avg_groundedness'] < 0.7:
    send_alert("RAG quality degraded - hallucination rate increased!")
```

### Example 4: A/B Testing

```python
# Test different prompts
results_prompt_a = []
results_prompt_b = []

for query in test_queries:
    # Test with Prompt A
    result_a = await rag_service.query(query, prompt_version="A")
    results_prompt_a.append(result_a['evaluation']['overall_score'])

    # Test with Prompt B
    result_b = await rag_service.query(query, prompt_version="B")
    results_prompt_b.append(result_b['evaluation']['overall_score'])

# Compare
avg_a = sum(results_prompt_a) / len(results_prompt_a)
avg_b = sum(results_prompt_b) / len(results_prompt_b)

print(f"Prompt A avg score: {avg_a:.3f}")
print(f"Prompt B avg score: {avg_b:.3f}")
print(f"Winner: {'Prompt B' if avg_b > avg_a else 'Prompt A'}")
```

---

## Understanding Scores

### Context Relevance Score

**Range:** 0.0 - 1.0

| Score | Meaning | Action |
|-------|---------|--------|
| 0.8 - 1.0 | Excellent retrieval | ✅ No action needed |
| 0.6 - 0.8 | Good retrieval | Consider tuning if trending down |
| 0.4 - 0.6 | Moderate retrieval | Review `SIMILARITY_THRESHOLD` |
| 0.0 - 0.4 | Poor retrieval | ⚠️ Investigate retrieval config |

**Common Issues & Fixes:**

- **Low scores (< 0.6):**
  - Lower `SIMILARITY_THRESHOLD` in `config/rag.py`
  - Increase `MAX_RETRIEVED_DOCS`
  - Review embedding quality
  - Check if documents are properly indexed

- **Milvus >> GraphRAG:**
  - GraphRAG may need reprocessing
  - Consider adjusting GraphRAG search parameters

- **GraphRAG >> Milvus:**
  - Knowledge graph excels for this query type
  - Consider prioritizing GraphRAG for similar queries

### Groundedness Score

**Range:** 0.0 - 1.0 (Hallucination Detector)

| Score | Meaning | Action |
|-------|---------|--------|
| 0.8 - 1.0 | Fully grounded | ✅ No hallucinations |
| 0.7 - 0.8 | Mostly grounded | Minor unsupported claims |
| 0.5 - 0.7 | Partially grounded | ⚠️ Review prompt templates |
| 0.0 - 0.5 | Poor groundedness | 🚨 Significant hallucinations |

**Score < 0.7 triggers automatic warning:**
```
⚠️ Low groundedness detected: 0.65 (potential hallucination)
```

**Common Issues & Fixes:**

- **Low scores (< 0.7):**
  - Review LLM prompts in `services/prompts/`
  - Ensure prompts instruct to "only use provided context"
  - Increase `MAX_CONTEXT_LENGTH` to provide more evidence
  - Consider switching LLM model
  - Add explicit "say I don't know if uncertain" instruction

- **Frequent hallucinations:**
  - Check if `has_relevant_data` flag is properly handled
  - Review fallback response logic
  - Consider reducing `MAX_RESPONSE_LENGTH`

### Answer Relevance Score

**Range:** 0.0 - 1.0

| Score | Meaning | Action |
|-------|---------|--------|
| 0.8 - 1.0 | Directly addresses question | ✅ Excellent response |
| 0.6 - 0.8 | Mostly on-topic | Good quality |
| 0.4 - 0.6 | Partially addresses question | Review prompt clarity |
| 0.0 - 0.4 | Off-topic or irrelevant | ⚠️ Investigate query processing |

**Common Issues & Fixes:**

- **Low scores (< 0.6):**
  - Review query preprocessing logic
  - Check if question intent is properly captured
  - Improve prompt templates to focus on user question
  - Verify retrieval is getting right topic

### Overall Score

**Average of all three metrics**

```python
overall_score = (context_relevance + groundedness + answer_relevance) / 3
```

**Quality Flags:**

- `excellent_response`: All three scores ≥ 0.8
- `high_quality`: Overall score ≥ 0.8
- `potential_hallucination`: Groundedness < 0.7
- `irrelevant_context`: Context relevance < 0.6
- `off_topic_answer`: Answer relevance < 0.6

---

## Dashboard

### Launching

```bash
python scripts/launch_trulens_dashboard.py
```

Or with custom port:
```bash
python scripts/launch_trulens_dashboard.py --port 8080
```

### Features

The TruLens dashboard provides:

1. **Overview Tab**
   - Total evaluations count
   - Average scores for each metric
   - Score distributions (histograms)
   - Trend over time (line charts)

2. **Records Tab**
   - Individual query drill-down
   - View exact inputs and outputs
   - See evaluation reasoning
   - Filter by score ranges

3. **Comparisons Tab**
   - Compare different app versions
   - A/B test results
   - Prompt performance comparison

4. **Feedback Tab**
   - Detailed score breakdowns
   - Statistical analysis
   - Export capabilities

### Dashboard Screenshots

```
┌─────────────────────────────────────────────────┐
│  TruLens Dashboard                              │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Overview                                    │
│  ┌───────────────────────────────────────┐     │
│  │ Total Evaluations: 156                │     │
│  │                                        │     │
│  │ Avg Context Relevance:    0.82 ✅     │     │
│  │ Avg Groundedness:         0.88 ✅     │     │
│  │ Avg Answer Relevance:     0.85 ✅     │     │
│  │                                        │     │
│  │ Hallucination Rate:       3.2% ⚠️     │     │
│  └───────────────────────────────────────┘     │
│                                                 │
│  📈 Trends (Last 7 Days)                        │
│  [Line chart showing score trends]             │
│                                                 │
│  📋 Recent Evaluations                          │
│  [Table with latest queries and scores]        │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## API Reference

### TruLensService

**File:** `trulens_service.py`

#### Methods

**`async initialize()`**
- Initializes TruLens with feedback providers
- Sets up database connection

**`async evaluate_rag_response(query, retrieved_contexts, generated_answer, ...)`**
- Evaluates a RAG response using the RAG Triad
- **Returns:** `EvaluationScores`

**`get_statistics()`**
- Returns evaluation statistics
- **Returns:** `Dict[str, Any]`

**`launch_dashboard(port=8501)`**
- Launches TruLens web dashboard
- **Blocking call**

#### EvaluationScores Dataclass

```python
@dataclass
class EvaluationScores:
    context_relevance: float              # 0-1
    groundedness: float                   # 0-1
    answer_relevance: float               # 0-1
    overall_score: float                  # 0-1
    milvus_context_relevance: Optional[float]
    graphrag_context_relevance: Optional[float]
    evaluation_time: float                # seconds
    model_used: str                       # e.g., "gpt-4"
```

### RAGEvaluator

**File:** `rag_evaluator.py`

#### Methods

**`async initialize()`**
- Initializes RAG evaluator with TruLens service

**`async evaluate_response(query, chunks, summaries, graph_data, generated_response, ...)`**
- Evaluates RAG response with per-component breakdown
- **Returns:** `Optional[EvaluationScores]`

**`async evaluate_from_rag_response(query, rag_response)`**
- Evaluates from RAGOrchestrator response dict
- **Returns:** `Optional[EvaluationScores]`

**`add_scores_to_response(response, scores)`**
- Adds evaluation data to response dict
- Adds `evaluation` and `quality_flags` fields
- **Returns:** `Dict[str, Any]`

**`get_statistics()`**
- Returns evaluation statistics
- **Returns:** `Dict[str, Any]`

### Statistics Dictionary

```python
{
    "total_evaluations": 156,
    "avg_context_relevance": 0.82,
    "avg_groundedness": 0.88,
    "avg_answer_relevance": 0.85,
    "low_groundedness_count": 5,
    "hallucination_rate": 0.032  # 3.2%
}
```

---

## Configuration

### Environment Variables (Primary Control)

**IMPORTANT:** TruLens is controlled via `.env` file. Default is **disabled**.

Add to `Server/.env`:

```env
# =============================================================================
# TruLens RAG Evaluation
# =============================================================================

# Enable/Disable TruLens (default: false)
TRULENS_ENABLED=true

# Database path
TRULENS_DB_PATH=./data/trulens_evaluations.db

# Evaluation model (gpt-4, gpt-3.5-turbo, or ollama)
TRULENS_EVALUATION_MODEL=gpt-4

# Hallucination threshold (0.0-1.0)
TRULENS_GROUNDEDNESS_THRESHOLD=0.7

# OpenAI API key (optional - uses Ollama/Mixtral if not set)
OPENAI_API_KEY=sk-...
```

**Configuration Notes:**
- **Default:** `TRULENS_ENABLED=false` (no performance impact)
- **To enable:** Set `TRULENS_ENABLED=true`
- **To disable:** Set `TRULENS_ENABLED=false` or omit the variable
- See `.env.example` for all available settings

### Programmatic Control (Optional)

You can also override the `.env` setting in code:

```python
from app.config import get_settings

settings = get_settings()
print(f"TruLens enabled: {settings.TRULENS_ENABLED}")
print(f"DB path: {settings.TRULENS_DB_PATH}")
print(f"Threshold: {settings.TRULENS_GROUNDEDNESS_THRESHOLD}")
```

These settings are automatically loaded from `Server/app/config/features.py`

---

## Performance Considerations

### Evaluation Overhead

- **Per-query evaluation time:** ~500-2000ms
  - Context Relevance: ~150-300ms
  - Groundedness: ~200-800ms
  - Answer Relevance: ~150-300ms

- **Total query time increase:** ~10-20%
  - Your RAG: ~5-10s
  - + TruLens: +1-2s

### Optimization Tips

1. **Run evaluations async** (already implemented)
2. **Sample evaluation** - Don't evaluate every query in high-traffic production:
   ```python
   import random
   if random.random() < 0.1:  # 10% sampling
       scores = await evaluator.evaluate_response(...)
   ```

3. **Use Ollama/Mixtral** for faster (free) evaluation
4. **Batch evaluation** for offline analysis

---

## Troubleshooting

### Issue: TruLens not installed

**Error:**
```
ImportError: No module named 'trulens_eval'
```

**Fix:**
```bash
pip install trulens-eval==0.33.0
```

### Issue: OpenAI API key not found

**Error:**
```
OpenAI API key not configured
```

**Fix:**
Set in `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
```

Or use Ollama provider (already implemented as fallback).

### Issue: Low groundedness scores

**Symptoms:**
- Frequent hallucination warnings
- Groundedness < 0.7

**Debug:**
1. Check LLM prompts - ensure they instruct to use only provided context
2. Review `has_relevant_data` flag handling
3. Inspect actual responses for unsupported claims
4. Increase context length if too restrictive

**Fix:**
```python
# In prompt template
"IMPORTANT: Only use information from the provided context.
If the context doesn't contain relevant information, say so."
```

### Issue: Low context relevance

**Symptoms:**
- Context relevance < 0.6
- Retrieved docs don't match query

**Debug:**
1. Check `SIMILARITY_THRESHOLD` setting
2. Review embedding quality
3. Test retrieval independently

**Fix:**
```python
# In config/rag.py
SIMILARITY_THRESHOLD = 0.05  # Lower threshold (was 0.1)
MAX_RETRIEVED_DOCS = 20      # More documents (was 15)
```

---

## Next Steps

1. ✅ **Install:** `pip install -r requirements.txt`
2. ✅ **Test:** `python tests/test_trulens_integration.py`
3. ✅ **Integrate:** See [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
4. ✅ **Monitor:** `python scripts/launch_trulens_dashboard.py`
5. ✅ **Optimize:** Use insights to tune RAG parameters

---

## Additional Resources

- **TruLens Documentation:** https://www.trulens.org/docs/
- **Integration Guide:** [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- **Example Tests:** `tests/test_trulens_integration.py`
- **Dashboard Script:** `scripts/launch_trulens_dashboard.py`

---

**Questions? Issues?**

Check the integration guide or review the test scripts for working examples.
