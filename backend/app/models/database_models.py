"""SQLAlchemy ORM models for the database."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, JSON, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
import enum


class RiskLevelEnum(str, enum.Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingTypeEnum(str, enum.Enum):
    """Type of finding."""
    SECURITY = "security"
    COST = "cost"
    COMPLIANCE = "compliance"


class DecisionStatusEnum(str, enum.Enum):
    """Status of a decision."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    decisions = relationship("Decision", back_populates="approved_by_user")


class CloudAccount(Base):
    """Cloud account configuration."""
    __tablename__ = "cloud_accounts"

    id = Column(String, primary_key=True, index=True)
    account_id = Column(String, unique=True, index=True, nullable=False)
    account_name = Column(String, nullable=False)
    auth_method = Column(String, nullable=False, default="role_arn")
    role_arn = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    access_key_id = Column(String, nullable=True)
    secret_access_key = Column(String, nullable=True)
    regions = Column(JSON, default=["us-east-1"])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_scanned_at = Column(DateTime, nullable=True)

    # Relationships
    findings = relationship("Finding", back_populates="account")
    cost_findings = relationship("CostFinding", back_populates="account")
    decisions = relationship("Decision", back_populates="account")
    scan_runs = relationship("ScanRun", back_populates="account")


class ScanRun(Base):
    """Snapshot of a completed or running scan."""
    __tablename__ = "scan_runs"

    id = Column(String, primary_key=True, index=True)
    account_id = Column(String, ForeignKey("cloud_accounts.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="completed")
    security_score = Column(Float, nullable=False, default=100.0)
    cost_score = Column(Float, nullable=False, default=100.0)
    overall_score = Column(Float, nullable=False, default=100.0)
    findings_summary = Column(JSON, default=dict)
    security_findings = Column(JSON, default=list)
    cost_findings = Column(JSON, default=list)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)

    account = relationship("CloudAccount", back_populates="scan_runs")


class Finding(Base):
    """Security finding."""
    __tablename__ = "findings"

    id = Column(String, primary_key=True, index=True)
    account_id = Column(String, ForeignKey("cloud_accounts.id"), nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    finding_type = Column(SQLEnum(FindingTypeEnum), default=FindingTypeEnum.SECURITY)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    security_risk = Column(SQLEnum(RiskLevelEnum), nullable=False)
    benchmark_metadata = Column(JSON, nullable=True)
    affected_entities = Column(JSON, default=list)
    remediation_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("CloudAccount", back_populates="findings")
    decision = relationship("Decision", back_populates="finding", uselist=False)
    execution_logs = relationship("ExecutionLog", back_populates="finding")


class CostFinding(Base):
    """Cost optimization finding."""
    __tablename__ = "cost_findings"

    id = Column(String, primary_key=True, index=True)
    account_id = Column(String, ForeignKey("cloud_accounts.id"), nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    current_monthly_cost = Column(Float, nullable=False)
    potential_monthly_savings = Column(Float, nullable=False)
    savings_percentage = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    account = relationship("CloudAccount", back_populates="cost_findings")


class Decision(Base):
    """Combined decision for a finding."""
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, index=True)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False, unique=True, index=True)
    account_id = Column(String, ForeignKey("cloud_accounts.id"), nullable=False, index=True)
    status = Column(SQLEnum(DecisionStatusEnum), default=DecisionStatusEnum.PENDING, index=True)
    
    # Decision data (JSON to store complete decision engine output)
    decision_data = Column(JSON, nullable=False)
    
    # Approval details
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    finding = relationship("Finding", back_populates="decision")
    account = relationship("CloudAccount", back_populates="decisions")
    approved_by_user = relationship("User", back_populates="decisions")
    remediation_plan = relationship("RemediationPlan", back_populates="decision", uselist=False)


class RemediationPlan(Base):
    """Remediation plan for a decision."""
    __tablename__ = "remediation_plans"

    id = Column(String, primary_key=True, index=True)
    decision_id = Column(String, ForeignKey("decisions.id"), nullable=False, unique=True, index=True)
    
    # Plan details
    description = Column(Text, nullable=False)
    risk_explanation = Column(Text, nullable=False)
    cost_impact = Column(Float, nullable=False)
    stability_impact = Column(SQLEnum(RiskLevelEnum), nullable=False)
    steps = Column(JSON, default=list)
    terraform_code = Column(Text, nullable=True)
    
    # Metadata
    requires_approval = Column(Boolean, default=True)
    estimated_time_minutes = Column(Integer, default=15)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    decision = relationship("Decision", back_populates="remediation_plan")


class ExecutionLog(Base):
    """Log of remediation executions."""
    __tablename__ = "execution_logs"

    id = Column(String, primary_key=True, index=True)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Execution details
    action = Column(String, nullable=False)
    status = Column(String, default="pending", index=True)
    details = Column(JSON, nullable=True)
    
    # Snapshot for rollback
    pre_execution_state = Column(JSON, nullable=True)
    post_execution_state = Column(JSON, nullable=True)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    finding = relationship("Finding", back_populates="execution_logs")


class RollbackState(Base):
    """State snapshots for rollback capability."""
    __tablename__ = "rollback_states"

    id = Column(String, primary_key=True, index=True)
    execution_log_id = Column(String, ForeignKey("execution_logs.id"), unique=True, index=True)
    
    # Previous state
    previous_state = Column(JSON, nullable=False)
    
    # Rollback status
    is_rolled_back = Column(Boolean, default=False)
    rolled_back_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Audit trail for compliance."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Action details
    action = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    changes = Column(JSON, nullable=True)
    
    # Request details
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
