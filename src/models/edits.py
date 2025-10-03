"""
Suggested Edit model
REQ-SE-001 to REQ-SE-006: Track-change format edits
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, BaseModel


class SuggestedEdit(Base, BaseModel):
    """
    Track-change format suggested edits
    REQ-SE-001: Word track-change format
    REQ-SE-004: Accept/reject controls with status tracking
    """

    __tablename__ = "suggested_edits"

    edit_id = Column(UUID(as_uuid=True), primary_key=True)
    version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.version_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_id = Column(
        UUID(as_uuid=True), ForeignKey("clauses.clause_id", ondelete="SET NULL")
    )
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.finding_id"))

    # Edit details
    edit_type = Column(String(50))  # insertion, deletion, replacement
    char_start = Column(Integer)
    char_end = Column(Integer)
    original_text = Column(Text)
    suggested_text = Column(Text)

    # REQ-SE-004: Status tracking
    status = Column(String(50), default="pending", nullable=False, index=True)

    # For modified edits
    modified_text = Column(Text)
    modification_rationale = Column(Text)

    # REQ-SE-002: Policy anchor
    policy_reference = Column(UUID(as_uuid=True), ForeignKey("policies.policy_id"))

    # Resolution tracking
    resolved_at = Column(String(100))  # ISO 8601 timestamp
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # Relationships
    version = relationship("DocumentVersion", back_populates="suggested_edits")
    clause = relationship("Clause", back_populates="suggested_edits")
    finding = relationship("Finding")
    policy = relationship("Policy")
    resolver = relationship("User", back_populates="resolved_edits")

    __table_args__ = (
        CheckConstraint(
            "edit_type IN ('insertion', 'deletion', 'replacement')",
            name="valid_edit_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'modified', 'superseded')",
            name="valid_edit_status",
        ),
    )
