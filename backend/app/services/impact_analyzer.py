"""Impact Analysis - determines blast radius and breakage risk."""
from typing import Dict, Any, List
from pydantic import BaseModel
from app.models.schemas import ImpactAnalysis, RiskLevel
from app.services.openrouter_client import OpenRouterClient
import logging

logger = logging.getLogger(__name__)


class AIImpactDraft(BaseModel):
    """Validated AI response for predictive impact analysis."""
    risk_of_breakage: RiskLevel
    explanation: str
    recommendation: str


class ImpactAnalyzer:
    """
    Analyzes the blast radius and potential breakage risk of remediation actions.
    
    This module prevents blind auto-fixes by identifying:
    - Which resources would be affected
    - Risk of active service disruption
    - Recommendations for safe execution
    """

    def __init__(self, aws_connector):
        """Initialize impact analyzer with AWS connector."""
        self.aws = aws_connector
        self.ai_client = OpenRouterClient()

    def analyze_security_group_change(
        self,
        sg_id: str,
        security_groups: List[Dict],
    ) -> ImpactAnalysis:
        """
        Analyze impact of restricting a security group.
        
        Args:
            sg_id: Security group ID to analyze
            security_groups: List of all security groups
            
        Returns:
            ImpactAnalysis with affected resources and recommendations
        """
        
        # Find the security group
        target_sg = None
        for sg in security_groups:
            if sg["GroupId"] == sg_id:
                target_sg = sg
                break
        
        if not target_sg:
            return ImpactAnalysis(
                affected_entities=[],
                risk_of_breakage=RiskLevel.LOW,
                explanation="Security group not found",
                recommendation="Verify security group exists",
            )
        
        # Get instances using this security group
        instances = self.aws.get_ec2_instances()
        affected_instances = []
        
        for instance in instances:
            for sg in instance.get("SecurityGroups", []):
                if sg.get("GroupId") == sg_id:
                    affected_instances.append(instance["InstanceId"])
        
        # Assess risk
        if not affected_instances:
            risk_level = RiskLevel.LOW
            explanation = "No instances are using this security group. Safe to modify."
        elif len(affected_instances) > 10:
            risk_level = RiskLevel.HIGH
            explanation = f"{len(affected_instances)} instances use this security group. Changes could cause widespread disruption."
        else:
            risk_level = RiskLevel.MEDIUM
            explanation = f"{len(affected_instances)} instances use this security group. Changes could affect service availability."
        
        recommendation = (
            "Schedule during maintenance window. Test with non-critical resources first. "
            f"Have SSH/RDP whitelist IPs ready before applying changes."
        )
        
        return ImpactAnalysis(
            affected_entities=affected_instances,
            risk_of_breakage=risk_level,
            explanation=explanation,
            recommendation=recommendation,
        )

    def analyze_ec2_termination(
        self,
        instance_id: str,
        instances: List[Dict],
    ) -> ImpactAnalysis:
        """
        Analyze impact of stopping/terminating an EC2 instance.
        
        Args:
            instance_id: Instance ID to analyze
            instances: List of all instances
            
        Returns:
            ImpactAnalysis with potential riskswith it
        """
        
        # Find the instance
        target_instance = None
        for instance in instances:
            if instance["InstanceId"] == instance_id:
                target_instance = instance
                break
        
        if not target_instance:
            return ImpactAnalysis(
                affected_entities=[],
                risk_of_breakage=RiskLevel.LOW,
                explanation="Instance not found",
                recommendation="Verify instance exists",
            )
        
        # Check if instance has dependent resources
        affected = [instance_id]
        risk_level = RiskLevel.LOW
        
        # Check if it's part of an ASG or load balancer (would need tags/metadata)
        tags = target_instance.get("Tags", {})
        
        if tags.get("aws:autoscaling:groupName"):
            risk_level = RiskLevel.MEDIUM
            explanation = "Instance is part of an Auto Scaling Group. Terminating may trigger scaling actions or deployment."
        elif tags.get("environment") == "production":
            risk_level = RiskLevel.HIGH
            explanation = "This is a production instance. Termination could cause service outage."
        else:
            explanation = "Instance appears to be non-critical. Safe to terminate with standard backup."
        
        recommendation = (
            "Verify workload is not active. Create AMI snapshot before terminating. "
            "Consider stopping first to test recovery."
        )
        
        return ImpactAnalysis(
            affected_entities=affected,
            risk_of_breakage=risk_level,
            explanation=explanation,
            recommendation=recommendation,
        )

    def analyze_volume_deletion(self, volume_id: str) -> ImpactAnalysis:
        """Analyze impact of deleting an EBS volume."""
        
        return ImpactAnalysis(
            affected_entities=[volume_id],
            risk_of_breakage=RiskLevel.LOW,
            explanation="EBS volume is unattached. Deletion has no active impact and cannot be recovered.",
            recommendation="Enable EBS snapshots before deletion if data retention is needed. Create snapshot for backup.",
        )

    def analyze_s3_public_access_restriction(self, bucket_name: str) -> ImpactAnalysis:
        """Analyze impact of restricting S3 bucket public access."""
        
        return ImpactAnalysis(
            affected_entities=[bucket_name],
            risk_of_breakage=RiskLevel.LOW,
            explanation="Restricting public access prevents unauthenticated access. Existing applications needing public access will break.",
            recommendation="Audit bucket policies and ACLs first. Update application configurations to use signed URLs or valid credentials.",
        )

    def analyze_impact(
        self,
        resource_id: str,
        resource_type: str,
        action: str,
        aws_resources: Dict[str, Any],
    ) -> ImpactAnalysis:
        """
        Main impact analysis dispatcher.
        
        Args:
            resource_id: AWS resource ID
            resource_type: Type of resource
            action: Action to be taken
            aws_resources: Pre-fetched AWS resource data
            
        Returns:
            ImpactAnalysis with recommendations
        """
        
        if resource_type == "SECURITY_GROUP":
            result = self.analyze_security_group_change(
                resource_id,
                aws_resources.get("security_groups", [])
            )
        elif resource_type == "EC2_INSTANCE":
            result = self.analyze_ec2_termination(
                resource_id,
                aws_resources.get("instances", [])
            )
        elif resource_type == "EBS_VOLUME":
            result = self.analyze_volume_deletion(resource_id)
        elif resource_type == "S3_BUCKET":
            result = self.analyze_s3_public_access_restriction(resource_id)
        else:
            result = ImpactAnalysis(
                affected_entities=[resource_id],
                risk_of_breakage=RiskLevel.MEDIUM,
                explanation="Impact analysis not available for this resource type.",
                recommendation="Perform manual impact assessment before execution.",
            )

        ai_draft = self._enhance_with_ai(resource_id, resource_type, action, result)
        if ai_draft:
            result.risk_of_breakage = ai_draft.risk_of_breakage
            result.explanation = ai_draft.explanation
            result.recommendation = ai_draft.recommendation

        return result

    def _enhance_with_ai(
        self,
        resource_id: str,
        resource_type: str,
        action: str,
        fallback_impact: ImpactAnalysis,
    ) -> AIImpactDraft | None:
        """Optionally enrich predictive impact analysis with AI reasoning."""
        system_prompt = (
            "You are a senior cloud reliability engineer. "
            "Return only JSON. Predict likely blast radius and breakage risk conservatively. "
            "Prefer operator-safe recommendations and rollback-first advice."
        )
        user_prompt = f"""
Analyze the likely impact of this cloud remediation.

Resource ID: {resource_id}
Resource Type: {resource_type}
Action: {action}

Fallback Impact:
- affected_entities: {fallback_impact.affected_entities}
- risk_of_breakage: {fallback_impact.risk_of_breakage}
- explanation: {fallback_impact.explanation}
- recommendation: {fallback_impact.recommendation}

Return JSON with:
- risk_of_breakage
- explanation
- recommendation
"""
        return self.ai_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AIImpactDraft,
        )
