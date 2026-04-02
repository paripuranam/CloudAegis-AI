"""AWS connection and resource management using STS role assumption."""
import boto3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AWSConnector:
    """Handles AWS account connection via IAM role assumption."""

    def __init__(
        self,
        role_arn: Optional[str] = None,
        external_id: Optional[str] = None,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        """
        Initialize AWS connector.
        
        Args:
            role_arn: ARN of the IAM role to assume
            external_id: Optional external ID for cross-account access
            region: AWS region
            access_key_id: Optional AWS access key ID
            secret_access_key: Optional AWS secret access key
        """
        self.role_arn = role_arn
        self.external_id = external_id
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self._session = None
        self._use_mock_data = settings.aws_use_mock_data
        self.sts_client = boto3.client("sts", region_name=region)

    def assume_role(self) -> Dict:
        """Assume the specified IAM role and return temporary credentials."""
        try:
            if self._use_mock_data:
                logger.info(f"Mock mode: returning mock credentials for {self.role_arn}")
                return {
                    "AccessKeyId": "ASIAFAKE123456789ABC",
                    "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG+bPxRfiCYzSAKeyMock",
                    "SessionToken": "AQoDYXdzEJr..mock",
                    "Expiration": "2026-04-01T12:00:00Z"
                }
            
            assume_role_params = {
                "RoleArn": self.role_arn,
                "RoleSessionName": "CloudAegis-Session",
                "DurationSeconds": 3600,
            }
            
            if self.external_id:
                assume_role_params["ExternalId"] = self.external_id

            response = self.sts_client.assume_role(**assume_role_params)
            
            credentials = response["Credentials"]
            self._session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=self.region,
            )
            
            logger.info(f"Successfully assumed role: {self.role_arn}")
            return credentials
        except Exception as e:
            logger.error(f"Failed to assume role {self.role_arn}: {str(e)}")
            raise

    def authenticate_with_keys(self) -> boto3.Session:
        """Create a boto3 session using long-lived AWS credentials."""
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError("AWS access_key_id and secret_access_key are required")

        self._session = boto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )
        logger.info("Successfully authenticated with AWS access keys")
        return self._session

    def get_session(self) -> boto3.Session:
        """Get or create boto3 session with assumed credentials."""
        if self._session is None:
            if self._use_mock_data:
                # Create mock session only when mock mode is explicitly enabled.
                self._session = boto3.Session(
                    aws_access_key_id="ASIAFAKE123456789ABC",
                    aws_secret_access_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYzSAKeyMock",
                    region_name=self.region,
                )
                logger.info(f"Mock mode: created mock session for {self.region}")
            elif self.access_key_id and self.secret_access_key:
                self.authenticate_with_keys()
            else:
                self.assume_role()
        return self._session

    def get_account_id(self) -> str:
        """Return the AWS account ID for the active credentials."""
        if self._use_mock_data:
            if self.role_arn and ":" in self.role_arn:
                arn_parts = self.role_arn.split(":")
                if len(arn_parts) >= 5 and arn_parts[4]:
                    return arn_parts[4]
            return "123456789012"

        session = self.get_session()
        sts_client = session.client("sts", region_name=self.region)
        identity = sts_client.get_caller_identity()
        return identity["Account"]

    def get_client(self, service: str):
        """Get AWS service client."""
        session = self.get_session()
        return session.client(service, region_name=self.region)

    def get_ec2_instances(self) -> List[Dict]:
        """Get all EC2 instances in the region."""
        if self._use_mock_data:
            logger.info("Mock mode: returning mock EC2 instances")
            return [
                {
                    "InstanceId": "i-0123456789abcdef0",
                    "InstanceType": "t2.micro",
                    "State": "stopped",
                    "LaunchTime": "2026-03-01T10:30:00",
                    "Tags": {"Name": "unused-instance", "Environment": "dev"},
                    "SecurityGroups": [{"GroupId": "sg-12345", "GroupName": "default"}],
                    "PublicIpAddress": None,
                    "PrivateIpAddress": "10.0.1.100",
                },
                {
                    "InstanceId": "i-0987654321fedcba0",
                    "InstanceType": "t3.large",
                    "State": "running",
                    "LaunchTime": "2026-01-15T08:00:00",
                    "Tags": {"Name": "prod-app-server", "Environment": "prod"},
                    "SecurityGroups": [{"GroupId": "sg-54321", "GroupName": "web"}],
                    "PublicIpAddress": "203.0.113.45",
                    "PrivateIpAddress": "10.0.2.50",
                }
            ]
        
        ec2_client = self.get_client("ec2")
        instances = []
        
        try:
            paginator = ec2_client.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        instances.append({
                            "InstanceId": instance["InstanceId"],
                            "InstanceType": instance["InstanceType"],
                            "State": instance["State"]["Name"],
                            "LaunchTime": instance["LaunchTime"].isoformat(),
                            "Tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
                            "SecurityGroups": instance.get("SecurityGroups", []),
                            "PublicIpAddress": instance.get("PublicIpAddress"),
                            "PrivateIpAddress": instance.get("PrivateIpAddress"),
                            "MetadataOptions": instance.get("MetadataOptions", {}),
                            "EbsOptimized": instance.get("EbsOptimized", False),
                        })
            logger.info(f"Found {len(instances)} EC2 instances")
        except Exception as e:
            logger.error(f"Error fetching EC2 instances: {str(e)}")

        return instances

    def get_s3_buckets(self) -> List[Dict]:
        """Get all S3 buckets."""
        if self._use_mock_data:
            logger.info("Mock mode: returning mock S3 buckets")
            return [
                {
                    "BucketName": "cloudaegis-logs-dev",
                    "CreationDate": "2025-12-01T05:00:00",
                    "PublicAccessBlock": {
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": False,
                        "RestrictPublicBuckets": False,
                    }
                },
                {
                    "BucketName": "old-backups-2024",
                    "CreationDate": "2024-01-15T08:30:00",
                    "PublicAccessBlock": {
                        "BlockPublicAcls": False,
                        "IgnorePublicAcls": False,
                        "BlockPublicPolicy": False,
                        "RestrictPublicBuckets": False,
                    }
                }
            ]
        
        s3_client = self.get_client("s3")
        buckets = []
        
        try:
            response = s3_client.list_buckets()
            for bucket in response.get("Buckets", []):
                bucket_name = bucket["Name"]
                
                # Get public access block
                try:
                    public_access_block = s3_client.get_public_access_block(Bucket=bucket_name)
                    pab = public_access_block["PublicAccessBlockConfiguration"]
                except:
                    pab = None

                buckets.append({
                    "BucketName": bucket_name,
                    "CreationDate": bucket["CreationDate"].isoformat(),
                    "PublicAccessBlock": pab,
                    "EncryptionEnabled": self.is_bucket_encrypted(bucket_name),
                    "VersioningStatus": self.get_bucket_versioning_status(bucket_name),
                    "LoggingEnabled": self.is_bucket_logging_enabled(bucket_name),
                })
            logger.info(f"Found {len(buckets)} S3 buckets")
        except Exception as e:
            logger.error(f"Error fetching S3 buckets: {str(e)}")

        return buckets

    def get_security_groups(self) -> List[Dict]:
        """Get all security groups."""
        if self._use_mock_data:
            logger.info("Mock mode: returning mock security groups")
            return [
                {
                    "GroupId": "sg-12345678",
                    "GroupName": "allow-all",
                    "VpcId": "vpc-12345",
                    "IngressRules": [
                        {
                            "IpProtocol": "-1",
                            "FromPort": 0,
                            "ToPort": 65535,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Allow all traffic"}]
                        }
                    ],
                    "EgressRules": []
                },
                {
                    "GroupId": "sg-87654321",
                    "GroupName": "web",
                    "VpcId": "vpc-12345",
                    "IngressRules": [
                        {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": []},
                    ],
                    "EgressRules": []
                }
            ]
        
        ec2_client = self.get_client("ec2")
        security_groups = []
        
        try:
            paginator = ec2_client.get_paginator("describe_security_groups")
            for page in paginator.paginate():
                for sg in page.get("SecurityGroups", []):
                    security_groups.append({
                        "GroupId": sg["GroupId"],
                        "GroupName": sg["GroupName"],
                        "VpcId": sg.get("VpcId"),
                        "IngressRules": sg.get("IpPermissions", []),
                        "EgressRules": sg.get("IpPermissionsEgress", []),
                    })
            logger.info(f"Found {len(security_groups)} security groups")
        except Exception as e:
            logger.error(f"Error fetching security groups: {str(e)}")

        return security_groups

    def get_iam_policies(self) -> List[Dict]:
        """Get all customer-managed IAM policies."""
        if self._use_mock_data:
            logger.info("Mock mode: returning mock IAM policies")
            return [
                {
                    "PolicyName": "AdminAccess",
                    "PolicyId": "ANPAI23HZ27SI2FAKEPOL",
                    "Arn": "arn:aws:iam::544885083112:policy/AdminAccess",
                    "CreateDate": "2025-06-01T10:00:00",
                    "UpdateDate": "2026-02-15T14:30:00",
                },
                {
                    "PolicyName": "S3FullAccess",
                    "PolicyId": "ANPAI56HZ78SI3FAKEPOL",
                    "Arn": "arn:aws:iam::544885083112:policy/S3FullAccess",
                    "CreateDate": "2025-07-10T08:00:00",
                    "UpdateDate": "2026-01-20T11:00:00",
                }
            ]
        
        iam_client = self.get_client("iam")
        policies = []
        
        try:
            paginator = iam_client.get_paginator("list_policies")
            for page in paginator.paginate(Scope="Local"):
                for policy in page.get("Policies", []):
                    policies.append({
                        "PolicyName": policy["PolicyName"],
                        "PolicyId": policy["PolicyId"],
                        "Arn": policy["Arn"],
                        "CreateDate": policy["CreateDate"].isoformat(),
                        "UpdateDate": policy["UpdateDate"].isoformat(),
                    })
            logger.info(f"Found {len(policies)} customer-managed IAM policies")
        except Exception as e:
            logger.error(f"Error fetching IAM policies: {str(e)}")

        return policies

    def get_ebs_volumes(self) -> List[Dict]:
        """Get all EBS volumes."""
        ec2_client = self.get_client("ec2")
        volumes = []
        
        try:
            paginator = ec2_client.get_paginator("describe_volumes")
            for page in paginator.paginate():
                for volume in page.get("Volumes", []):
                    volumes.append({
                        "VolumeId": volume["VolumeId"],
                        "Size": volume["Size"],
                        "VolumeType": volume["VolumeType"],
                        "State": volume["State"],
                        "Attachments": volume.get("Attachments", []),
                        "CreateTime": volume["CreateTime"].isoformat(),
                        "Encrypted": volume.get("Encrypted", False),
                        "Iops": volume.get("Iops"),
                    })
            logger.info(f"Found {len(volumes)} EBS volumes")
        except Exception as e:
            logger.error(f"Error fetching EBS volumes: {str(e)}")

        return volumes

    def get_rds_instances(self) -> List[Dict]:
        """Get all RDS instances in the region."""
        rds_client = self.get_client("rds")
        instances = []

        try:
            paginator = rds_client.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for instance in page.get("DBInstances", []):
                    instances.append({
                        "DBInstanceIdentifier": instance["DBInstanceIdentifier"],
                        "DBInstanceClass": instance["DBInstanceClass"],
                        "Engine": instance["Engine"],
                        "EngineVersion": instance["EngineVersion"],
                        "AllocatedStorage": instance.get("AllocatedStorage", 0),
                        "StorageEncrypted": instance.get("StorageEncrypted", False),
                        "PubliclyAccessible": instance.get("PubliclyAccessible", False),
                        "BackupRetentionPeriod": instance.get("BackupRetentionPeriod", 0),
                        "MultiAZ": instance.get("MultiAZ", False),
                        "DBInstanceStatus": instance.get("DBInstanceStatus"),
                    })
            logger.info(f"Found {len(instances)} RDS instances")
        except Exception as e:
            logger.error(f"Error fetching RDS instances: {str(e)}")

        return instances

    def get_elastic_ips(self) -> List[Dict]:
        """Get allocated Elastic IP addresses."""
        ec2_client = self.get_client("ec2")
        addresses = []

        try:
            response = ec2_client.describe_addresses()
            for address in response.get("Addresses", []):
                addresses.append({
                    "AllocationId": address.get("AllocationId"),
                    "AssociationId": address.get("AssociationId"),
                    "PublicIp": address.get("PublicIp"),
                    "InstanceId": address.get("InstanceId"),
                    "NetworkInterfaceId": address.get("NetworkInterfaceId"),
                })
            logger.info(f"Found {len(addresses)} Elastic IP addresses")
        except Exception as e:
            logger.error(f"Error fetching Elastic IP addresses: {str(e)}")

        return addresses

    def is_bucket_encrypted(self, bucket_name: str) -> bool:
        """Return whether default encryption is enabled for a bucket."""
        s3_client = self.get_client("s3")
        try:
            response = s3_client.get_bucket_encryption(Bucket=bucket_name)
            rules = response.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            return len(rules) > 0
        except Exception:
            return False

    def get_bucket_versioning_status(self, bucket_name: str) -> str:
        """Return bucket versioning status."""
        s3_client = self.get_client("s3")
        try:
            response = s3_client.get_bucket_versioning(Bucket=bucket_name)
            return response.get("Status", "Disabled")
        except Exception:
            return "Disabled"

    def is_bucket_logging_enabled(self, bucket_name: str) -> bool:
        """Return whether server access logging is enabled for the bucket."""
        s3_client = self.get_client("s3")
        try:
            response = s3_client.get_bucket_logging(Bucket=bucket_name)
            return bool(response.get("LoggingEnabled"))
        except Exception:
            return False

    def get_cloudwatch_metrics(
        self,
        instance_id: str,
        metric_name: str,
        period: int = 3600,
        days: int = 14,
    ) -> Dict:
        """Get CloudWatch metrics for an instance."""
        cloudwatch_client = self.get_client("cloudwatch")
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            response = cloudwatch_client.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=["Average"],
            )
            datapoints = sorted(response.get("Datapoints", []), key=lambda point: point["Timestamp"])
            return {"Datapoints": datapoints}
        except Exception as e:
            logger.error(f"Error fetching CloudWatch metrics: {str(e)}")
            return {}

    def get_average_cpu_utilization(self, instance_id: str, days: int = 14) -> Optional[float]:
        """Return average CPU utilization over the requested lookback window."""
        metrics = self.get_cloudwatch_metrics(instance_id, "CPUUtilization", days=days)
        datapoints = metrics.get("Datapoints", [])
        if not datapoints:
            return None

        return sum(point.get("Average", 0) for point in datapoints) / len(datapoints)

    def get_average_rds_cpu_utilization(self, db_instance_identifier: str, days: int = 14) -> Optional[float]:
        """Return average CPU utilization for an RDS instance."""
        cloudwatch_client = self.get_client("cloudwatch")

        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            response = cloudwatch_client.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_instance_identifier}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Average"],
            )
            datapoints = response.get("Datapoints", [])
            if not datapoints:
                return None
            return sum(point.get("Average", 0) for point in datapoints) / len(datapoints)
        except Exception as e:
            logger.error(f"Error fetching RDS CPU metrics for {db_instance_identifier}: {str(e)}")
            return None
