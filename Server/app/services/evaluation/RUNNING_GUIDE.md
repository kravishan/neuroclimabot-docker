# How to Run and See TruLens Evaluation Values

## 🚀 Quick Start Guide

This guide shows you how to run your RAG application with TruLens evaluation enabled and view the evaluation scores.

---

## 📋 Prerequisites

- Docker and Docker Compose installed (if using containerized setup)
- Python 3.9+ (if running locally)
- OpenAI API key (optional - can use Ollama instead)

---

## Step 1: Configure Environment Variables

### 1.1 Copy the example environment file

```bash
cd /home/user/neuroclimabot-docker/Server
cp .env.example .env
```

### 1.2 Edit `.env` file

Open `Server/.env` and configure TruLens:

```bash
# =============================================================================
# TruLens RAG Evaluation
# =============================================================================

# Enable TruLens evaluation
TRULENS_ENABLED=true

# Database path
TRULENS_DB_PATH=./data/trulens_evaluations.db

# Groundedness threshold
TRULENS_GROUNDEDNESS_THRESHOLD=0.7

# -----------------------------------------------------------------------------
# TruLens OpenAI Configuration (Dedicated for Evaluation)
# -----------------------------------------------------------------------------

# Option 1: Use OpenAI for evaluation (recommended for accuracy)
TRULENS_OPENAI_API_KEY=sk-your-openai-api-key-here
TRULENS_OPENAI_MODEL=gpt-4
TRULENS_OPENAI_BASE_URL=https://api.openai.com/v1

# Option 2: Leave empty to use Ollama/Mixtral (free, local)
# TRULENS_OPENAI_API_KEY=
```

**Important:** If you don't have an OpenAI API key, leave `TRULENS_OPENAI_API_KEY` empty and TruLens will automatically use Ollama/Mixtral.

---

## Step 2: Configure Evaluation Flags (Optional)

Edit `Server/app/constants.py` to choose which evaluations to run:

```python
# In Server/app/constants.py (around line 277)

# Full evaluation (default)
TRULENS_EVAL_CONTEXT_RELEVANCE = True    # Retrieval quality
TRULENS_EVAL_GROUNDEDNESS = True         # Hallucination detection
TRULENS_EVAL_ANSWER_RELEVANCE = True     # Response quality

# Or use a preset (uncomment one):

# Preset 2: Hallucination detection only (50% cheaper)
# TRULENS_EVAL_CONTEXT_RELEVANCE = False
# TRULENS_EVAL_GROUNDEDNESS = True
# TRULENS_EVAL_ANSWER_RELEVANCE = False
```

---

## Step 3: Install Dependencies

### Option A: Docker (Recommended)

```bash
cd /home/user/neuroclimabot-docker
docker-compose up --build
```

### Option B: Local Python Environment

```bash
cd /home/user/neuroclimabot-docker/Server

# Create virtual environment (if needed)
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

This installs `trulens-eval==0.33.0` and all other dependencies.

---

## Step 4: Start the Application

### Option A: Docker

```bash
cd /home/user/neuroclimabot-docker
docker-compose up
```

Wait for logs showing:
```
✅ RAG evaluator initialized with TruLens (TRULENS_ENABLED=true)
✅ TruLens using dedicated OpenAI provider (model: gpt-4, endpoint: https://api.openai.com/v1)
📊 TruLens database: ./data/trulens_evaluations.db
```

### Option B: Local

```bash
cd /home/user/neuroclimabot-docker/Server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Step 5: Test TruLens Integration

### 5.1 Run the Test Script

```bash
cd /home/user/neuroclimabot-docker/Server
python tests/test_trulens_integration.py
```

**Expected Output:**

```
=============================================================
TruLens Integration Test
=============================================================

1️⃣  Initializing services...
   ✅ Services initialized successfully

=============================================================
Test Query 1/3
=============================================================
📝 Query: What are social tipping points in climate systems?

💬 Response (1234 chars):
   Social tipping points are...

📊 TruLens Evaluation Scores:
   • Context Relevance:  0.850 ✅
   • Groundedness:       0.920 ✅
   • Answer Relevance:   0.880 ✅
   • Overall Score:      0.883 ✅

   Source-specific Scores:
   • Milvus Quality:     0.870
   • GraphRAG Quality:   0.820

   ⏱️  Evaluation Time:   1250ms
   🤖 Eval Model:        gpt-4

🎯 Quality Analysis:
   ✅ Excellent response quality!
   ✅ High quality response

📚 Data Sources Used:
   • chunks: 5
   • summaries: 2
   • graph: 3
```

---

## Step 6: Make API Requests and See Evaluation Values

### 6.1 Using curl

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main causes of climate change?",
    "language": "en",
    "session_id": "test-session-001"
  }'
```

**Response with TruLens evaluation:**

```json
{
  "content": "The main causes of climate change are...",
  "title": "Climate Change Causes",
  "has_relevant_data": true,
  "sources_used": {
    "chunks": 5,
    "summaries": 2,
    "graph": 3
  },
  "references": [...],

  "evaluation": {
    "context_relevance": 0.85,
    "groundedness": 0.92,
    "answer_relevance": 0.88,
    "overall_score": 0.88,
    "milvus_context_relevance": 0.87,
    "graphrag_context_relevance": 0.82,
    "evaluation_time_ms": 1250,
    "model_used": "gpt-4"
  },

  "quality_flags": {
    "excellent_response": true,
    "high_quality": true,
    "potential_hallucination": false,
    "irrelevant_context": false,
    "off_topic_answer": false
  }
}
```

### 6.2 Using Python

```python
import requests

url = "http://localhost:8000/api/v1/query"
payload = {
    "question": "What are social tipping points?",
    "language": "en",
    "session_id": "test-001"
}

response = requests.post(url, json=payload)
result = response.json()

# Access TruLens evaluation scores
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

### 6.3 Using Frontend

If you have a frontend client:

```javascript
// Make request
const response = await fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: 'What are social tipping points?',
    language: 'en',
    session_id: 'test-001'
  })
});

const result = await response.json();

// Display evaluation scores
if (result.evaluation) {
  console.log('TruLens Scores:', {
    context: result.evaluation.context_relevance,
    groundedness: result.evaluation.groundedness,
    answer: result.evaluation.answer_relevance,
    overall: result.evaluation.overall_score
  });

  // Check for quality issues
  if (result.quality_flags.potential_hallucination) {
    alert('⚠️ Warning: Response may contain hallucinations');
  }
}
```

---

## Step 7: View Evaluation Scores in Logs

### 7.1 Check Application Logs

When TruLens is enabled, you'll see evaluation scores in the logs:

```
INFO: Running TruLens evaluations: context_relevance, groundedness, answer_relevance
INFO: 📊 TruLens Scores: Context=0.85, Groundedness=0.92, Answer=0.88, Overall=0.88
```

If hallucination is detected:
```
WARNING: ⚠️ Low groundedness detected: 0.65 (threshold: 0.7, potential hallucination)
```

### 7.2 Docker Logs

```bash
# View real-time logs
docker-compose logs -f server

# Search for TruLens scores
docker-compose logs server | grep "TruLens Scores"

# Search for hallucination warnings
docker-compose logs server | grep "Low groundedness"
```

---

## Step 8: Launch TruLens Dashboard

### 8.1 Start the Dashboard

```bash
cd /home/user/neuroclimabot-docker/Server
python scripts/launch_trulens_dashboard.py
```

**Output:**
```
======================================================================
TruLens RAG Evaluation Dashboard
======================================================================

🔄 Initializing TruLens service...
✅ TruLens service initialized

📊 Current Evaluation Statistics:
   Total Evaluations:    156
   Avg Context Rel:      0.820
   Avg Groundedness:     0.880
   Avg Answer Rel:       0.850
   Hallucination Rate:   3.2%

======================================================================
🚀 Launching TruLens Dashboard...
======================================================================

📊 Dashboard URL:    http://localhost:8501
📂 Database:         ./data/trulens_evaluations.db

Dashboard Features:
  • Real-time evaluation metrics
  • Score distributions and trends
  • Query-level drill-down
  • Hallucination detection alerts
  • Export and reporting

Press Ctrl+C to stop the dashboard
======================================================================
```

### 8.2 Open Dashboard in Browser

Navigate to: **http://localhost:8501**

The dashboard shows:
- **Overview Tab**: Total evaluations, average scores, trends
- **Records Tab**: Individual query drill-down with full context
- **Comparisons Tab**: A/B testing, prompt comparisons
- **Feedback Tab**: Detailed score breakdowns and statistics

---

## Step 9: Interpret the Results

### Understanding Evaluation Scores

#### Context Relevance (0-1)
```
0.8-1.0: ✅ Excellent retrieval
0.6-0.8: ✅ Good retrieval
0.4-0.6: ⚠️ Moderate - tune retrieval
0.0-0.4: ❌ Poor - investigate
```

#### Groundedness (0-1) - Hallucination Detection
```
0.8-1.0: ✅ No hallucinations
0.7-0.8: ✅ Minor unsupported claims
0.5-0.7: ⚠️ Some hallucinations
0.0-0.5: ❌ Significant hallucinations
```

#### Answer Relevance (0-1)
```
0.8-1.0: ✅ Directly addresses question
0.6-0.8: ✅ Mostly on-topic
0.4-0.6: ⚠️ Partially addresses question
0.0-0.4: ❌ Off-topic
```

### Quality Flags

```json
{
  "excellent_response": true,        // All scores >= 0.8
  "high_quality": true,              // Overall >= 0.8
  "potential_hallucination": false,  // Groundedness < 0.7
  "irrelevant_context": false,       // Context relevance < 0.6
  "off_topic_answer": false          // Answer relevance < 0.6
}
```

---

## Step 10: Monitor Evaluation Statistics

### 10.1 Via API

```python
from app.services.evaluation.rag_evaluator import get_rag_evaluator

evaluator = await get_rag_evaluator()
stats = evaluator.get_statistics()

print(f"Total Evaluations: {stats['total_evaluations']}")
print(f"Avg Groundedness: {stats['avg_groundedness']:.3f}")
print(f"Hallucination Rate: {stats['hallucination_rate']:.2%}")
```

### 10.2 Via Dashboard

The dashboard automatically tracks:
- Total number of evaluations
- Average scores for each metric
- Score distributions (histograms)
- Trends over time (line charts)
- Hallucination rate

---

## 🎯 Complete Example Workflow

```bash
# 1. Configure TruLens
echo "TRULENS_ENABLED=true" >> Server/.env
echo "TRULENS_OPENAI_API_KEY=sk-your-key" >> Server/.env

# 2. Install dependencies
cd Server
pip install -r requirements.txt

# 3. Run test to verify setup
python tests/test_trulens_integration.py

# 4. Start application
python -m uvicorn app.main:app --reload

# 5. Make a test query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are social tipping points?", "language": "en"}'

# 6. Launch dashboard (in new terminal)
python scripts/launch_trulens_dashboard.py

# 7. Open browser to http://localhost:8501
```

---

## 🔍 Troubleshooting

### No Evaluation Scores in Response

**Check:**
1. Is `TRULENS_ENABLED=true` in `.env`?
2. Are evaluation flags enabled in `constants.py`?
3. Check logs for: `"RAG evaluation disabled"`

**Fix:**
```bash
# Check .env
grep TRULENS_ENABLED Server/.env

# Should show: TRULENS_ENABLED=true

# Check logs
docker-compose logs server | grep "TruLens"
```

### Evaluation is Slow

**Check current configuration:**
- How many metrics are enabled?
- Is `TRULENS_EVAL_PARALLEL=True`?
- Which OpenAI model are you using?

**Optimize:**
```python
# In constants.py - enable only groundedness
TRULENS_EVAL_CONTEXT_RELEVANCE = False
TRULENS_EVAL_GROUNDEDNESS = True
TRULENS_EVAL_ANSWER_RELEVANCE = False

# Use faster model in .env
TRULENS_OPENAI_MODEL=gpt-3.5-turbo
```

### OpenAI API Key Error

**Error:**
```
TruLens using Ollama/Mixtral provider (no TRULENS_OPENAI_API_KEY configured)
```

**Fix:**
```bash
# Option 1: Add OpenAI key
echo "TRULENS_OPENAI_API_KEY=sk-your-key" >> Server/.env

# Option 2: Use Ollama (free, local) - no action needed
# TruLens automatically falls back to Ollama
```

### Dashboard Won't Start

**Error:**
```
TruLens not installed
```

**Fix:**
```bash
cd Server
pip install trulens-eval==0.33.0
```

---

## 📊 What You'll See

### In API Response

```json
{
  "evaluation": {
    "context_relevance": 0.85,
    "groundedness": 0.92,
    "answer_relevance": 0.88,
    "overall_score": 0.88
  },
  "quality_flags": {
    "excellent_response": true,
    "potential_hallucination": false
  }
}
```

### In Logs

```
INFO: Running TruLens evaluations: context_relevance, groundedness, answer_relevance
INFO: 📊 TruLens Scores: Context=0.85, Groundedness=0.92, Answer=0.88, Overall=0.88
```

### In Dashboard

- Real-time score charts
- Query-by-query breakdown
- Hallucination alerts
- Performance metrics
- Export capabilities

---

## 🎓 Next Steps

1. ✅ **Run the test** to verify setup
2. ✅ **Make some queries** to collect evaluation data
3. ✅ **Launch the dashboard** to visualize results
4. ✅ **Tune based on scores** (see EVALUATION_FLAGS.md)
5. ✅ **Monitor production** with real queries

---

## 📚 Additional Resources

- **QUICKSTART.md** - Basic configuration guide
- **EVALUATION_FLAGS.md** - Detailed flag documentation
- **INTEGRATION_GUIDE.md** - Integration with RAG chain
- **README.md** - Complete API reference

---

## 💡 Tips

1. **Start with full evaluation** during development
2. **Switch to hallucination-only** in production for cost savings
3. **Use the dashboard** to identify trends and issues
4. **Check logs regularly** for hallucination warnings
5. **Tune retrieval** based on context relevance scores

---

**You're all set!** Run the test script to see TruLens in action. 🚀
