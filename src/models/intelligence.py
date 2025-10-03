"""
Counterparty Intelligence and Obligation Tracking models
REQ-CI-001: Counterparty pattern analysis
REQ-OE-001: Obligation extraction
"""

from sqlalchemy import Column, String, Integer, Text, Date, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, BaseModel


class Counterparty(Base, BaseModel):
    """
    External party in contract negotiation
    REQ-CI-001: Counterparty tracking
    """

    __tablename__ = "counterparties"

    counterparty_id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    organization_type = Column(String(100))

    # Relationships
    sessions = relationship("NegotiationSession", back_populates="counterparty")
    profile = relationship(
        "CounterpartyProfile", back_populates="counterparty", uselist=False, cascade="all, delete-orphan"
    )


class CounterpartyProfile(Base, BaseModel):
    """
    Aggregated negotiation patterns for counterparty
    REQ-CI-001: Historical pattern analysis
    """

    __tablename__ = "counterparty_profiles"

    profile_id = Column(UUID(as_uuid=True), primary_key=True)
    counterparty_id = Column(
        UUID(as_uuid=True),
        ForeignKey("counterparties.counterparty_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    contract_count = Column(Integer, default=0)
    typical_positions = Column(JSONB, default={})  # {clause_type: stance}
    common_concessions = Column(JSONB, default=[])  # Array of concession patterns
    avg_cycle_time_days = Column(Numeric(5, 2))

    # Relationships
    counterparty = relationship("Counterparty", back_populates="profile")

    __table_args__ = (
        CheckConstraint(
            "contract_count >= 3",
            name="minimum_contracts_for_profile",
        ),
    )


class Obligation(Base, BaseModel):
    """
    Contractual obligations extracted from clauses
    REQ-OE-001: Obligation identification and tracking
    """

    __tablename__ = "obligations"

    obligation_id = Column(UUID(as_uuid=True), primary_key=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        index=True,
    )
    clause_id = Column(
        UUID(as_uuid=True), ForeignKey("clauses.clause_id", ondelete="SET NULL")
    )

    # Obligation details (actor-action-deadline triple)
    responsible_party = Column(String(50))  # internal, counterparty, both
    action_description = Column(Text, nullable=False)
    deadline = Column(Date, index=True)
    deadline_text = Column(String(255))  # Original text like "within 30 days"

    # Status tracking
    status = Column(String(50), default="pending", nullable=False, index=True)
    reminder_sent = Column(Boolean, default=False)
    completed_at = Column(String(100))  # ISO 8601 timestamp

    # Relationships
    session = relationship("NegotiationSession", back_populates="obligations")
    clause = relationship("Clause")

    __table_args__ = (
        CheckConstraint(
            "responsible_party IN ('internal', 'counterparty', 'both')",
            name="valid_responsible_party",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'overdue', 'waived')",
            name="valid_obligation_status",
        ),
    )
