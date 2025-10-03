"""
Negotiation Session and Document Version models
REQ-VC-001: Version creation with UUID + timestamp
REQ-VC-005: Rollback capability
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, BaseModel


class NegotiationSession(Base, BaseModel):
    """
    Negotiation session spanning multiple contract versions
    Tracks complete negotiation lifecycle
    """

    __tablename__ = "negotiation_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.organization_id"), index=True
    )
    contract_name = Column(String(500), nullable=False)
    counterparty_id = Column(UUID(as_uuid=True), ForeignKey("counterparties.counterparty_id"))
    matter_id = Column(String(100))  # External matter reference
    status = Column(
        String(50),
        default="active",
        nullable=False,
        index=True,
    )
    current_version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.version_id"))

    # REQ-PA-007: Session-level personality settings
    style_overrides = Column(JSONB, nullable=True)
    metadata = Column(JSONB, default={})

    # Relationships
    organization = relationship("Organization", back_populates="sessions")
    counterparty = relationship("Counterparty", back_populates="sessions")
    versions = relationship(
        "DocumentVersion", back_populates="session", foreign_keys="DocumentVersion.session_id"
    )
    current_version = relationship(
        "DocumentVersion", foreign_keys=[current_version_id], post_update=True
    )
    negotiation_logs = relationship("NegotiationLog", back_populates="session")
    obligations = relationship("Obligation", back_populates="session")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'archived', 'cancelled')",
            name="valid_session_status",
        ),
    )


class DocumentVersion(Base, BaseModel):
    """
    Document version with complete metadata
    REQ-VC-001: Version creation with UUID, timestamp, hash
    REQ-VC-005: Rollback support via rollback_to field
    """

    __tablename__ = "document_versions"

    version_id = Column(UUID(as_uuid=True), primary_key=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_version_id = Column(
        UUID(as_uuid=True), ForeignKey("document_versions.version_id"), index=True
    )
    version_number = Column(Integer, nullable=False)
    source = Column(String(50), nullable=False)
    document_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    file_path = Column(Text, nullable=False)
    file_name = Column(String(500))
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # REQ-VC-005: Rollback tracking
    rollback_to = Column(UUID(as_uuid=True), ForeignKey("document_versions.version_id"))
    rollback_reason = Column(Text)

    metadata = Column(JSONB, default={})

    # Relationships
    session = relationship(
        "NegotiationSession",
        back_populates="versions",
        foreign_keys=[session_id],
    )
    parent = relationship(
        "DocumentVersion", remote_side=[version_id], foreign_keys=[parent_version_id]
    )
    uploader = relationship("User", back_populates="uploaded_versions")
    clauses = relationship("Clause", back_populates="version", cascade="all, delete-orphan")
    annotations = relationship(
        "Annotation", back_populates="version", cascade="all, delete-orphan"
    )
    findings = relationship("Finding", back_populates="version", cascade="all, delete-orphan")
    suggested_edits = relationship(
        "SuggestedEdit", back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "source IN ('internal', 'counterparty')",
            name="valid_source",
        ),
    )
