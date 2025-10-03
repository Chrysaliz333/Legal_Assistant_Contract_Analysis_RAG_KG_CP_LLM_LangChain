"""
Audit and logging models
REQ-VC-004: Negotiation history log
REQ-VC-006: Rejection blocklist
"""

from sqlalchemy import Column, String, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from pgvector.sqlalchemy import Vector
from .base import Base, BaseModel


class NegotiationLog(Base, BaseModel):
    """
    Comprehensive audit trail of all contract changes
    REQ-VC-004: Consolidated audit trail
    """

    __tablename__ = "negotiation_log"

    log_entry_id = Column(UUID(as_uuid=True), primary_key=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id = Column(
        UUID(as_uuid=True), ForeignKey("document_versions.version_id", ondelete="SET NULL")
    )
    clause_id = Column(
        UUID(as_uuid=True), ForeignKey("clauses.clause_id", ondelete="SET NULL")
    )

    change_type = Column(String(50), nullable=False)
    before_state = Column(JSONB)
    after_state = Column(JSONB)
    rationale_id = Column(UUID(as_uuid=True))  # Reference to neutral_rationale
    source = Column(String(50), nullable=False)
    status = Column(String(50))
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    signature = Column(String(128))  # Optional cryptographic signature

    # Relationships
    session = relationship("NegotiationSession", back_populates="negotiation_logs")
    actor = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "change_type IN ('insertion', 'deletion', 'modification', 'status_change', "
            "'version_creation', 'rollback')",
            name="valid_change_type",
        ),
        CheckConstraint(
            "source IN ('internal', 'counterparty')",
            name="valid_source",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'superseded') OR status IS NULL",
            name="valid_status",
        ),
    )


class RejectedClause(Base, BaseModel):
    """
    Blocklist of rejected clauses to prevent reintroduction
    REQ-VC-006: Risk mitigation via semantic similarity
    """

    __tablename__ = "rejected_clauses"

    rejection_id = Column(UUID(as_uuid=True), primary_key=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        index=True,
    )
    clause_text = Column(Text, nullable=False)
    rejection_rationale = Column(Text, nullable=False)
    rejecting_party = Column(String(50))
    rejected_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # Semantic similarity search
    embedding_vector = Column(Vector(384))

    metadata = Column(JSONB, default={})

    # Relationships
    rejecter = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "rejecting_party IN ('internal', 'counterparty')",
            name="valid_rejecting_party",
        ),
    )


class AuditLog(Base, BaseModel):
    """
    System-wide audit log for all user actions
    REQ-VC-007: RBAC audit logging
    """

    __tablename__ = "audit_log"

    audit_id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), index=True)
    ip_address = Column(INET)
    user_agent = Column(Text)
    request_data = Column(JSONB)
    response_status = Column(Integer)

    # Relationships
    user = relationship("User")
