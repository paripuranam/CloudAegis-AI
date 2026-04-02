# Quick Start Guide

## Prerequisites

- Docker and Docker Compose (recommended)
- Or: Python 3.10+, Node.js 18+, PostgreSQL 14+

## Docker Compose (Recommended)

**Fastest way to get CloudAegis AI running:**

```bash
cd /home/ubuntu/ops/cloudguard
docker-compose down -v       # Clean slate (optional)
docker-compose up -d --build
```

**Services** will be available at:
- Frontend UI: `http://localhost:3008`
- Backend API: `http://localhost:8010`
- API Documentation: `http://localhost:8010/docs`
- Database: `postgres://cloudaegis:cloudaegis@localhost:5432/cloudaegis_db`

**Wait ~15 seconds** for all services to fully start, then reload the frontend.

## Development Mode (Default)

CloudAegis AI ships in **development mode** with mock AWS data:

- ✅ Full UI functionality
- ✅ Security scanning with mock resources
- ✅ Cost analysis working
- ✅ Decision engine producing recommendations
- ✅ Remediation planning & execution
- ❌ No real AWS account required

**Perfect for:**
- Evaluating the product
- Testing workflows
- Understanding decision logic
- Validating remediation approach

## Important Environment Variables

### Backend

- `DATABASE_URL` - PostgreSQL connection string
- `API_HOST` - API bind address (default: 0.0.0.0)
- `API_PORT` - API port (default: 8000)
- `API_ENV` - `development` or `production` (default: development)
- `SECRET_KEY` - JWT secret (default: dev key)
- `LOG_LEVEL` - Logging verbosity (default: INFO)

### Frontend

- `VITE_API_URL` - Backend API base URL (default: http://localhost:8010/api/v1)

### Development vs Production

| Feature | Development | Production |
|---------|-------------|-----------|
| Mock AWS Data | ✅ Yes | ❌ No |
| Real AWS Scans | ⚠️ Optional (with credentials) | ✅ Required |
| Authentication | ⚠️ Basic | ✅ Full |
| Logging | 📝 Verbose | 📝 Standard |

## Connecting Real AWS Account

To connect a real AWS account in production:

### 1. Update Environment

```bash
# In docker-compose.yml, change:
API_ENV: production
```

### 2. Create IAM Role

Create a CloudAegis AI-specific IAM role with read-only permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:Get*",
        "s3:List*",
        "iam:Get*",
        "iam:List*",
        "rds:Describe*",
        "cloudwatch:GetMetrics*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Configure Trust Policy

Allow CloudAegis AI account to assume the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::CLOUDAEGIS_ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 4. Connect via UI

1. Go to "Connect AWS" page
2. Enter:
   - Account Name: `Production`
   - IAM Role ARN: `arn:aws:iam::TARGET_ACCOUNT:role/CloudAegis`
   - Regions: `us-east-1,us-west-2` (or your regions)
3. Click "Connect Account"

## First Scan Workflow

1. **Connect AWS Account** (or start with mock data)
2. **Dashboard** shows connected accounts and current state
3. **Run Scan** from Findings page
4. **Review Results**:
   - Security findings with CIS controls
   - Cost optimization opportunities
   - Decision recommendations
5. **Preview & Approve** fixes using Fix Preview Modal
6. **Execute & Track** remediation with full audit trail

## Troubleshooting

### "Failed to connect AWS account" Error

**In Development Mode:**
- This uses mock credentials, should succeed automatically

**In Production Mode:**
- Check IAM role ARN format
- Verify trust policy allows current account
- Check role has read permissions

### "Connection refused" to Backend

- Wait 15+ seconds for backend to start
- Check: `docker-compose logs backend`
- Ensure port 8010 is not in use

### Dashboard Data Disappearing

**Fixed in Latest Release:**
- Updated useFetching hook to preserve data during network errors
- Memoized API calls to prevent unnecessary re-fetches
- Improved error handling with data retention

If still seeing issues:
1. Hard refresh browser (Ctrl+Shift+R)
2. Check browser console for errors
3. Check backend logs: `docker-compose logs backend -f`

### PostgreSQL Connection Error

```bash
# Verify database is running
docker-compose logs postgres

# Check connection string in docker-compose.yml
# Should be: postgresql://cloudaegis:cloudaegis@postgres:5432/cloudaegis_db
```

## Adding AWS CIS Benchmark Support

CloudAegis AI supports AWS CIS Foundations Benchmark in scans:

**Currently Supported:**
- Version 3.0.0 (default)
- Version 1.4.0
- Version 1.2.0

Select benchmark version before running a scan for control-mapped findings.

## Manual Setup (Without Docker)

```bash
# Terminal 1: Database
docker run -d --name cloudaegis-postgres \
  -e POSTGRES_DB=cloudaegis_db \
  -e POSTGRES_USER=cloudaegis \
  -e POSTGRES_PASSWORD=cloudaegis \
  -p 5432:5432 \
  postgres:14-alpine

# Terminal 2: Backend
cd backend
pip install -r requirements.txt
python run.py

# Terminal 3: Frontend
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`

## Production Deployment

For production deployments, see [ARCHITECTURE.md](./ARCHITECTURE.md#deployment) for:
- Multi-tenancy setup
- Scaling recommendations
- Security hardening
- High availability config

  - `overall_score`
- the Dashboard compares scans over time
- the Findings page can inspect a specific scan snapshot

This means findings should no longer be treated only as a live, constantly shifting list.

## Key Pages

### Dashboard

Shows:
- selected account
- selected scan
- security score
- cost efficiency score
- overall posture score
- delta vs previous scan
- service coverage
- top security risks
- top cost opportunities
- scan timeline

### Findings

Shows:
- scan history for the selected account
- findings for the selected scan
- CIS benchmark version selection before a scan
- benchmark-mapped controls on applicable security findings
- security and cost split
- snapshot metrics
- review modal entrypoint

### Review Modal

For a finding, the review surface can include:
- AI recommended action
- AI reasoning
- AI confidence
- predictive impact analysis
- AI cost optimization analysis
- security remediation guidance
- cost optimization remediation guidance
- Terraform draft
- proposed execution steps

## Current Check Coverage

### Security

- AWS CIS benchmark mapping for supported controls and versions
- S3 public access
- S3 encryption disabled
- S3 versioning disabled
- S3 logging disabled
- Security groups open to admin ports
- Broad internet exposure on security groups
- Public EC2 instances
- EC2 IMDSv1 usage
- Unencrypted EBS volumes
- Public RDS instances
- Unencrypted RDS
- Weak RDS backup retention
- IAM wildcard / over-privileged policies

### Cost

- Idle EC2
- Over-provisioned EC2
- Stopped EC2 review
- Unattached EBS
- Oversized EBS
- S3 lifecycle opportunities
- Unattached Elastic IPs
- Idle RDS

## AI Setup

To enable OpenRouter:

```bash
export OPENROUTER_API_KEY=your_key_here
export OPENROUTER_MODEL=openai/gpt-4o-mini
docker-compose up -d --build backend
```

OpenRouter enriches:
- finding analysis
- recommended action
- impact prediction
- cost optimization explanation
- remediation guidance
- Terraform draft generation

It does not directly execute cloud changes.

## Troubleshooting

### Account disappears briefly in the UI

Recent frontend changes were made to preserve the selected account during refreshes and not clear it while the accounts API is still loading.

If the live deployment still flickers:

```bash
docker-compose up -d --build frontend
```

### Scan fails with foreign key errors

Recent backend changes made scans append-only so historical findings are not deleted during rescans. Rebuild the backend:

```bash
docker-compose up -d --build backend
```

### Mock account ID still appears

If you still see `123456789012`, the running deployment likely still contains a stale demo account row or old build artifacts.

You need to:
1. rebuild/redeploy frontend and backend
2. remove the stale demo account from the live database if present
3. reconnect the real AWS account

### Frontend cannot reach backend

Check the Vite proxy target in Compose and rebuild the frontend container.

### AI content does not appear

Check:
- `OPENROUTER_API_KEY`
- backend restart after config change
- backend logs for OpenRouter errors

## Keeping Docs Current

When changing any of the following, update the docs in `docs/`:
- architecture or data flow
- scan model
- benchmark model or supported CIS versions
- AWS auth model
- AI capabilities
- frontend page behavior
- API shapes

This repo now depends on the docs staying in sync with the product shape, especially because the dashboard and findings experience are scan-history driven rather than purely live-list driven.
