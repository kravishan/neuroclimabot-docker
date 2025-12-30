# NeuroClima Docker Setup

This Docker setup provides a complete containerized environment for the NeuroClima application, including all required services.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- At least 8GB of available RAM
- At least 20GB of free disk space

## Architecture

The Docker Compose setup includes the following services:

1. **Client** - React + Vite frontend (Port 80)
2. **Server** - FastAPI backend (Port 8000)
3. **Redis** - Session and caching (Port 6379)
4. **Milvus** - Vector database for embeddings (Port 19530)
5. **MinIO** - Object storage for documents (Ports 9000, 9001)
6. **Ollama** - Local LLM service (Port 11434)
7. **etcd** - Milvus dependency

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd neuroclimabot-docker
```

### 2. Configure Environment Variables

Environment files have been created with Docker-friendly defaults:
- `Server/.env` - Backend configuration
- `Client/.env` - Frontend configuration

Review and update these files if needed, especially:
- API keys (OpenAI, Langfuse, etc.)
- Email configuration
- Security settings (SECRET_KEY)

### 3. Start All Services

```bash
docker-compose up -d
```

This will:
- Build the Client and Server Docker images
- Pull and start all required services
- Set up the networking between containers
- Initialize all databases and storage

### 4. Initial Setup

#### Download Ollama Model

After Ollama starts, download the required model:

```bash
docker exec -it neuroclima-ollama ollama pull mistral:7b
```

Or use a different model by updating the `OLLAMA_MODEL` in `Server/.env`

#### Create MinIO Buckets (Optional)

The buckets should be created automatically, but if needed:

```bash
# Access MinIO console at http://localhost:9001
# Login: minioadmin / minioadmin
# Create buckets: researchpapers, news, policies, scientificdata, reports
```

### 5. Access the Application

- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001
- **Prometheus Metrics**: http://localhost:8001

## Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f server
docker-compose logs -f client
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart server
```

### Stop Services

```bash
docker-compose down
```

### Stop and Remove All Data

```bash
docker-compose down -v
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build server
```

## Development Mode

For active development with hot-reload:

### Client Development

```bash
cd Client
npm install
npm run dev
```

Then access at http://localhost:5173

### Server Development

```bash
cd Server
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Note: You'll still need the supporting services (Redis, Milvus, MinIO) running via Docker.

## Service Health Checks

Check if all services are healthy:

```bash
docker-compose ps
```

All services should show `healthy` or `running` status.

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs <service-name>

# Restart service
docker-compose restart <service-name>
```

### Port Already in Use

If a port is already in use, you can modify the port mappings in `docker-compose.yml`:

```yaml
ports:
  - "NEW_PORT:CONTAINER_PORT"
```

### Out of Memory

Milvus and Ollama can be memory-intensive. Increase Docker's memory limit:
- Docker Desktop: Settings → Resources → Memory (recommend 8GB+)

### Ollama Model Not Found

```bash
# Check available models
docker exec neuroclima-ollama ollama list

# Pull required model
docker exec neuroclima-ollama ollama pull mistral:7b
```

### Milvus Connection Issues

```bash
# Check Milvus health
docker-compose logs milvus

# Ensure etcd and MinIO are healthy
docker-compose ps etcd minio
```

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up -d
```

## Production Considerations

Before deploying to production:

1. **Security**:
   - Change all default passwords (MinIO, Redis, etc.)
   - Set a strong `SECRET_KEY` in Server/.env
   - Enable HTTPS/SSL
   - Configure proper CORS settings
   - Enable authentication (`AUTH_ENABLED=true`)

2. **Performance**:
   - Use external managed services for Redis, Milvus
   - Configure proper resource limits
   - Enable caching and optimization features
   - Use production-grade reverse proxy (nginx, traefik)

3. **Monitoring**:
   - Enable Langfuse for observability
   - Set up proper logging aggregation
   - Monitor Prometheus metrics
   - Configure health check endpoints

4. **Backups**:
   - Regular backups of volumes (especially Milvus and MinIO)
   - Database backup strategy
   - Disaster recovery plan

## Environment Variables

### Server Key Variables

- `REDIS_URL` - Redis connection string
- `MILVUS_HOST`, `MILVUS_PORT` - Milvus vector database
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` - Object storage
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL` - LLM configuration
- `OPENAI_API_KEY` - Optional OpenAI integration
- `AUTH_ENABLED` - Enable/disable authentication

### Client Key Variables

- `VITE_API_BASE_URL` - Backend API endpoint
- `VITE_AUTH_ENABLED` - Match server auth setting
- `VITE_ENABLE_GRAPH_VISUALIZATION` - Enable graph features

## File Structure

```
neuroclimabot-docker/
├── docker-compose.yml          # Main orchestration file
├── Client/
│   ├── Dockerfile              # Client build instructions
│   ├── nginx.conf              # Nginx configuration
│   ├── .dockerignore          # Files to exclude from build
│   └── .env                    # Client environment variables
├── Server/
│   ├── Dockerfile              # Server build instructions
│   ├── .dockerignore          # Files to exclude from build
│   └── .env                    # Server environment variables
└── DOCKER_README.md            # This file
```

## Support

For issues and questions:
1. Check the logs: `docker-compose logs`
2. Review the troubleshooting section above
3. Check Docker and Docker Compose versions
4. Ensure sufficient system resources

## License

[Your License Here]
