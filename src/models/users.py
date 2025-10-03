"""
User and Organization models
Implements RBAC (Role-Based Access Control)
"""

from sqlalchemy import Column, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from datetime import datetime
from .base import Base, BaseModel


class UserRole(str, enum.Enum):
    """
    User roles for RBAC
    REQ-VC-007: Role-based permissions
    """

    VIEWER = "viewer"  # Read-only access to published versions
    REVIEWER = "reviewer"  # Add comments, no edit rights
    EDITOR = "editor"  # Create redlines, cannot publish
    APPROVER = "approver"  # Publish versions, cannot edit directly
    ADMIN = "admin"  # Full access including rollback


class User(Base, BaseModel):
    """
    User model with role-based access control
    """

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.organization_id"), index=True
    )
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    uploaded_versions = relationship(
        "DocumentVersion", back_populates="uploader", foreign_keys="DocumentVersion.uploader_id"
    )
    created_findings = relationship("Finding", back_populates="creator")
    resolved_edits = relationship("SuggestedEdit", back_populates="resolver")

    def has_permission(self, action: str) -> bool:
        """
        Check if user has permission for action
        REQ-VC-007: RBAC permission checks
        """
        permissions = {
            UserRole.VIEWER: ["read"],
            UserRole.REVIEWER: ["read", "comment"],
            UserRole.EDITOR: ["read", "comment", "edit"],
            UserRole.APPROVER: ["read", "comment", "edit", "approve"],
            UserRole.ADMIN: ["read", "comment", "edit", "approve", "rollback"],
        }

        return action in permissions.get(self.role, [])


class Organization(Base, BaseModel):
    """
    Organization model with default personality settings
    REQ-PA-006: Organizational default settings
    """

    __tablename__ = "organizations"

    organization_id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    default_style_params = Column(
        JSONB,
        default={
            "tone": "concise",
            "formality": "legal",
            "aggressiveness": "balanced",
            "audience": "internal",
        },
    )

    # Relationships
    users = relationship("User", back_populates="organization")
    sessions = relationship("NegotiationSession", back_populates="organization")
    policies = relationship("Policy", back_populates="organization")
