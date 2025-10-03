# Multi-Session Continuity System - Quick Start Guide

## Prerequisites

- Python 3.10.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional, recommended)

## Option 1: Docker Compose (Recommended)

### 1. Clone and Configure

```bash
cd /Users/liz/Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- FastAPI application (port 8000)
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- Celery worker (background tasks)

### 3. Initialize Database

```bash
docker-compose exec app alembic upgrade head
```

### 4. Access Application

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Option 2: Manual Setup

### 1. Install PostgreSQL and Redis

**macOS (Homebrew):**
```bash
brew install postgresql@14 redis
brew services start postgresql@14
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql-14 redis-server
sudo systemctl start postgresql redis
```

### 2. Create Database

```bash
psql -U postgres
CREATE DATABASE legal_assistant;
CREATE USER legal_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE legal_assistant TO legal_user;
\q
```

### 3. Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate
source venv/bin/activate  # Unix/macOS
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements-new.txt

# Install spaCy model
python -m spacy download en_core_web_sm
```

### 4. Configure Environment

```bash
cp .env.example .env
nano .env
```

Update:
```env
DATABASE_URL=postgresql+asyncpg://legal_user:your_password@localhost:5432/legal_assistant
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=your_anthropic_key_here
SECRET_KEY=generate_with_openssl_rand_hex_32
```

### 5. Initialize Database Schema

```bash
# Run SQL schema
psql -U legal_user -d legal_assistant -f docs/database_schema.sql

# OR use Alembic migrations
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 6. Start Application

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. Start Background Worker (separate terminal)

```bash
source venv/bin/activate
celery -A src.tasks worker --loglevel=info
```

## Testing the System

### 1. Upload a Contract

```bash
curl -X POST "http://localhost:8000/api/v1/contracts/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_contract.docx" \
  -F "source=internal"
```

Response:
```json
{
  "version_id": "123e4567-e89b-12d3-a456-426614174000",
  "session_id": "987fcdeb-51a2-4321-b987-987654321000",
  "filename": "sample_contract.docx",
  "status": "uploaded"
}
```

### 2. Get Analysis

```bash
curl "http://localhost:8000/api/v1/contracts/{version_id}/analysis"
```

### 3. Get Styled Analysis

```bash
curl "http://localhost:8000/api/v1/contracts/{version_id}/analysis?tone=concise&aggressiveness=strict&audience=counterparty"
```

### 4. Compare Versions

```bash
curl "http://localhost:8000/api/v1/versions/{version_id}/comparison?compare_to={other_version_id}"
```

### 5. Get Negotiation History

```bash
curl "http://localhost:8000/api/v1/sessions/{session_id}/negotiation-log"
```

## Using the Interactive API Documentation

Navigate to http://localhost:8000/docs for Swagger UI with:
- Complete API reference
- Try-it-out functionality
- Request/response examples
- Schema documentation

## Common Tasks

### Create New User

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "lawyer@firm.com",
    "full_name": "Jane Smith",
    "role": "editor",
    "organization_id": "org-uuid-here"
  }'
```

### Upload New Policy

```bash
curl -X POST "http://localhost:8000/api/v1/policies" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_identifier": "LP-401",
    "policy_title": "Limitation of Liability Standard",
    "policy_text": "Vendor contracts must include 2× annual fees minimum liability cap",
    "policy_category": "liability"
  }'
```

### Get High-Risk Findings

```bash
curl "http://localhost:8000/api/v1/findings?severity=high,critical&session_id={session_id}"
```

### Accept Suggested Edit

```bash
curl -X PUT "http://localhost:8000/api/v1/edits/{edit_id}/accept" \
  -H "Content-Type: application/json"
```

### Rollback to Previous Version

```bash
curl -X POST "http://localhost:8000/api/v1/versions/{version_id}/rollback" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Reverting unauthorized changes"
  }'
```

## Monitoring

### Check System Health

```bash
curl http://localhost:8000/health
```

### View Logs

```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f db

# Worker logs
docker-compose logs -f celery_worker
```

### Redis Cache Stats

```bash
redis-cli INFO stats
```

### Database Connections

```bash
psql -U legal_user -d legal_assistant -c "SELECT count(*) FROM pg_stat_activity WHERE datname='legal_assistant';"
```

## Development Workflow

### Run Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit

# Integration tests
pytest tests/integration

# With coverage
pytest --cov=src --cov-report=html

# Specific test
pytest tests/unit/test_neutral_rationale_agent.py::test_neutral_rationale_no_prohibited_words
```

### Code Quality

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Lint
flake8 src tests

# Type checking
mypy src
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check credentials
psql -U legal_user -d legal_assistant -c "SELECT 1;"
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Check Redis URL in .env matches
echo $REDIS_URL
```

### Import Errors

```bash
# Ensure you're in virtual environment
which python
# Should show: /path/to/venv/bin/python

# Reinstall dependencies
pip install -r requirements-new.txt --force-reinstall
```

### Claude API Errors

```bash
# Verify API key
echo $ANTHROPIC_API_KEY

# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn src.api.main:app --port 8001
```

## Performance Tuning

### PostgreSQL

```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Create missing indexes
CREATE INDEX CONCURRENTLY idx_name ON table_name(column_name);
```

### Redis Cache Hit Rate

```bash
redis-cli INFO stats | grep keyspace
```

### Application Profiling

```python
# Add to route
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## Security Checklist

- [ ] Change default SECRET_KEY in .env
- [ ] Use strong database passwords
- [ ] Enable HTTPS in production
- [ ] Configure CORS appropriately
- [ ] Implement rate limiting
- [ ] Enable audit logging
- [ ] Regular dependency updates
- [ ] Database backups configured

## Next Steps

1. **Read Full Implementation Guide**: `docs/IMPLEMENTATION_GUIDE.md`
2. **Review Database Schema**: `docs/database_schema.sql`
3. **Check Requirements Document**: Original PDF with all feature specifications
4. **Explore Existing Code**: `Legal_Assistant_Contract_Analysis.ipynb`

## Support

- **Issues**: GitHub Issues
- **Documentation**: `/docs` directory
- **API Reference**: http://localhost:8000/docs

---

**Ready to implement!** Follow the phases in `IMPLEMENTATION_GUIDE.md` for complete system development.
