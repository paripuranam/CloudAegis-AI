"""Security scanning module - SecOps checks."""
from typing import List, Dict, Any
from app.models.database_models import RiskLevelEnum
import logging

logger = logging.getLogger(__name__)


AWS_CIS_BENCHMARKS = {
    "1.2.0": {
        "label": "CIS AWS Foundations Benchmark v1.2.0",
        "controls": {
            "s3_public_access": ["2.1.1"],
            "s3_no_encryption": ["2.2.1"],
            "open_security_group": ["4.1"],
            "iam_wildcard_policy": ["1.16"],
            "iam_overprivileged_policy": ["1.16"],
        },
    },
    "1.4.0": {
        "label": "CIS AWS Foundations Benchmark v1.4.0",
        "controls": {
            "s3_public_access": ["2.1.4"],
            "s3_no_encryption": ["2.1.5"],
            "s3_versioning_disabled": ["2.1.7"],
            "open_security_group": ["4.1", "4.2"],
            "ebs_unencrypted": ["2.2.1"],
            "rds_public_access": ["2.3.2"],
            "rds_unencrypted": ["2.3.1"],
            "rds_backup_retention": ["2.3.3"],
            "iam_wildcard_policy": ["1.22"],
            "iam_overprivileged_policy": ["1.22"],
        },
    },
    "3.0.0": {
        "label": "CIS Amazon Web Services Foundations Benchmark v3.0.0",
        "controls": {
            "s3_public_access": ["2.1.4"],
            "s3_no_encryption": ["2.1.5"],
            "s3_versioning_disabled": ["2.1.7"],
            "s3_logging_disabled": ["2.1.6"],
            "open_security_group": ["5.1", "5.2"],
            "public_ec2_instance": ["5.3"],
            "ec2_imdsv1_enabled": ["5.6"],
            "ebs_unencrypted": ["2.2.1"],
            "rds_public_access": ["2.3.2"],
            "rds_unencrypted": ["2.3.1"],
            "rds_backup_retention": ["2.3.3"],
            "iam_wildcard_policy": ["1.22"],
            "iam_overprivileged_policy": ["1.22"],
        },
    },
}


class SecurityScanner:
    """Performs security checks on AWS resources."""

    def __init__(self, aws_connector, cis_benchmark_version: str = "3.0.0"):
        """Initialize security scanner with AWS connector."""
        self.aws = aws_connector
        self.cis_benchmark_version = cis_benchmark_version if cis_benchmark_version in AWS_CIS_BENCHMARKS else "3.0.0"

    def _with_benchmark_metadata(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Attach CIS benchmark metadata to a finding when a mapping exists."""
        check_type = finding.get("check_type")
        benchmark = AWS_CIS_BENCHMARKS.get(self.cis_benchmark_version, {})
        controls = benchmark.get("controls", {}).get(check_type)

        if controls:
            finding["benchmark_metadata"] = {
                "framework": "AWS CIS Foundations Benchmark",
                "version": self.cis_benchmark_version,
                "label": benchmark.get("label"),
                "controls": controls,
            }
        else:
            finding["benchmark_metadata"] = {
                "framework": "AWS CIS Foundations Benchmark",
                "version": self.cis_benchmark_version,
                "label": benchmark.get("label"),
                "controls": [],
            }

        return finding

    def scan_s3_public_access(self) -> List[Dict[str, Any]]:
        """
        Check for S3 buckets with public access enabled.
        
        Returns:
            List of findings for publicly accessible S3 buckets
        """
        findings = []
        buckets = self.aws.get_s3_buckets()
        
        for bucket in buckets:
            pab = bucket.get("PublicAccessBlock")
            
            # Check if public access is blocked
            is_publicly_accessible = not (
                pab and 
                pab.get("BlockPublicAcls") and 
                pab.get("BlockPublicPolicy") and
                pab.get("IgnorePublicAcls") and
                pab.get("RestrictPublicBuckets")
            )
            
            if is_publicly_accessible:
                findings.append(self._with_benchmark_metadata({
                    "resource_id": bucket["BucketName"],
                    "resource_type": "S3_BUCKET",
                    "title": f"S3 Bucket: {bucket['BucketName']} has public access enabled",
                    "description": "S3 bucket does not have public access block enabled. This could expose sensitive data.",
                    "security_risk": RiskLevelEnum.HIGH,
                    "affected_entities": [bucket["BucketName"]],
                    "remediation_available": True,
                    "check_type": "s3_public_access",
                }))
        
        logger.info(f"Found {len(findings)} S3 public access findings")
        return findings

    def scan_open_security_groups(self) -> List[Dict[str, Any]]:
        """
        Check for security groups with dangerous open rules (0.0.0.0/0 on SSH/RDP).
        
        Returns:
            List of findings for overly permissive security groups
        """
        findings = []
        security_groups = self.aws.get_security_groups()
        
        dangerous_ports = [22, 3389]  # SSH and RDP
        
        for sg in security_groups:
            for rule in sg.get("IngressRules", []):
                for ip_range in rule.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        from_port = rule.get("FromPort", 0)
                        to_port = rule.get("ToPort", 65535)
                        
                        # Check if dangerous port is in range
                        for port in dangerous_ports:
                            if from_port <= port <= to_port or (from_port == -1 and to_port == -1):
                                findings.append(self._with_benchmark_metadata({
                                    "resource_id": sg["GroupId"],
                                    "resource_type": "SECURITY_GROUP",
                                    "title": f"Security Group {sg['GroupId']} allows unrestricted access to port {port}",
                                    "description": f"Security group allows 0.0.0.0/0 (entire internet) access to port {port}. This is a critical security risk.",
                                    "security_risk": RiskLevelEnum.CRITICAL,
                                    "affected_entities": [sg["GroupId"]],
                                    "remediation_available": True,
                                    "check_type": "open_security_group",
                                }))
        
        logger.info(f"Found {len(findings)} security group findings")
        return findings

    def scan_public_security_groups(self) -> List[Dict[str, Any]]:
        """
        Flag security groups that expose non-admin ports or all traffic to the internet.
        """
        findings = []
        security_groups = self.aws.get_security_groups()

        for sg in security_groups:
            for rule in sg.get("IngressRules", []):
                from_port = rule.get("FromPort", 0)
                to_port = rule.get("ToPort", 65535)
                protocol = rule.get("IpProtocol", "")

                for ip_range in rule.get("IpRanges", []):
                    cidr = ip_range.get("CidrIp")
                    if cidr != "0.0.0.0/0":
                        continue

                    if protocol == "-1":
                        findings.append(self._with_benchmark_metadata({
                            "resource_id": sg["GroupId"],
                            "resource_type": "SECURITY_GROUP",
                            "title": f"Security Group {sg['GroupId']} allows all traffic from the internet",
                            "description": "This security group exposes all protocols and ports to 0.0.0.0/0, creating a broad attack surface.",
                            "security_risk": RiskLevelEnum.CRITICAL,
                            "affected_entities": [sg["GroupId"]],
                            "remediation_available": True,
                            "check_type": "open_security_group",
                        }))
                        continue

                    if from_port not in (22, 3389) and to_port not in (22, 3389):
                        findings.append(self._with_benchmark_metadata({
                            "resource_id": sg["GroupId"],
                            "resource_type": "SECURITY_GROUP",
                            "title": f"Security Group {sg['GroupId']} exposes ports {from_port}-{to_port} to the internet",
                            "description": f"Ingress on ports {from_port}-{to_port} is open to 0.0.0.0/0. Review whether this exposure is intended and protected.",
                            "security_risk": RiskLevelEnum.HIGH,
                            "affected_entities": [sg["GroupId"]],
                            "remediation_available": True,
                            "check_type": "open_security_group",
                        }))

        logger.info(f"Found {len(findings)} general public exposure security group findings")
        return findings

    def scan_public_ec2_instances(self) -> List[Dict[str, Any]]:
        """
        Flag EC2 instances with public IP addresses so they can be reviewed in context.
        """
        findings = []
        instances = self.aws.get_ec2_instances()

        for instance in instances:
            public_ip = instance.get("PublicIpAddress")
            if not public_ip or instance.get("State") != "running":
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": instance["InstanceId"],
                "resource_type": "EC2_INSTANCE",
                "title": f"EC2 Instance {instance['InstanceId']} is directly internet reachable",
                "description": f"Instance has public IP address {public_ip}. Confirm this workload should be publicly accessible and protected by tightly scoped security groups.",
                "security_risk": RiskLevelEnum.MEDIUM,
                "affected_entities": [instance["InstanceId"], public_ip],
                "remediation_available": False,
                "check_type": "public_ec2_instance",
            }))

        logger.info(f"Found {len(findings)} public EC2 instance findings")
        return findings

    def scan_ec2_imdsv1_usage(self) -> List[Dict[str, Any]]:
        """Flag instances that still allow IMDSv1."""
        findings = []
        instances = self.aws.get_ec2_instances()

        for instance in instances:
            metadata_options = instance.get("MetadataOptions", {})
            if metadata_options.get("HttpTokens") == "required":
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": instance["InstanceId"],
                "resource_type": "EC2_INSTANCE",
                "title": f"EC2 Instance {instance['InstanceId']} does not require IMDSv2",
                "description": "Instance metadata service still allows IMDSv1. Enforce IMDSv2 to reduce SSRF and credential theft risk.",
                "security_risk": RiskLevelEnum.MEDIUM,
                "affected_entities": [instance["InstanceId"]],
                "remediation_available": True,
                "check_type": "ec2_imdsv1_enabled",
            }))

        logger.info(f"Found {len(findings)} IMDSv1 findings")
        return findings

    def scan_ebs_unencrypted(self) -> List[Dict[str, Any]]:
        """Flag EBS volumes without encryption at rest."""
        findings = []
        volumes = self.aws.get_ebs_volumes()

        for volume in volumes:
            if volume.get("Encrypted"):
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": volume["VolumeId"],
                "resource_type": "EBS_VOLUME",
                "title": f"EBS Volume {volume['VolumeId']} is not encrypted",
                "description": "Volume data is stored without EBS encryption. Snapshot, recreate with encryption, and cut over safely.",
                "security_risk": RiskLevelEnum.HIGH,
                "affected_entities": [volume["VolumeId"]],
                "remediation_available": True,
                "check_type": "ebs_unencrypted",
            }))

        logger.info(f"Found {len(findings)} unencrypted EBS findings")
        return findings

    def scan_s3_without_encryption(self) -> List[Dict[str, Any]]:
        """Flag S3 buckets without default encryption enabled."""
        findings = []
        buckets = self.aws.get_s3_buckets()

        for bucket in buckets:
            if bucket.get("EncryptionEnabled"):
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": bucket["BucketName"],
                "resource_type": "S3_BUCKET",
                "title": f"S3 Bucket {bucket['BucketName']} has no default encryption",
                "description": "Default bucket encryption is disabled. Enable SSE-S3 or SSE-KMS to protect data at rest.",
                "security_risk": RiskLevelEnum.HIGH,
                "affected_entities": [bucket["BucketName"]],
                "remediation_available": True,
                "check_type": "s3_no_encryption",
            }))

        logger.info(f"Found {len(findings)} S3 encryption findings")
        return findings

    def scan_s3_without_versioning(self) -> List[Dict[str, Any]]:
        """Flag S3 buckets without versioning."""
        findings = []
        buckets = self.aws.get_s3_buckets()

        for bucket in buckets:
            if bucket.get("VersioningStatus") == "Enabled":
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": bucket["BucketName"],
                "resource_type": "S3_BUCKET",
                "title": f"S3 Bucket {bucket['BucketName']} has versioning disabled",
                "description": "Versioning is disabled, which increases ransomware and accidental deletion risk.",
                "security_risk": RiskLevelEnum.MEDIUM,
                "affected_entities": [bucket["BucketName"]],
                "remediation_available": True,
                "check_type": "s3_versioning_disabled",
            }))

        logger.info(f"Found {len(findings)} S3 versioning findings")
        return findings

    def scan_s3_without_logging(self) -> List[Dict[str, Any]]:
        """Flag S3 buckets without server access logging."""
        findings = []
        buckets = self.aws.get_s3_buckets()

        for bucket in buckets:
            if bucket.get("LoggingEnabled"):
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": bucket["BucketName"],
                "resource_type": "S3_BUCKET",
                "title": f"S3 Bucket {bucket['BucketName']} has access logging disabled",
                "description": "Server access logging is not enabled, reducing auditability of object access patterns.",
                "security_risk": RiskLevelEnum.LOW,
                "affected_entities": [bucket["BucketName"]],
                "remediation_available": True,
                "check_type": "s3_logging_disabled",
            }))

        logger.info(f"Found {len(findings)} S3 logging findings")
        return findings

    def scan_rds_public_access(self) -> List[Dict[str, Any]]:
        """Flag publicly accessible RDS instances."""
        findings = []
        instances = self.aws.get_rds_instances()

        for instance in instances:
            if not instance.get("PubliclyAccessible"):
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": instance["DBInstanceIdentifier"],
                "resource_type": "RDS_INSTANCE",
                "title": f"RDS Instance {instance['DBInstanceIdentifier']} is publicly accessible",
                "description": "The database can be reached from public networks. Confirm this is intentional and protected with least-privilege network rules.",
                "security_risk": RiskLevelEnum.HIGH,
                "affected_entities": [instance["DBInstanceIdentifier"]],
                "remediation_available": True,
                "check_type": "rds_public_access",
            }))

        logger.info(f"Found {len(findings)} public RDS findings")
        return findings

    def scan_rds_unencrypted(self) -> List[Dict[str, Any]]:
        """Flag RDS instances without storage encryption."""
        findings = []
        instances = self.aws.get_rds_instances()

        for instance in instances:
            if instance.get("StorageEncrypted"):
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": instance["DBInstanceIdentifier"],
                "resource_type": "RDS_INSTANCE",
                "title": f"RDS Instance {instance['DBInstanceIdentifier']} is not encrypted",
                "description": "Database storage encryption is disabled. Recreate or migrate to an encrypted database instance.",
                "security_risk": RiskLevelEnum.HIGH,
                "affected_entities": [instance["DBInstanceIdentifier"]],
                "remediation_available": True,
                "check_type": "rds_unencrypted",
            }))

        logger.info(f"Found {len(findings)} unencrypted RDS findings")
        return findings

    def scan_rds_backup_retention(self) -> List[Dict[str, Any]]:
        """Flag RDS instances with short or disabled backup retention."""
        findings = []
        instances = self.aws.get_rds_instances()

        for instance in instances:
            retention = instance.get("BackupRetentionPeriod", 0)
            if retention >= 7:
                continue

            risk = RiskLevelEnum.HIGH if retention == 0 else RiskLevelEnum.MEDIUM
            findings.append(self._with_benchmark_metadata({
                "resource_id": instance["DBInstanceIdentifier"],
                "resource_type": "RDS_INSTANCE",
                "title": f"RDS Instance {instance['DBInstanceIdentifier']} has insufficient backup retention",
                "description": f"Backup retention is set to {retention} day(s). Increase retention to improve resilience and recovery posture.",
                "security_risk": risk,
                "affected_entities": [instance["DBInstanceIdentifier"]],
                "remediation_available": True,
                "check_type": "rds_backup_retention",
            }))

        logger.info(f"Found {len(findings)} RDS backup findings")
        return findings

    def scan_iam_overprivileged_policies(self) -> List[Dict[str, Any]]:
        """Flag obviously broad IAM policies by name for review."""
        findings = []
        policies = self.aws.get_iam_policies()

        risky_terms = ("admin", "administrator", "fullaccess", "poweruser")
        for policy in policies:
            name = policy.get("PolicyName", "").lower()
            if not any(term in name for term in risky_terms):
                continue

            findings.append(self._with_benchmark_metadata({
                "resource_id": policy["PolicyId"],
                "resource_type": "IAM_POLICY",
                "title": f"IAM Policy {policy['PolicyName']} appears highly privileged",
                "description": "Policy naming suggests broad administrative access. Review attached permissions and reduce to least privilege where possible.",
                "security_risk": RiskLevelEnum.HIGH,
                "affected_entities": [policy["Arn"]],
                "remediation_available": False,
                "check_type": "iam_overprivileged_policy",
            }))

        logger.info(f"Found {len(findings)} overprivileged IAM policy findings")
        return findings

    def scan_iam_wildcard_policies(self) -> List[Dict[str, Any]]:
        """
        Check for IAM policies with wildcards in actions and resources.
        
        Returns:
            List of findings for overly permissive IAM policies
        """
        findings = []
        policies = self.aws.get_iam_policies()
        
        for policy in policies:
            # Note: This would require fetching policy document and parsing statements
            # For MVP, we'll flag policies as potential risks if they're flagged
            findings.append(self._with_benchmark_metadata({
                "resource_id": policy["PolicyId"],
                "resource_type": "IAM_POLICY",
                "title": f"IAM Policy: {policy['PolicyName']} should be reviewed",
                "description": "IAM policy should be reviewed for overly permissive Actions and Resources. Use least privilege principle.",
                "security_risk": RiskLevelEnum.MEDIUM,
                "affected_entities": [policy["Arn"]],
                "remediation_available": False,
                "check_type": "iam_wildcard_policy",
            }))
        
        logger.info(f"Found {len(findings)} IAM policy findings")
        return findings

    def scan_all(self) -> List[Dict[str, Any]]:
        """Run all security scans."""
        all_findings = []
        
        all_findings.extend(self.scan_s3_public_access())
        all_findings.extend(self.scan_s3_without_encryption())
        all_findings.extend(self.scan_s3_without_versioning())
        all_findings.extend(self.scan_s3_without_logging())
        all_findings.extend(self.scan_open_security_groups())
        all_findings.extend(self.scan_public_security_groups())
        all_findings.extend(self.scan_public_ec2_instances())
        all_findings.extend(self.scan_ec2_imdsv1_usage())
        all_findings.extend(self.scan_ebs_unencrypted())
        all_findings.extend(self.scan_rds_public_access())
        all_findings.extend(self.scan_rds_unencrypted())
        all_findings.extend(self.scan_rds_backup_retention())
        all_findings.extend(self.scan_iam_overprivileged_policies())
        all_findings.extend(self.scan_iam_wildcard_policies())
        
        logger.info(f"Total security findings: {len(all_findings)}")
        return all_findings
