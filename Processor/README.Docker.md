# NeuroClima Document Processor - Docker Setup

This guide explains how to run the NeuroClima Document Processor using Docker Compose.

## Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- **Already deployed and running:**
  - MinIO (port 9000)
  - Milvus (port 19530)
  - Ollama (port 11434)

## Architecture

The Docker Compose setup includes the following services:

1. **unstructured** - Document extraction API (port 9000 → maps to internal 8000)
2. **processor** - Main document processing service (port 5000)

The processor connects to your existing MinIO, Milvus, and Ollama services running on localhost.

## Quick Start

### 1. Navigate to the Processor directory

```bash
cd Processor
```

### 2. Review and update the .env file

The `.env` file is pre-configured to use your existing services on localhost. Update if needed:

```bash
nano .env
```

Key settings to review:
- `MODEL_PROVIDER` - Set to "free" (Ollama) or "paid" (OpenAI)
- `OPENAI_API_KEY` - Required if using MODEL_PROVIDER=paid
- `ACCESS_KEY` / `SECRET_KEY` - MinIO credentials (match your deployment)
- `OLLAMA_API_URL` - Ollama endpoint (default: http://localhost:11434)
- `MINIO_ENDPOINT` - MinIO endpoint (default: localhost:9000)
- `MILVUS_HOST` - Milvus host (default: localhost)

### 3. Ensure external services are running

Make sure your existing services are accessible:

```bash
# Check MinIO
curl http://localhost:9000/minio/health/live

# Check Milvus
curl http://localhost:19530

# Check Ollama
curl http://localhost:11434/
```

### 4. Start the Docker services

```bash
docker-compose up -d
```

This will:
- Download the Unstructured API image (~2GB)
- Build the Processor image
- Start both services with health checks

### 5. Verify services are running

```bash
docker-compose ps
```

Both services should show "healthy" status after a few minutes.

### 6. Check processor health

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "ollama": "connected",
    "minio": "connected",
    "milvus": "connected",
    "unstructured": "healthy"
  }
}
```

## Usage

### Access the API

The processor API is available at `http://localhost:5000`

### Access MinIO Console

Access your existing MinIO deployment (refer to your MinIO setup for the console URL)

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

## Service Endpoints

The processor uses these endpoints:

- **Unstructured API**: `http://unstructured:8000` (internal Docker network)
- **MinIO**: `localhost:9000` (your external service)
- **Milvus**: `localhost:19530` (your external service)
- **Ollama**: `http://localhost:11434` (your external service)

The processor container can access localhost services via `host.docker.internal`.

## Troubleshooting

### Processor fails to start

1. Verify external services are accessible:
   ```bash
   # From your host
   curl http://localhost:11434/  # Ollama
   curl http://localhost:9000/minio/health/live  # MinIO

   # Check if Ollama models are available
   curl http://localhost:11434/api/tags
   ```

2. Check processor logs:
   ```bash
   docker-compose logs processor
   ```

3. Verify Docker network access to host:
   ```bash
   docker exec -it neuroclima-processor curl http://host.docker.internal:11434/
   ```

### Out of memory errors

- Increase Docker memory limit (Docker Desktop → Settings → Resources)
- Reduce concurrent tasks: Set `MAX_CONCURRENT_TASKS=1` in `.env`
- Use smaller models: Change `OLLAMA_MODEL=mistral:7b` to `tinyllama`

### Milvus connection errors

1. Verify Milvus is accessible from host:
   ```bash
   curl http://localhost:19530
   ```

2. Check if processor can reach host services:
   ```bash
   docker exec -it neuroclima-processor ping host.docker.internal
   ```

### Unstructured API timeout

- Increase timeout in `.env`: `UNSTRUCTURED_TIMEOUT=10`
- Check unstructured service logs:
  ```bash
  docker-compose logs unstructured
  ```

## External Service Requirements

Ensure these services are running before starting the processor:

### MinIO (Object Storage)
- Port: 9000
- Credentials configured in `.env`
- Buckets created: researchpapers, policy, news, scientificdata

### Milvus (Vector Database)
- Port: 19530
- Databases created as needed by the application

### Ollama (LLM Service)
- Port: 11434
- Required models downloaded:
  ```bash
  ollama pull mistral:7b
  ollama pull nomic-embed-text
  ollama pull llava:13b  # Optional, for image extraction
  ```

## Data Persistence

Processor data is persisted in Docker volumes:

- `processor_data` - Application data and cache
- `graphrag_data` - GraphRAG knowledge graphs
- `lancedb_data` - LanceDB storage

External service data (MinIO, Milvus, Ollama) is managed by your existing deployments.

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

| Service | Port | Purpose | Location |
|---------|------|---------|----------|
| Processor | 5000 | Main API | Docker |
| Unstructured | 9000 | Document extraction | Docker |
| MinIO | 9000 | Object storage | External |
| Milvus | 19530 | Vector DB | External |
| Ollama | 11434 | LLM API | External |

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
- Verify external services are accessible (MinIO, Milvus, Ollama)
- Check Ollama models: `curl http://localhost:11434/api/tags`
