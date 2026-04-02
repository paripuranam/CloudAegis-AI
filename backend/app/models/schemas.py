"""Pydantic schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingType(str, Enum):
    """Type of finding."""
    SECURITY = "security"
    COST = "cost"
    COMPLIANCE = "compliance"


class DecisionStatus(str, Enum):
    """Status of a decision."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# AWS Connection Schemas

class AWSConnectionRequest(BaseModel):
    """Request to connect AWS account."""
    auth_method: str = Field("role_arn", description="Authentication method: role_arn or access_key")
    role_arn: Optional[str] = Field(None, description="ARN of the IAM role to assume")
    external_id: Optional[str] = Field(None, description="External ID for cross-account access")
    access_key_id: Optional[str] = Field(None, description="AWS access key ID")
    secret_access_key: Optional[str] = Field(None, description="AWS secret access key")
    account_name: str = Field(..., description="Friendly name for the account")
    regions: List[str] = Field(default_factory=lambda: ["us-east-1"], description="Regions to scan")


class AWSConnectionResponse(BaseModel):
    """Response for AWS connection."""
    account_id: str
    account_name: str
    status: str
    regions: List[str]


# Scan Request/Response Schemas

class ScanRequest(BaseModel):
    """Request to scan cloud resources."""
    account_id: str
    regions: Optional[List[str]] = None
    include_security: bool = True
    include_cost: bool = True
    cis_benchmark_version: Optional[str] = Field("3.0.0", description="AWS CIS benchmark version to use for security findings")


class ScanResponse(BaseModel):
    """Response from scan."""
    scan_id: str
    account_id: str
    status: str
    started_at: datetime
    message: str


# Finding Schemas

class SecurityFindingSchema(BaseModel):
    """Security finding."""
    id: str
    resource_id: str
    resource_type: str
    finding_type: str
    title: str
    description: str
    benchmark_metadata: Optional[Dict[str, Any]] = None
    security_risk: RiskLevel
    affected_entities: List[str]
    remediation_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CostFindingSchema(BaseModel):
    """Cost optimization finding."""
    id: str
    resource_id: str
    resource_type: str
    title: str
    description: str
    current_monthly_cost: float
    potential_monthly_savings: float
    savings_percentage: float
    created_at: datetime

    class Config:
        from_attributes = True


# Decision Schemas

class ImpactAnalysis(BaseModel):
    """Impact analysis for a remediation."""
    affected_entities: List[str]
    risk_of_breakage: RiskLevel
    explanation: str
    recommendation: str


class DecisionOutput(BaseModel):
    """Core decision output combining security, cost, stability."""
    resource: str
    security_risk: RiskLevel
    monthly_cost: float
    potential_savings: float
    cost_analysis: Optional[str] = None
    stability_risk: RiskLevel
    recommended_action: str
    confidence_score: float = Field(ge=0, le=1)
    reasoning: str


class RemediationPlan(BaseModel):
    """Plan for remediation."""
    id: str
    finding_id: str
    description: str
    risk_explanation: str
    security_remediation: Optional[str] = None
    cost_optimization: Optional[str] = None
    cost_impact: float
    stability_impact: RiskLevel
    steps: List[str]
    terraform_code: Optional[str]
    requires_approval: bool
    estimated_time_minutes: int


class RemediationApprovalRequest(BaseModel):
    """Request to approve remediation."""
    finding_id: str
    approved_by: str
    notes: Optional[str] = None


class RemediationExecutionResponse(BaseModel):
    """Response from execution."""
    execution_id: str
    finding_id: str
    status: str
    executed_at: datetime
    message: str


class RollbackRequest(BaseModel):
    """Request to rollback execution."""
    execution_id: str
    reason: Optional[str] = None


# Audit Log Schemas

class AuditLogSchema(BaseModel):
    """Audit log entry."""
    id: str
    user_id: str
    action: str
    resource_id: str
    resource_type: str
    changes: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str]

    class Config:
        from_attributes = True


# Combined Response Schemas

class FindingDetailResponse(BaseModel):
    """Complete finding detail with decision and remediation."""
    finding: Dict[str, Any]
    decision: DecisionOutput
    impact_analysis: ImpactAnalysis
    remediation_plan: RemediationPlan
    status: DecisionStatus
