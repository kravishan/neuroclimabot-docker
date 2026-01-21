# News Article Visualization Fix

## Issue Summary

News article knowledge graph visualizations were not appearing when users clicked the "Explore" button. This document explains the root cause and the solution.

## Root Cause Analysis

### The Problem
1. **Regular documents** (policy, research papers, scientific data) → Processed by GraphRAG → Have graph data ✅
2. **News articles** → Uploaded to MinIO → NOT processed by GraphRAG → No graph data ❌
3. When users click "Explore" for news articles → Backend returns empty entities → Frontend shows generic error

### Technical Flow
```
User clicks "Explore" on news article
   ↓
Frontend sends doc_name to /api/v1/graph/force-graph-visualization
   ↓
Backend calls GraphRAG Processor at /graphrag/visualization
   ↓
Processor searches for doc_name in documents.parquet (GraphRAG database)
   ↓
NOT FOUND (404) → Returns empty response with success=true but nodes=[]
   ↓
Frontend detects empty nodes
   ↓
Shows error: "Sorry, we don't have the knowledge graph data for this question."
```

### Why News Articles Aren't Processed

News articles ARE configured to be processable by GraphRAG:
- `Processor/config.py:117` - news is in `processable_buckets`
- `Processor/config.py:268` - news has entity types defined for GraphRAG
- `Processor/config.py:362-370` - news has chunking configuration
- `Processor/config.py:411-419` - news has summarization configuration

**However**, the news articles need to be explicitly processed through the GraphRAG pipeline to generate the graph data (entities, relationships, communities).

## Solution Implemented

### 1. Improved Error Messages (Completed)

Updated `Client/src/pages/ExplorePage/index.jsx` to provide clearer error messages:

**Before:**
```javascript
setError('Sorry, we don\'t have the knowledge graph data for this question.')
```

**After:**
```javascript
setError(`Knowledge graph visualization is not available for this document "${docName}".

This could happen if:
• The document hasn't been processed by GraphRAG yet
• The document is a news article that needs GraphRAG indexing
• The document name doesn't match any processed documents in the database

Please try exploring a different document, or contact support if this persists.`)
```

### 2. Changes Made

- **File:** `Client/src/pages/ExplorePage/index.jsx`
- **Lines:** 148, 158
- **Changes:**
  - Updated error message when all fetch attempts fail (line 148)
  - Updated error message when no nodes are found (line 158)
  - Both messages now explain that news articles need GraphRAG processing

## Next Steps - How to Fix News Article Visualizations

To enable visualizations for news articles, you need to process them through the GraphRAG pipeline. Here are the steps:

### Option 1: Process Specific News Articles

Use the Processor API to process specific news articles:

```bash
# Process a single news article
curl -X POST "http://processor-url:5000/api/v1/processing/process-document" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket": "news",
    "doc_name": "your-news-article.pdf",
    "include_graphrag": true
  }'
```

### Option 2: Batch Process All News Articles

Process all news articles in the news bucket:

```bash
# Process entire news bucket
curl -X POST "http://processor-url:5000/api/v1/processing/batch-process-bucket" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket": "news",
    "include_graphrag": true
  }'
```

### Option 3: Automatic Processing on Upload

Set up automatic processing when news articles are uploaded to MinIO:

1. Check if MinIO webhook is configured in `Processor/api/processing.py`
2. Ensure the webhook processes news bucket uploads
3. Verify GraphRAG processing is enabled in the webhook handler

## Verification Steps

After processing news articles through GraphRAG, verify the fix:

1. **Check GraphRAG Output:**
   ```bash
   # Check if documents.parquet exists and contains news articles
   ls -la Processor/graphrag_workspace/output/
   ```

2. **Test Visualization Endpoint:**
   ```bash
   curl -X POST "http://server-url:8080/api/v1/graph/force-graph-visualization" \
     -H "Content-Type: application/json" \
     -d '{
       "doc_name": "your-news-article.pdf"
     }'
   ```

3. **Test in Frontend:**
   - Ask a question about climate news
   - Click the "Explore" button
   - Verify the knowledge graph loads with entities and relationships

## Expected Behavior After Fix

Once news articles are processed:

1. ✅ News articles have GraphRAG data (entities, relationships, communities)
2. ✅ Clicking "Explore" loads the knowledge graph visualization
3. ✅ All tabs (Graph, Entities, Relationships, Communities, Claims) show data
4. ✅ Users can interact with the 3D force graph and export data

## Configuration Files

Key configuration files for news article processing:

- `Processor/config.py` - Processing configuration
- `Processor/api/processing.py` - Processing endpoints
- `Server/app/services/external/graphrag_api_client.py` - GraphRAG client
- `Client/src/pages/ExplorePage/index.jsx` - Frontend visualization

## Monitoring and Debugging

### Check Processing Status

```bash
# Check if news articles are in Milvus
# Use Milvus client or admin UI to query the News collection

# Check processor logs
docker logs processor-container | grep "news"

# Check GraphRAG output
ls -R Processor/graphrag_workspace/output/
```

### Debug Visualization Issues

Enable debug logging in browser console:
- Open Developer Tools (F12)
- Go to Console tab
- Look for messages starting with 🔍, ⚠️, ❌
- Check the doc_name being sent to the API

## Support

If news article visualizations still don't work after processing:

1. Check processor logs for GraphRAG errors
2. Verify the doc_name in references matches the processed document name
3. Ensure the Processor GraphRAG service is running
4. Check network connectivity between Server and Processor
5. Review the error messages in the browser console

## Implementation Timeline

- ✅ **Phase 1 (Completed):** Improved error messages
- 🔲 **Phase 2 (Pending):** Process existing news articles through GraphRAG
- 🔲 **Phase 3 (Pending):** Set up automatic processing for new news uploads
- 🔲 **Phase 4 (Pending):** Monitor and verify all news visualizations work

## Technical Details

### Why Empty Response Returns success=true

The GraphRAG client returns `success=true` with empty arrays when a document isn't found (404). This is intentional to avoid breaking the frontend flow, but it means the frontend must check if nodes/entities exist before rendering.

### Frontend Detection Logic

```javascript
function hasGraphData(result) {
  if (!result || !result.entities) return false
  const entitiesCount = result.entities.length || result.metadata?.entities_count || 0
  return entitiesCount > 0
}
```

This checks if the response has actual entity data, not just a successful HTTP status.

---

**Last Updated:** 2026-01-21
**Author:** Claude Code
**Status:** Error messages improved, processing configuration verified, awaiting news article GraphRAG processing
