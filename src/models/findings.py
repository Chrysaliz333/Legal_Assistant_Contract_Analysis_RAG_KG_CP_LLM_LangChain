"""
Finding, Neutral Rationale, and Rationale Transformation models
REQ-DR-004: Structured findings
REQ-NR-001 to REQ-NR-005: Neutral rationale storage
REQ-PA-001: Personality transformations
"""

from sqlalchemy import Column, String, Text, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, BaseModel


class Finding(Base, BaseModel):
    """
    Policy deviation or compliance issue found in contract
    REQ-DR-004: Structured findings with reusable schema
    REQ-DR-005: Provenance logging
    """

    __tablename__ = "findings"

    finding_id = Column(UUID(as_uuid=True), primary_key=True)
    version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.version_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_id = Column(
        UUID(as_uuid=True), ForeignKey("clauses.clause_id", ondelete="SET NULL")
    )
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.policy_id"))
    rule_id = Column(UUID(as_uuid=True), ForeignKey("playbook_rules.rule_id"))

    issue_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)

    # REQ-DR-003: Evidence anchoring for high-risk findings
    evidence_quote = Column(Text)
    policy_requirement = Column(Text)
    suggested_edit = Column(Text)

    # REQ-DR-005: Provenance tracking
    provenance = Column(JSONB, nullable=False)

    # Creator for audit
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # Relationships
    version = relationship("DocumentVersion", back_populates="findings")
    clause = relationship("Clause", back_populates="findings")
    policy = relationship("Policy", back_populates="findings")
    rule = relationship("PlaybookRule", back_populates="findings")
    creator = relationship("User", back_populates="created_findings")
    neutral_rationale = relationship(
        "NeutralRationale", back_populates="finding", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "issue_type IN ('deviation', 'risk', 'compliance', 'missing_clause')",
            name="valid_issue_type",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="valid_severity",
        ),
        # REQ-DR-003: High-risk findings must have evidence
        CheckConstraint(
            "severity NOT IN ('high', 'critical') OR "
            "(evidence_quote IS NOT NULL AND policy_id IS NOT NULL)",
            name="high_severity_requires_evidence",
        ),
    )


class NeutralRationale(Base, BaseModel):
    """
    Neutral, objective rationale for finding
    REQ-NR-001: Evidence-grounded explanations
    REQ-NR-002: Proposed changes
    REQ-NR-003: Fallback options
    REQ-NR-004: Strict separation from tone/aggressiveness
    REQ-NR-005: Schema validation
    """

    __tablename__ = "neutral_rationale"

    rationale_id = Column(UUID(as_uuid=True), primary_key=True)
    finding_id = Column(
        UUID(as_uuid=True),
        ForeignKey("findings.finding_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    schema_version = Column(String(10), default="1.0")
    neutral_explanation = Column(Text, nullable=False)

    # REQ-NR-002: Proposed change structure
    proposed_change = Column(JSONB, nullable=False)

    # REQ-NR-003: Fallback options
    fallback_options = Column(JSONB, default=[])

    confidence_score = Column(Numeric(3, 2))

    # Relationships
    finding = relationship("Finding", back_populates="neutral_rationale")
    transformations = relationship(
        "RationaleTransformation", back_populates="rationale", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="valid_confidence_score",
        ),
    )


class RationaleTransformation(Base, BaseModel):
    """
    Personality-transformed version of neutral rationale
    REQ-PA-001: Structured rationale persistence (separate from neutral)
    REQ-PA-002 to REQ-PA-004: Style parameters
    """

    __tablename__ = "rationale_transformations"

    transformation_id = Column(UUID(as_uuid=True), primary_key=True)
    rationale_id = Column(
        UUID(as_uuid=True),
        ForeignKey("neutral_rationale.rationale_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # REQ-PA-002 to REQ-PA-004: Style parameters
    style_params = Column(JSONB, nullable=False)
    transformed_text = Column(Text, nullable=False)

    # Cache TTL tracking
    cache_ttl = Column(String(100))  # ISO 8601 timestamp

    # Relationships
    rationale = relationship("NeutralRationale", back_populates="transformations")
