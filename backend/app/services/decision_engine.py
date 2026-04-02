"""Core Decision Engine - combines security, cost, and stability into decisions."""
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.models.schemas import DecisionOutput, RiskLevel
from app.services.openrouter_client import OpenRouterClient
import logging

logger = logging.getLogger(__name__)


class AIDecisionDraft(BaseModel):
    """Validated AI response for decision enrichment."""
    recommended_action: str
    confidence_score: float = Field(ge=0, le=1)
    reasoning: str
    cost_analysis: str
    stability_risk: RiskLevel


class DecisionEngine:
    """
    Core intelligence engine that combines:
    - Security risk assessment
    - Cost impact analysis
    - Stability risk evaluation
    - Decision recommendations
    """

    def __init__(self):
        """Initialize the decision engine."""
        self.ai_client = OpenRouterClient()
        self.risk_weights = {
            "security": 0.4,      # Security is 40% of decision
            "cost": 0.35,         # Cost is 35% of decision
            "stability": 0.25,    # Stability is 25% of decision
        }

    def analyze_finding(
        self,
        finding_id: str,
        resource_id: str,
        resource_type: str,
        security_risk: str,
        monthly_cost: float = 0,
        potential_savings: float = 0,
        check_type: str = None,
    ) -> DecisionOutput:
        """
        Generate decision for a finding by analyzing all dimensions.
        
        Args:
            finding_id: Finding identifier
            resource_id: AWS resource ID
            resource_type: Type of resource (EC2_INSTANCE, S3_BUCKET, etc)
            security_risk: Security risk level (low, medium, high, critical)
            monthly_cost: Current monthly cost
            potential_savings: Potential monthly savings
            check_type: Type of check that generated the finding
            
        Returns:
            DecisionOutput with recommendation
        """
        
        # Security risk score (0-1)
        security_score = self._calculate_security_score(security_risk)
        
        # Cost efficiency score (0-1) - higher savings = higher score
        cost_score = self._calculate_cost_score(monthly_cost, potential_savings)
        
        # Stability risk score (0-1)
        stability_score = self._calculate_stability_score(resource_type, check_type)
        
        # Calculate combined confidence score
        confidence = self._calculate_confidence(check_type, security_risk)
        
        # Determine recommended action
        recommended_action = self._determine_action(
            check_type,
            security_risk,
            potential_savings,
            stability_score
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            check_type,
            security_risk,
            potential_savings,
            stability_score
        )
        
        decision = DecisionOutput(
            resource=resource_id,
            security_risk=security_risk,
            monthly_cost=monthly_cost,
            potential_savings=potential_savings,
            cost_analysis=self._generate_cost_analysis(monthly_cost, potential_savings, check_type),
            stability_risk=self._score_to_risk_level(stability_score),
            recommended_action=recommended_action,
            confidence_score=confidence,
            reasoning=reasoning,
        )

        ai_draft = self._enhance_with_ai(
            resource_id=resource_id,
            resource_type=resource_type,
            security_risk=security_risk,
            monthly_cost=monthly_cost,
            potential_savings=potential_savings,
            check_type=check_type,
            fallback_decision=decision,
        )
        if ai_draft:
            decision.recommended_action = ai_draft.recommended_action
            decision.confidence_score = ai_draft.confidence_score
            decision.reasoning = ai_draft.reasoning
            decision.cost_analysis = ai_draft.cost_analysis
            decision.stability_risk = ai_draft.stability_risk

        return decision

    def _calculate_security_score(self, risk_level: str) -> float:
        """Convert risk level to 0-1 score."""
        score_map = {
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8,
            "critical": 1.0,
        }
        return score_map.get(risk_level.lower(), 0.3)

    def _calculate_cost_score(self, monthly_cost: float, potential_savings: float) -> float:
        """Calculate cost efficiency score."""
        if monthly_cost == 0:
            return 0.0
        
        savings_percentage = (potential_savings / monthly_cost) if monthly_cost > 0 else 0
        
        # Cap at 1.0
        return min(savings_percentage / 2, 1.0)  # Normalize

    def _calculate_stability_score(self, resource_type: str, check_type: str) -> float:
        """
        Assess stability risk of remediation.
        
        Lower scores = lower stability risk (safer to fix)
        Higher scores = higher stability risk (dangerous to fix)
        """
        
        # Check type stability mapping
        stability_map = {
            # High risk changes
            "open_security_group": 0.7,  # Could break existing connections
            "idle_ec2": 0.4,             # Safe to stop
            "unattached_ebs": 0.1,       # Very safe to delete
            "s3_public_access": 0.3,     # Safe but test needed
            "iam_wildcard_policy": 0.8,  # Could break applications
            "s3_lifecycle": 0.2,         # Low risk
            "over_provisioned_ec2": 0.5, # Medium risk - could degrade performance
        }
        
        return stability_map.get(check_type, 0.5)

    def _score_to_risk_level(self, score: float) -> str:
        """Convert stability score to risk level."""
        if score < 0.25:
            return RiskLevel.LOW
        elif score < 0.5:
            return RiskLevel.MEDIUM
        elif score < 0.75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _determine_action(
        self,
        check_type: str,
        security_risk: str,
        potential_savings: float,
        stability_score: float,
    ) -> str:
        """
        Determine recommended action based on all factors.
        
        Priority:
        1. Critical security risks → Fix immediately
        2. High security + low stability risk → Fix with approval
        3. High security + high stability risk → Recommend with caution
        4. Cost issues → Recommend for approval
        """
        
        action_map = {
            "s3_public_access": "restrict_public_access",
            "open_security_group": "restrict_security_group",
            "idle_ec2": "stop_instance",
            "over_provisioned_ec2": "downgrade_instance",
            "unattached_ebs": "delete_volume",
            "iam_wildcard_policy": "review_policy",
            "s3_lifecycle": "add_lifecycle_policy",
        }
        
        base_action = action_map.get(check_type, "review_manually")
        
        # Adjust based on risk vs stability
        if security_risk == "critical" and stability_score < 0.5:
            return f"{base_action}_immediately"
        elif security_risk in ["high", "medium"] and stability_score < 0.3:
            return base_action
        elif stability_score > 0.7:
            return f"{base_action}_with_rollback_plan"
        else:
            return base_action

    def _calculate_confidence(self, check_type: str, security_risk: str) -> float:
        """
        Calculate confidence in the recommendation (0-1).
        
        Factors:
        - Check type reliability
        - Data freshness (assume recent)
        - Risk level clarity
        """
        
        # Base confidence by check type
        confidence_map = {
            "s3_public_access": 0.95,       # Very reliable check
            "open_security_group": 0.98,    # Definitive check
            "unattached_ebs": 0.99,         # Definitive check
            "idle_ec2": 0.75,               # Depends on monitoring window
            "over_provisioned_ec2": 0.70,   # Heuristic-based
            "iam_wildcard_policy": 0.65,    # Requires manual review
            "s3_lifecycle": 0.60,           # Recommendation-based
        }
        
        confidence = confidence_map.get(check_type, 0.65)
        
        # Adjust based on security risk clarity
        if security_risk in ["low", "critical"]:
            confidence = min(confidence + 0.05, 1.0)  # More confidence for clear cases
        
        return confidence

    def _generate_reasoning(
        self,
        check_type: str,
        security_risk: str,
        potential_savings: float,
        stability_score: float,
    ) -> str:
        """Generate human-readable reasoning for the decision."""
        
        reasoning_templates = {
            "s3_public_access": f"S3 bucket is publicly accessible, posing a {security_risk} security risk. Enable public access block to restrict.",
            "open_security_group": f"Security group allows unrestricted internet access on dangerous ports ({security_risk} risk). Whitelist specific IPs.",
            "idle_ec2": f"Instance shows consistently low CPU utilization. Consider stopping to save ~${potential_savings:.2f}/month.",
            "over_provisioned_ec2": f"Instance is over-provisioned for current workload. Downgrade could save ~${potential_savings:.2f}/month with {stability_score*100:.0f}% stability risk.",
            "unattached_ebs": f"EBS volume is not attached and incurs charges. Safe to delete and save ${potential_savings:.2f}/month.",
            "iam_wildcard_policy": f"IAM policy may be overly permissive. Review and apply least privilege principle.",
            "s3_lifecycle": f"Implement lifecycle policy to move old objects to cheaper storage and save ~${potential_savings:.2f}/month.",
        }
        
        return reasoning_templates.get(
            check_type,
            f"Review this finding: {check_type}. Security: {security_risk}, Stability risk: {stability_score*100:.0f}%"
        )

    def _generate_cost_analysis(
        self,
        monthly_cost: float,
        potential_savings: float,
        check_type: str,
    ) -> str:
        """Generate a cost-focused explanation for the finding."""
        if potential_savings <= 0 and monthly_cost <= 0:
            return "This finding is primarily risk-driven and does not present a meaningful direct cost optimization opportunity."

        if monthly_cost <= 0:
            return f"This change may not reduce current measured spend directly, but it supports governance hygiene with an estimated savings opportunity of ${potential_savings:.2f} per month."

        savings_ratio = (potential_savings / monthly_cost) if monthly_cost > 0 else 0
        percent = round(savings_ratio * 100)

        templates = {
            "idle_ec2": f"The instance currently costs about ${monthly_cost:.2f}/month and shows low utilization. Rightsizing or stopping it could recover roughly ${potential_savings:.2f}/month ({percent}% of current spend).",
            "over_provisioned_ec2": f"The workload appears oversized for demand. A smaller shape could reduce spend by about ${potential_savings:.2f}/month while preserving service if performance checks pass.",
            "unattached_ebs": f"This volume is generating spend without serving an active workload. Deleting it would remove approximately ${potential_savings:.2f}/month in wasted storage cost.",
            "oversized_ebs": f"The volume size suggests over-allocation. Rightsizing storage could recover around ${potential_savings:.2f}/month with relatively low operational impact after validation.",
            "s3_lifecycle": f"Storage lifecycle optimization could lower recurring bucket cost by about ${potential_savings:.2f}/month by transitioning colder data to cheaper tiers.",
            "idle_rds": f"The database appears underutilized relative to its current class. Rightsizing or consolidating it could reduce spend by roughly ${potential_savings:.2f}/month.",
            "unattached_eip": f"This Elastic IP is unattached and now billable. Releasing it would eliminate approximately ${potential_savings:.2f}/month of waste.",
        }

        return templates.get(
            check_type,
            f"Current estimated spend is ${monthly_cost:.2f}/month with a potential reduction of ${potential_savings:.2f}/month ({percent}% savings) if the recommendation is applied safely."
        )

    def _enhance_with_ai(
        self,
        resource_id: str,
        resource_type: str,
        security_risk: str,
        monthly_cost: float,
        potential_savings: float,
        check_type: str,
        fallback_decision: DecisionOutput,
    ) -> AIDecisionDraft | None:
        """Optionally refine the operator-facing decision with AI."""
        system_prompt = (
            "You are a senior cloud security and FinOps analyst. "
            "Return only JSON. Improve the recommendation and reasoning, but stay conservative. "
            "Never suggest automatic execution. Prefer rollback-safe, approval-first actions."
        )
        user_prompt = f"""
Analyze this cloud finding and produce a concise decision draft.

Resource ID: {resource_id}
Resource Type: {resource_type}
Check Type: {check_type}
Security Risk: {security_risk}
Monthly Cost: {monthly_cost}
Potential Savings: {potential_savings}

Fallback Decision:
- recommended_action: {fallback_decision.recommended_action}
- confidence_score: {fallback_decision.confidence_score}
- stability_risk: {fallback_decision.stability_risk}
- reasoning: {fallback_decision.reasoning}
- cost_analysis: {fallback_decision.cost_analysis}

Return JSON with:
- recommended_action
- confidence_score
- reasoning
- cost_analysis
- stability_risk
"""

        return self.ai_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AIDecisionDraft,
        )

    def batch_analyze(self, findings: List[Dict[str, Any]]) -> List[DecisionOutput]:
        """Run decision engine on multiple findings."""
        decisions = []
        
        for finding in findings:
            try:
                decision = self.analyze_finding(
                    finding_id=finding.get("id", ""),
                    resource_id=finding.get("resource_id", ""),
                    resource_type=finding.get("resource_type", ""),
                    security_risk=finding.get("security_risk", "medium"),
                    monthly_cost=finding.get("current_monthly_cost", 0),
                    potential_savings=finding.get("potential_monthly_savings", 0),
                    check_type=finding.get("check_type", ""),
                )
                decisions.append(decision)
            except Exception as e:
                logger.error(f"Error analyzing finding {finding.get('id')}: {str(e)}")
        
        logger.info(f"Generated {len(decisions)} decisions from {len(findings)} findings")
        return decisions
