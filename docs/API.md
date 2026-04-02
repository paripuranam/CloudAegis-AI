# CloudAegis AI API Documentation

**Base URL:** `http://localhost:8010/api/v1`

**Documentation:** `http://localhost:8010/docs` (FastAPI/Swagger)

## Overview

CloudAegis AI exposes a REST API for:
- Connecting AWS accounts (role-based STS assumption)
- Running security & cost scans
- Retrieving scan history with timestamped snapshots
- Accessing security and cost findings
- Managing remediation decisions and executions
- Reading audit logs for compliance

**Development Mode:**
- Mock AWS data is returned in development environment
- Transitioning to production requires real AWS credentials

## AWS Account Management

### `POST /connect-aws`

Connect an AWS account via IAM role assumption.

**Request:**
```json
{
  "account_name": "Production",
  "role_arn": "arn:aws:iam::123456789012:role/CloudAegisRole",
  "external_id": "optional-external-id",
  "regions": ["us-east-1", "us-west-2"]
}
```

**Response (Success):**
```json
{
  "account_id": "123456789012",
  "account_name": "Production",
  "status": "connected",
  "regions": ["us-east-1", "us-west-2"]
}
```

**Response (Error):**
```json
{
  "detail": "Failed to assume role: ..."
}
```

**Notes:**
- In development mode, mock credentials are used
- In production mode, real STS role assumption occurs
- Account ID is extracted from the role ARN
- Duplicate accounts are updated, not created again

### `GET /accounts`

List all connected AWS accounts.

**Response:**
```json
[
  {
    "id": "uuid",
    "account_id": "123456789012",
    "account_name": "Production",
    "role_arn": "arn:aws:iam::123456789012:role/CloudAegis",
    "regions": ["us-east-1", "us-west-2"],
    "is_active": true,
    "created_at": "2026-04-02T10:00:00Z",
    "last_scanned_at": "2026-04-02T10:15:00Z"
  }
]
```

### `GET /accounts/{account_id}/inventory`

Get current inventory counts for the account.

**Response:**
```json
{
  "account_id": "123456789012",
  "summary": {
    "ec2_instances": 12,
    "ebs_volumes": 21,
    "s3_buckets": 8,
    "security_groups": 16,
    "iam_policies": 42,
    "rds_instances": 3,
    "elastic_ips": 2
  }
}
```

### `GET /accounts/{account_id}/scan-history`

Retrieve scan snapshots in reverse chronological order.

**Response:**
```json
[
  {
    "id": "scan-uuid",
    "account_id": "123456789012",
    "completed_at": "2026-04-02T10:15:00Z",
    "security_score": 72.5,
    "cost_score": 58.3,
    "overall_score": 65.4,
    "delta": {
      "security_score": +5.2,
      "cost_score": -3.1,
      "overall_score": +2.3
    },
    "summary": {
      "security_findings_count": 12,
      "cost_findings_count": 8,
      "critical_findings_count": 1,
      "high_findings_count": 4,
      "current_monthly_cost": 15000,
      "potential_monthly_savings": 2300
    }
  }
]
```

## Scanning

### `POST /scan`

Start a new security and/or cost scan.

**Request:**
```json
{
  "account_id": "123456789012",
  "regions": ["us-east-1"],
  "include_security": true,
  "include_cost": true
}
```

**Response:**
```json
{
  "scan_id": "scan-uuid",
  "account_id": "123456789012",
  "status": "in_progress",
  "started_at": "2026-04-02T10:20:00Z",
  "message": "Scan started"
}
```

### `GET /scan-history/{scan_id}`

Retrieve detailed scan results.

**Response:**
```json
{
  "id": "scan-uuid",
  "account_id": "123456789012",
  "completed_at": "2026-04-02T10:25:00Z",
  "security_score": 72.5,
  "cost_score": 58.3,
  "overall_score": 65.4,
  "summary": { ... },
  "security_findings": [
    {
      "id": "finding-uuid",
      "resource_id": "i-0123456789abcdef0",
      "title": "Security Group Allows All Traffic",
      "description": "...",
      "security_risk": "high",
      "affected_resource_count": 1
    }
  ],
  "cost_findings": [
    {
      "id": "finding-uuid",
      "resource_id": "vol-0123456789abcdef0",
      "title": "Unattached EBS Volume",
      "description": "...",
      "potential_monthly_savings": 15.00
    }
  ]
}
```

## Findings

### `GET /findings?account_id=...`

List security findings.

### `GET /cost-findings?account_id=...`

List cost findings.

### `GET /finding/{finding_id}?finding_type=security`

Get detailed finding information.

## Decisions & Remediation

### `POST /generate-plan/{finding_id}`

Generate a remediation plan for a finding.

**Response:**
```json
{
  "id": "plan-uuid",
  "finding_id": "finding-uuid",
  "recommended_action": "Block public access with security group rule",
  "risk_assessment": "Low",
  "security_impact": "High",
  "steps": [
    "Identify affected instances",
    "Update security group"
  ],
  "terraform_code": "resource \"aws:...\""
}
```

### `POST /approve/{decision_id}`

Approve execution of a remediation decision.

**Request:**
```json
{
  "approver_comment": "Approved for production"
}
```

### `POST /execute/{decision_id}`

Execute an approved decision.

**Response:**
```json
{
  "execution_id": "exec-uuid",
  "status": "success",
  "date_completed": "2026-04-02T10:35:00Z"
}
```

### `POST /rollback/{execution_id}`

Rollback a previous execution using pre-execution snapshot.

## Audit & Compliance

### `GET /logs?limit=100`

Retrieve audit logs.

**Response:**
```json
[
  {
    "id": "log-uuid",
    "timestamp": "2026-04-02T10:35:00Z",
    "action": "execute_decision",
    "actor": "admin",
    "resource_id": "finding-uuid",
    "status": "success",
    "details": { ... }
  }
]
```

### `GET /health`

API health check.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-04-02T10:40:00Z"
}
```

## Error Handling

All errors return standard HTTP status codes with JSON bodies:

```json
{
  "detail": "Human-readable error message"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Invalid request parameters
- `404` - Resource not found
- `500` - Internal server error

## Rate Limiting

Currently not implemented. Production deployments should add rate limiting per:
- Account
- User
- IP address

## Versioning

API version is in the URL path: `/api/v1`

Future versions will be available at `/api/v2`, etc. with backward compatibility maintained where possible.
{
  "scan_id": "uuid",
  "account_id": "123456789012",
  "status": "completed",
  "started_at": "2026-04-02T10:30:00Z",
  "message": "Found 42 findings"
}
```

Behavior notes:
- scans append new findings and preserve historical records
- each run also writes a snapshot into `scan_runs`
- the frontend should use scan snapshots for stable review

### `GET /accounts/{account_id}/scan-history`

Return the scan timeline for an account.

Response:

```json
[
  {
    "id": "scan-uuid",
    "status": "completed",
    "started_at": "2026-04-02T10:00:00Z",
    "completed_at": "2026-04-02T10:04:00Z",
    "security_score": 78.0,
    "cost_score": 65.5,
    "overall_score": 72.2,
    "summary": {
      "security_findings_count": 12,
      "cost_findings_count": 8,
      "critical_findings_count": 2,
      "high_findings_count": 4,
      "potential_monthly_savings": 154.22,
      "current_monthly_cost": 482.11,
      "cis_benchmark_version": "3.0.0"
    },
    "delta": {
      "security_score": 5.0,
      "cost_score": 2.5,
      "overall_score": 4.0
    }
  }
]
```

### `GET /scan-history/{scan_id}`

Return a full point-in-time scan snapshot.

Response:

```json
{
  "id": "scan-uuid",
  "status": "completed",
  "security_score": 78.0,
  "cost_score": 65.5,
  "overall_score": 72.2,
  "summary": {
    "security_findings_count": 12,
    "cost_findings_count": 8,
    "critical_findings_count": 2,
    "high_findings_count": 4,
    "potential_monthly_savings": 154.22,
    "current_monthly_cost": 482.11,
    "cis_benchmark_version": "3.0.0"
  },
  "security_findings": [],
  "cost_findings": [],
  "started_at": "2026-04-02T10:00:00Z",
  "completed_at": "2026-04-02T10:04:00Z"
}
```

## Findings

### `GET /findings?account_id=...`

Return durable security findings stored for the account.

### `GET /cost-findings?account_id=...`

Return durable cost findings stored for the account.

### `GET /finding/{finding_id}?finding_type=security|cost`

Return full review data for a finding, including decision output, predictive impact analysis, and remediation plan.

Response shape:

```json
{
  "finding": {
    "id": "uuid",
    "resource_id": "sg-123",
    "resource_type": "SECURITY_GROUP",
    "title": "Security group allows unrestricted access to port 22",
    "description": "SSH is open to the internet",
    "security_risk": "critical",
    "benchmark_metadata": {
      "framework": "AWS CIS Foundations Benchmark",
      "version": "3.0.0",
      "label": "CIS Amazon Web Services Foundations Benchmark v3.0.0",
      "controls": ["5.1", "5.2"]
    }
  },
  "decision": {
    "resource": "sg-123",
    "security_risk": "critical",
    "monthly_cost": 0,
    "potential_savings": 0,
    "stability_risk": "medium",
    "recommended_action": "restrict_ssh_access",
    "confidence_score": 0.92,
    "reasoning": "Internet-exposed SSH creates an immediate attack surface.",
    "cost_analysis": "This is primarily a security issue and has little direct cost impact."
  },
  "impact_analysis": {
    "affected_entities": ["ec2-instance-id"],
    "risk_of_breakage": "medium",
    "explanation": "SSH access may currently be used by operators.",
    "recommendation": "Whitelist trusted IPs before restricting ingress."
  },
  "remediation_plan": {
    "description": "Restrict SSH ingress to trusted source ranges.",
    "risk_explanation": "Reduces exposure while preserving operator access.",
    "security_remediation": "Replace 0.0.0.0/0 with approved source CIDRs.",
    "cost_optimization": "No material cost optimization expected from this change.",
    "cost_impact": 0,
    "stability_impact": "medium",
    "steps": ["Review active access", "Update ingress rule", "Validate connectivity"],
    "terraform_code": "resource ...",
    "requires_approval": true
  },
  "status": "pending"
}
```

## Decisions and Workflow

### `GET /decisions?status=...`

List stored decisions.

### `POST /generate-plan/{finding_id}`

Generate a remediation plan for a finding.

### `POST /approve/{decision_id}`

Approve a pending decision.

Request:

```json
{
  "approved_by": "user-id",
  "notes": "Approved after review"
}
```

### `POST /execute/{decision_id}`

Execute an approved workflow.

### `POST /rollback/{execution_id}`

Rollback a prior execution.

Request:

```json
{
  "reason": "Unexpected impact in production"
}
```

## Audit and Health

### `GET /logs?limit=100`

Return audit log records.

### `GET /health`

Basic backend health endpoint.

## AI Integration

OpenRouter is optional. When configured, it can enrich:
- recommended actions
- reasoning
- confidence
- predictive impact analysis
- cost optimization analysis
- remediation narratives
- Terraform drafts

Execution is still expected to remain deterministic and approval-gated.
