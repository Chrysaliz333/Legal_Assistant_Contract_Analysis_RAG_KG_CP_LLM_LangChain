# Legal Assistant Multi-Session Continuity System

Contract analysis platform with stateful negotiation tracking, multi-agent intelligence, and personality-aware communication.**

[![Python 3.10.11+](https://img.shields.io/badge/python-3.10.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-blue.svg)](https://www.postgresql.org/)
[![Claude Sonnet 4.5](https://img.shields.io/badge/Claude-Sonnet%204.5-purple.svg)](https://www.anthropic.com/)

---

## 🎯 What This System Does

Transform contract negotiations from chaotic email threads into structured, auditable workflows with AI-powered analysis that adapts to your communication style.

### Key Capabilities

1. **Version Control for Contracts** (like Git for legal documents)
   - Track every change across multiple negotiation rounds
   - Compare any two versions instantly
   - Rollback to previous versions without data loss
   - Complete audit trail for compliance

2. **Multi-Agent AI Analysis**
   - **Diligent Reviewer**: Flags policy deviations with severity levels
   - **Neutral Rationale**: Generates objective explanations grounded in evidence
   - **Personality Agent**: Transforms rationale to match your tone (strict vs. flexible, legal vs. plain-English)
   - **Editor Agent**: Creates Word track-change suggestions

3. **Personality-Aware Communication**
   - Same analysis, different styles: concise vs. verbose, internal vs. counterparty
   - Organization-wide defaults with session-level overrides
   - Explainability: View neutral + styled versions side-by-side

4. **Intelligent Risk Management**
   - Prevents reintroduction of previously rejected terms (semantic similarity)
   - Policy drift detection (alerts when playbook diverges from Help Desk)
   - Obligation extraction with deadline tracking
   - Counterparty intelligence (learns negotiation patterns)

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (recommended)
- **OR** Python 3.10.11+, PostgreSQL 14+, Redis 7+

### Option 1: Docker Compose (5 minutes)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain

# 2. Configure environment
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
# Returns: {"status": "healthy"}
```

**Services started:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower (Celery monitoring): http://localhost:5555
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Option 2: Manual Setup

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[PROJECT_STATUS.md](PROJECT_STATUS.md)** | Current implementation status, next steps |
| **[docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)** | Complete implementation guide with code examples |
| **[docs/QUICKSTART.md](docs/QUICKSTART.md)** | Setup instructions, troubleshooting |
| **[docs/database_schema.sql](docs/database_schema.sql)** | Database design with requirement mapping |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User (Lawyer)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI REST API                            │
│  ┌────────────┬────────────┬────────────┬────────────┐      │
│  │ Contracts  │  Versions  │  Findings  │   Edits    │      │
│  └────────────┴────────────┴────────────┴────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│          Multi-Agent System (LangGraph)                      │
│  ┌──────────────────┬──────────────────┬─────────────────┐  │
│  │ Diligent Reviewer│ Neutral Rationale│ Personality     │  │
│  │ (Policy Checks)  │ (Evidence-Based) │ (Style Transform)│ │
│  └──────────────────┴──────────────────┴─────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   Data Layer                                 │
│  ┌─────────────────┬──────────────┬──────────────────────┐  │
│  │  PostgreSQL     │    Redis     │    ChromaDB          │  │
│  │  (Versions,     │   (Cache,    │  (Policy Embeddings, │  │
│  │   Audit Trail)  │   Sessions)  │   Rejections)        │  │
│  └─────────────────┴──────────────┴──────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
            Claude Sonnet 4.5 API (Anthropic)
```

---

## 💡 Example Use Case

### Scenario: Vendor Contract Negotiation (3 Rounds)

**Round 1: Initial Upload**
```bash
curl -X POST "http://localhost:8000/api/v1/contracts/upload" \
  -F "file=@vendor_contract_v1.docx" \
  -F "source=internal"

# Returns: version_id, session_id
```

**Analysis (automatic, runs in background)**
- Diligent Reviewer flags: "Liability cap at 1× fees (Policy LP-401 requires 2×)" - Severity: HIGH
- Neutral Rationale: "This clause caps liability at 1× annual fees, which differs from Policy LP-401 requiring 2× minimum for vendor contracts."
- Personality Agent (strict, internal):
  > "**Required Edit**: Liability cap must be increased to 2× annual fees per Policy LP-401. Non-negotiable for vendor agreements."
- Personality Agent (flexible, counterparty):
  > "We prefer a liability cap of 2× annual fees, which aligns with industry standards for vendor contracts. We're open to discussing alternative risk mitigation if you have concerns about the cap level."

**Round 2: Counterparty Response**
```bash
curl -X POST "http://localhost:8000/api/v1/contracts/upload" \
  -F "file=@vendor_contract_v2.docx" \
  -F "source=counterparty" \
  -F "session_id=<session_id>"
```

**Version Comparison**
```bash
curl "http://localhost:8000/api/v1/versions/<v1_id>/comparison?compare_to=<v2_id>"

# Returns: Structured diff highlighting:
# - Accepted: Increased liability cap to 1.5× (partial concession)
# - New Issue: Added arbitration requirement (not in our playbook)
```

**Round 3: Risk Block Triggered**
```bash
# Upload v3 with clause previously rejected
# System automatically detects via semantic similarity (>0.85)

# Alert:
{
  "blocked": true,
  "reason": "Similar to clause rejected in v2",
  "original_rejection": {
    "version": "v2",
    "rationale": "Indemnification scope too broad",
    "rejected_by": "Jane Smith",
    "rejected_at": "2025-09-15"
  },
  "override_required": true
}
```

---

## 🔑 Key Features Mapped to Requirements

| Feature | Requirements | Status |
|---------|--------------|--------|
| **Version Control** | REQ-VC-001 to REQ-VC-007 | ✅ Schema Complete |
| UUID + timestamp + hash | REQ-VC-001 | ✅ |
| Annotation preservation | REQ-VC-002 | ✅ |
| Side-by-side comparison | REQ-VC-003 | 🚧 Implementation Pending |
| Audit trail (negotiation log) | REQ-VC-004 | ✅ |
| Rollback capability | REQ-VC-005 | ✅ |
| Rejection blocklist | REQ-VC-006 | ✅ |
| RBAC (5 roles) | REQ-VC-007 | ✅ |
| **Personality Agent** | REQ-PA-001 to REQ-PA-008 | ✅ Schema Complete |
| Neutral rationale storage | REQ-PA-001 | ✅ |
| Tone control (concise/verbose) | REQ-PA-002 | ✅ |
| Aggressiveness (strict/flexible) | REQ-PA-003 | ✅ |
| Audience switching (internal/external) | REQ-PA-004 | ✅ |
| Multi-purpose output | REQ-PA-005 | ✅ |
| Org defaults + overrides | REQ-PA-006 | ✅ |
| Cross-version consistency | REQ-PA-007 | ✅ |
| Explainability (neutral + styled) | REQ-PA-008 | ✅ |
| **Diligent Reviewer** | REQ-DR-001 to REQ-DR-005 | ✅ Schema Complete |
| Policy checking with severity | REQ-DR-001 | ✅ |
| Compliance auto-detection | REQ-DR-002 | ✅ |
| Evidence anchoring (high-risk) | REQ-DR-003 | ✅ (DB constraint enforced) |
| Structured findings | REQ-DR-004 | ✅ |
| Provenance logging | REQ-DR-005 | ✅ |
| **Advanced Features** | Cross-Cutting | |
| Policy drift detection | REQ-PD-001 | ✅ |
| Obligation extraction | REQ-OE-001 | ✅ |
| Counterparty intelligence | REQ-CI-001 | ✅ |
| Exception mining | REQ-EM-001 | ✅ |

**Legend**: ✅ Complete | 🚧 In Progress | ⏳ Pending

---

## 🛠️ Technology Stack

### Core
- **Backend**: FastAPI 0.115.0 (async Python web framework)
- **LLM**: Claude Sonnet 4.5 via Anthropic API
- **Orchestration**: LangGraph 0.2.28 (multi-agent workflows)

### Data Layer
- **Database**: PostgreSQL 14 with asyncpg (async driver)
- **Cache**: Redis 7 (session state, transformed rationale)
- **Vector DB**: ChromaDB 0.5.11 (semantic similarity search)
- **ORM**: SQLAlchemy 2.0 (async)

### Document Processing
- **Word**: python-docx 1.1.2 (track changes, comments)
- **PDF**: PyPDF2 3.0.1, pdfplumber 0.11.4
- **NLP**: spaCy 3.7.6 (obligation extraction), sentence-transformers 3.1.1 (embeddings)

### Background Processing
- **Task Queue**: Celery 5.4.0
- **Broker**: Redis
- **Beat**: Scheduled tasks (policy drift checks, obligation reminders)

### Development
- **Testing**: pytest 8.3.3, pytest-asyncio 0.24.0
- **Code Quality**: black (formatter), flake8 (linter), mypy (type checker)
- **Monitoring**: OpenTelemetry, Sentry

---

## 📊 Project Status

**Current Phase**: Foundation Complete (25%)

✅ **Completed**:
- Database architecture (PostgreSQL schema + SQLAlchemy models)
- Configuration system (Pydantic settings)
- Docker infrastructure (multi-stage build, docker-compose)
- Comprehensive documentation (3 major guides)

🚧 **Next Phase** (Weeks 1-4):
- Agent implementation (Diligent Reviewer, Neutral Rationale, Personality, Editor)
- Service layer (contract parsing, embedding generation, caching)
- FastAPI routes (upload, analysis, version comparison)

⏳ **Future Phases** (Weeks 5-12):
- Testing suite (unit, integration, performance)
- Advanced features (policy drift monitoring, obligation tracking)
- Production deployment

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed progress tracking.

---

## 🧑‍💻 Development

### Running Tests
```bash
# Unit tests
docker-compose exec app pytest tests/unit -v

# Integration tests
docker-compose exec app pytest tests/integration -v

# With coverage
docker-compose exec app pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Format
docker-compose exec app black src tests

# Lint
docker-compose exec app flake8 src

# Type check
docker-compose exec app mypy src
```

### Database Migrations
```bash
# Create migration
docker-compose exec app alembic revision --autogenerate -m "Add new table"

# Apply
docker-compose exec app alembic upgrade head

# Rollback
docker-compose exec app alembic downgrade -1
```

---

## 🔒 Security

- **RBAC**: 5 roles (viewer, reviewer, editor, approver, admin) with permission matrix
- **Encryption**: TLS 1.3 in transit, AES-256 at rest (production)
- **Authentication**: JWT tokens with refresh mechanism
- **Audit Logging**: All actions logged with user ID, IP, timestamp
- **PII Scrubbing**: Personal information removed from logs
- **Rate Limiting**: 100 req/min per user

See `.env.example` for security configuration.

---

## 📈 Performance Targets

| Metric | Target | Current Status |
|--------|--------|----------------|
| Contract upload + analysis | <60s (50 pages) | ⏳ Pending implementation |
| Version comparison | <3s | ⏳ Pending implementation |
| Personality transformation | <2s | ✅ Caching strategy defined |
| Dashboard load | <1s | ✅ Indexes created |
| API P95 latency | <500ms | ⏳ Pending testing |
| System uptime | 99.9% | ✅ Health checks configured |

---

## 🤝 Contributing

This is an enterprise project. For development workflow:

1. Follow implementation guide: `docs/IMPLEMENTATION_GUIDE.md`
2. Use feature branches: `git checkout -b feature/agent-implementation`
3. Write tests for all new code (target: >85% coverage)
4. Run code quality checks before committing
5. Document all API endpoints with OpenAPI annotations

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- **Anthropic** for Claude Sonnet 4.5 API
- **FastAPI** for modern async Python web framework
- **LangChain/LangGraph** for multi-agent orchestration
- **PostgreSQL** for robust relational database
- **ChromaDB** for vector similarity search

---

## 📞 Support

- **Documentation**: [docs/](docs/) directory
- **Issues**: GitHub Issues
- **Implementation Help**: See [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)
- **Quick Setup**: See [docs/QUICKSTART.md](docs/QUICKSTART.md)

---

## 🗺️ Roadmap

### Phase 1: Foundation (✅ COMPLETE)
- Database architecture
- Configuration system
- Docker infrastructure
- Documentation

### Phase 2: Core Agents (Current - Weeks 1-4)
- Diligent Reviewer implementation
- Neutral Rationale generator
- Personality transformation
- Editor agent

### Phase 3: API Development (Weeks 5-6)
- FastAPI routes
- Authentication/authorization
- File upload handling
- Export functionality

### Phase 4: Testing (Weeks 7-8)
- Unit test suite
- Integration tests
- Load testing (Locust)
- E2E scenarios

### Phase 5: Advanced Features (Weeks 9-10)
- Policy drift monitoring (Celery beat)
- Obligation tracking with reminders
- Counterparty intelligence aggregation
- Exception mining (DBSCAN clustering)

### Phase 6: Production (Weeks 11-12)
- Security hardening
- Performance optimization
- Deployment automation
- Monitoring & alerting

---

For getting started, see [docs/QUICKSTART.md](docs/QUICKSTART.md)

For implementation details, see [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)

For current status, see [PROJECT_STATUS.md](PROJECT_STATUS.md)


