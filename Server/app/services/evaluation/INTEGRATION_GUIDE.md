# TruLens Integration Guide for NeuroClimaBot RAG

## 🎯 How TruLens Works in Your Application

TruLens evaluates your RAG system using the **RAG Triad**:

```
┌───────────────────────────────────────────────────┐
│            RAG TRIAD EVALUATION                    │
├───────────────────────────────────────────────────┤
│                                                    │
│  1️⃣  CONTEXT RELEVANCE (0-1)                      │
│      Query → Retrieved Contexts                   │
│      "Did we retrieve relevant information?"      │
│      • Evaluates Milvus + GraphRAG separately     │
│      • Identifies poor retrieval                  │
│                                                    │
│  2️⃣  GROUNDEDNESS (0-1)                           │
│      Retrieved Contexts → Generated Answer        │
│      "Is the answer supported by our data?"       │
│      • Hallucination detection                    │
│      • Scores < 0.7 trigger warnings              │
│                                                    │
│  3️⃣  ANSWER RELEVANCE (0-1)                       │
│      Query → Generated Answer                     │
│      "Does the answer address the question?"      │
│      • End-to-end quality check                   │
│                                                    │
└───────────────────────────────────────────────────┘
```

---

## 📊 Integration with Your Architecture

### Current Flow
```python
User Query
  ↓
CleanRAGService.query()
  ↓
RAGOrchestrator.process_*_conversation()
  ├→ MultiSourceRetriever (Milvus chunks, summaries, GraphRAG)
  ├→ UltraFastReranker (score-based ranking)
  └→ ResponseGeneratorService (LLM generation)
  ↓
Response
```

### With TruLens Evaluation
```python
User Query
  ↓
CleanRAGService.query() + RAGEvaluator
  ↓
RAGOrchestrator.process_*_conversation()
  ├→ MultiSourceRetriever
  ├→ UltraFastReranker
  └→ ResponseGeneratorService
  ↓
Response + TruLens Evaluation Scores
  ├→ Context Relevance (by source: Milvus vs GraphRAG)
  ├→ Groundedness (hallucination check)
  ├→ Answer Relevance
  └→ Quality Flags
```

---

## 🔧 Installation

### Step 1: Add TruLens to Requirements

Add to `Server/requirements.txt`:

```txt
# TruLens for RAG evaluation
trulens-eval==0.33.0
```

Install:
```bash
cd Server
pip install trulens-eval
```

---

## 💻 Code Integration

### Option 1: Minimal Integration (Recommended for Testing)

Modify `Server/app/services/rag/chain.py`:

```python
# Add at top of file
from app.services.evaluation.rag_evaluator import get_rag_evaluator

class CleanRAGService:
    def __init__(self):
        # ... existing code ...
        self.evaluator = None  # Add evaluator

    async def initialize(self):
        """Initialize the RAG service with evaluation"""
        try:
            from app.services.prompts.manager import get_prompt_manager

            # Initialize evaluator
            self.evaluator = await get_rag_evaluator(enabled=True)

            # ... rest of existing initialization ...
```

Then in the `query()` method, add evaluation after response generation:

```python
async def query(
    self,
    question: str,
    session_id: Optional[str] = None,
    include_sources: bool = True,
    language: str = "en",
    difficulty_level: str = "low",
    conversation_type: str = "continue",
    **kwargs
) -> Dict[str, Any]:
    """Process a query with TruLens evaluation"""

    # ... existing RAG processing ...

    # Get RAG response
    rag_result = await self.orchestrator.process_*_conversation(...)

    # 🆕 EVALUATE THE RESPONSE
    if self.evaluator:
        eval_scores = await self.evaluator.evaluate_from_rag_response(
            query=question,
            rag_response=rag_result
        )

        # Add evaluation scores to response
        if eval_scores:
            rag_result = self.evaluator.add_scores_to_response(
                rag_result,
                eval_scores
            )

    # ... rest of existing code ...
    return rag_result
```

### Option 2: Detailed Integration with Per-Component Evaluation

```python
async def query(self, question: str, **kwargs) -> Dict[str, Any]:
    """Process query with detailed evaluation"""

    # ... retrieval code ...

    # After retrieval
    chunks = retrieved_chunks
    summaries = retrieved_summaries
    graph_data = retrieved_graph_data

    # ... reranking code ...

    # After generation
    generated_response = final_response

    # 🆕 DETAILED EVALUATION
    if self.evaluator:
        eval_scores = await self.evaluator.evaluate_response(
            query=question,
            chunks=chunks,
            summaries=summaries,
            graph_data=graph_data,
            generated_response=generated_response,
            metadata={
                "session_id": session_id,
                "language": language,
                "conversation_type": conversation_type
            }
        )

        # Log evaluation results
        if eval_scores:
            logger.info(
                f"📊 Evaluation - "
                f"Context: {eval_scores.context_relevance:.2f}, "
                f"Grounded: {eval_scores.groundedness:.2f}, "
                f"Relevant: {eval_scores.answer_relevance:.2f}"
            )

            # Warn on potential hallucination
            if eval_scores.groundedness < 0.7:
                logger.warning(
                    f"⚠️ Potential hallucination detected! "
                    f"Groundedness: {eval_scores.groundedness:.2f}"
                )

    return response
```

---

## 🚀 Usage Examples

### Example 1: Basic Evaluation

```python
from app.services.evaluation.rag_evaluator import get_rag_evaluator
from app.services.rag.chain import get_rag_service

# Initialize
evaluator = await get_rag_evaluator(enabled=True)
rag_service = await get_rag_service()

# Process query
result = await rag_service.query(
    question="What are the main causes of climate change?",
    session_id="test-123",
    language="en"
)

# Check evaluation scores
if "evaluation" in result:
    eval_data = result["evaluation"]
    print(f"Context Relevance: {eval_data['context_relevance']:.2f}")
    print(f"Groundedness: {eval_data['groundedness']:.2f}")
    print(f"Answer Relevance: {eval_data['answer_relevance']:.2f}")
    print(f"Overall Score: {eval_data['overall_score']:.2f}")

    # Check quality flags
    quality = result["quality_flags"]
    if quality["potential_hallucination"]:
        print("⚠️ Warning: Potential hallucination detected!")
    if quality["excellent_response"]:
        print("✅ Excellent response quality!")
```

### Example 2: Compare Milvus vs GraphRAG

```python
# After evaluation
if "evaluation" in result:
    eval_data = result["evaluation"]

    milvus_score = eval_data.get("milvus_context_relevance")
    graphrag_score = eval_data.get("graphrag_context_relevance")

    if milvus_score and graphrag_score:
        print(f"Milvus Context Quality: {milvus_score:.2f}")
        print(f"GraphRAG Context Quality: {graphrag_score:.2f}")

        if milvus_score > graphrag_score:
            print("→ Milvus provided better context")
        else:
            print("→ GraphRAG provided better context")
```

### Example 3: Batch Evaluation

```python
from app.services.evaluation.trulens_service import get_trulens_service

# Load test queries
test_queries = [
    "What are social tipping points?",
    "How does climate change affect biodiversity?",
    "What are the latest climate policies?"
]

evaluator = await get_rag_evaluator(enabled=True)
results = []

for query in test_queries:
    result = await rag_service.query(question=query)

    if "evaluation" in result:
        results.append({
            "query": query,
            "scores": result["evaluation"],
            "quality": result["quality_flags"]
        })

# Analyze results
avg_groundedness = sum(r["scores"]["groundedness"] for r in results) / len(results)
hallucination_rate = sum(
    1 for r in results if r["quality"]["potential_hallucination"]
) / len(results)

print(f"Average Groundedness: {avg_groundedness:.2f}")
print(f"Hallucination Rate: {hallucination_rate:.2%}")
```

---

## 📈 TruLens Dashboard

### Launch Dashboard

Create a script `Server/scripts/launch_trulens_dashboard.py`:

```python
"""Launch TruLens dashboard for evaluation monitoring"""
import asyncio
from app.services.evaluation.trulens_service import get_trulens_service

async def main():
    service = await get_trulens_service()
    print("🚀 Launching TruLens Dashboard...")
    print("📊 Dashboard URL: http://localhost:8501")
    service.launch_dashboard(port=8501)

if __name__ == "__main__":
    asyncio.run(main())
```

Run:
```bash
cd Server
python scripts/launch_trulens_dashboard.py
```

Open browser: `http://localhost:8501`

### Dashboard Features

The TruLens dashboard provides:
- **Real-time evaluation trends** over time
- **Score distributions** for each metric
- **Hallucination detection** alerts
- **Query-level drill-down** to inspect individual responses
- **Comparison views** between different prompts/models
- **Export capabilities** for reports

---

## 🔍 Understanding the Scores

### Context Relevance (0-1)
- **> 0.8**: Excellent retrieval, highly relevant contexts
- **0.6-0.8**: Good retrieval, mostly relevant
- **0.4-0.6**: Moderate, some irrelevant contexts
- **< 0.4**: Poor retrieval, needs improvement

**What to do if low:**
- Adjust `SIMILARITY_THRESHOLD` in `config/rag.py`
- Improve embedding quality
- Review chunk sizes
- Tune reranker settings

### Groundedness (0-1)
- **> 0.8**: Excellent, no hallucinations
- **0.7-0.8**: Good, minor unsupported claims
- **0.5-0.7**: Moderate, some hallucinations
- **< 0.5**: Poor, significant hallucinations

**What to do if low:**
- Review LLM prompts (check `services/prompts/`)
- Increase context quality
- Adjust `MAX_CONTEXT_LENGTH`
- Consider different LLM model

### Answer Relevance (0-1)
- **> 0.8**: Excellent, directly addresses question
- **0.6-0.8**: Good, mostly on-topic
- **0.4-0.6**: Moderate, partially addresses question
- **< 0.4**: Poor, off-topic

**What to do if low:**
- Review query preprocessing logic
- Improve prompt templates
- Check if retrieval is getting right topics

---

## ⚙️ Configuration

Add to `Server/.env`:

```env
# TruLens Configuration
TRULENS_ENABLED=true
TRULENS_DB_PATH=./data/trulens_evaluations.db
TRULENS_EVALUATION_MODEL=gpt-4  # or use Ollama/Mixtral
```

Add to `Server/app/config/rag.py`:

```python
class RAGConfig(BaseSettings):
    # ... existing config ...

    # TruLens Evaluation
    TRULENS_ENABLED: bool = Field(
        default=True,
        description="Enable TruLens evaluation"
    )
    TRULENS_DB_PATH: str = Field(
        default="./data/trulens_evaluations.db",
        description="Path to TruLens SQLite database"
    )
    EVALUATION_GROUNDEDNESS_THRESHOLD: float = Field(
        default=0.7,
        description="Threshold for hallucination warnings"
    )
```

---

## 🧪 Testing the Integration

### Test Script

Create `Server/tests/test_trulens_integration.py`:

```python
import asyncio
from app.services.rag.chain import get_rag_service
from app.services.evaluation.rag_evaluator import get_rag_evaluator

async def test_evaluation():
    """Test TruLens integration"""

    print("Initializing RAG service with evaluation...")
    rag_service = await get_rag_service()
    evaluator = await get_rag_evaluator(enabled=True)

    print("\n✅ Services initialized\n")

    # Test query
    test_query = "What are the main drivers of climate change?"

    print(f"Query: {test_query}")
    print("Processing...")

    result = await rag_service.query(
        question=test_query,
        session_id="test-trulens-001",
        language="en",
        conversation_type="start"
    )

    print(f"\n📝 Response: {result['content'][:200]}...\n")

    # Check evaluation
    if "evaluation" in result:
        eval_data = result["evaluation"]
        print("📊 TruLens Evaluation Scores:")
        print(f"  • Context Relevance:  {eval_data['context_relevance']:.3f}")
        print(f"  • Groundedness:       {eval_data['groundedness']:.3f}")
        print(f"  • Answer Relevance:   {eval_data['answer_relevance']:.3f}")
        print(f"  • Overall Score:      {eval_data['overall_score']:.3f}")

        if eval_data.get('milvus_context_relevance'):
            print(f"  • Milvus Quality:     {eval_data['milvus_context_relevance']:.3f}")
        if eval_data.get('graphrag_context_relevance'):
            print(f"  • GraphRAG Quality:   {eval_data['graphrag_context_relevance']:.3f}")

        print(f"\n⏱️  Evaluation Time: {eval_data['evaluation_time_ms']:.0f}ms")

        # Quality flags
        quality = result["quality_flags"]
        print("\n🎯 Quality Flags:")
        if quality["excellent_response"]:
            print("  ✅ Excellent response!")
        if quality["potential_hallucination"]:
            print("  ⚠️  Potential hallucination detected")
        if quality["high_quality"]:
            print("  ✅ High quality response")
    else:
        print("❌ No evaluation data found")

    # Get statistics
    stats = evaluator.get_statistics()
    print(f"\n📈 Evaluation Statistics:")
    print(f"  Total evaluations: {stats.get('total_evaluations', 0)}")
    print(f"  Avg groundedness: {stats.get('avg_groundedness', 0):.3f}")
    print(f"  Hallucination rate: {stats.get('hallucination_rate', 0):.2%}")

if __name__ == "__main__":
    asyncio.run(test_evaluation())
```

Run:
```bash
cd Server
python tests/test_trulens_integration.py
```

---

## 📊 Monitoring in Production

### 1. Track Evaluation Metrics

```python
# In your API endpoint
@router.post("/query")
async def query_endpoint(request: QueryRequest):
    result = await rag_service.query(question=request.question)

    # Track evaluation metrics
    if "evaluation" in result:
        eval_data = result["evaluation"]

        # Send to monitoring (Prometheus/Grafana)
        GROUNDEDNESS_METRIC.observe(eval_data["groundedness"])
        CONTEXT_RELEVANCE_METRIC.observe(eval_data["context_relevance"])
        ANSWER_RELEVANCE_METRIC.observe(eval_data["answer_relevance"])

        # Alert on hallucinations
        if eval_data["groundedness"] < 0.7:
            HALLUCINATION_COUNTER.inc()
            logger.warning(f"Hallucination detected: {request.question}")

    return result
```

### 2. Periodic Quality Reports

```python
# Create weekly quality reports
async def generate_quality_report():
    evaluator = await get_rag_evaluator()
    stats = evaluator.get_statistics()

    report = f"""
    RAG Quality Report
    ==================

    Period: Last 7 days
    Total Queries: {stats['total_evaluations']}

    Average Scores:
    - Context Relevance: {stats['avg_context_relevance']:.3f}
    - Groundedness: {stats['avg_groundedness']:.3f}
    - Answer Relevance: {stats['avg_answer_relevance']:.3f}

    Quality Metrics:
    - Hallucination Rate: {stats['hallucination_rate']:.2%}
    - High Quality Responses: {stats.get('high_quality_rate', 0):.2%}

    """

    return report
```

---

## 🎓 Next Steps

1. **Start with basic integration** - Add evaluator to `chain.py`
2. **Run test queries** - Use `test_trulens_integration.py`
3. **Launch dashboard** - Monitor evaluation trends
4. **Set quality thresholds** - Define acceptable score ranges
5. **Create alerts** - Notify on hallucinations or low scores
6. **Iterate and improve** - Use insights to tune RAG parameters

---

## 🤝 Integration with Existing Tools

### Langfuse Integration

TruLens complements your existing Langfuse tracing:

- **Langfuse**: Tracks LLM calls, costs, latencies
- **TruLens**: Evaluates quality, detects hallucinations

You can use both together for comprehensive observability.

### Prometheus/Grafana

Export TruLens scores to Prometheus:

```python
from prometheus_client import Histogram

GROUNDEDNESS_SCORE = Histogram(
    'rag_groundedness_score',
    'TruLens groundedness score distribution'
)

# After evaluation
GROUNDEDNESS_SCORE.observe(eval_scores.groundedness)
```

---

## 📚 Additional Resources

- [TruLens Documentation](https://www.trulens.org/docs/)
- [RAG Triad Paper](https://arxiv.org/abs/2309.15217)
- [Example Notebooks](https://github.com/truera/trulens/tree/main/examples)
