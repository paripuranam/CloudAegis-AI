"""Remediation Planner - creates actionable fix plans."""
from typing import Dict, Any, List
from pydantic import BaseModel
from app.models.schemas import RemediationPlan, RiskLevel
from app.services.openrouter_client import OpenRouterClient
import logging

logger = logging.getLogger(__name__)


class AIRemediationDraft(BaseModel):
    """Validated AI response for remediation plan enrichment."""
    description: str
    risk_explanation: str
    security_remediation: str
    cost_optimization: str
    steps: List[str]
    terraform_code: str | None = None


class RemediationPlanner:
    """
    Generates detailed remediation plans for findings.
    
    Each plan includes:
    - Description of what will be fixed
    - Risk and cost impacts
    - Step-by-step instructions
    - Terraform Infrastructure-as-Code representation
    """

    def __init__(self) -> None:
        self.ai_client = OpenRouterClient()

    def create_plan(
        self,
        decision_id: str,
        resource_id: str,
        resource_type: str,
        recommended_action: str,
        check_type: str,
        stability_risk: str,
        cost_impact: float,
    ) -> RemediationPlan:
        """
        Create remediation plan based on finding and decision.
        
        Args:
            decision_id: Associated decision ID
            resource_id: AWS resource ID
            resource_type: Type of resource
            recommended_action: The recommended action
            check_type: Type of check that found the issue
            stability_risk: Risk level of applying fix
            cost_impact: Cost impact (positive = cost, negative = savings)
            
        Returns:
            RemediationPlan with detailed steps and Terraform code
        """
        
        # Dispatch to specific planner based on check type
        if check_type == "s3_public_access":
            plan = self._plan_s3_public_access_fix(decision_id, resource_id, stability_risk, cost_impact)
        elif check_type == "open_security_group":
            plan = self._plan_security_group_fix(decision_id, resource_id, stability_risk, cost_impact)
        elif check_type == "idle_ec2":
            plan = self._plan_idle_ec2_fix(decision_id, resource_id, stability_risk, cost_impact)
        elif check_type == "unattached_ebs":
            plan = self._plan_ebs_deletion(decision_id, resource_id, stability_risk, cost_impact)
        elif check_type == "over_provisioned_ec2":
            plan = self._plan_ec2_downgrade(decision_id, resource_id, stability_risk, cost_impact)
        else:
            plan = self._plan_manual_review(decision_id, resource_id, stability_risk, cost_impact)

        ai_draft = self._enhance_with_ai(
            resource_id=resource_id,
            resource_type=resource_type,
            recommended_action=recommended_action,
            check_type=check_type,
            stability_risk=stability_risk,
            cost_impact=cost_impact,
            fallback_plan=plan,
        )
        if ai_draft:
            plan.description = ai_draft.description
            plan.risk_explanation = ai_draft.risk_explanation
            plan.security_remediation = ai_draft.security_remediation
            plan.cost_optimization = ai_draft.cost_optimization
            plan.steps = ai_draft.steps
            if ai_draft.terraform_code:
                plan.terraform_code = ai_draft.terraform_code

        return plan

    def _plan_s3_public_access_fix(
        self,
        decision_id: str,
        bucket_name: str,
        stability_risk: str,
        cost_impact: float,
    ) -> RemediationPlan:
        """Create plan to restrict S3 bucket public access."""
        
        steps = [
            "1. Verify bucket name and contents",
            "2. Review existing bucket policies and ACLs",
            "3. Enable Public Access Block configuration",
            "4. Set BlockPublicAcls=true, IgnorePublicAcls=true, BlockPublicPolicy=true, RestrictPublicBuckets=true",
            "5. Test application access - verify no breakage",
            "6. Monitor CloudTrail logs for failed access attempts",
        ]
        
        terraform_code = f"""resource "aws_s3_public_access_block" "{bucket_name.replace('-', '_')}" {{
  bucket = "{bucket_name}"

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}}
"""
        
        return RemediationPlan(
            id=decision_id,
            finding_id="",
            description="Restrict S3 bucket public access by enabling Public Access Block configuration",
            risk_explanation="This change prevents public access. Applications relying on public access will be blocked until configured with proper credentials.",
            security_remediation="Enable S3 Public Access Block, review bucket policy and ACLs, and move any public content behind signed URLs or an approved CDN path.",
            cost_optimization="This is primarily a security remediation. Direct cost savings are minimal, but reducing exposure can prevent incident response and data exposure costs.",
            cost_impact=0,  # No cost change
            stability_impact=RiskLevel.LOW,
            steps=steps,
            terraform_code=terraform_code,
            requires_approval=True,
            estimated_time_minutes=10,
        )

    def _plan_security_group_fix(
        self,
        decision_id: str,
        sg_id: str,
        stability_risk: str,
        cost_impact: float,
    ) -> RemediationPlan:
        """Create plan to restrict security group access."""
        
        steps = [
            "1. Identify currently allowed IPs/CIDR blocks",
            "2. Document which systems need access",
            "3. Create new restrictive ingress rule(s) with specific CIDR blocks",
            "4. Remove overly permissive 0.0.0.0/0 rules",
            "5. Test remote access from whitelisted IPs",
            "6. Wait for any active connections to close before final removal",
        ]
        
        terraform_code = f"""# Remove dangerous ingress rule
resource "aws_security_group_rule" "remove_unsafe_ssh" {{
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = "{sg_id}"
  
  # Set to 'destroy' in apply to remove it
}}

# Add restricted SSH access
resource "aws_security_group_rule" "restrict_ssh" {{
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["YOUR_IP/32" 
  security_group_id = "{sg_id}"
}}
"""
        
        return RemediationPlan(
            id=decision_id,
            finding_id="",
            description="Restrict security group ingress rules from 0.0.0.0/0 to specific IP ranges",
            risk_explanation=f"Restricting security group access has {stability_risk} stability risk. Active SSH/RDP connections from other IPs will be blocked.",
            security_remediation="Replace 0.0.0.0/0 access with approved CIDR blocks, bastion access, VPN entry points, or just-in-time administrative access.",
            cost_optimization="This is mainly a risk reduction measure. It does not directly lower infrastructure spend, but it reduces the likelihood of costly exposure or misuse.",
            cost_impact=0,
            stability_impact=RiskLevel(stability_risk),
            steps=steps,
            terraform_code=terraform_code,
            requires_approval=True,
            estimated_time_minutes=30,
        )

    def _plan_idle_ec2_fix(
        self,
        decision_id: str,
        instance_id: str,
        stability_risk: str,
        cost_impact: float,
    ) -> RemediationPlan:
        """Create plan to address idle EC2 instance."""
        
        steps = [
            "1. Verify instance is not running critical workloads",
            "2. Check CloudWatch metrics for 14+ days of low utilization",
            "3. Create AMI snapshot as backup",
            "4. Stop the instance (or schedule termination after 30 days)",
            "5. Monitor associated storage and network costs",
            "6. Set CloudWatch alarm if instance restarts unexpectedly",
        ]
        
        terraform_code = f"""# Stop the idle instance
resource "aws_ec2_instance_state" "{instance_id}" {{
  instance_id = "{instance_id}"
  force       = true
  state       = "stopped"
}}

# Or schedule termination after 7 days
# Uncomment to enable
# resource "aws_instance_lifecycle_action" "terminate_idle" {{
#   instance_id = "{instance_id}"
#   lifecycle_transition = "autoscaling:EC2_INSTANCE_TERMINATING"
#   default_result = "CONTINUE"
# }}
"""
        
        return RemediationPlan(
            id=decision_id,
            finding_id="",
            description="Stop idle EC2 instance to reduce cloud costs",
            risk_explanation="Stopping the instance will make it unavailable. Data persists on EBS volumes. Services depending on this instance will go down.",
            security_remediation="Before stopping, verify the instance is not providing a security control, jump host, or monitoring function that would weaken your defensive posture.",
            cost_optimization="Stopping or scheduling retirement for the idle instance reduces recurring compute charges while preserving attached data for rollback or recovery.",
            cost_impact=cost_impact,  # Negative value = savings
            stability_impact=RiskLevel.MEDIUM,
            steps=steps,
            terraform_code=terraform_code,
            requires_approval=True,
            estimated_time_minutes=5,
        )

    def _plan_ebs_deletion(
        self,
        decision_id: str,
        volume_id: str,
        stability_risk: str,
        cost_impact: float,
    ) -> RemediationPlan:
        """Create plan to delete unattached EBS volume."""
        
        steps = [
            "1. Verify volume is unattached and not in snapshots",
            "2. Review creation date and last attachment time",
            "3. Create snapshot as backup (optional but recommended)",
            "4. Delete the EBS volume",
            "5. Verify deletion in AWS Console",
        ]
        
        terraform_code = f"""resource "aws_ebs_volume" "{volume_id.replace('-', '_')}" {{
  availability_zone = "us-east-1a"  # Replace with actual AZ
  size              = 100           # Replace with actual size
  
  # Mark for deletion
  # terraform destroy will delete this resource
  
  tags = {{
    Name = "{volume_id}"
    Status = "deleted"
  }}
}}
"""
        
        return RemediationPlan(
            id=decision_id,
            finding_id="",
            description="Delete unattached EBS volume to reduce cloud costs",
            risk_explanation="Unattached volume has no active impact. Data will be permanently deleted. No stability risk.",
            security_remediation="Create and retain a final encrypted snapshot before deletion if the volume may contain sensitive or regulated data.",
            cost_optimization="Deleting the unattached volume removes pure storage waste because the asset is no longer serving an active workload.",
            cost_impact=cost_impact,  # Savings from deletion
            stability_impact=RiskLevel.LOW,
            steps=steps,
            terraform_code=terraform_code,
            requires_approval=True,
            estimated_time_minutes=5,
        )

    def _plan_ec2_downgrade(
        self,
        decision_id: str,
        instance_id: str,
        stability_risk: str,
        cost_impact: float,
    ) -> RemediationPlan:
        """Create plan to downgrade over-provisioned EC2 instance."""
        
        steps = [
            "1. Stop the instance (requires downtime)",
            "2. Change instance type to smaller size (e.g., t3.large → t3.medium)",
            "3. Start the instance",
            "4. Monitor application performance for 24-48 hours",
            "5. Verify CPU and memory utilization remain normal",
            "6. Monitor application logs for errors",
        ]
        
        terraform_code = f"""resource "aws_instance" "{instance_id.replace('-', '_')}" {{
  instance_id = "{instance_id}"

  # Change instance type (requires stop/start)
  instance_type = "t3.medium"  # Change FROM current type

  tags = {{
    Name  = "{instance_id}"
    Downgraded = "true"
    DowngradedDate = timestamp()
  }}

  lifecycle {{
    ignore_changes = [ami]
  }}
}}
"""
        
        return RemediationPlan(
            id=decision_id,
            finding_id="",
            description="Downgrade EC2 instance to smaller type for cost optimization",
            risk_explanation=f"Downgrading requires stopping the instance, causing brief downtime. Has {stability_risk} stability risk - verify application can run on smaller instance type.",
            security_remediation="Validate that the smaller instance still supports required security tooling, logging agents, endpoint protection, and patching windows.",
            cost_optimization="Rightsizing the instance reduces recurring compute cost while preserving workload availability if performance validation passes after the resize.",
            cost_impact=cost_impact,  # Negative = savings
            stability_impact=RiskLevel(stability_risk),
            steps=steps,
            terraform_code=terraform_code,
            requires_approval=True,
            estimated_time_minutes=15,
        )

    def _plan_manual_review(
        self,
        decision_id: str,
        resource_id: str,
        stability_risk: str,
        cost_impact: float,
    ) -> RemediationPlan:
        """Create plan for manual review (when automation isn't available)."""
        
        steps = [
            "1. Review the finding details and impact analysis",
            "2. Consult with the resource owner and operations team",
            "3. Assess feasibility of automation",
            "4. Decide: Fix manually or mark as accepted risk",
            "5. Document decision and rationale",
        ]
        
        return RemediationPlan(
            id=decision_id,
            finding_id="",
            description="Manual review required for this finding",
            risk_explanation="Automated remediation not available. Manual review and execution required.",
            security_remediation="Review the control gap, define the target secure state, and document the manual remediation path before any change is made.",
            cost_optimization="Assess whether the finding also reflects underused or misconfigured spend, and document the expected savings before approving action.",
            cost_impact=0,
            stability_impact=RiskLevel.MEDIUM,
            steps=steps,
            terraform_code=None,
            requires_approval=True,
            estimated_time_minutes=30,
        )

    def _enhance_with_ai(
        self,
        resource_id: str,
        resource_type: str,
        recommended_action: str,
        check_type: str,
        stability_risk: str,
        cost_impact: float,
        fallback_plan: RemediationPlan,
    ) -> AIRemediationDraft | None:
        """Optionally refine the operator-facing remediation plan."""
        system_prompt = (
            "You are a senior DevSecOps and Terraform engineer. "
            "Return only JSON. Draft conservative remediation guidance and Terraform. "
            "Avoid unsafe automation and preserve approval-first workflows."
        )
        user_prompt = f"""
Create a remediation draft for this cloud finding.

Resource ID: {resource_id}
Resource Type: {resource_type}
Check Type: {check_type}
Recommended Action: {recommended_action}
Stability Risk: {stability_risk}
Cost Impact: {cost_impact}

Fallback Plan:
- description: {fallback_plan.description}
- risk_explanation: {fallback_plan.risk_explanation}
- security_remediation: {fallback_plan.security_remediation}
- cost_optimization: {fallback_plan.cost_optimization}
- steps: {fallback_plan.steps}
- terraform_code: {fallback_plan.terraform_code}

Return JSON with:
- description
- risk_explanation
- security_remediation
- cost_optimization
- steps
- terraform_code
"""
        return self.ai_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AIRemediationDraft,
        )
