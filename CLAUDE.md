# CLAUDE.md - NeuroClima Bot AI Assistant Guide

This document provides comprehensive guidance for AI assistants working with the NeuroClima Bot codebase.

## Project Overview

**NeuroClima Bot** is an AI-powered document analysis and knowledge management system designed for climate-related research. It uses a microservices architecture with three main components:

- **Client**: React 19 frontend with Vite, Tailwind CSS
- **Server**: FastAPI backend for RAG (Retrieval-Augmented Generation), authentication, and API management
- **Processor**: FastAPI service for document processing, GraphRAG knowledge graphs, and STP classification

### Key Features
- RAG with Milvus vector database and GraphRAG integration
- Multi-language support (English, Italian, Portuguese, Greek)
- Social Tipping Points (STP) classification
- Document processing for research papers, news, and scientific data
- Real-time session management with WebSocket support
- LLM observability via Langfuse

## Architecture

```
neuroclimabot-docker/
├── Client/                 # React frontend (Vite + Tailwind CSS)
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API clients
│   │   ├── locales/        # i18n translation files
│   │   └── routes/         # Router configuration
│   ├── Dockerfile
│   └── package.json
│
├── Server/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── config/         # Configuration management
│   │   ├── core/           # Middleware, dependencies, exceptions
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic
│   │   │   ├── rag/        # RAG pipeline
│   │   │   ├── llm/        # LLM integrations
│   │   │   ├── auth/       # Authentication
│   │   │   ├── memory/     # Session management
│   │   │   ├── tracing/    # Langfuse integration
│   │   │   └── external/   # Milvus, MinIO, GraphRAG clients
│   │   ├── repositories/   # Data access layer
│   │   └── utils/          # Utilities
│   ├── Dockerfile
│   └── requirements.txt
│
├── Processor/              # Document processing service
│   ├── api/                # REST API endpoints
│   ├── processors/         # Document processing pipelines
│   ├── storage/            # Database and vector storage
│   ├── services/           # Processing services
│   ├── graphrag/           # GraphRAG configuration
│   ├── stp/                # Social Tipping Points classification
│   ├── Dockerfile
│   └── requirements.txt
│
├── k8s/                    # Kubernetes deployment configs
├── docker-compose.yml      # Docker orchestration
└── redis.conf              # Redis configuration
```

## Tech Stack

### Backend (Server & Processor)
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11 | Runtime |
| FastAPI | 0.115+ | API Framework |
| Pydantic | 2.11 | Data validation |
| SQLAlchemy | 2.0 | ORM |
| Redis | 7 | Session/cache |
| Milvus | 2.5 | Vector database |
| GraphRAG | 2.2.1 | Knowledge graphs |
| LangChain | 0.3.x | LLM orchestration |
| Langfuse | 3.0.9 | LLM observability |
| Sentence Transformers | 4.1 | Embeddings |

### Frontend (Client)
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.0 | UI Framework |
| Vite | 6.2 | Build tool |
| Tailwind CSS | 4.0 | Styling |
| i18next | 24.x | Internationalization |
| Axios | 1.8 | HTTP client |
| React Router | 7.3 | Routing |
| D3.js/Three.js | Latest | Graph visualization |

### Infrastructure
- **Docker**: Containerization with multi-stage builds
- **Docker Compose**: Local orchestration
- **Kubernetes**: Production deployment
- **Nginx**: Frontend web server

## Development Commands

### Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# Start with logs
docker-compose up

# Rebuild specific service
docker-compose up -d --build processor

# View logs
docker-compose logs -f server
docker-compose logs -f processor
docker-compose logs -f client

# Stop all services
docker-compose down

# Stop and remove volumes (deletes data)
docker-compose down -v
```

### Frontend Development (Client)
```bash
cd Client
npm install           # Install dependencies
npm run dev           # Start dev server with hot reload
npm run build         # Production build
npm run lint          # Run ESLint
npm run preview       # Preview production build
```

### Backend Development (Server)
```bash
cd Server
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Processor Development
```bash
cd Processor
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

## Code Conventions

### Python (Server & Processor)

#### File Organization
- **API endpoints**: `api/v1/*.py` - One file per resource/domain
- **Business logic**: `services/` - Organized by domain
- **Data models**: `models/` for SQLAlchemy, `schemas/` for Pydantic
- **Configuration**: `config/` with separate files per concern

#### Naming Conventions
```python
# Files: snake_case.py
auth_service.py
milvus_client.py

# Classes: PascalCase
class ConversationOrchestrator:
class MilvusClient:

# Functions/methods: snake_case
async def get_conversation_history():
def validate_session():

# Constants: UPPER_SNAKE_CASE
SESSION_TIMEOUT_SECONDS = 3600
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
```

#### Async Patterns
```python
# Always use async for I/O operations
async def initialize_services():
    tasks = [
        initialize_milvus(),
        initialize_redis(),
        initialize_minio(),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

# Use dependency injection for services
@router.post("/start")
async def start_conversation(
    request: ChatRequest,
    token: str = Depends(require_auth),
    orchestrator = Depends(get_conversation_orchestrator),
):
```

#### Error Handling
```python
# Use HTTPException for API errors
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Session not found"
)

# Log errors with context
logger.error(f"Error processing document {doc_id}: {str(e)}", exc_info=True)
```

#### Pydantic Schemas
```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[UUID] = None
    difficulty_level: Optional[str] = "low"
    include_sources: bool = True
```

### JavaScript/React (Client)

#### File Organization
```
src/
├── components/
│   ├── common/           # Shared components (ErrorBoundary, etc.)
│   ├── layout/           # Header, Footer, navigation
│   ├── auth/             # Authentication components
│   └── consent/          # Privacy/consent components
├── pages/                # Route-level components
├── hooks/                # Custom hooks (useAuth, useLanguage, useSession)
├── services/             # API service functions
├── locales/              # i18n translation JSON files
└── routes/               # Route definitions
```

#### Component Patterns
```jsx
// Functional components with hooks
function AppContent() {
  const { selectedLanguage, changeLanguage } = useLanguage()
  const [difficultyLevel, setDifficultyLevel] = useState('low')

  // Effects
  useEffect(() => {
    // Side effects
  }, [dependencies])

  return (
    <div className="app-container">
      {/* JSX */}
    </div>
  )
}

export default AppContent
```

#### Import Aliases
```jsx
// Use @ alias for src directory
import { useLanguage } from '@/hooks/useLanguage'
import Header from '@/components/layout/Header'
import AppRoutes from '@/routes/AppRoutes'
```

#### Styling with Tailwind
```jsx
// Use Tailwind utility classes
<div className={`app-container ${isHomePage ? 'blurred-bg' : ''}`}>
  <main className="main-content">
    {/* Content */}
  </main>
</div>
```

## Configuration

### Environment Files
Each service requires a `.env` file. Copy from `.env.example`:

```bash
cp Client/.env.example Client/.env
cp Server/.env.example Server/.env
cp Processor/.env.example Processor/.env
```

### Key Configuration Areas

#### Server (`Server/.env`)
- **Database**: SQLite for auth, Milvus for vectors
- **LLM**: OpenAI-compatible API configuration
- **Redis**: Session management
- **Langfuse**: Tracing (optional)
- **RAG**: Pipeline parameters

#### Processor (`Processor/.env`)
- **MinIO**: Object storage credentials
- **Milvus**: Vector database connection
- **GraphRAG**: Knowledge graph settings
- **STP**: Social Tipping Points configuration
- **Chunking**: Document processing parameters

#### Client (`Client/.env`)
- **API endpoints**: Server and Processor URLs
- **Feature flags**: Voice model, graph visualization
- **Session**: Timeout settings

### Configuration Import Pattern (Server)
```python
# Preferred import
from app.config import get_settings, Settings

settings = get_settings()

# Database configs
from app.config.database import get_milvus_config, get_redis_config
milvus_config = get_milvus_config()
```

## API Structure

### Server API (`/api/v1/`)
| Endpoint | File | Purpose |
|----------|------|---------|
| `/chat/*` | `chat.py` | Conversation management |
| `/auth/*` | `auth.py` | Authentication (token-based) |
| `/graph/*` | `graph.py` | GraphRAG queries |
| `/feedback/*` | `feedback.py` | User feedback |
| `/analytics/*` | `analytics.py` | Usage analytics |
| `/health` | `health.py` | Health checks |
| `/admin/*` | `admin.py` | Admin operations |

### Processor API
| Endpoint | Purpose |
|----------|---------|
| `/` | Service info |
| `/health` | Health check |
| `/process/*` | Document processing |
| `/search/*` | RAG/STP search |
| `/graphrag/*` | GraphRAG operations |
| `/translate/*` | Translation service |

## External Services

The system connects to these external services (typically on host machine):

| Service | Default Port | Purpose |
|---------|--------------|---------|
| MinIO | 9000 | Object storage |
| Milvus | 19530 | Vector database |
| Ollama | 11434 | Local LLM (optional) |

Access from Docker containers via `host.docker.internal`.

## Common Tasks

### Adding a New API Endpoint (Server)

1. Create/update schema in `app/schemas/`:
```python
# app/schemas/my_feature.py
class MyFeatureRequest(BaseModel):
    field: str

class MyFeatureResponse(BaseModel):
    result: str
```

2. Add endpoint in `app/api/v1/`:
```python
# app/api/v1/my_feature.py
from fastapi import APIRouter, Depends
from app.schemas.my_feature import MyFeatureRequest, MyFeatureResponse

router = APIRouter()

@router.post("/", response_model=MyFeatureResponse)
async def my_endpoint(request: MyFeatureRequest):
    return MyFeatureResponse(result="success")
```

3. Register in router (`app/api/v1/router.py`):
```python
from app.api.v1 import my_feature
api_router.include_router(my_feature.router, prefix="/my-feature", tags=["my-feature"])
```

### Adding a New React Component (Client)

1. Create component file:
```jsx
// src/components/MyComponent/MyComponent.jsx
import React from 'react'
import { useTranslation } from 'react-i18next'

function MyComponent({ prop1, prop2 }) {
  const { t } = useTranslation()

  return (
    <div className="my-component">
      {t('my.translation.key')}
    </div>
  )
}

export default MyComponent
```

2. Add translations to `src/locales/*/translation.json`

### Adding a New Document Processor (Processor)

1. Create processor in `processors/`:
```python
# processors/my_processor.py
class MyProcessor:
    async def process(self, document):
        # Processing logic
        return processed_result
```

2. Register in pipeline or service container

## Testing

### Health Check Endpoints
```bash
# Server
curl http://localhost:8000/api/v1/health

# Processor
curl http://localhost:5000/health

# Client (Nginx)
curl http://localhost/
```

### Container Access
```bash
# Access container shell
docker exec -it neuroclima-server /bin/bash
docker exec -it neuroclima-processor /bin/bash

# Check logs
docker-compose logs -f server
```

## Key Patterns

### Service Initialization (Server)
Services initialize at startup via `lifespan` context manager in `app/main.py`:
- Langfuse tracing
- Authentication service
- Milvus vector database
- MinIO object storage
- RAG service
- Session manager
- GraphRAG client

### Translation Flow
All translation logic is centralized in `app/api/v1/helpers/translation.py`:
1. Auto-detect input language
2. Translate to English for RAG processing
3. Process with RAG pipeline
4. Translate response back to user's language

### Session Management
- Redis-based session storage
- WebSocket for real-time countdown
- Automatic cleanup on disconnect
- Configurable timeout via environment variables

## Troubleshooting

### Common Issues

1. **Services won't start**: Check Docker resources and logs
```bash
docker-compose logs
docker stats
```

2. **Can't connect to external services**: Verify host services are running
```bash
curl http://localhost:11434/  # Ollama
curl http://localhost:9000/minio/health/live  # MinIO
```

3. **Port conflicts**: Check what's using ports
```bash
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

4. **Build failures**: Clean Docker cache
```bash
docker-compose build --no-cache
docker system prune -a
```

## Important Notes for AI Assistants

1. **Always check existing patterns** before adding new code - this codebase has established conventions

2. **Environment variables** are critical - never hardcode credentials or URLs

3. **Async everywhere** - Use async/await for all I/O operations in Python

4. **Translation is centralized** - Don't add translation logic in individual endpoints

5. **Feature flags** - Check `.env.example` files for available feature toggles

6. **GraphRAG is optional** - The system should work without it enabled

7. **Multi-language support** - All user-facing text should use i18n (frontend) or be translatable (backend)

8. **Pydantic v2** - Use Pydantic v2 syntax for schemas

9. **Docker-first** - Development typically happens via Docker Compose

10. **Configuration hierarchy**: Database configs use `app/config/database.py`, feature configs use `app/config/features.py`, etc.
