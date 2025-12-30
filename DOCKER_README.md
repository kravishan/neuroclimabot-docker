# NeuroClima Docker Setup

This directory contains Docker configurations for running the NeuroClima application stack.

## Architecture

The application consists of three main services:

- **Client**: React + Vite frontend served by Nginx
- **Server**: FastAPI backend with RAG capabilities
- **Redis**: Session storage and caching

## Quick Start

### 1. Setup Environment Variables

#### Root Level
```bash
cp .env.example .env
# Edit .env with your configuration
```

#### Server Configuration
```bash
cd Server
cp .env.example .env
# Edit Server/.env with your API keys and configuration
cd ..
```

### 2. Run with Docker Compose

#### Option A: Run All Services (Recommended)
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

#### Option B: Run Individual Services
```bash
# Run only the client
cd Client
docker-compose up -d

# Run only the server (with Redis)
cd Server
docker-compose up -d
```

### 3. Access the Application

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Metrics**: http://localhost:8001/metrics

## Docker Files Overview

### Client
- `Client/Dockerfile`: Multi-stage build for React app
- `Client/docker-compose.yml`: Standalone client setup
- `Client/nginx.conf`: Nginx configuration for serving the app
- `Client/.dockerignore`: Excludes unnecessary files from build

### Server
- `Server/Dockerfile`: Python 3.11 with FastAPI and dependencies
- `Server/docker-compose.yml`: Server + Redis setup
- `Server/.dockerignore`: Excludes unnecessary files from build

### Root
- `docker-compose.yml`: Orchestrates all services together
- `.env.example`: Environment variables template

## Volume Persistence

The following data is persisted in Docker volumes:

- `redis_data`: Redis data and sessions
- `server_data`: SQLite database and uploaded files

To remove volumes (⚠️ destroys all data):
```bash
docker-compose down -v
```

## Health Checks

All services include health checks:

- **Client**: Checks if Nginx is responding
- **Server**: Checks `/api/v1/health` endpoint
- **Redis**: Checks Redis PING command

View health status:
```bash
docker-compose ps
```

## Development vs Production

### Development
The current setup is optimized for development with:
- Hot reload disabled in server
- Debug mode configurable via `.env`
- Exposed ports for all services
- CORS configured for localhost

### Production Recommendations
For production deployment, consider:

1. **Enable HTTPS**: Add SSL certificates and configure Nginx
2. **Secure Redis**: Use strong passwords
3. **Environment Variables**: Use secrets management
4. **Resource Limits**: Add memory and CPU limits
5. **Logging**: Configure log aggregation
6. **Backups**: Implement volume backup strategy

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs [service-name]

# Check health status
docker-compose ps
```

### Port already in use
```bash
# Change ports in docker-compose.yml or .env
# Example: Use port 8080 instead of 80
ports:
  - "8080:80"
```

### Build issues
```bash
# Rebuild without cache
docker-compose build --no-cache

# Remove old images
docker system prune -a
```

### Database issues
```bash
# Reset volumes (⚠️ destroys data)
docker-compose down -v
docker-compose up -d
```

## Updating

To update the application:

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Resource Usage

Typical resource usage:
- **Client**: ~50MB RAM
- **Server**: ~500MB-2GB RAM (depends on ML models)
- **Redis**: ~50-100MB RAM

Adjust based on your needs in `docker-compose.yml`:
```yaml
services:
  server:
    deploy:
      resources:
        limits:
          memory: 2G
```

## Additional Commands

```bash
# View resource usage
docker stats

# Execute commands in container
docker-compose exec server bash
docker-compose exec client sh

# View network configuration
docker network inspect neuroclimabot-docker_neuroclima-network

# Export/backup volumes
docker run --rm -v neuroclimabot-docker_server_data:/data -v $(pwd):/backup alpine tar czf /backup/server_data_backup.tar.gz -C /data .
```
