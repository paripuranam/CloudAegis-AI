"""Cost optimization analysis module - FinOps checks."""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CostAnalyzer:
    """Analyzes cloud resources for cost optimization opportunities."""

    def __init__(self, aws_connector):
        """Initialize cost analyzer with AWS connector."""
        self.aws = aws_connector

    def analyze_idle_ec2_instances(self) -> List[Dict[str, Any]]:
        """
        Identify EC2 instances with low CPU usage (idle).
        
        Returns:
            List of findings for idle EC2 instances
        """
        findings = []
        instances = self.aws.get_ec2_instances()
        
        for instance in instances:
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]
            
            if instance["State"] != "running":
                continue

            cpu_usage = self.aws.get_average_cpu_utilization(instance_id, days=14)
            if cpu_usage is None:
                logger.info(f"Skipping idle EC2 analysis for {instance_id}: no CloudWatch CPU data")
                continue
            
            if cpu_usage < 5:
                # Estimate cost (simplified pricing)
                cost_map = {
                    "t2.micro": 0.0116,
                    "t2.small": 0.023,
                    "t2.medium": 0.0464,
                    "t3.micro": 0.0104,
                    "t3.small": 0.0208,
                    "t3.medium": 0.0416,
                    "m5.large": 0.096,
                    "m5.xlarge": 0.192,
                }
                
                hourly_cost = cost_map.get(instance_type, 0.05)
                monthly_cost = hourly_cost * 730
                
                findings.append({
                    "resource_id": instance_id,
                    "resource_type": "EC2_INSTANCE",
                    "title": f"EC2 Instance {instance_id} has low CPU utilization",
                    "description": f"Instance {instance_id} ({instance_type}) has average CPU usage of {cpu_usage:.1f}% over last 14 days. Consider stopping or downsizing.",
                    "current_monthly_cost": monthly_cost,
                    "potential_monthly_savings": monthly_cost * 0.5,  # 50% savings by downsizing
                    "savings_percentage": 50,
                    "check_type": "idle_ec2",
                })
        
        logger.info(f"Found {len(findings)} idle EC2 findings")
        return findings

    def analyze_unattached_ebs_volumes(self) -> List[Dict[str, Any]]:
        """
        Identify unattached EBS volumes that incur charges.
        
        Returns:
            List of findings for unattached EBS volumes
        """
        findings = []
        volumes = self.aws.get_ebs_volumes()
        
        for volume in volumes:
            if not volume["Attachments"]:  # No attachments = unattached
                volume_size = volume["Size"]
                volume_type = volume["VolumeType"]
                
                # Pricing: gp3 is $0.10 per GB-month, gp2 is $0.10 per GB-month, io1 is $0.125
                price_map = {
                    "gp3": 0.10,
                    "gp2": 0.10,
                    "io1": 0.125,
                    "io2": 0.125,
                }
                
                monthly_cost = volume_size * price_map.get(volume_type, 0.10)
                
                findings.append({
                    "resource_id": volume["VolumeId"],
                    "resource_type": "EBS_VOLUME",
                    "title": f"EBS Volume {volume['VolumeId']} is unattached",
                    "description": f"EBS volume {volume['VolumeId']} ({volume_size}GB {volume_type}) is not attached to any instance and incurs charges.",
                    "current_monthly_cost": monthly_cost,
                    "potential_monthly_savings": monthly_cost,
                    "savings_percentage": 100,
                    "check_type": "unattached_ebs",
                })
        
        logger.info(f"Found {len(findings)} unattached EBS findings")
        return findings

    def analyze_over_provisioned_ec2(self) -> List[Dict[str, Any]]:
        """
        Identify EC2 instances that might be over-provisioned.
        
        Returns:
            List of findings for over-provisioned instances
        """
        findings = []
        instances = self.aws.get_ec2_instances()
        
        for instance in instances:
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]

            if instance["State"] != "running":
                continue

            cpu_usage = self.aws.get_average_cpu_utilization(instance_id, days=14)
            if cpu_usage is None:
                logger.info(f"Skipping right-sizing analysis for {instance_id}: no CloudWatch CPU data")
                continue

            sizeable_instance = any(
                instance_type.startswith(prefix)
                for prefix in ("m", "c", "r", "t3.large", "t3.xlarge", "t3.2xlarge")
            )

            if sizeable_instance and cpu_usage < 20:
                # Estimate potential downgrade savings
                current_cost_map = {
                    "t3.large": 0.0832,
                    "t3.xlarge": 0.1664,
                    "m5.large": 0.096,
                    "m5.xlarge": 0.192,
                    "c5.large": 0.085,
                    "c5.xlarge": 0.17,
                }
                
                current_hourly = current_cost_map.get(instance_type, 0.05)
                current_monthly = current_hourly * 730
                
                # Suggest one size down - estimate 40% savings
                potential_savings = current_monthly * 0.40
                
                findings.append({
                    "resource_id": instance_id,
                    "resource_type": "EC2_INSTANCE",
                    "title": f"EC2 Instance {instance_id} may be over-provisioned",
                    "description": f"Instance {instance_type} shows average CPU usage of {cpu_usage:.1f}% over the last 14 days. Consider downgrading to a smaller instance type.",
                    "current_monthly_cost": current_monthly,
                    "potential_monthly_savings": potential_savings,
                    "savings_percentage": 40,
                    "check_type": "over_provisioned_ec2",
                })
        
        logger.info(f"Found {len(findings)} over-provisioned EC2 findings")
        return findings

    def analyze_s3_lifecycle_policies(self) -> List[Dict[str, Any]]:
        """
        Identify S3 buckets without lifecycle policies.
        
        Returns:
            List of findings for S3 buckets needing lifecycle policies
        """
        findings = []
        buckets = self.aws.get_s3_buckets()
        
        for bucket in buckets:
            # In production, fetch actual lifecycle policies
            # For MVP, flag all buckets as needing review
            findings.append({
                "resource_id": bucket["BucketName"],
                "resource_type": "S3_BUCKET",
                "title": f"S3 Bucket {bucket['BucketName']} lacks lifecycle policy",
                "description": f"Bucket {bucket['BucketName']} should have a lifecycle policy to transition old objects to cheaper storage classes.",
                "current_monthly_cost": 100,  # Mock cost
                "potential_monthly_savings": 25,  # Mock savings
                "savings_percentage": 25,
                "check_type": "s3_lifecycle",
            })
        
        logger.info(f"Found {len(findings)} S3 lifecycle findings")
        return findings

    def analyze_large_ebs_volumes(self) -> List[Dict[str, Any]]:
        """
        Highlight large EBS volumes for rightsizing review.
        """
        findings = []
        volumes = self.aws.get_ebs_volumes()

        for volume in volumes:
            if volume["Size"] < 500:
                continue

            monthly_cost = volume["Size"] * 0.10
            findings.append({
                "resource_id": volume["VolumeId"],
                "resource_type": "EBS_VOLUME",
                "title": f"EBS Volume {volume['VolumeId']} is large and should be rightsized",
                "description": f"Volume size is {volume['Size']} GB. Review actual filesystem usage and snapshot strategy to reduce wasted storage.",
                "current_monthly_cost": monthly_cost,
                "potential_monthly_savings": monthly_cost * 0.20,
                "savings_percentage": 20,
                "check_type": "oversized_ebs",
            })

        logger.info(f"Found {len(findings)} oversized EBS findings")
        return findings

    def analyze_stopped_ec2_instances(self) -> List[Dict[str, Any]]:
        """
        Flag stopped instances that still incur storage cost and operational clutter.
        """
        findings = []
        instances = self.aws.get_ec2_instances()

        for instance in instances:
            if instance["State"] != "stopped":
                continue

            instance_type = instance["InstanceType"]
            reference_cost_map = {
                "t2.micro": 8.47,
                "t3.micro": 7.59,
                "t3.small": 15.18,
                "t3.medium": 30.37,
                "t3.large": 60.74,
                "m5.large": 70.08,
            }

            current_monthly_cost = reference_cost_map.get(instance_type, 25.00) * 0.15

            findings.append({
                "resource_id": instance["InstanceId"],
                "resource_type": "EC2_INSTANCE",
                "title": f"Stopped EC2 Instance {instance['InstanceId']} should be reviewed",
                "description": f"Stopped instance {instance['InstanceId']} still retains attached storage and configuration overhead. Confirm whether it should be restarted, archived, or deleted.",
                "current_monthly_cost": current_monthly_cost,
                "potential_monthly_savings": current_monthly_cost,
                "savings_percentage": 100,
                "check_type": "stopped_ec2",
            })

        logger.info(f"Found {len(findings)} stopped EC2 findings")
        return findings

    def analyze_unattached_elastic_ips(self) -> List[Dict[str, Any]]:
        """
        Flag Elastic IPs that are allocated but not attached.
        """
        findings = []
        addresses = self.aws.get_elastic_ips()

        for address in addresses:
            if address.get("AssociationId") or address.get("InstanceId") or address.get("NetworkInterfaceId"):
                continue

            findings.append({
                "resource_id": address.get("AllocationId") or address.get("PublicIp"),
                "resource_type": "ELASTIC_IP",
                "title": f"Elastic IP {address.get('PublicIp')} is unattached",
                "description": "Allocated Elastic IP is not attached to an instance or network interface and now incurs hourly cost.",
                "current_monthly_cost": 3.60,
                "potential_monthly_savings": 3.60,
                "savings_percentage": 100,
                "check_type": "unattached_eip",
            })

        logger.info(f"Found {len(findings)} unattached Elastic IP findings")
        return findings

    def analyze_idle_rds_instances(self) -> List[Dict[str, Any]]:
        """
        Flag RDS instances with very low CPU utilization.
        """
        findings = []
        instances = self.aws.get_rds_instances()

        hourly_cost_map = {
            "db.t3.micro": 0.017,
            "db.t3.small": 0.034,
            "db.t3.medium": 0.068,
            "db.t3.large": 0.136,
            "db.m5.large": 0.192,
            "db.m5.xlarge": 0.384,
        }

        for instance in instances:
            identifier = instance["DBInstanceIdentifier"]
            avg_cpu = self.aws.get_average_rds_cpu_utilization(identifier, days=14)
            if avg_cpu is None or avg_cpu >= 5:
                continue

            hourly_cost = hourly_cost_map.get(instance["DBInstanceClass"], 0.20)
            monthly_cost = hourly_cost * 730
            findings.append({
                "resource_id": identifier,
                "resource_type": "RDS_INSTANCE",
                "title": f"RDS Instance {identifier} has low CPU utilization",
                "description": f"Database average CPU usage is {avg_cpu:.1f}% over the last 14 days. Consider rightsizing or consolidating this instance.",
                "current_monthly_cost": monthly_cost,
                "potential_monthly_savings": monthly_cost * 0.30,
                "savings_percentage": 30,
                "check_type": "idle_rds",
            })

        logger.info(f"Found {len(findings)} idle RDS findings")
        return findings

    def analyze_all(self) -> List[Dict[str, Any]]:
        """Run all cost analysis checks."""
        all_findings = []
        
        all_findings.extend(self.analyze_idle_ec2_instances())
        all_findings.extend(self.analyze_unattached_ebs_volumes())
        all_findings.extend(self.analyze_large_ebs_volumes())
        all_findings.extend(self.analyze_over_provisioned_ec2())
        all_findings.extend(self.analyze_stopped_ec2_instances())
        all_findings.extend(self.analyze_unattached_elastic_ips())
        all_findings.extend(self.analyze_idle_rds_instances())
        all_findings.extend(self.analyze_s3_lifecycle_policies())
        
        logger.info(f"Total cost findings: {len(all_findings)}")
        return all_findings
