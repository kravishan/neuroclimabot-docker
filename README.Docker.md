# NeuroClima Bot - Complete Docker Setup

This guide explains how to run the complete NeuroClima Bot stack using Docker Compose.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    NeuroClima Stack                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐                                       │
│  │   Client     │  ← Nginx (Port 80)                    │
│  │  (React)     │                                       │
│  └──────┬───────┘                                       │
│         │                                               │
│         ├──────────────┬────────────────┐               │
│         ▼              ▼                ▼               │
│  ┌──────────┐   ┌──────────────┐  ┌──────────┐         │
│  │  Server  │   │  Processor   │  │  Redis   │         │
│  │ (FastAPI)│   │  (FastAPI)   │  │          │         │
│  │  :8000   │   │    :5000     │  │  :6379   │         │
│  └─────┬────┘   └──────┬───────┘  └──────────┘         │
│        │               │                                │
│        └───────────────┴──────────────┐                 │
│                        │               │                │
│                 ┌──────▼──────┐  ┌────▼────┐            │
│                 │Unstructured │  │External │            │
│                 │    :9000    │  │Services │            │
│                 └─────────────┘  └─────────┘            │
│                                  • MinIO                │
│                                  • Milvus               │
│                                  • Ollama               │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required
- Docker (version 20.10+)
- Docker Compose (version 2.0+)

### External Services (Already Deployed)
- **MinIO** - Object storage (port 9000)
- **Milvus** - Vector database (port 19530)
- **Ollama** - LLM service (port 11434)
  - Required models: `mistral:7b`, `nomic-embed-text`

## Quick Start

### 1. Clone and navigate to the repository

```bash
cd /path/to/neuroclimabot-docker
```

### 2. Configure environment variables

Each service has its own `.env` file:

**Processor** (`Processor/.env`):
```bash
# Already configured for Docker
# Update MinIO credentials if needed
ACCESS_KEY=minioadmin
SECRET_KEY=minioadmin
```

**Server** (`Server/.env`):
```bash
# Set Redis password
REDIS_PASSWORD=neuroclima123

# Other configurations...
```

**Client** (`Client/.env`):
```bash
# Usually doesn't need changes
```

### 3. Start the entire stack

```bash
# Start all services
docker-compose up -d

# Or watch the logs
docker-compose up
```

**Startup Order:**
1. **Processor Services** (Unstructured + Processor)
2. **Server Services** (Redis + Server)
3. **Client** (Frontend)

### 4. Verify services are running

```bash
docker-compose ps
```

Expected output:
```
NAME                      STATUS        PORTS
neuroclima-client         Up            0.0.0.0:80->80/tcp
neuroclima-server         Up            0.0.0.0:8000->8000/tcp, 0.0.0.0:8001->8001/tcp
neuroclima-processor      Up            0.0.0.0:5000->5000/tcp
neuroclima-unstructured   Up            0.0.0.0:9000->8000/tcp
neuroclima-redis          Up            0.0.0.0:6379->6379/tcp
```

### 5. Access the application

- **Frontend**: http://localhost
- **Server API**: http://localhost:8000
- **Processor API**: http://localhost:5000
- **Unstructured API**: http://localhost:9000

## Service Details

### Processor Services

| Service | Port | Description |
|---------|------|-------------|
| processor | 5000 | Document processing, GraphRAG, STP classification |
| unstructured | 9000 | Document extraction and parsing |

### Server Services

| Service | Port | Description |
|---------|------|-------------|
| server | 8000 | Main API backend |
| server | 8001 | Metrics endpoint |
| redis | 6379 | Session storage and caching |

### Client Service

| Service | Port | Description |
|---------|------|-------------|
| client | 80 | React frontend (Nginx) |

## Common Commands

### Start services

```bash
# Start all services in background
docker-compose up -d

# Start specific service
docker-compose up -d processor

# Start with logs
docker-compose up
```

### Stop services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop processor
```

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f processor
docker-compose logs -f server
docker-compose logs -f client

# Last 100 lines
docker-compose logs --tail=100 processor
```

### Restart services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart processor
```

### Rebuild services

```bash
# Rebuild all
docker-compose build

# Rebuild specific service
docker-compose build processor

# Rebuild and restart
docker-compose up -d --build processor
```

### Check service health

```bash
# Check status
docker-compose ps

# Check logs for errors
docker-compose logs --tail=50

# Test endpoints
curl http://localhost:5000/health      # Processor
curl http://localhost:8000/api/v1/health  # Server
curl http://localhost/                 # Client
```

## Development Workflow

### Making changes to a service

```bash
# 1. Stop the service
docker-compose stop processor

# 2. Make your code changes

# 3. Rebuild and restart
docker-compose up -d --build processor

# 4. Watch logs
docker-compose logs -f processor
```

### Debugging

```bash
# Access container shell
docker exec -it neuroclima-processor /bin/bash
docker exec -it neuroclima-server /bin/bash

# Check container resources
docker stats

# Inspect container
docker inspect neuroclima-processor
```

## Environment Variables

### Processor Environment

Key variables in `Processor/.env`:
- `OLLAMA_API_URL` - Ollama endpoint (default: http://localhost:11434)
- `MINIO_ENDPOINT` - MinIO endpoint (default: localhost:9000)
- `MILVUS_HOST` - Milvus host (default: localhost)
- `UNSTRUCTURED_API_URL` - Overridden by docker-compose

### Server Environment

Key variables in `Server/.env`:
- `REDIS_PASSWORD` - Redis password
- `DOCUMENT_PROCESSOR_URL` - Overridden to http://processor:5000
- Database and API configurations

### Client Environment

Build-time variables in `Client/.env`:
- `VITE_API_BASE_URL` - Server API URL
- `VITE_API_DOCUMENT_URL` - Processor API URL

## Data Persistence

Data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep neuroclima

# Backup a volume
docker run --rm -v neuroclima_processor_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/processor_backup.tar.gz /data

# Restore a volume
docker run --rm -v neuroclima_processor_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/processor_backup.tar.gz -C /
```

**Volumes:**
- `processor_data` - Processor database and files
- `graphrag_data` - GraphRAG knowledge graphs
- `lancedb_data` - LanceDB storage
- `redis_data` - Redis persistence
- `server_data` - Server database and uploads

## Troubleshooting

### Services won't start

```bash
# Check logs for errors
docker-compose logs

# Check Docker resources
docker system df

# Clean up unused resources
docker system prune -a
```

### Port conflicts

If ports are already in use:

```bash
# Check what's using the port
netstat -ano | findstr :80    # Windows
lsof -i :80                   # Linux/Mac

# Change ports in docker-compose.yml
ports:
  - "8080:80"  # Change 80 to 8080
```

### Can't connect to external services

```bash
# From processor container
docker exec -it neuroclima-processor curl http://host.docker.internal:11434/

# Check if services are accessible from host
curl http://localhost:11434/  # Ollama
curl http://localhost:9000/minio/health/live  # MinIO
curl http://localhost:19530    # Milvus
```

### Out of memory

```bash
# Check memory usage
docker stats

# Increase Docker memory limit:
# Docker Desktop → Settings → Resources → Memory
# Recommended: 8GB minimum
```

### Build failures

```bash
# Clean build cache
docker-compose build --no-cache processor

# Remove old images
docker image prune -a

# Check disk space
docker system df
```

## Production Deployment

For production environments:

1. **Use environment-specific configurations**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

2. **Enable HTTPS**
   - Add nginx reverse proxy
   - Configure SSL certificates
   - Update CORS settings

3. **Set strong passwords**
   - Redis password
   - MinIO credentials
   - Database passwords

4. **Configure resource limits**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

5. **Enable monitoring**
   - Add Prometheus + Grafana
   - Configure health checks
   - Set up log aggregation

## Updating Services

### Pull latest images

```bash
# Pull latest base images
docker-compose pull

# Rebuild with latest code
docker-compose build --no-cache

# Restart with new images
docker-compose up -d
```

### Update a specific service

```bash
# Update processor
docker-compose build --no-cache processor
docker-compose up -d processor
```

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify external services are running (MinIO, Milvus, Ollama)
3. Check resource usage: `docker stats`
4. Review environment variables in `.env` files
5. Ensure all required ports are available
