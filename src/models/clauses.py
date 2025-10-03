"""
Clause and Annotation models
REQ-VC-002: Comment & redline preservation with clause anchoring
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, BaseModel


class Clause(Base, BaseModel):
    """
    Individual clause extracted from contract
    REQ-VC-002: Clause anchoring for annotations
    """

    __tablename__ = "clauses"

    clause_id = Column(UUID(as_uuid=True), primary_key=True)
    version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.version_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_identifier = Column(String(100), nullable=False)  # e.g., "5.1", "Limitation of Liability"
    clause_type = Column(String(100), index=True)  # e.g., "liability", "termination", "confidentiality"
    clause_text = Column(Text, nullable=False)

    # Anchoring information for precise location
    char_start = Column(Integer)
    char_end = Column(Integer)
    xpath = Column(Text)  # For XML/structured documents
    paragraph_id = Column(String(100))  # For Word documents with paragraph IDs

    # Relationships
    version = relationship("DocumentVersion", back_populates="clauses")
    annotations = relationship("Annotation", back_populates="clause", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="clause")
    suggested_edits = relationship("SuggestedEdit", back_populates="clause")


class Annotation(Base, BaseModel):
    """
    Comments and redlines linked to specific clauses
    REQ-VC-002: Version-linked annotations
    """

    __tablename__ = "annotations"

    annotation_id = Column(UUID(as_uuid=True), primary_key=True)
    version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.version_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clauses.clause_id", ondelete="SET NULL"),
        index=True,
    )

    # Anchoring method
    anchor_method = Column(String(50))  # xpath, paragraph_id, char_offset
    anchor_value = Column(Text, nullable=False)

    # Annotation type and content
    annotation_type = Column(String(50), nullable=False)  # comment, redline
    content = Column(JSONB, nullable=False)

    author_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # Relationships
    version = relationship("DocumentVersion", back_populates="annotations")
    clause = relationship("Clause", back_populates="annotations")
    author = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "annotation_type IN ('comment', 'redline')",
            name="valid_annotation_type",
        ),
        CheckConstraint(
            "anchor_method IN ('xpath', 'paragraph_id', 'char_offset')",
            name="valid_anchor_method",
        ),
    )
