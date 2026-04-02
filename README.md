# CloudAegis AI - Unified Cloud Governance Platform

A production-grade SaaS platform combining **Security (SecOps)**, **Cost Optimization (FinOps)**, and **Decision Intelligence** into a single unified cloud governance solution.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.10+ (for local development)

### Deploy with Docker Compose

```bash
cd /home/ubuntu/ops/cloudguard
docker-compose up -d --build

# Services will be available at:
# Frontend: http://localhost:3008
# Backend API: http://localhost:8010
# API Docs: http://localhost:8010/docs
# Database: localhost:5432
```

### Development Mode
CloudAegis AI runs in development mode by default with **mock AWS data**. This allows you to:
- Test the UI without AWS credentials
- Evaluate security scanning logic
- Review decision engine output
- Test remediation workflows

To connect real AWS accounts in development, update `API_ENV` to `production` in docker-compose.yml and provide valid AWS credentials.

## 🎯 Core Vision

CloudAegis AI combines three dimensions of cloud governance:

- **🔐 Security (SecOps)** → Detect security risks with AWS CIS checks
- **💰 Cost Optimization (FinOps)** → Identify waste and optimization opportunities
- **🧠 Decision Intelligence** → Intelligently balance security, cost, and stability
- **⚙️ Safe Remediation** → Controlled, approval-based execution with rollback support

## ✨ Key Principles

### NEVER:
- Auto-fix blindly without understanding impact
- Show raw alerts without business context
- Execute changes without explicit approval

### ALWAYS:
- Provide decision-ready insights with:
  - Security Risk assessment (0-100 score)
  - Cost Impact analysis (monthly savings potential)
  - Stability Risk evaluation (breakage risk assessment)
  - Recommended Action with confidence score
- Require approval before execution
- Support rollback for failed changes
- Maintain complete audit trail
- Preserve cloud account data during refresh cycles

## 🏗️ System Architecture

### Backend (Python 3.10+ + FastAPI 0.104+)

**Core Modules:**

```
/services/
├── aws_connector.py          # AWS STS role assumption with development mode support
├── scanner.py                # Security scanning (3x AWS CIS checks)
├── cost_analyzer.py          # Cost analysis (4x optimization patterns)
├── decision_engine.py        # CORE: Security (40%) + Cost (35%) + Stability (25%)
├── impact_analyzer.py        # Blast radius analysis & breakage prevention
├── remediation_planner.py    # Terraform-based fix plan generation
└── executor.py               # Safe execution with pre-run snapshots & rollback

/api/
└── routes.py                 # 16 RESTful endpoints with proper error handling

/models/
├── schemas.py                # Pydantic validation schemas
└── database_models.py        # SQLAlchemy ORM (9 tables)

/db/
├── database.py               # Connection pooling & session management
└── base.py                   # Declarative base
```

### Frontend (React 18 + Vite 5 + Tailwind CSS)

**Pages:**
- **Dashboard** - At-a-glance posture, scan timeline, service coverage
- **Findings** - Unified security + cost findings view with filtering
- **ConnectAWS** - IAM role ARN setup with multi-region support
- **AuditLogs** - Compliance audit trail with search/export

**Key Components:**
- **RiskBadge** - Visual risk level (critical/high/medium/low)
- **RiskBar** - Aggregated governance score bars
- **FixPreviewModal** - Critical approval UI for decision execution
- **FindingsTable** - Paginated findings list with inline actions

**Improvements in Latest Build:**
- Fixed auto-refresh data loss by preserving data on network errors
- Optimized useFetching hook to prevent race conditions
- Memoized API calls to prevent unnecessary re-renders
- Enhanced UI alignment and spacing

### Database (PostgreSQL 14-alpine)

**Schema (9 Tables):**

```sql
-- Multi-account management
cloud_accounts        # AWS accounts with role ARN & regions

-- Findings & Analysis
findings              # Security findings + risk levels
cost_findings         # Cost optimization findings + savings potential

-- Decision Engine
decisions             # Combined risk/cost/stability decisions
remediation_plans     # Fix plans with Terraform code

-- Execution & Audit
execution_logs        # Record of all remediation executions
rollback_states       # Pre-execution snapshots for safe rollback
audit_logs            # Compliance trail (who, what, when, result)

-- Access Control
users                 # User accounts & RBAC
```

## 🔍 Security Checks (MVP)

### SecOps Checks:

1. **S3 Public Access**
   - Detects S3 buckets without public access block
   - Risk: HIGH
   - Recommendation: Enable public access block

2. **Security Groups with Dangerous Rules**
   - Detects 0.0.0.0/0 on SSH (22) and RDP (3389)
   - Risk: CRITICAL
   - Recommendation: Restrict to specific IPs

3. **IAM Wildcard Policies**
   - Detects overly permissive IAM policies
   - Risk: MEDIUM (requires manual review)
   - Recommendation: Apply least privilege principle

## 💰 FinOps Checks (MVP)

### Cost Optimization Checks:

1. **Idle EC2 Instances**
   - Detects instances with < 5% CPU over 14 days
   - Savings: 50% by downsizing
   - Recommendation: Stop or downgrade instance

2. **Unattached EBS Volumes**
   - Detects volumes not connected to instances
   - Savings: 100% (delete safely)
   - Recommendation: Delete volume

3. **Over-Provisioned EC2 Instances**
   - Detects instances with < 30% memory usage
   - Savings: 40% by downsizing
   - Recommendation: Downgrade to smaller type

4. **S3 Without Lifecycle Policies**
   - Detects buckets lacking storage optimization
   - Savings: 25-50% (move to cheaper tiers)
   - Recommendation: Add lifecycle policy

## 🧠 Decision Engine (CORE FEATURE)

The decision engine combines three dimensions:

```python
Output:
{
  "resource": "ec2-i-12345",
  "security_risk": "low",
  "monthly_cost": "$80",
  "potential_savings": "$50",
  "stability_risk": "medium",
  "recommended_action": "downgrade_instance",
  "confidence_score": 0.85,
  "reasoning": "Low CPU usage over 14 days. Safe to downgrade."
}
```

**Weighting:**
- Security Risk: 40%
- Cost Impact: 35%
- Stability Risk: 25%

## 🔥 Impact Analyzer (Blast Radius)

Before any fix, analyze:

```python
Output:
{
  "affected_entities": ["i-67890", "i-78901"],
  "risk_of_breakage": "medium",
  "explanation": "Restricting SSH will block current active IPs",
  "recommendation": "Whitelist IPs before applying"
}
```

Prevents blind auto-fixes by identifying:
- Which resources are affected
- Risk of active service disruption
- Safe execution timeline

## ⚙️ API Endpoints

### Connection
- `POST /api/v1/connect-aws` - Connect AWS account via IAM role

### Scanning
- `POST /api/v1/scan` - Scan account for findings
- `GET /api/v1/findings` - Get security findings
- `GET /api/v1/cost-findings` - Get cost findings
- `GET /api/v1/finding/{id}` - Get complete finding detail

### Decision & Remediation
- `GET /api/v1/decisions` - Get all decisions
- `POST /api/v1/generate-plan/{finding_id}` - Generate remediation plan
- `POST /api/v1/approve/{decision_id}` - Approve decision
- `POST /api/v1/execute/{decision_id}` - Execute remediation
- `POST /api/v1/rollback/{execution_id}` - Rollback execution

### Audit
- `GET /api/v1/logs` - Get audit trail

### Health
- `GET /api/v1/health` - Health check

## 🔐 AWS Integration

**Authentication Model:**
- No hardcoded credentials
- IAM role assumption via STS
- Multi-account + multi-region support
- Temporary credentials with auto-refresh

**Required IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:GetBucketPublicAccessBlock",
        "s3:ListBucket",
        "iam:ListPolicies",
        "cloudwatch:GetMetricStatistics"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🔁 Safe Remediation System

### Execution Workflow:

1. **Approval Required**
   - All fixes require explicit approval
   - Audit trail records approver and timestamp

2. **Pre-Execution Snapshot**
   - Capture current resource state
   - Store in rollback_states table
   - Enable safe recovery

3. **Controlled Execution**
   - Execute fix with error handling
   - Log all changes
   - Return status to user

4. **Rollback Support**
   - Restore to pre-execution state
   - Maintain operation history
   - Support partial rollback

## 📦 Terraform Export

Generate Infrastructure-as-Code for all fixes:

```terraform
# S3 Public Access Fix
resource "aws_s3_public_access_block" "main" {
  bucket = "my-bucket"
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# Security Group Fix
resource "aws_security_group_rule" "restrict_ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["YOUR_IP/32"]
  security_group_id = "sg-12345"
}
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- AWS account with IAM role setup

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and API settings

# Create database tables
alembic upgrade head

# Run development server
python run.py
# API available at http://localhost:8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
# UI available at http://localhost:3000
```

API Proxy configured in vite.config.js to forward `/api` requests to backend.

### Database Setup

```bash
# Create PostgreSQL database
createdb cloudaegis_db

# Migrations handled by SQLAlchemy models
# Tables auto-created on app startup
```

## 📊 Dashboard Components

### Dashboard Page
- **Stats Cards**
  - Total Findings
  - Pending Approvals
  - Total Monthly Savings
- **Critical Findings** - Risk prioritization
- **Cost Distribution** - FinOps overview
- **Quick Actions** - Navigate to key flows

### Unified Findings Page
- **Multi-dimensional Filter** - By type, risk, status
- **Risk Color Coding** - Visual risk assessment
- **Inline Actions** - Review, approve, execute
- **Bulk Operations** - Edit multiple findings

### Fix Preview Modal (MOST CRITICAL)
- **Issue Context** - What's wrong and why
- **Risk Assessment** - Security + Cost + Stability
- **Impact Analysis** - Blast radius and warnings
- **Approval Workflow** - Notes + Execute buttons
- **Terraform Export** - Infrastructure-as-Code
- **Schedule Option** - Defer execution

### Audit Logs Page
- **Complete Audit Trail** - Who, what, when
- **Approval History** - Decision records
- **Execution Timeline** - Change tracking
- **Compliance Export** - SOC 2 ready

## 🔐 Security Best Practices

- ✅ JWT authentication (expandable)
- ✅ Role-based access control (RBAC)
- ✅ Encryption for sensitive data
- ✅ Rate limiting on API
- ✅ CORS configuration
- ✅ Input validation (Pydantic)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Audit logging for compliance

## 📝 Database Schema

See [models/database_models.py](backend/app/models/database_models.py) for complete ORM definitions.

Key relationships:
- User → Decision (approvals)
- CloudAccount → Finding (multi-tenancy)
- Finding → Decision → RemediationPlan (1:1:1)
- Decision → ExecutionLog (1:N)
- ExecutionLog → RollbackState (1:1)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📚 Testing with Mock Data

All modules support mock AWS data for development:

```python
# Services detect when AWS credentials are unavailable
# and return realistic mock responses for testing
```

## 🚀 Production Deployment

### Backend (Docker)
```dockerfile
FROM python:3.11-slim
COPY backend /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "run.py"]
```

### Frontend (Docker)
```dockerfile
FROM node:18 AS builder
COPY frontend /app
WORKDIR /app
RUN npm install && npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

### Kubernetes
See `k8s/` directory for example deployments (not included in MVP).

## 🔥 Bonus Features (Roadmap)

- [ ] Slack alerts on critical findings
- [ ] GitHub PR creation for fixes (GitOps)
- [ ] CI/CD pipeline integration
- [ ] Multi-user collaboration with comments
- [ ] Custom rule engine
- [ ] Azure + GCP support
- [ ] Machine learning for anomaly detection
- [ ] Scheduled scanning
- [ ] SNS/SQS integration
- [ ] CloudFormation support

## 📄 License

CloudAegis AI - Production-grade cloud governance platform

## 👥 Support

For issues, questions, or suggestions:
- 📧 support@cloudaegis.dev
- 📚 docs.cloudaegis.dev
- 💬 slack.cloudaegis.dev

---

**Built with ❤️ by DevSecOps teams who believe in safe, intelligent cloud transformation.**

