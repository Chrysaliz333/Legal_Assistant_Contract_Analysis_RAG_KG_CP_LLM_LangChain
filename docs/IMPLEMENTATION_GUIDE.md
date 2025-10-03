# Legal Assistant Multi-Session Continuity - Implementation Guide

## Overview

This document provides a comprehensive, step-by-step implementation guide for transforming the existing Jupyter notebook-based contract analysis tool into a production-ready multi-agent system with stateful negotiation tracking.

## Table of Contents

1. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
2. [Phase 2: Database & Models](#phase-2-database--models)
3. [Phase 3: Core Agents](#phase-3-core-agents)
4. [Phase 4: API Development](#phase-4-api-development)
5. [Phase 5: Testing & Validation](#phase-5-testing--validation)
6. [Phase 6: Deployment](#phase-6-deployment)

---

## Phase 1: Foundation Setup

### 1.1 Environment Configuration

**File: `config/settings.py`**
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Legal Assistant Multi-Session"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL: int = 3600  # 1 hour cache TTL

    # Claude API
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.3

    # Vector Database
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # File Storage
    FILE_STORAGE_PATH: str = "./storage"
    MAX_FILE_SIZE_MB: int = 50

    # Background Tasks
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**File: `.env.example`**
```env
# Application
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/legal_assistant
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Security
SECRET_KEY=your_secret_key_here_generate_with_openssl_rand_hex_32

# File Storage
FILE_STORAGE_PATH=./storage

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 1.2 Database Initialization

**File: `src/database/connection.py`**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config.settings import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

## Phase 2: Database & Models

### 2.1 Base Model with Common Fields

**File: `src/models/base.py`**
```python
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BaseModel:
    """Base model with common fields"""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
```

### 2.2 User and Organization Models

**File: `src/models/users.py`**
```python
from sqlalchemy import Column, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from .base import Base, BaseModel

class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    REVIEWER = "reviewer"
    EDITOR = "editor"
    APPROVER = "approver"
    ADMIN = "admin"

class User(Base, BaseModel):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.organization_id"))
    is_active = Column(Boolean, default=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")

class Organization(Base, BaseModel):
    __tablename__ = "organizations"

    organization_id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    default_style_params = Column(JSONB, default={
        "tone": "concise",
        "formality": "legal",
        "aggressiveness": "balanced",
        "audience": "internal"
    })

    # Relationships
    users = relationship("User", back_populates="organization")
    sessions = relationship("NegotiationSession", back_populates="organization")
```

### 2.3 Complete Model Implementation Order

The complete models should be implemented in this order:

1. ✅ `base.py` - Base model class
2. ✅ `users.py` - User and Organization
3. `sessions.py` - NegotiationSession, DocumentVersion
4. `clauses.py` - Clause, Annotation
5. `policies.py` - Policy, PlaybookRule
6. `findings.py` - Finding, NeutralRationale, RationaleTransformation
7. `edits.py` - SuggestedEdit
8. `audit.py` - NegotiationLog, AuditLog, RejectedClause
9. `intelligence.py` - Counterparty, CounterpartyProfile, Obligation
10. `drift.py` - DriftAlert, ExceptionPattern

---

## Phase 3: Core Agents

### 3.1 Agent Architecture

The system uses LangGraph for multi-agent orchestration. Each agent is a specialized component:

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                        │
│                      (LangGraph)                             │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├──> Diligent Reviewer Agent
               │    └──> Policy checking & deviation flagging
               │
               ├──> Neutral Rationale Agent
               │    └──> Evidence-grounded explanations
               │
               ├──> Personality Agent
               │    └──> Style transformation (tone, formality)
               │
               ├──> Editor Agent
               │    └──> Track-change generation
               │
               └──> Policy Drift Agent
                    └──> Background monitoring
```

### 3.2 Diligent Reviewer Agent (REQ-DR-001 to REQ-DR-005)

**File: `src/agents/diligent_reviewer.py`**

```python
from typing import List, Dict, Optional
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
import json

class PolicyDeviation(BaseModel):
    clause_id: str
    policy_id: str
    deviation_type: str  # missing_clause, excessive_value, prohibited_term, incomplete_requirement
    severity: str  # low, medium, high, critical
    evidence_quote: str
    policy_requirement: str

class DiligentReviewerAgent:
    """
    REQ-DR-001: Policy Checking with Severity Labels
    REQ-DR-002: Auto-Detection of Compliance
    REQ-DR-003: Evidence Anchoring for High-Risk Findings
    REQ-DR-004: Structured Findings Output
    REQ-DR-005: Traceability with Provenance Logging
    """

    def __init__(self, llm: ChatAnthropic, policy_repository, embedding_service):
        self.llm = llm
        self.policy_repository = policy_repository
        self.embedding_service = embedding_service

    async def review_contract(
        self,
        contract_text: str,
        clauses: List[Dict],
        policies: List[Dict],
        version_id: str
    ) -> List[Dict]:
        """
        Perform comprehensive policy-based contract review

        Returns: List of structured findings with provenance
        """
        findings = []

        for clause in clauses:
            # Retrieve relevant policies for this clause type
            relevant_policies = await self._get_relevant_policies(
                clause['clause_text'],
                clause.get('clause_type'),
                policies
            )

            # Check each policy against the clause
            for policy in relevant_policies:
                deviation = await self._check_policy_compliance(
                    clause,
                    policy
                )

                if deviation:
                    finding = await self._create_finding(
                        deviation,
                        clause,
                        policy,
                        version_id
                    )
                    findings.append(finding)

        # REQ-DR-002: Mark compliant clauses (silent pass)
        compliant_clauses = self._identify_compliant_clauses(clauses, findings)

        return findings

    async def _check_policy_compliance(
        self,
        clause: Dict,
        policy: Dict
    ) -> Optional[PolicyDeviation]:
        """Check single clause against single policy"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a legal compliance expert. Analyze the contract clause against the policy requirement.

            Return ONLY a JSON object with this structure if there's a deviation:
            {{
                "has_deviation": true,
                "deviation_type": "missing_clause|excessive_value|prohibited_term|incomplete_requirement",
                "severity": "low|medium|high|critical",
                "evidence_quote": "exact quote from clause showing deviation",
                "explanation": "brief objective explanation"
            }}

            Return {{"has_deviation": false}} if the clause is compliant.

            Be strict and objective. Every claim must be supported by evidence."""),
            ("user", """Policy: {policy_text}

            Clause: {clause_text}

            Analyze compliance:""")
        ])

        response = await self.llm.ainvoke(
            prompt.format(
                policy_text=policy['policy_text'],
                clause_text=clause['clause_text']
            )
        )

        result = json.loads(response.content)

        if not result.get('has_deviation'):
            return None

        return PolicyDeviation(
            clause_id=clause['clause_id'],
            policy_id=policy['policy_id'],
            deviation_type=result['deviation_type'],
            severity=result['severity'],
            evidence_quote=result['evidence_quote'],
            policy_requirement=policy['policy_text']
        )

    async def _create_finding(
        self,
        deviation: PolicyDeviation,
        clause: Dict,
        policy: Dict,
        version_id: str
    ) -> Dict:
        """
        REQ-DR-004: Create structured finding
        REQ-DR-005: Add provenance information
        """
        import datetime
        from config.settings import settings

        finding = {
            "finding_id": str(uuid4()),
            "schema_version": "1.0",
            "version_id": version_id,
            "clause_id": deviation.clause_id,
            "policy_id": deviation.policy_id,
            "issue_type": "deviation",
            "severity": deviation.severity,
            "evidence_quote": deviation.evidence_quote,
            "policy_requirement": deviation.policy_requirement,
            "provenance": {
                "retrieval_sources": [policy['policy_id']],
                "model_version": settings.CLAUDE_MODEL,
                "analysis_timestamp": datetime.datetime.utcnow().isoformat(),
                "reviewer_id": "diligent_reviewer_agent",
                "confidence_score": 0.95
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        # REQ-DR-003: High-risk findings must have evidence
        if deviation.severity in ['high', 'critical']:
            assert deviation.evidence_quote, "High-risk finding missing evidence"
            assert deviation.policy_id, "High-risk finding missing policy reference"

        return finding

    async def _get_relevant_policies(
        self,
        clause_text: str,
        clause_type: Optional[str],
        all_policies: List[Dict]
    ) -> List[Dict]:
        """Retrieve policies relevant to this clause using semantic search"""

        # Filter by clause type first
        if clause_type:
            policies = [p for p in all_policies if p.get('policy_category') == clause_type]
        else:
            policies = all_policies

        # Use semantic similarity for ranking (if needed)
        # This would use vector embeddings for more sophisticated matching

        return policies[:5]  # Top 5 most relevant

    def _identify_compliant_clauses(
        self,
        all_clauses: List[Dict],
        findings: List[Dict]
    ) -> List[str]:
        """REQ-DR-002: Identify clauses with no deviations (silent pass)"""

        clauses_with_findings = {f['clause_id'] for f in findings}
        all_clause_ids = {c['clause_id'] for c in all_clauses}

        compliant_clause_ids = all_clause_ids - clauses_with_findings

        return list(compliant_clause_ids)
```

### 3.3 Neutral Rationale Agent (REQ-NR-001 to REQ-NR-005)

**File: `src/agents/neutral_rationale.py`**

```python
from typing import Dict, List, Optional
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
import json
from textblob import TextBlob  # For sentiment validation

class NeutralRationaleAgent:
    """
    REQ-NR-001: Neutral Rationale Generation
    REQ-NR-002: Proposed Changes
    REQ-NR-003: Fallback Options
    REQ-NR-004: Strict Separation (no tone/aggressiveness)
    REQ-NR-005: Schema Validation
    """

    # Prohibited words that imply tone/aggressiveness
    PROHIBITED_WORDS = [
        'must', 'should', 'required', 'mandatory', 'essential',
        'consider', 'perhaps', 'might', 'recommend', 'suggest',
        'dangerous', 'unacceptable', 'critical', 'urgent'
    ]

    def __init__(self, llm: ChatAnthropic):
        self.llm = llm

    async def generate_rationale(
        self,
        finding: Dict,
        clause: Dict,
        policy: Dict
    ) -> Dict:
        """
        Generate neutral, evidence-grounded rationale for a finding

        Returns: Neutral rationale conforming to schema
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a neutral legal analyst. Your task is to explain contract deviations objectively.

            CRITICAL RULES:
            1. Use ONLY descriptive language (indicative mood)
            2. NO imperatives (must, should, required)
            3. NO hedging (consider, perhaps, might)
            4. NO subjective terms (dangerous, unacceptable)
            5. Use only: "differs from", "exceeds", "missing", "contradicts"
            6. Every claim must cite evidence from the clause

            Return a JSON object with this EXACT structure:
            {{
                "issue_summary": "One sentence objective description",
                "evidence_quote": "Exact quote from clause",
                "policy_reference": "policy_id",
                "impact_explanation": "Objective explanation of how this differs from policy",
                "proposed_change": {{
                    "change_type": "value_update|text_replacement|clause_insertion|clause_deletion",
                    "current": "current text or value",
                    "proposed": "proposed text or value",
                    "reasoning": "why this change aligns with policy"
                }},
                "fallback_options": [
                    {{
                        "option_text": "alternative wording",
                        "conditions": ["prerequisite 1", "prerequisite 2"],
                        "risk_level": "low|medium|high"
                    }}
                ]
            }}

            Example good explanation:
            "This clause caps liability at 1× fees, which differs from Policy X requiring 2× minimum for vendor contracts."

            Example BAD (never do this):
            "This clause MUST be revised because it's UNACCEPTABLE. We SHOULD increase the cap."
            """),
            ("user", """Finding: {finding}

            Clause: {clause_text}

            Policy: {policy_text}

            Generate neutral rationale:""")
        ])

        response = await self.llm.ainvoke(
            prompt.format(
                finding=json.dumps(finding),
                clause_text=clause['clause_text'],
                policy_text=policy['policy_text']
            )
        )

        rationale_data = json.loads(response.content)

        # REQ-NR-004: Validate neutrality
        self._validate_neutrality(rationale_data)

        # REQ-NR-005: Validate schema
        self._validate_schema(rationale_data)

        # Add metadata
        rationale = {
            "rationale_id": str(uuid4()),
            "finding_id": finding['finding_id'],
            "schema_version": "1.0",
            "neutral_explanation": self._build_neutral_explanation(rationale_data),
            "proposed_change": rationale_data['proposed_change'],
            "fallback_options": rationale_data.get('fallback_options', []),
            "confidence_score": 0.95,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        return rationale

    def _validate_neutrality(self, rationale_data: Dict):
        """REQ-NR-004: Ensure no tone/aggressiveness in neutral rationale"""

        full_text = json.dumps(rationale_data).lower()

        # Check for prohibited words
        found_prohibited = [word for word in self.PROHIBITED_WORDS if word in full_text]
        if found_prohibited:
            raise ValueError(f"Neutral rationale contains prohibited words: {found_prohibited}")

        # Sentiment analysis - must be neutral (polarity between -0.1 and 0.1)
        blob = TextBlob(rationale_data['impact_explanation'])
        if abs(blob.sentiment.polarity) > 0.1:
            raise ValueError(f"Rationale sentiment not neutral: {blob.sentiment.polarity}")

    def _validate_schema(self, rationale_data: Dict):
        """REQ-NR-005: Validate against JSON schema"""

        required_fields = ['issue_summary', 'evidence_quote', 'policy_reference',
                          'impact_explanation', 'proposed_change']

        for field in required_fields:
            if field not in rationale_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate proposed_change structure
        change = rationale_data['proposed_change']
        required_change_fields = ['change_type', 'proposed', 'reasoning']
        for field in required_change_fields:
            if field not in change:
                raise ValueError(f"proposed_change missing field: {field}")

        # Validate fallback_options if present
        if 'fallback_options' in rationale_data:
            for option in rationale_data['fallback_options']:
                if not all(k in option for k in ['option_text', 'conditions', 'risk_level']):
                    raise ValueError("Invalid fallback_option structure")

    def _build_neutral_explanation(self, rationale_data: Dict) -> str:
        """Construct full neutral explanation from components"""

        return f"{rationale_data['issue_summary']} {rationale_data['impact_explanation']}"
```

### 3.4 Personality Agent (REQ-PA-001 to REQ-PA-008)

**File: `src/agents/personality.py`**

```python
from typing import Dict
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
import hashlib

class PersonalityAgent:
    """
    REQ-PA-001: Structured Rationale Persistence (transform without overwriting)
    REQ-PA-002: Tone Control (concise vs verbose, formal vs plain-English)
    REQ-PA-003: Aggressiveness Control (strict vs flexible)
    REQ-PA-004: Audience Mode Switching (internal vs counterparty)
    REQ-PA-005: Multi-Purpose Output (reuse across contexts)
    REQ-PA-006: Default & Override Settings
    REQ-PA-007: Consistency Across Versions
    REQ-PA-008: Explainability (show neutral + styled side-by-side)
    """

    def __init__(self, llm: ChatAnthropic, cache_service):
        self.llm = llm
        self.cache = cache_service  # Redis cache

    async def transform_rationale(
        self,
        neutral_rationale: Dict,
        style_params: Dict,
        finding: Dict
    ) -> Dict:
        """
        Transform neutral rationale based on personality settings

        Args:
            neutral_rationale: The neutral, objective rationale
            style_params: {tone, formality, aggressiveness, audience}
            finding: Associated finding for context

        Returns:
            Transformation record with styled text
        """

        # REQ-PA-001: Check cache first (avoid redundant LLM calls)
        cache_key = self._generate_cache_key(neutral_rationale['rationale_id'], style_params)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Generate transformation prompt based on style parameters
        prompt = self._build_transformation_prompt(style_params)

        # Transform
        response = await self.llm.ainvoke(
            prompt.format(
                neutral_explanation=neutral_rationale['neutral_explanation'],
                proposed_change=json.dumps(neutral_rationale['proposed_change']),
                fallback_options=json.dumps(neutral_rationale.get('fallback_options', [])),
                severity=finding.get('severity', 'medium')
            )
        )

        transformation = {
            "transformation_id": str(uuid4()),
            "rationale_id": neutral_rationale['rationale_id'],
            "style_params": style_params,
            "transformed_text": response.content,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        # Cache for 1 hour
        await self.cache.set(cache_key, transformation, ttl=3600)

        return transformation

    def _build_transformation_prompt(self, style_params: Dict) -> ChatPromptTemplate:
        """Build prompt based on style parameters"""

        # REQ-PA-002: Tone control
        tone_instruction = self._get_tone_instruction(style_params['tone'])

        # REQ-PA-003: Aggressiveness control
        aggressiveness_instruction = self._get_aggressiveness_instruction(
            style_params['aggressiveness']
        )

        # REQ-PA-004: Audience mode
        audience_instruction = self._get_audience_instruction(
            style_params['audience']
        )

        # REQ-PA-002: Formality
        formality_instruction = self._get_formality_instruction(
            style_params['formality']
        )

        system_message = f"""You are transforming neutral legal analysis into a specific communication style.

{tone_instruction}

{aggressiveness_instruction}

{audience_instruction}

{formality_instruction}

Transform the neutral explanation below according to these guidelines.
Maintain factual accuracy. Do not add information not present in the source.
"""

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", """Neutral Explanation: {neutral_explanation}

Proposed Change: {proposed_change}

Fallback Options: {fallback_options}

Severity: {severity}

Transform according to the style guidelines above:""")
        ])

    def _get_tone_instruction(self, tone: str) -> str:
        """REQ-PA-002: Tone control instructions"""

        if tone == "concise":
            return """TONE: Concise
- Maximum 50 words
- Direct, brief statements
- No elaboration unless critical
- Example: "Clause caps liability at 1× fees. Policy requires 2×. Increase to 2×."
"""
        elif tone == "verbose":
            return """TONE: Verbose
- Maximum 500 words
- Include legal precedents and context
- Explain implications thoroughly
- Reference policy reasoning
- Example: "The limitation of liability clause in Section 5.2 establishes a cap of 1× annual fees, which represents a deviation from our organizational playbook Policy LP-401 that mandates a minimum 2× multiplier for vendor contracts. This policy is based on..."
"""
        else:  # balanced
            return """TONE: Balanced
- 100-200 words
- Clear explanation with key context
- Brief policy reference
"""

    def _get_aggressiveness_instruction(self, aggressiveness: str) -> str:
        """REQ-PA-003: Aggressiveness control"""

        if aggressiveness == "strict":
            return """AGGRESSIVENESS: Strict
- Use mandatory language: "must revise", "required edit", "non-negotiable"
- Present as firm requirement
- DO NOT mention fallback options
- Position: "This change is required for approval"
"""
        elif aggressiveness == "flexible":
            return """AGGRESSIVENESS: Flexible
- Use preference language: "recommend considering", "preferred approach"
- Present fallback options clearly
- Position: "We prefer X, but Y is acceptable if Z"
- Collaborative tone
"""
        else:  # balanced
            return """AGGRESSIVENESS: Balanced
- Use clear but not absolutist language
- Mention fallbacks if available
- Position: "This change aligns with policy. Alternatives exist under specific conditions."
"""

    def _get_audience_instruction(self, audience: str) -> str:
        """REQ-PA-004: Audience mode switching"""

        if audience == "internal":
            return """AUDIENCE: Internal Legal Team
- Use legal abbreviations: LoL, IP, SLA, etc.
- Reference policy IDs (e.g., "LP-401")
- Use internal shorthand
- Include technical legal terminology
- Example: "LoL cap at 1× (Policy LP-401 req 2× for vendor)"
"""
        else:  # counterparty
            return """AUDIENCE: Counterparty/External Counsel
- Spell out all abbreviations
- No internal policy IDs (use descriptive references)
- Plain English where possible
- Business context over legal jargon
- Example: "The liability limitation of 1× annual fees is below our standard 2× requirement for vendor agreements"
"""

    def _get_formality_instruction(self, formality: str) -> str:
        """REQ-PA-002: Formality control"""

        if formality == "legal":
            return """FORMALITY: Legal/Technical
- Use precise legal terminology
- Formal sentence structure
- Citations and references
- Example: "The aforesaid limitation of liability provision contained in Section 5.2 herein..."
"""
        else:  # plain_english
            return """FORMALITY: Plain English
- Conversational but professional
- Avoid legalese
- Use analogies where helpful
- Example: "The liability cap in Section 5.2 is like having insurance that only covers half the potential loss..."
"""

    def _generate_cache_key(self, rationale_id: str, style_params: Dict) -> str:
        """Generate cache key for transformation"""

        # Create deterministic hash of rationale_id + style_params
        params_str = json.dumps(style_params, sort_keys=True)
        cache_input = f"{rationale_id}:{params_str}"
        cache_hash = hashlib.sha256(cache_input.encode()).hexdigest()

        return f"transformation:{cache_hash}"
```

---

## Phase 4: API Development

### 4.1 FastAPI Application Structure

**File: `src/api/main.py`**

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from config.settings import settings
from src.database.connection import init_db
from src.api.routes import (
    contracts,
    versions,
    findings,
    edits,
    sessions,
    users,
    policies
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    # Close database connections, etc.

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(contracts.router, prefix="/api/v1/contracts", tags=["contracts"])
app.include_router(versions.router, prefix="/api/v1/versions", tags=["versions"])
app.include_router(findings.router, prefix="/api/v1/findings", tags=["findings"])
app.include_router(edits.router, prefix="/api/v1/edits", tags=["edits"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(policies.router, prefix="/api/v1/policies", tags=["policies"])

@app.get("/")
async def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### 4.2 Contract Analysis Endpoint

**File: `src/api/routes/contracts.py`**

```python
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.database.connection import get_db
from src.services.contract_service import ContractService
from src.services.document_processor import DocumentProcessor
from src.agents.diligent_reviewer import DiligentReviewerAgent
from src.agents.neutral_rationale import NeutralRationaleAgent
from src.agents.personality import PersonalityAgent
from pydantic import BaseModel
import hashlib

router = APIRouter()

class ContractUploadResponse(BaseModel):
    version_id: str
    session_id: str
    filename: str
    status: str

@router.post("/upload", response_model=ContractUploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    session_id: str = None,
    source: str = "internal",
    db: AsyncSession = Depends(get_db)
):
    """
    REQ-VC-001: Upload contract and create new version
    """

    # Read file
    content = await file.read()

    # Calculate hash (SHA-256)
    document_hash = hashlib.sha256(content).hexdigest()

    # Save file
    doc_processor = DocumentProcessor()
    file_path = await doc_processor.save_file(content, file.filename)

    # Extract text
    contract_text = await doc_processor.extract_text(file_path)

    # Create version
    contract_service = ContractService(db)
    version = await contract_service.create_version(
        session_id=session_id,
        filename=file.filename,
        file_path=file_path,
        document_hash=document_hash,
        source=source
    )

    # Trigger analysis asynchronously
    # (In production, this would use Celery)
    from src.services.analysis_service import AnalysisService
    analysis_service = AnalysisService(db)
    await analysis_service.analyze_contract_async(version.version_id, contract_text)

    return ContractUploadResponse(
        version_id=str(version.version_id),
        session_id=str(version.session_id),
        filename=file.filename,
        status="uploaded"
    )

@router.get("/{version_id}/analysis")
async def get_contract_analysis(
    version_id: str,
    style_params: dict = None,  # Optional personality overrides
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete contract analysis with styled rationale
    """

    from src.services.analysis_service import AnalysisService

    analysis_service = AnalysisService(db)
    analysis = await analysis_service.get_analysis(
        version_id,
        style_params=style_params
    )

    return analysis
```

---

## Phase 5: Testing & Validation

### 5.1 Unit Testing Example

**File: `tests/unit/test_neutral_rationale_agent.py`**

```python
import pytest
from src.agents.neutral_rationale import NeutralRationaleAgent
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_neutral_rationale_no_prohibited_words():
    """REQ-NR-004: Ensure neutral rationale contains no tone/aggressiveness words"""

    # Mock LLM
    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value=Mock(
        content='{"issue_summary": "Clause differs from policy", ...}'
    ))

    agent = NeutralRationaleAgent(mock_llm)

    finding = {"finding_id": "test-123", "severity": "high"}
    clause = {"clause_text": "Liability cap at 1x fees"}
    policy = {"policy_text": "Require 2x fees minimum"}

    rationale = await agent.generate_rationale(finding, clause, policy)

    # Check no prohibited words
    full_text = str(rationale).lower()
    prohibited_found = [w for w in agent.PROHIBITED_WORDS if w in full_text]

    assert not prohibited_found, f"Found prohibited words: {prohibited_found}"

@pytest.mark.asyncio
async def test_neutral_rationale_schema_validation():
    """REQ-NR-005: Ensure all rationale conforms to schema"""

    # Test implementation...
    pass
```

### 5.2 Integration Testing Example

**File: `tests/integration/test_contract_upload_flow.py`**

```python
import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
async def test_complete_contract_upload_and_analysis():
    """Test complete flow: upload → analysis → findings → styled rationale"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Upload contract
        with open("tests/fixtures/sample_contract.docx", "rb") as f:
            response = await client.post(
                "/api/v1/contracts/upload",
                files={"file": f}
            )

        assert response.status_code == 200
        version_id = response.json()["version_id"]

        # 2. Wait for analysis (in real system, poll or use webhook)
        await asyncio.sleep(5)

        # 3. Get analysis
        response = await client.get(f"/api/v1/contracts/{version_id}/analysis")
        assert response.status_code == 200

        analysis = response.json()
        assert "findings" in analysis
        assert len(analysis["findings"]) > 0

        # 4. Test personality transformation
        response = await client.get(
            f"/api/v1/contracts/{version_id}/analysis",
            params={
                "tone": "concise",
                "aggressiveness": "strict"
            }
        )

        styled_analysis = response.json()
        # Verify styled text is different from neutral
        assert styled_analysis != analysis
```

---

## Phase 6: Deployment

### 6.1 Docker Setup

**File: `Dockerfile`**

```dockerfile
FROM python:3.10.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-new.txt .
RUN pip install --no-cache-dir -r requirements-new.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application
COPY . .

# Run migrations
RUN alembic upgrade head

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File: `docker-compose.yml`**

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/legal_assistant
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./storage:/app/storage

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=legal_assistant
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery_worker:
    build: .
    command: celery -A src.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/legal_assistant
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

---

## Next Steps

### Immediate Actions

1. **Set up development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements-new.txt
   ```

2. **Initialize database**
   ```bash
   psql -U postgres < docs/database_schema.sql
   alembic init alembic
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

3. **Start implementing models** (see Phase 2.3 for order)

4. **Implement agents** (see Phase 3 for details)

5. **Build API endpoints** (see Phase 4)

6. **Write tests** (see Phase 5)

7. **Deploy** (see Phase 6)

### Priority Order

**Week 1-2: Foundation**
- Database setup and models
- Basic API structure
- Configuration management

**Week 3-4: Core Agents**
- Diligent Reviewer Agent
- Neutral Rationale Agent
- Personality Agent

**Week 5-6: Version Control**
- Document version management
- Annotation system
- Negotiation log

**Week 7-8: Advanced Features**
- Policy drift detection
- Counterparty intelligence
- Obligation extraction

**Week 9-10: Testing & Refinement**
- Comprehensive test suite
- Performance optimization
- Security hardening

**Week 11-12: Deployment**
- Docker containerization
- CI/CD pipeline
- Production deployment

---

## Key Design Principles

1. **Separation of Concerns**
   - Neutral rationale stored separately from styled transformations
   - Each agent has single responsibility

2. **Immutability**
   - Never overwrite neutral rationale
   - All transformations cached separately
   - Complete audit trail

3. **Composability**
   - Agents can be orchestrated in different orders
   - Style transformations composable

4. **Performance**
   - Cache transformed rationale (Redis, 1-hour TTL)
   - Async database operations
   - Background task processing (Celery)

5. **Testability**
   - Pure functions where possible
   - Dependency injection
   - Mock-friendly architecture

---

## Architecture Diagrams

### System Context
```
┌─────────────┐
│   Lawyers   │
│   (Users)   │
└──────┬──────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│        Legal Assistant Platform                │
│  ┌──────────────────────────────────────────┐ │
│  │  FastAPI REST API                        │ │
│  └──────────────┬───────────────────────────┘ │
│                 │                              │
│  ┌──────────────▼───────────────────────────┐ │
│  │  Multi-Agent System (LangGraph)          │ │
│  │  - Diligent Reviewer                     │ │
│  │  - Neutral Rationale Generator           │ │
│  │  - Personality Transformer               │ │
│  │  - Editor                                │ │
│  └──────────────┬───────────────────────────┘ │
│                 │                              │
│  ┌──────────────▼───────────────────────────┐ │
│  │  Data Layer                              │ │
│  │  - PostgreSQL (versions, audit)          │ │
│  │  - Redis (cache, sessions)               │ │
│  │  - Chroma (vector embeddings)            │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
       │
       ▼
┌────────────────┐
│ Claude API     │
│ (Anthropic)    │
└────────────────┘
```

---

## Support & Resources

- **Database Schema**: `docs/database_schema.sql`
- **Requirements**: `requirements-new.txt`
- **Original Notebook**: `Legal_Assistant_Contract_Analysis.ipynb`
- **Requirements Doc**: User-provided PDF (all features mapped to REQ-XX-XXX)

---

## Conclusion

This implementation guide provides a complete roadmap for building the multi-session continuity system. The architecture is designed to be:

- **Scalable**: Async operations, caching, background tasks
- **Maintainable**: Clear separation of concerns, comprehensive tests
- **Extensible**: New agents can be added easily
- **Compliant**: Full audit trail, RBAC, encryption

Follow the phase-by-phase approach, implementing and testing each component before moving to the next. The system can be deployed incrementally, starting with core version control and gradually adding advanced features.
