# NeuroClima Docker Setup

This Docker setup provides a containerized environment for the NeuroClima application. The setup includes only the core application services (Client, Server, Redis), while Milvus, MinIO, and Ollama run on external VMs.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- At least 4GB of available RAM
- External services running on separate VMs:
  - **Milvus** - Vector database (Port 19530)
  - **MinIO** - Object storage (Port 9000)
  - **Ollama** - LLM service (Port 11434)

## Architecture

The Docker Compose setup includes the following containerized services:

1. **Client** - React + Vite frontend (Port 80)
2. **Server** - FastAPI backend (Port 8000, 8001)
3. **Redis** - Session and caching with password authentication (Port 6379)

**External Services** (running on separate VMs):
- **Milvus** - Vector database for embeddings
- **MinIO** - Object storage for documents
- **Ollama** - LLM inference service

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd neuroclimabot-docker
```

### 2. Configure Environment Variables

**IMPORTANT:** You must configure the Server/.env file before starting!

Edit `Server/.env` and update the following:

```bash
# Redis Password (REQUIRED)
REDIS_PASSWORD=your-secure-redis-password-here

# External Milvus Configuration
MILVUS_HOST=your-milvus-vm-ip-or-hostname
MILVUS_PORT=19530

# External MinIO Configuration
MINIO_ENDPOINT=your-minio-vm-ip-or-hostname:9000
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
MINIO_SECURE=true

# External Ollama Configuration
OLLAMA_BASE_URL=http://your-ollama-vm-ip-or-hostname:11434
```

Also configure optional settings:
- API keys (OpenAI, Langfuse, etc.)
- Email configuration
- Security settings (SECRET_KEY)

### 3. Start Docker Services

Using the helper script (recommended):

```bash
./start.sh
```

Or use Docker Compose directly:

```bash
docker-compose up -d
```

This will:
- Build the Client and Server Docker images
- Start Redis with password authentication
- Set up the networking between containers
- Connect to your external Milvus, MinIO, and Ollama services

### 4. Verify External Services

Ensure your external services are accessible from the Docker containers:
- Milvus should be reachable at the configured host:port
- MinIO should be reachable at the configured endpoint
- Ollama should have the required model downloaded

### 5. Access the Application

- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
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

### Redis Authentication Failed

```bash
# Verify REDIS_PASSWORD is set in Server/.env
cat Server/.env | grep REDIS_PASSWORD

# Check Redis logs
docker-compose logs redis

# Test Redis connection
docker exec neuroclima-redis redis-cli -a your-password ping
```

### Cannot Connect to External Services

```bash
# Test connectivity from server container
docker exec neuroclima-server ping your-milvus-host
docker exec neuroclima-server curl http://your-ollama-host:11434
docker exec neuroclima-server curl http://your-minio-host:9000

# Check server logs for connection errors
docker-compose logs server
```

### Milvus Connection Issues

- Verify Milvus is running on the external VM
- Check firewall rules allow connections from Docker host
- Verify MILVUS_HOST and MILVUS_PORT in Server/.env
- Check server logs: `docker-compose logs server`

### MinIO Connection Issues

- Verify MinIO is accessible from Docker host
- Check MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
- Test MinIO connectivity: `curl http://your-minio-host:9000`
- Verify MINIO_SECURE setting (true for HTTPS, false for HTTP)

### Ollama Model Issues

- Verify Ollama is running on external VM
- Check model is downloaded: `ollama list` on Ollama VM
- Verify OLLAMA_BASE_URL in Server/.env
- Check model name matches OLLAMA_MODEL setting

### Reset Docker Services

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
   - Use a strong `REDIS_PASSWORD` (minimum 32 characters)
   - Set a secure `SECRET_KEY` in Server/.env
   - Enable HTTPS/SSL for all services
   - Configure proper CORS settings in Server/.env
   - Enable authentication (`AUTH_ENABLED=true`)
   - Use TLS/SSL for external service connections (MinIO, Milvus)
   - Implement network security groups/firewall rules

2. **Performance**:
   - Configure proper resource limits in docker-compose.yml
   - Enable caching and optimization features
   - Use production-grade reverse proxy (nginx, traefik) with SSL
   - Consider Redis clustering for high availability
   - Optimize Docker host resources

3. **Monitoring**:
   - Enable Langfuse for observability
   - Set up proper logging aggregation (ELK, Loki)
   - Monitor Prometheus metrics at :8001
   - Configure health check endpoints
   - Set up alerts for service failures

4. **Backups**:
   - Regular backups of Redis data volume
   - Server data volume backups (SQLite database)
   - Backup strategy for external Milvus and MinIO
   - Disaster recovery plan
   - Test restore procedures regularly

5. **External Services**:
   - Ensure external services (Milvus, MinIO, Ollama) have proper backups
   - Configure high availability for external services
   - Monitor external service health
   - Set up VPN or secure network for inter-service communication

## Environment Variables

### Server Key Variables (Required)

- `REDIS_PASSWORD` - Redis password for authentication (REQUIRED)
- `REDIS_URL` - Redis connection string with password
- `MILVUS_HOST`, `MILVUS_PORT` - External Milvus vector database
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` - External MinIO object storage
- `MINIO_SECURE` - Use HTTPS for MinIO (true/false)
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL` - External Ollama LLM service
- `SECRET_KEY` - Application secret key for security

### Server Optional Variables

- `OPENAI_API_KEY` - OpenAI API key (alternative to Ollama)
- `AUTH_ENABLED` - Enable/disable authentication (true/false)
- `LANGFUSE_ENABLED` - Enable Langfuse observability
- `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST` - Langfuse config
- `GRAPHRAG_SERVER_URL` - GraphRAG service endpoint
- `TRANSLATION_SERVICE_URL` - Translation service endpoint
- `STP_SERVICE_URL` - Social Tipping Point service endpoint

### Client Key Variables

- `VITE_API_BASE_URL` - Backend API endpoint
- `VITE_AUTH_ENABLED` - Match server auth setting
- `VITE_ENABLE_GRAPH_VISUALIZATION` - Enable graph features

## File Structure

```
neuroclimabot-docker/
├── docker-compose.yml          # Main orchestration file (Redis, Server, Client)
├── start.sh                    # Helper script to start services
├── stop.sh                     # Helper script to stop services
├── Client/
│   ├── Dockerfile              # Client build instructions
│   ├── nginx.conf              # Nginx configuration for React app
│   ├── .dockerignore          # Files to exclude from build
│   └── .env                    # Client environment variables
├── Server/
│   ├── Dockerfile              # Server build instructions
│   ├── .dockerignore          # Files to exclude from build
│   ├── .env                    # Server environment variables (CONFIGURE THIS!)
│   └── app/                    # FastAPI application code
└── DOCKER_README.md            # This file
```

## Important Notes

1. **External Services Required**: This Docker setup requires Milvus, MinIO, and Ollama to be running on external VMs. Configure their endpoints in `Server/.env`.

2. **Redis Password**: Redis runs with password authentication. You must set a strong `REDIS_PASSWORD` in `Server/.env` before starting.

3. **Network Connectivity**: Ensure Docker containers can reach external services. You may need to:
   - Configure firewall rules on external VMs
   - Use Docker host network mode if on the same host
   - Set up VPN or secure networking between services

4. **Data Persistence**: Redis and server data are persisted in Docker volumes. Back up these volumes regularly.

5. **Environment Files**: The `.env` files contain sensitive information and are not committed to git. You must configure them manually.

## Support

For issues and questions:
1. Check the logs: `docker-compose logs`
2. Review the troubleshooting section above
3. Check Docker and Docker Compose versions
4. Ensure sufficient system resources

## License

[Your License Here]
