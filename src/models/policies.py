"""
Policy and Playbook Rule models
Support for policy-based contract analysis
"""

from sqlalchemy import Column, String, Text, ForeignKey, Boolean, Date, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector  # For semantic search
from .base import Base, BaseModel


class Policy(Base, BaseModel):
    """
    Organization policies for contract review
    REQ-DR-001: Policy checking with deviation flagging
    """

    __tablename__ = "policies"

    policy_id = Column(UUID(as_uuid=True), primary_key=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.organization_id"), index=True
    )
    policy_identifier = Column(String(100), unique=True, nullable=False, index=True)
    policy_title = Column(Text, nullable=False)
    policy_text = Column(Text, nullable=False)
    policy_version = Column(String(50), nullable=False)
    policy_category = Column(String(100), index=True)  # liability, ip, termination, etc.
    effective_date = Column(Date)
    source_system = Column(String(100))  # e.g., "Help Desk"

    # Vector embedding for semantic search
    embedding_vector = Column(Vector(384))  # Dimension for all-MiniLM-L6-v2

    metadata = Column(JSONB, default={})

    # Relationships
    organization = relationship("Organization", back_populates="policies")
    playbook_rules = relationship("PlaybookRule", back_populates="policy", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="policy")
    drift_alerts = relationship("DriftAlert", back_populates="policy")


class PlaybookRule(Base, BaseModel):
    """
    Specific rules derived from policies
    REQ-DR-001: Structured rule evaluation
    REQ-NR-003: Fallback options when allowed
    """

    __tablename__ = "playbook_rules"

    rule_id = Column(UUID(as_uuid=True), primary_key=True)
    policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policies.policy_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_text = Column(Text, nullable=False)
    rule_type = Column(String(100))  # required_clause, value_constraint, prohibited_term
    severity = Column(String(20), index=True)
    allows_alternatives = Column(Boolean, default=False)
    alternative_conditions = Column(JSONB, default=[])

    # Relationships
    policy = relationship("Policy", back_populates="playbook_rules")
    findings = relationship("Finding", back_populates="rule")

    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="valid_severity",
        ),
    )
