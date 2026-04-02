"""Main API routes for CloudAegis AI."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime
from app.db.database import get_db
from app.models import schemas, database_models
from app.services.aws_connector import AWSConnector
from app.services.scanner import SecurityScanner, AWS_CIS_BENCHMARKS
from app.services.cost_analyzer import CostAnalyzer
from app.services.decision_engine import DecisionEngine
from app.services.impact_analyzer import ImpactAnalyzer
from app.services.remediation_planner import RemediationPlanner
from app.services.executor import ExecutionManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances
decision_engine = DecisionEngine()
execution_manager = ExecutionManager()


def _validate_aws_connection_request(request: schemas.AWSConnectionRequest) -> None:
    """Validate required fields for the selected AWS auth method."""
    if request.auth_method == "access_key":
        if not request.access_key_id or not request.secret_access_key:
            raise ValueError("access_key_id and secret_access_key are required for access_key auth")
        return

    if request.auth_method != "role_arn":
        raise ValueError("auth_method must be either 'role_arn' or 'access_key'")

    if not request.role_arn:
        raise ValueError("role_arn is required for role_arn auth")


def _infer_check_type(resource_type: str, title: str) -> str:
    """Infer a check type when it is not stored explicitly in the database."""
    normalized = f"{resource_type} {title}".lower()

    if "public access" in normalized and "s3" in normalized:
        return "s3_public_access"
    if "versioning" in normalized and "s3" in normalized:
        return "s3_versioning_disabled"
    if "logging" in normalized and "s3" in normalized:
        return "s3_logging_disabled"
    if "encrypt" in normalized and "s3" in normalized:
        return "s3_no_encryption"
    if "security group" in normalized or "port 22" in normalized or "port 3389" in normalized:
        return "open_security_group"
    if "imdsv2" in normalized or "imdsv1" in normalized:
        return "ec2_imdsv1_enabled"
    if "low cpu utilization" in normalized:
        return "idle_ec2"
    if "over-provisioned" in normalized:
        return "over_provisioned_ec2"
    if "stopped ec2" in normalized:
        return "stopped_ec2"
    if "unattached" in normalized and "ebs" in normalized:
        return "unattached_ebs"
    if "rightsized" in normalized and "ebs" in normalized:
        return "oversized_ebs"
    if "publicly accessible" in normalized and "rds" in normalized:
        return "rds_public_access"
    if "backup retention" in normalized and "rds" in normalized:
        return "rds_backup_retention"
    if "not encrypted" in normalized and "rds" in normalized:
        return "rds_unencrypted"
    if "low cpu utilization" in normalized and "rds" in normalized:
        return "idle_rds"
    if "elastic ip" in normalized:
        return "unattached_eip"
    if "lifecycle" in normalized and "s3" in normalized:
        return "s3_lifecycle"
    if "iam policy" in normalized:
        return "iam_wildcard_policy"

    return "manual_review"


def _calculate_scan_scores(security_findings: list[dict], cost_findings: list[dict]) -> dict:
    """Calculate posture scores for a scan snapshot."""
    security_penalty_map = {
        "critical": 18,
        "high": 10,
        "medium": 5,
        "low": 2,
    }

    security_penalty = sum(
        security_penalty_map.get(str(finding.get("security_risk", "medium")).lower(), 4)
        for finding in security_findings
    )
    security_score = max(0.0, 100.0 - security_penalty)

    total_current_cost = sum(float(finding.get("current_monthly_cost", 0) or 0) for finding in cost_findings)
    total_savings = sum(float(finding.get("potential_monthly_savings", 0) or 0) for finding in cost_findings)
    if total_current_cost <= 0:
        cost_score = 100.0
    else:
        savings_ratio = min(1.0, total_savings / total_current_cost)
        cost_score = max(0.0, 100.0 - (savings_ratio * 100))

    overall_score = round((security_score * 0.6) + (cost_score * 0.4), 2)

    return {
        "security_score": round(security_score, 2),
        "cost_score": round(cost_score, 2),
        "overall_score": overall_score,
        "summary": {
            "security_findings_count": len(security_findings),
            "cost_findings_count": len(cost_findings),
            "critical_findings_count": len([f for f in security_findings if str(f.get("security_risk", "")).lower() == "critical"]),
            "high_findings_count": len([f for f in security_findings if str(f.get("security_risk", "")).lower() == "high"]),
            "potential_monthly_savings": round(total_savings, 2),
            "current_monthly_cost": round(total_current_cost, 2),
        },
    }


# AWS Connection Endpoints

@router.post("/connect-aws", response_model=schemas.AWSConnectionResponse)
async def connect_aws(
    request: schemas.AWSConnectionRequest,
    db: Session = Depends(get_db)
):
    """Connect a new AWS account to CloudAegis AI."""
    try:
        _validate_aws_connection_request(request)

        connector = AWSConnector(
            role_arn=request.role_arn,
            external_id=request.external_id,
            region=request.regions[0],
            access_key_id=request.access_key_id,
            secret_access_key=request.secret_access_key,
        )

        # Test the supplied credentials and discover the AWS account ID.
        connector.get_session()
        account_id = connector.get_account_id()
        
        # Check if account already exists
        existing = db.query(database_models.CloudAccount).filter(
            database_models.CloudAccount.account_id == account_id
        ).first()
        
        if existing:
            logger.info(f"AWS account {account_id} already connected, updating...")
            existing.account_name = request.account_name
            existing.auth_method = request.auth_method
            existing.role_arn = request.role_arn
            existing.external_id = request.external_id
            existing.access_key_id = request.access_key_id
            existing.secret_access_key = request.secret_access_key
            existing.regions = request.regions
            db.commit()
            db.refresh(existing)
            return schemas.AWSConnectionResponse(
                account_id=account_id,
                account_name=request.account_name,
                status="connected",
                regions=request.regions,
            )
        
        # Store in database
        account = database_models.CloudAccount(
            id=str(uuid.uuid4()),
            account_id=account_id,
            account_name=request.account_name,
            auth_method=request.auth_method,
            role_arn=request.role_arn,
            external_id=request.external_id,
            access_key_id=request.access_key_id,
            secret_access_key=request.secret_access_key,
            regions=request.regions,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        
        logger.info(f"Connected AWS account {account_id}")
        
        return schemas.AWSConnectionResponse(
            account_id=account_id,
            account_name=request.account_name,
            status="connected",
            regions=request.regions,
        )
    except Exception as e:
        logger.error(f"Failed to connect AWS account: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts")
async def get_accounts(
    db: Session = Depends(get_db)
):
    """List connected cloud accounts."""
    accounts = db.query(database_models.CloudAccount).order_by(database_models.CloudAccount.created_at.desc()).all()

    return [
        {
            "id": account.id,
            "account_id": account.account_id,
            "account_name": account.account_name,
            "auth_method": account.auth_method,
            "regions": account.regions or [],
            "is_active": account.is_active,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "last_scanned_at": account.last_scanned_at.isoformat() if account.last_scanned_at else None,
        }
        for account in accounts
    ]


@router.get("/benchmarks/aws-cis")
async def get_aws_cis_benchmarks():
    """Return supported AWS CIS benchmark versions for scan selection."""
    versions = [
        {
            "version": version,
            "label": metadata["label"],
            "control_count": len(metadata.get("controls", {})),
        }
        for version, metadata in AWS_CIS_BENCHMARKS.items()
    ]
    versions.sort(key=lambda item: item["version"])

    return {
        "framework": "AWS CIS Foundations Benchmark",
        "default_version": "3.0.0",
        "versions": versions,
    }


@router.get("/accounts/{account_id}/inventory")
async def get_account_inventory(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Fetch live inventory summary for a connected account."""
    account = db.query(database_models.CloudAccount).filter(
        database_models.CloudAccount.account_id == account_id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    connector = AWSConnector(
        role_arn=account.role_arn,
        external_id=account.external_id,
        access_key_id=account.access_key_id,
        secret_access_key=account.secret_access_key,
    )

    instances = connector.get_ec2_instances()
    volumes = connector.get_ebs_volumes()
    buckets = connector.get_s3_buckets()
    security_groups = connector.get_security_groups()
    policies = connector.get_iam_policies()
    rds_instances = connector.get_rds_instances()
    elastic_ips = connector.get_elastic_ips()

    return {
        "account_id": account.account_id,
        "account_name": account.account_name,
        "regions": account.regions or [],
        "summary": {
            "ec2_instances": len(instances),
            "ebs_volumes": len(volumes),
            "s3_buckets": len(buckets),
            "security_groups": len(security_groups),
            "iam_policies": len(policies),
            "rds_instances": len(rds_instances),
            "elastic_ips": len(elastic_ips),
        },
        "resources": {
            "instances": instances[:20],
            "volumes": volumes[:20],
            "buckets": buckets[:20],
            "security_groups": security_groups[:20],
            "iam_policies": policies[:20],
            "rds_instances": rds_instances[:20],
            "elastic_ips": elastic_ips[:20],
        },
    }


@router.get("/accounts/{account_id}/scan-history")
async def get_scan_history(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Return scan history snapshots for an account."""
    account = db.query(database_models.CloudAccount).filter(
        database_models.CloudAccount.account_id == account_id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    scan_runs = db.query(database_models.ScanRun).filter(
        database_models.ScanRun.account_id == account.id
    ).order_by(database_models.ScanRun.started_at.desc()).all()

    payload = []
    previous = None
    for scan in scan_runs:
        item = {
            "id": scan.id,
            "status": scan.status,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "security_score": scan.security_score,
            "cost_score": scan.cost_score,
            "overall_score": scan.overall_score,
            "summary": scan.findings_summary or {},
            "delta": {
                "security_score": round(scan.security_score - previous.security_score, 2) if previous else None,
                "cost_score": round(scan.cost_score - previous.cost_score, 2) if previous else None,
                "overall_score": round(scan.overall_score - previous.overall_score, 2) if previous else None,
            },
        }
        payload.append(item)
        previous = scan

    return payload


@router.get("/scan-history/{scan_id}")
async def get_scan_detail(
    scan_id: str,
    db: Session = Depends(get_db)
):
    """Return a full scan snapshot by id."""
    scan = db.query(database_models.ScanRun).filter(
        database_models.ScanRun.id == scan_id
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {
        "id": scan.id,
        "status": scan.status,
        "security_score": scan.security_score,
        "cost_score": scan.cost_score,
        "overall_score": scan.overall_score,
        "summary": scan.findings_summary or {},
        "security_findings": scan.security_findings or [],
        "cost_findings": scan.cost_findings or [],
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
    }


# Scanning Endpoints

@router.post("/scan", response_model=schemas.ScanResponse)
async def scan_resources(
    request: schemas.ScanRequest,
    db: Session = Depends(get_db)
):
    """Scan AWS account for security and cost findings."""
    try:
        # Get account from database
        account = db.query(database_models.CloudAccount).filter(
            database_models.CloudAccount.account_id == request.account_id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Initialize AWS connector
        connector = AWSConnector(
            role_arn=account.role_arn,
            external_id=account.external_id,
            access_key_id=account.access_key_id,
            secret_access_key=account.secret_access_key,
        )
        
        findings_data = []

        # Keep prior findings in place so historical decisions, approvals, and execution logs
        # remain referentially intact. The scan snapshot is the source of truth for "current"
        # findings in the UI, while these rows serve as durable records for workflow history.
        
        # Run security scan
        if request.include_security:
            security_scanner = SecurityScanner(
                connector,
                cis_benchmark_version=request.cis_benchmark_version or "3.0.0",
            )
            security_findings = security_scanner.scan_all()
            findings_data.extend(security_findings)
        
        # Run cost analysis
        if request.include_cost:
            cost_analyzer = CostAnalyzer(connector)
            cost_findings = cost_analyzer.analyze_all()
            findings_data.extend(cost_findings)
        
        # Store findings in database
        stored_security_findings = []
        stored_cost_findings = []
        for finding in findings_data:
            if finding.get("security_risk"):
                # Security finding
                db_finding = database_models.Finding(
                    id=str(uuid.uuid4()),
                    account_id=account.id,
                    resource_id=finding["resource_id"],
                    resource_type=finding["resource_type"],
                    title=finding["title"],
                    description=finding["description"],
                    security_risk=finding["security_risk"],
                    benchmark_metadata=finding.get("benchmark_metadata"),
                    affected_entities=finding.get("affected_entities", []),
                    remediation_available=finding.get("remediation_available", True),
                )
                db.add(db_finding)
                stored_security_findings.append({
                    "id": db_finding.id,
                    "resource_id": finding["resource_id"],
                    "resource_type": finding["resource_type"],
                    "title": finding["title"],
                    "description": finding["description"],
                    "security_risk": str(finding["security_risk"].value if hasattr(finding["security_risk"], "value") else finding["security_risk"]),
                    "benchmark_metadata": finding.get("benchmark_metadata"),
                    "type": "security",
                })
            else:
                # Cost finding
                db_finding = database_models.CostFinding(
                    id=str(uuid.uuid4()),
                    account_id=account.id,
                    resource_id=finding["resource_id"],
                    resource_type=finding["resource_type"],
                    title=finding["title"],
                    description=finding["description"],
                    current_monthly_cost=finding["current_monthly_cost"],
                    potential_monthly_savings=finding["potential_monthly_savings"],
                    savings_percentage=finding["savings_percentage"],
                )
                db.add(db_finding)
                stored_cost_findings.append({
                    "id": db_finding.id,
                    "resource_id": finding["resource_id"],
                    "resource_type": finding["resource_type"],
                    "title": finding["title"],
                    "description": finding["description"],
                    "current_monthly_cost": finding["current_monthly_cost"],
                    "potential_monthly_savings": finding["potential_monthly_savings"],
                    "savings_percentage": finding["savings_percentage"],
                    "type": "cost",
                })
        
        # Update scan timestamp
        account.last_scanned_at = datetime.utcnow()
        scorecard = _calculate_scan_scores(stored_security_findings, stored_cost_findings)
        scorecard["summary"]["cis_benchmark_version"] = request.cis_benchmark_version or "3.0.0"
        scan_id = str(uuid.uuid4())
        scan_run = database_models.ScanRun(
            id=scan_id,
            account_id=account.id,
            status="completed",
            security_score=scorecard["security_score"],
            cost_score=scorecard["cost_score"],
            overall_score=scorecard["overall_score"],
            findings_summary=scorecard["summary"],
            security_findings=stored_security_findings,
            cost_findings=stored_cost_findings,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(scan_run)
        db.commit()
        
        logger.info(f"Scan completed for account {request.account_id}: {len(findings_data)} findings")
        
        return schemas.ScanResponse(
            scan_id=scan_id,
            account_id=request.account_id,
            status="completed",
            started_at=datetime.utcnow(),
            message=f"Found {len(findings_data)} findings",
        )
    except Exception as e:
        logger.error(f"Scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Findings Endpoints

@router.get("/findings", response_model=List[dict])
async def get_findings(
    account_id: str = None,
    db: Session = Depends(get_db)
):
    """Get all security findings."""
    query = db.query(database_models.Finding)
    
    if account_id:
        account = db.query(database_models.CloudAccount).filter(
            database_models.CloudAccount.account_id == account_id
        ).first()
        if account:
            query = query.filter(database_models.Finding.account_id == account.id)
    
    findings = query.all()
    return [
        {
            "id": f.id,
            "resource_id": f.resource_id,
            "resource_type": f.resource_type,
            "title": f.title,
            "description": f.description,
            "security_risk": f.security_risk.value,
            "benchmark_metadata": f.benchmark_metadata,
            "created_at": f.created_at.isoformat(),
        }
        for f in findings
    ]


@router.get("/cost-findings", response_model=List[dict])
async def get_cost_findings(
    account_id: str = None,
    db: Session = Depends(get_db)
):
    """Get all cost optimization findings."""
    query = db.query(database_models.CostFinding)
    
    if account_id:
        account = db.query(database_models.CloudAccount).filter(
            database_models.CloudAccount.account_id == account_id
        ).first()
        if account:
            query = query.filter(database_models.CostFinding.account_id == account.id)
    
    findings = query.all()
    return [
        {
            "id": f.id,
            "resource_id": f.resource_id,
            "resource_type": f.resource_type,
            "title": f.title,
            "description": f.description,
            "current_monthly_cost": f.current_monthly_cost,
            "potential_monthly_savings": f.potential_monthly_savings,
            "savings_percentage": f.savings_percentage,
            "created_at": f.created_at.isoformat(),
        }
        for f in findings
    ]


@router.get("/finding/{finding_id}")
async def get_finding_detail(
    finding_id: str,
    finding_type: str = "security",
    db: Session = Depends(get_db)
):
    """Get complete finding detail with decision and remediation plan."""
    try:
        if finding_type == "cost":
            cost_finding = db.query(database_models.CostFinding).filter(
                database_models.CostFinding.id == finding_id
            ).first()
            if not cost_finding:
                raise HTTPException(status_code=404, detail="Finding not found")

            account = db.query(database_models.CloudAccount).filter(
                database_models.CloudAccount.id == cost_finding.account_id
            ).first()
            check_type = _infer_check_type(cost_finding.resource_type, cost_finding.title)
            connector = AWSConnector(
                role_arn=account.role_arn,
                external_id=account.external_id,
                access_key_id=account.access_key_id,
                secret_access_key=account.secret_access_key,
            )
            decision_output = decision_engine.analyze_finding(
                finding_id=cost_finding.id,
                resource_id=cost_finding.resource_id,
                resource_type=cost_finding.resource_type,
                security_risk="low",
                monthly_cost=cost_finding.current_monthly_cost,
                potential_savings=cost_finding.potential_monthly_savings,
                check_type=check_type,
            )
            impact_analyzer = ImpactAnalyzer(connector)
            aws_resources = {
                "instances": connector.get_ec2_instances(),
                "security_groups": connector.get_security_groups(),
                "volumes": connector.get_ebs_volumes(),
                "buckets": connector.get_s3_buckets(),
                "rds_instances": connector.get_rds_instances(),
            }
            impact = impact_analyzer.analyze_impact(
                resource_id=cost_finding.resource_id,
                resource_type=cost_finding.resource_type,
                action=decision_output.recommended_action,
                aws_resources=aws_resources,
            )
            planner = RemediationPlanner()
            plan = planner.create_plan(
                decision_id=str(uuid.uuid4()),
                resource_id=cost_finding.resource_id,
                resource_type=cost_finding.resource_type,
                recommended_action=decision_output.recommended_action,
                check_type=check_type,
                stability_risk=decision_output.stability_risk.value,
                cost_impact=cost_finding.potential_monthly_savings,
            )
            return {
                "finding": {
                    "id": cost_finding.id,
                    "resource_id": cost_finding.resource_id,
                    "resource_type": cost_finding.resource_type,
                    "title": cost_finding.title,
                    "description": cost_finding.description,
                    "security_risk": "low",
                    "current_monthly_cost": cost_finding.current_monthly_cost,
                    "potential_monthly_savings": cost_finding.potential_monthly_savings,
                },
                "decision": decision_output.model_dump(),
                "impact_analysis": impact.model_dump(),
                "remediation_plan": plan.model_dump(),
                "status": "pending",
            }

        finding = db.query(database_models.Finding).filter(
            database_models.Finding.id == finding_id
        ).first()

        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        account = db.query(database_models.CloudAccount).filter(
            database_models.CloudAccount.id == finding.account_id
        ).first()
        check_type = _infer_check_type(finding.resource_type, finding.title)

        decision = db.query(database_models.Decision).filter(
            database_models.Decision.finding_id == finding_id
        ).first()

        if not decision:
            decision_output = decision_engine.analyze_finding(
                finding_id=finding.id,
                resource_id=finding.resource_id,
                resource_type=finding.resource_type,
                security_risk=finding.security_risk.value,
                check_type=check_type,
            )

            decision = database_models.Decision(
                id=str(uuid.uuid4()),
                finding_id=finding.id,
                account_id=finding.account_id,
                decision_data=decision_output.model_dump(),
            )
            db.add(decision)
            db.commit()
            db.refresh(decision)

        connector = AWSConnector(
            role_arn=account.role_arn,
            external_id=account.external_id,
            access_key_id=account.access_key_id,
            secret_access_key=account.secret_access_key,
        )
        impact_analyzer = ImpactAnalyzer(connector)
        aws_resources = {
            "instances": connector.get_ec2_instances(),
            "security_groups": connector.get_security_groups(),
            "volumes": connector.get_ebs_volumes(),
            "buckets": connector.get_s3_buckets(),
            "rds_instances": connector.get_rds_instances(),
        }
        impact = impact_analyzer.analyze_impact(
            resource_id=finding.resource_id,
            resource_type=finding.resource_type,
            action=decision.decision_data.get("recommended_action", "review_manually"),
            aws_resources=aws_resources,
        )
        planner = RemediationPlanner()
        plan = planner.create_plan(
            decision_id=decision.id,
            resource_id=finding.resource_id,
            resource_type=finding.resource_type,
            recommended_action=decision.decision_data.get("recommended_action", "review_manually"),
            check_type=check_type,
            stability_risk=decision.decision_data.get("stability_risk", "medium"),
            cost_impact=decision.decision_data.get("potential_savings", 0),
        )

        return {
            "finding": {
                "id": finding.id,
                "resource_id": finding.resource_id,
                "resource_type": finding.resource_type,
                "title": finding.title,
                "description": finding.description,
                "security_risk": finding.security_risk.value,
                "benchmark_metadata": finding.benchmark_metadata,
            },
            "decision": decision.decision_data,
            "impact_analysis": impact.model_dump(),
            "remediation_plan": plan.model_dump(),
            "status": decision.status.value,
        }
    except Exception as e:
        logger.error(f"Error fetching finding detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Decision Endpoints

@router.get("/decisions")
async def get_decisions(
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get all decisions."""
    query = db.query(database_models.Decision)
    
    if status:
        query = query.filter(database_models.Decision.status == status)
    
    decisions = query.all()
    return [
        {
            "id": d.id,
            "finding_id": d.finding_id,
            "status": d.status.value,
            "created_at": d.created_at.isoformat(),
            "decision_data": d.decision_data,
        }
        for d in decisions
    ]


# Remediation Endpoints

@router.post("/generate-plan/{finding_id}")
async def generate_remediation_plan(
    finding_id: str,
    db: Session = Depends(get_db)
):
    """Generate remediation plan for a finding."""
    try:
        finding = db.query(database_models.Finding).filter(
            database_models.Finding.id == finding_id
        ).first()
        
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")
        
        # Get decision
        decision = db.query(database_models.Decision).filter(
            database_models.Decision.finding_id == finding_id
        ).first()
        
        if not decision:
            raise HTTPException(status_code=400, detail="Decision not generated yet")
        
        # Generate remediation plan
        decision_data = decision.decision_data
        planner = RemediationPlanner()
        
        plan = planner.create_plan(
            decision_id=decision.id,
            resource_id=finding.resource_id,
            resource_type=finding.resource_type,
            recommended_action=decision_data.get("recommended_action"),
            check_type="generic",  # Would be extracted from finding
            stability_risk=decision_data.get("stability_risk", "medium"),
            cost_impact=decision_data.get("potential_savings", 0),
        )
        
        # Store plan
        db_plan = database_models.RemediationPlan(
            id=str(uuid.uuid4()),
            decision_id=decision.id,
            description=plan.description,
            risk_explanation=plan.risk_explanation,
            cost_impact=plan.cost_impact,
            stability_impact=plan.stability_impact,
            steps=plan.steps,
            terraform_code=plan.terraform_code,
            requires_approval=plan.requires_approval,
            estimated_time_minutes=plan.estimated_time_minutes,
        )
        db.add(db_plan)
        db.commit()
        
        return {
            "plan_id": db_plan.id,
            "description": plan.description,
            "steps": plan.steps,
            "terraform_code": plan.terraform_code,
            "estimated_time_minutes": plan.estimated_time_minutes,
        }
    except Exception as e:
        logger.error(f"Error generating plan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{decision_id}")
async def approve_decision(
    decision_id: str,
    request: schemas.RemediationApprovalRequest,
    db: Session = Depends(get_db)
):
    """Approve a decision for execution."""
    try:
        decision = db.query(database_models.Decision).filter(
            database_models.Decision.id == decision_id
        ).first()
        
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        
        decision.status = database_models.DecisionStatusEnum.APPROVED
        decision.approved_by = request.approved_by
        decision.approved_at = datetime.utcnow()
        decision.approval_notes = request.notes
        
        db.commit()
        
        logger.info(f"Decision {decision_id} approved by {request.approved_by}")
        
        return {"status": "approved", "decision_id": decision_id}
    except Exception as e:
        logger.error(f"Error approving decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/{decision_id}")
async def execute_decision(
    decision_id: str,
    db: Session = Depends(get_db)
):
    """Execute remediation for an approved decision."""
    try:
        decision = db.query(database_models.Decision).filter(
            database_models.Decision.id == decision_id
        ).first()
        
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        
        if decision.status != database_models.DecisionStatusEnum.APPROVED:
            raise HTTPException(status_code=400, detail="Decision must be approved first")
        
        # Execute
        execution_id = str(uuid.uuid4())
        
        # Create snapshot before execution
        snapshot_id = execution_manager.create_execution_snapshot(
            decision.finding.resource_id,
            decision.finding.resource_type,
            {"status": "active"}
        )
        
        result = execution_manager.execute_action(
            execution_id,
            decision.finding.resource_id,
            decision.finding.resource_type,
            decision.decision_data.get("recommended_action"),
            snapshot_id,
        )
        
        if result["status"] == "success":
            decision.status = database_models.DecisionStatusEnum.EXECUTED
        else:
            decision.status = database_models.DecisionStatusEnum.FAILED
        
        decision.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "execution_id": execution_id,
            "status": result["status"],
            "message": result["message"],
        }
    except Exception as e:
        logger.error(f"Error executing decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback/{execution_id}")
async def rollback_execution(
    execution_id: str,
    request: schemas.RollbackRequest = None,
    db: Session = Depends(get_db)
):
    """Rollback a completed execution."""
    try:
        result = execution_manager.rollback_execution(execution_id)
        
        if result["status"] == "success":
            logger.info(f"Execution {execution_id} rolled back")
        
        return result
    except Exception as e:
        logger.error(f"Error rolling back execution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Audit Logs Endpoint

@router.get("/logs")
async def get_audit_logs(
    account_id: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get audit logs."""
    query = db.query(database_models.AuditLog).order_by(database_models.AuditLog.timestamp.desc()).limit(limit)
    
    logs = query.all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "resource_id": l.resource_id,
            "resource_type": l.resource_type,
            "timestamp": l.timestamp.isoformat(),
            "user_id": l.user_id,
        }
        for l in logs
    ]


# Health Check

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
