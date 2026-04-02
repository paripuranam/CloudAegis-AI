# Architecture Overview

## Product Shape

CloudAegis AI is now built around three operating concepts:

1. Connected AWS accounts
2. Timestamped scan snapshots
3. AI-assisted review and remediation planning

The UI no longer has to depend on a constantly shifting live findings list. Each scan is captured, scored, and retained so posture changes can be compared over time.

## System Components

```text
┌───────────────────────────────────────────────────────────────────────┐
│                              CloudAegis AI                            │
├───────────────────────────────────────────────────────────────────────┤
│ React Frontend                                                        │
│  • Layout / control-plane shell                                       │
│  • Dashboard                                                          │
│  • Findings (scan-centric)                                            │
│  • Connect AWS                                                        │
│  • Fix Preview Modal                                                  │
│  • Audit Logs                                                         │
├───────────────────────────────────────────────────────────────────────┤
│ FastAPI Backend                                                       │
│  • AWS Connector                                                      │
│  • Security Scanner                                                   │
│  • Cost Analyzer                                                      │
│  • Decision Engine                                                    │
│  • Impact Analyzer                                                    │
│  • Remediation Planner                                                │
│  • Executor                                                           │
│  • OpenRouter Client                                                  │
├───────────────────────────────────────────────────────────────────────┤
│ PostgreSQL                                                            │
│  • cloud_accounts                                                     │
│  • findings                                                           │
│  • cost_findings                                                      │
│  • scan_runs                                                          │
│  • decisions                                                          │
│  • remediation_plans                                                  │
│  • execution_logs                                                     │
│  • rollback_states                                                    │
│  • audit_logs                                                         │
└───────────────────────────────────────────────────────────────────────┘
```

## Backend Modules

### `aws_connector.py`

Responsible for authenticated AWS access and resource discovery.

**Current Coverage:**
- EC2 instances
- EBS volumes
- S3 buckets
- Security groups
- IAM policies
- RDS instances
- Elastic IPs
- CloudWatch metrics

**Authentication Options:**
- current UI onboarding uses `access_key`
- backend still supports `role_arn` for future/admin integrations
- credentials are used to discover the real AWS account ID via STS

### `scanner.py`

Security checks currently include:
- S3 public block all disabled
- S3 encryption disabled
- Security groups with CIDR 0.0.0.0/0
- Public/overly permissive access rules
- EC2/RDS public exposure
- Encryption status validation

**AWS CIS Coverage:**
- Supports AWS CIS Foundations Benchmark v3.0.0 (MVP)
- Control mapping for findings
- Version-aware security recommendations

### `cost_analyzer.py`

Cost checks currently include:
- Idle EC2 instances (low CPU utilization)
- Over-provisioned instances (too large for workload)
- Unattached EBS volumes
- Oversized EBS volumes
- S3 lifecycle optimization opportunities
- Unattached Elastic IPs
- Idle RDS instances

**Savings Calculation:**
- Monthly cost basis from instance types and configurations
- Percentage-based potential savings per optimization
- Cumulative opportunity reporting

### `decision_engine.py`

Produces decision-ready analysis for each finding:

**Scoring Model:**
- Security Risk: 0-100 (40% weight in governance score)
- Cost Impact: 0-100 (35% weight in governance score)  
- Stability Risk: 0-100 (25% weight in governance score)

**Output:**
- Recommended action with confidence score (0-100)
- Reasoning and supporting details
- Cost optimization analysis
- Stability impact assessment

### `impact_analyzer.py`

Builds predictive impact analysis before execution:
- Identifies affected resources
- Calculates breakage risk (low/medium/high)
- Provides operator recommendations
- Prevents blind single-resource fixes

### `remediation_planner.py`

Generates:
- Step-by-step remediation instructions
- Security & cost guidance
- Terraform IaC draft code
- Risk disclosure

### `executor.py`

Controlled execution with safeguards:
- Pre-execution snapshots (resource state capture)
- Approval validation
- Deterministic Terraform application
- Rollback state tracking
- Execution logging & audit trail

- execute supported workflow
- record logs
- enable rollback

## Scan-Centric Flow

### Connection Flow

1. User connects an AWS account through `POST /connect-aws`
2. Backend validates access key credentials and discovers the real AWS account ID
3. Account is stored in `cloud_accounts`
4. Frontend sets it as the active account
5. Initial scan is triggered from the UI

### Scan Flow

1. User triggers `POST /scan`
2. AWS resources are collected
3. Security checks and cost checks run
4. Security findings are tagged against the selected AWS CIS benchmark version
5. Findings are written as durable records
6. A scan snapshot is written to `scan_runs`
7. Scores are calculated:
   - `security_score`
   - `cost_score`
   - `overall_score`
7. Dashboard and Findings read primarily from the selected scan snapshot

Important design note:
- scans are append-only
- historical findings are not deleted during a new scan
- this preserves `decisions`, approvals, and execution history

### Review Flow

1. User opens a finding in the review modal
2. Backend loads finding detail
3. Decision engine builds recommendation
4. Impact analyzer predicts blast radius / breakage risk
5. Remediation planner creates steps and Terraform draft
6. Frontend shows AI-assisted review data in one surface

## Frontend Architecture

```text
src/
├── components/
│   ├── Layout.jsx
│   ├── FindingsTable.jsx
│   ├── FixPreviewModal.jsx
│   └── RiskBadge.jsx
├── hooks/
│   ├── useFetching.jsx (with JSX pragma for proper Babel parsing)
│   └── useStore.jsx
├── pages/
│   ├── Dashboard.jsx
│   ├── Findings.jsx
│   ├── ConnectAWS.jsx
│   └── AuditLogs.jsx
├── services/
│   └── api.js
└── styles/
    └── index.css
```

Current UI behavior:
- shared app shell with collapsible sidebar and top bar
- persistent selected account
- persistent selected scan
- scan history selection
- scan-over-scan score deltas
- review modal with AI recommendation and remediation context
- streamlined left navigation with icon-first items and reduced sidebar copy

## Database Model

### `cloud_accounts`

Stores:
- AWS account identity
- account display name
- auth method
- access key credentials when used
- role ARN / external ID when used programmatically
- regions
- last scan timestamp

### `findings`

Durable security finding records used for review, approval, execution history, and audit traceability.
These records can also store benchmark metadata for mapped AWS CIS findings.

### `cost_findings`

Durable cost-optimization finding records.

### `scan_runs`

The canonical scan snapshot table. Stores:
- scan timestamps
- scorecards
- summary counts
- serialized security findings
- serialized cost findings

### `decisions`

Stores decision engine output and approval state for security findings.

### `remediation_plans`

Stores detailed remediation plans including Terraform drafts and remediation guidance.

## AI Architecture

OpenRouter is optional and configured through:
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_APP_NAME`
- `OPENROUTER_SITE_URL`

AI is used for:
- recommended actions
- reasoning
- confidence tuning
- predictive impact analysis
- cost optimization analysis
- remediation guidance
- Terraform draft generation

AI is not used for:
- direct AWS execution
- raw resource discovery
- bypassing approval controls

## Deployment Notes

### Local / Compose

- Frontend: Vite dev server
- Backend: FastAPI + Uvicorn
- Database: PostgreSQL

Compose passes:
- backend API configuration
- AWS mock-mode flag
- OpenRouter configuration
- frontend API proxy target

### Operational Constraints

- live UI changes require rebuilding/redeploying the running frontend/backend
- database state can still contain stale demo rows if the deployment was seeded earlier
- docs should be updated whenever scan flow, AI flow, or data model changes
