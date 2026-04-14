# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Data Agent V4** is a multi-tenant SaaS platform for intelligent data analysis powered by AI. It uses a monorepo architecture with Docker Compose orchestration.

- **Backend**: FastAPI + Python 3.11 (backend/)
- **Frontend**: Next.js 14 + TypeScript (frontend/)
- **AI Agent**: LangGraph SQL Agent with MCP protocol (AgentV2/, Agent/)
- **Database**: PostgreSQL with multi-tenant isolation
- **Vector DB**: ChromaDB / Qdrant (for semantic search)
- **Object Storage**: MinIO
- **Semantic Layer**: Cube.js

---

## Common Commands

### Docker (Primary Development Mode)

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend
docker-compose restart frontend

# View logs
docker logs dataagent-backend --tail 50
docker-compose logs -f backend  # Follow logs

# Rebuild a service
docker-compose up backend --build -d
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev          # Dev server (port 3000)
npm run build        # Production build
npm run type-check   # TypeScript type checking
npm test            # Unit tests (Jest)
npm run test:e2e    # E2E tests (Playwright)
```

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8004
```

### Testing

```bash
# Backend tests
cd backend
pytest                              # All tests
pytest tests/api/v1/                # Specific directory
pytest tests/test_tenant_isolation.py -v  # Single file
pytest -m "not slow"              # Exclude slow tests
pytest -k "test_health"            # Match name pattern
pytest --cov=src --cov-report=html  # Coverage report

# Frontend tests
cd frontend
npm test            # Jest unit tests
npm run test:e2e    # Playwright E2E tests
```

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1  # Rollback one migration
```

---

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js dev server |
| Backend API | 8004 | FastAPI service |
| API Docs | 8004/docs | Swagger UI |
| PostgreSQL | 5432 | Database |
| MinIO API | 9000 | Object storage |
| MinIO Console | 9001 | MinIO UI |
| ChromaDB | 8001 | Vector database |
| Qdrant | 6333/6334 | Vector DB (SOTA) |
| Cube.js | 4000 | Semantic layer |
| MCP ECharts | 3033 | Chart service |

---

## Architecture Overview

### Multi-Tenant Isolation (Critical)

All data operations MUST include `tenant_id` filtering:

```python
# WRONG - queries all tenants
query(select(Tenant).all())

# CORRECT - tenant isolated
query(select(Tenant).where(Tenant.tenant_id == current_tenant_id))
```

### Frontend API Call Convention

**ALWAYS use full URLs, never relative paths:**

```typescript
// WRONG
fetch('/api/v1/data-sources')

// CORRECT
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
fetch(`${API_URL}/data-sources`)
```

### Backend Async Pattern

All service functions MUST use async/await:

```python
async def create_tenant(db: AsyncSession, tenant_data: TenantCreate):
    stmt = insert(Tenant).values(**tenant_data.dict())
    result = await db.execute(stmt)
    await db.commit()
```

### FastAPI Route Order

Fixed paths MUST be registered before dynamic paths:

```python
@router.get("/health")      # Fixed path FIRST
@router.get("/{tenant_id}")   # Dynamic path AFTER
```

---

## AI Agent Architecture

### Agent Modules

1. **Agent/** - Original LangGraph SQL Agent
   - Natural language to SQL
   - MCP PostgreSQL integration
   - ECharts visualization

2. **AgentV2/** - Enhanced Agent with SOTA features
   - Multi-agent swarm architecture
   - Semantic layer (Cube.js) integration
   - Middleware system (14 components: loop_detection, error_tracking, time_aggregation, tenant_isolation, sql_security...)
   - Subagents: planner, generator, critic, repair, router
   - Knowledge base with Qdrant + business glossary
   - Self-healing with learning node

### Agent Integration

```python
# Container PYTHONPATH configuration enables these imports:
from Agent.sql_agent import SQLAgent
from AgentV2.sql_agent import SQLAgent as SQLAgentV2
```

The docker-compose.yml mounts:
- `./Agent:/Agent` → Container `/Agent`
- `./AgentV2:/AgentV2` → Container `/AgentV2`
- `PYTHONPATH=/app:/` → Enables imports from root

---

## LLM Provider Configuration

Priority order: DeepSeek → Zhipu AI → OpenRouter

```env
# DeepSeek (default, recommended)
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Zhipu AI (fallback)
ZHIPUAI_API_KEY=sk-xxx

# OpenRouter (optional)
OPENROUTER_API_KEY=sk-xxx
```

---

## Environment Configuration

### Layered Structure

- Root `.env` - Global configuration
- `backend/.env` - Backend-specific
- `frontend/.env.local` - Frontend-specific

### Security Key Generation

```bash
# Generate strong keys
python scripts/generate_keys.py --save

# Verify configuration
python scripts/security_audit.py
```

---

## Known Pitfalls

1. **Variable Naming Conflicts**: Avoid names that shadow modules (e.g., `status`, `id`)
2. **Development Mode**: Uses dev token automatically - check for yellow debug panel
3. **Agent Module Imports**: Require `PYTHONPATH=/app:/` in container
4. **Docker Volume Data**: Stored in named volumes (postgres_data, minio_data, etc.)
5. **Frontend API Calls**: Must use `NEXT_PUBLIC_API_URL`, not relative paths

---

## Module-Specific Documentation

- [Backend](backend/CLAUDE.md) - FastAPI services, API endpoints, data models
- [Frontend](frontend/CLAUDE.md) - Next.js components, state management, routing
- [Agent](Agent/README.md) - LangGraph SQL Agent, MCP integration
- [AgentV2](AgentV2/) - Enhanced multi-agent architecture (see inline docs)

---

## Deployment Data Considerations

When deploying to production, persistent data is stored in Docker named volumes:
- `postgres_data` - Database
- `minio_data` - Object storage
- `chroma_data` / `qdrant_data` - Vector indices
- `./data_storage` - Local directory for uploads

For production, consider using managed services (RDS, S3) instead of Docker volumes.
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-1f8c46bb617f18ba4604adabe9bab069477b273ad6c55b9bc5f51dadccf74117",
    "ANTHROPIC_BASE_URL": "https://api.svips.org",
    "ANTHROPIC_MODEL": "GLM-5"
  }
}