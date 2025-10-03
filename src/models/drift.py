"""
Policy Drift Detection and Exception Mining models
REQ-PD-001: Policy drift detection
REQ-EM-001: Exception pattern clustering
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, BaseModel


class DriftAlert(Base, BaseModel):
    """
    Alert for detected drift between policy source and playbook
    REQ-PD-001: Help Desk vs Playbook synchronization monitoring
    """

    __tablename__ = "drift_alerts"

    alert_id = Column(UUID(as_uuid=True), primary_key=True)
    policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policies.policy_id"),
        nullable=False,
        index=True,
    )
    policy_version_new = Column(String(50), nullable=False)
    policy_version_playbook = Column(String(50), nullable=False)
    drift_score = Column(Numeric(4, 3))  # Cosine similarity (0-1)
    affected_rules = Column(JSONB, default=[])  # Array of rule IDs
    recommended_action = Column(Text)
    alert_status = Column(String(50), default="open", nullable=False, index=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    acknowledged_at = Column(String(100))  # ISO 8601 timestamp

    # Relationships
    policy = relationship("Policy", back_populates="drift_alerts")
    acknowledger = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "drift_score >= 0 AND drift_score <= 1",
            name="valid_drift_score",
        ),
        CheckConstraint(
            "alert_status IN ('open', 'acknowledged', 'resolved', 'dismissed')",
            name="valid_alert_status",
        ),
    )


class ExceptionPattern(Base, BaseModel):
    """
    Clustered exception patterns suggesting new playbook rules
    REQ-EM-001: Playbook evolution via pattern detection
    """

    __tablename__ = "exception_patterns"

    pattern_id = Column(UUID(as_uuid=True), primary_key=True)
    exception_cluster_id = Column(Integer)  # DBSCAN cluster ID
    suggested_rule_text = Column(Text, nullable=False)
    supporting_exceptions = Column(JSONB, default=[])  # Array of exception IDs
    frequency = Column(Integer, default=0)
    recommendation_confidence = Column(Numeric(3, 2))
    status = Column(String(50), default="pending", nullable=False, index=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    reviewed_at = Column(String(100))  # ISO 8601 timestamp

    # Relationships
    reviewer = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'implemented')",
            name="valid_pattern_status",
        ),
    )
