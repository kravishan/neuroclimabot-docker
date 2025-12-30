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

## Deployment Options

This setup provides **separate docker-compose files** for flexible deployment:

### Option 1: Deploy Everything Together
- **Files**: `docker-compose.server.yml` + `docker-compose.client.yml`
- **Scripts**: `./start.sh` and `./stop.sh`
- **Use Case**: Development, single-server deployment, all-in-one setup

### Option 2: Deploy Server Only (Backend + Redis)
- **File**: `docker-compose.server.yml`
- **Scripts**: `./start-server.sh` and `./stop-server.sh`
- **Use Case**: Backend server deployment, separate frontend hosting, API-only deployment

### Option 3: Deploy Client Only (Frontend)
- **File**: `docker-compose.client.yml`
- **Scripts**: `./start-client.sh` and `./stop-client.sh`
- **Use Case**: Frontend-only deployment, CDN hosting, separate client server

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
MINIO_ENDPOINT=your-milvus-vm-ip-or-hostname:9000
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

Choose one of the following deployment options:

#### Option A: Start Everything (Recommended for Development)

Using the helper script:
```bash
./start.sh
```

Or use Docker Compose directly:
```bash
docker-compose -f docker-compose.server.yml -f docker-compose.client.yml up -d
```

#### Option B: Start Server Only (Backend + Redis)

Using the helper script:
```bash
./start-server.sh
```

Or use Docker Compose directly:
```bash
docker-compose -f docker-compose.server.yml up -d
```

#### Option C: Start Client Only (Frontend)

Using the helper script:
```bash
./start-client.sh
```

Or use Docker Compose directly:
```bash
docker-compose -f docker-compose.client.yml up -d
```

**Note**: When starting client only, make sure the backend is accessible at `http://localhost:8000`

This will:
- Build the necessary Docker images
- Start the selected services
- Set up networking between containers
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
docker-compose -f docker-compose.server.yml -f docker-compose.client.yml logs -f

# Server logs only
docker-compose -f docker-compose.server.yml logs -f server

# Client logs only
docker-compose -f docker-compose.client.yml logs -f client

# Redis logs
docker-compose -f docker-compose.server.yml logs -f redis
```

### Restart Services

```bash
# Restart all services
docker-compose -f docker-compose.server.yml -f docker-compose.client.yml restart

# Restart server only
docker-compose -f docker-compose.server.yml restart server

# Restart client only
docker-compose -f docker-compose.client.yml restart client
```

### Stop Services

```bash
# Stop all services
./stop.sh
# Or: docker-compose -f docker-compose.server.yml -f docker-compose.client.yml down

# Stop server only
./stop-server.sh
# Or: docker-compose -f docker-compose.server.yml down

# Stop client only
./stop-client.sh
# Or: docker-compose -f docker-compose.client.yml down
```

### Stop and Remove All Data

```bash
# Remove server data (Redis, Server volumes)
docker-compose -f docker-compose.server.yml down -v

# Client doesn't have volumes, so just stop it
docker-compose -f docker-compose.client.yml down
```

### Rebuild After Code Changes

```bash
# Rebuild server
docker-compose -f docker-compose.server.yml up -d --build

# Rebuild client
docker-compose -f docker-compose.client.yml up -d --build

# Rebuild all
docker-compose -f docker-compose.server.yml -f docker-compose.client.yml up -d --build
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

Note: You'll still need Redis running. Start it with:
```bash
docker-compose -f docker-compose.server.yml up -d redis
```

## Service Health Checks

Check if all services are healthy:

```bash
# Check all services
docker-compose -f docker-compose.server.yml -f docker-compose.client.yml ps

# Check server services only
docker-compose -f docker-compose.server.yml ps

# Check client service only
docker-compose -f docker-compose.client.yml ps
```

All services should show `healthy` or `running` status.

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.server.yml logs <service-name>

# Restart service
docker-compose -f docker-compose.server.yml restart <service-name>
```

### Port Already in Use

If a port is already in use, you can modify the port mappings in the respective `docker-compose.*.yml` file:

```yaml
ports:
  - "NEW_PORT:CONTAINER_PORT"
```

### Redis Authentication Failed

```bash
# Verify REDIS_PASSWORD is set in Server/.env
cat Server/.env | grep REDIS_PASSWORD

# Check Redis logs
docker-compose -f docker-compose.server.yml logs redis

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
docker-compose -f docker-compose.server.yml logs server
```

### Milvus Connection Issues

- Verify Milvus is running on the external VM
- Check firewall rules allow connections from Docker host
- Verify MILVUS_HOST and MILVUS_PORT in Server/.env
- Check server logs: `docker-compose -f docker-compose.server.yml logs server`

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

### Client Can't Reach Server

If client is deployed separately and can't reach the backend:
- Verify backend is accessible at the configured URL
- Update `VITE_API_BASE_URL` in Client/.env to point to your backend server
- Rebuild client after environment changes: `docker-compose -f docker-compose.client.yml up -d --build`

### Reset Docker Services

```bash
# Reset server + Redis
docker-compose -f docker-compose.server.yml down -v
docker-compose -f docker-compose.server.yml up -d

# Reset client
docker-compose -f docker-compose.client.yml down
docker-compose -f docker-compose.client.yml up -d --build

# Reset all
docker-compose -f docker-compose.server.yml down -v
docker-compose -f docker-compose.client.yml down
./start.sh
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
   - Configure proper resource limits in docker-compose files
   - Enable caching and optimization features
   - Use production-grade reverse proxy (nginx, traefik) with SSL
   - Consider Redis clustering for high availability
   - Optimize Docker host resources
   - Consider separate servers for client and server deployment

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

6. **Separate Deployment**:
   - Client and Server can be deployed on different servers
   - Update `VITE_API_BASE_URL` in Client/.env to point to server's public URL
   - Ensure proper CORS configuration on server for client origin
   - Consider CDN for client static files

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

- `VITE_API_BASE_URL` - Backend API endpoint (update for separate deployment)
- `VITE_AUTH_ENABLED` - Match server auth setting
- `VITE_ENABLE_GRAPH_VISUALIZATION` - Enable graph features

## File Structure

```
neuroclimabot-docker/
├── docker-compose.yml          # Legacy main file (backward compatibility)
├── docker-compose.server.yml   # Server + Redis deployment
├── docker-compose.client.yml   # Client-only deployment
├── start.sh                    # Start all services
├── stop.sh                     # Stop all services
├── start-server.sh             # Start server + Redis only
├── stop-server.sh              # Stop server + Redis
├── start-client.sh             # Start client only
├── stop-client.sh              # Stop client only
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

3. **Separate Deployment**: You can deploy client and server independently using their respective docker-compose files. This allows for:
   - Scaling client and server separately
   - Deploying client on CDN/edge servers
   - Different update cycles for frontend and backend

4. **Network Connectivity**: Ensure Docker containers can reach external services. You may need to:
   - Configure firewall rules on external VMs
   - Use Docker host network mode if on the same host
   - Set up VPN or secure network for inter-service communication

5. **Data Persistence**: Redis and server data are persisted in Docker volumes. Back up these volumes regularly.

6. **Environment Files**: The `.env` files contain sensitive information and are not committed to git. You must configure them manually.

## Support

For issues and questions:
1. Check the logs using the appropriate docker-compose file
2. Review the troubleshooting section above
3. Check Docker and Docker Compose versions
4. Ensure sufficient system resources
5. Verify external services are accessible

## License

[Your License Here]
