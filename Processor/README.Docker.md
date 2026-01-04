# NeuroClima Document Processor - Docker Setup

This guide explains how to run the NeuroClima Document Processor using Docker Compose.

## Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- At least 16GB RAM (recommended for all services)
- At least 20GB free disk space

## Architecture

The Docker Compose setup includes the following services:

1. **unstructured** - Document extraction API (port 9000)
2. **processor** - Main document processing service (port 5000)
3. **minio** - S3-compatible object storage (ports 9001, 9002)
4. **milvus** - Vector database for embeddings (port 19530)
5. **etcd** - Metadata storage for Milvus
6. **ollama** - Local LLM and embedding service (port 11434)

## Quick Start

### 1. Navigate to the Processor directory

```bash
cd Processor
```

### 2. Review and update the .env file (optional)

The `.env` file is pre-configured with Docker service names. Update if needed:

```bash
nano .env
```

Key settings to review:
- `MODEL_PROVIDER` - Set to "free" (Ollama) or "paid" (OpenAI)
- `OPENAI_API_KEY` - Required if using MODEL_PROVIDER=paid
- `ACCESS_KEY` / `SECRET_KEY` - MinIO credentials (default: minioadmin)

### 3. Start all services

```bash
docker-compose up -d
```

This will:
- Download required Docker images (~10GB)
- Start all services in the correct order
- Wait for health checks before starting dependent services

### 4. Download Ollama models (first time only)

After Ollama starts, download the required models:

```bash
# Download the LLM model (Mistral 7B - ~4GB)
docker exec -it neuroclima-ollama ollama pull mistral:7b

# Download the embedding model (~1GB)
docker exec -it neuroclima-ollama ollama pull nomic-embed-text

# (Optional) Download vision model for image extraction (~7GB)
docker exec -it neuroclima-ollama ollama pull llava:13b
```

### 5. Verify services are running

```bash
docker-compose ps
```

All services should show "healthy" status after a few minutes.

### 6. Check processor health

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "ollama": "healthy",
    "minio": "healthy",
    "milvus": "healthy",
    "unstructured": "healthy"
  }
}
```

## Usage

### Access the API

The processor API is available at `http://localhost:5000`

### Access MinIO Console

MinIO web console: `http://localhost:9002`
- Username: `minioadmin` (or your ACCESS_KEY)
- Password: `minioadmin` (or your SECRET_KEY)

### Process a document

```bash
curl -X POST http://localhost:5000/process/document \
  -H "Content-Type: application/json" \
  -d '{
    "bucket": "researchpapers",
    "object_key": "your-document.pdf"
  }'
```

## Common Commands

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f processor
docker-compose logs -f ollama
docker-compose logs -f unstructured
```

### Stop all services

```bash
docker-compose down
```

### Stop and remove all data

```bash
docker-compose down -v
```

### Restart a specific service

```bash
docker-compose restart processor
```

### Rebuild the processor image

```bash
docker-compose build processor
docker-compose up -d processor
```

## Service Endpoints (Internal)

When running in Docker, services communicate using these internal endpoints:

- Unstructured API: `http://unstructured:8000`
- MinIO: `minio:9000`
- Milvus: `milvus:19530`
- Ollama: `http://ollama:11434`

These are already configured in the `.env` file.

## Troubleshooting

### Processor fails to start

1. Check Ollama models are downloaded:
   ```bash
   docker exec -it neuroclima-ollama ollama list
   ```

2. Check service health:
   ```bash
   docker-compose ps
   ```

3. View processor logs:
   ```bash
   docker-compose logs processor
   ```

### Out of memory errors

- Increase Docker memory limit (Docker Desktop → Settings → Resources)
- Reduce concurrent tasks: Set `MAX_CONCURRENT_TASKS=1` in `.env`
- Use smaller models: Change `OLLAMA_MODEL=mistral:7b` to `tinyllama`

### Milvus connection errors

1. Wait for Milvus to fully start (can take 30-60 seconds)
2. Check Milvus logs:
   ```bash
   docker-compose logs milvus
   ```

### Unstructured API timeout

- Increase timeout in `.env`: `UNSTRUCTURED_TIMEOUT=10`
- Check unstructured service logs:
  ```bash
  docker-compose logs unstructured
  ```

## GPU Support (Optional)

To enable GPU acceleration for Ollama:

1. Install NVIDIA Container Toolkit
2. Uncomment the GPU section in `docker-compose.yml`:
   ```yaml
   ollama:
     deploy:
       resources:
         reservations:
           devices:
             - driver: nvidia
               count: 1
               capabilities: [gpu]
   ```

3. Restart services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Data Persistence

All data is persisted in Docker volumes:

- `minio_data` - Uploaded documents
- `milvus_data` - Vector embeddings
- `ollama_data` - Downloaded models
- `processor_data` - SQLite database
- `graphrag_data` - GraphRAG knowledge graphs
- `lancedb_data` - LanceDB storage

To backup data:
```bash
docker-compose down
docker run --rm -v processor_processor_data:/data -v $(pwd):/backup ubuntu tar czf /backup/processor_backup.tar.gz /data
```

## Environment Variables

Key environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `free` | Use "free" (Ollama) or "paid" (OpenAI) |
| `OLLAMA_MODEL` | `mistral:7b` | LLM model for processing |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `MAX_CONCURRENT_TASKS` | `3` | Max parallel processing tasks |
| `ENABLE_MICROSOFT_GRAPHRAG` | `True` | Enable GraphRAG processing |
| `ENABLE_STP` | `True` | Enable STP classification |

## Port Reference

| Service | Internal Port | External Port | Description |
|---------|--------------|---------------|-------------|
| Processor | 5000 | 5000 | Main API |
| Unstructured | 8000 | 9000 | Document extraction |
| MinIO API | 9000 | 9001 | Object storage API |
| MinIO Console | 9001 | 9002 | Web console |
| Milvus | 19530 | 19530 | Vector database |
| Ollama | 11434 | 11434 | LLM API |

## Integration with Client and Server

The processor integrates with the Client and Server through environment variables:

**Client** (`.env`):
```env
VITE_API_DOCUMENT_URL=http://localhost:5000
VITE_TRANSLATE_API_URL=http://localhost:5000
VITE_STP_SERVICE_URL=http://localhost:5000
```

**Server** (`.env`):
```env
DOCUMENT_PROCESSOR_URL=http://localhost:5000
```

## Production Deployment

For production:

1. Update `.env` with strong credentials:
   ```env
   ACCESS_KEY=your-secure-key
   SECRET_KEY=your-secure-secret
   SECURE=True  # Enable HTTPS for MinIO
   ```

2. Configure CORS:
   ```env
   CORS_ORIGINS=https://your-domain.com
   ```

3. Use managed services for production:
   - Replace MinIO with AWS S3, Google Cloud Storage, or Azure Blob
   - Replace Milvus with Zilliz Cloud (managed Milvus)
   - Use OpenAI API (`MODEL_PROVIDER=paid`) for better quality

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review `.env` configuration
- Ensure all health checks pass: `docker-compose ps`
- Verify Ollama models are downloaded: `docker exec -it neuroclima-ollama ollama list`
