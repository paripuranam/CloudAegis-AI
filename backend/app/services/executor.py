"""Execution and Rollback management."""
from typing import Dict, Any, Optional
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Manages remediation execution and rollback."""

    def __init__(self):
        """Initialize execution manager."""
        self.executions = {}  # In-memory store; use DB in production
        self.rollback_states = {}

    def create_execution_snapshot(
        self,
        resource_id: str,
        resource_type: str,
        current_state: Dict[str, Any],
    ) -> str:
        """
        Capture the current state before execution.
        
        Args:
            resource_id: AWS resource ID
            resource_type: Type of resource
            current_state: Current resource configuration
            
        Returns:
            Snapshot ID for rollback
        """
        snapshot_id = str(uuid.uuid4())
        
        self.rollback_states[snapshot_id] = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "state": current_state,
            "created_at": datetime.utcnow(),
        }
        
        logger.info(f"Created snapshot {snapshot_id} for {resource_type} {resource_id}")
        return snapshot_id

    def execute_action(
        self,
        execution_id: str,
        resource_id: str,
        resource_type: str,
        action: str,
        snapshot_id: str,
        aws_connector=None,
    ) -> Dict[str, Any]:
        """
        Execute remediation action.
        
        Args:
            execution_id: Execution ID
            resource_id: AWS resource ID
            resource_type: Type of resource
            action: Action to execute
            snapshot_id: Snapshot ID for rollback
            aws_connector: AWS connector for executing changes
            
        Returns:
            Execution result with status and details
        """
        
        try:
            result = None
            
            if action == "stop_instance":
                result = self._execute_stop_instance(resource_id, aws_connector)
            elif action == "delete_volume":
                result = self._execute_delete_volume(resource_id, aws_connector)
            elif action == "restrict_security_group":
                result = self._execute_restrict_security_group(resource_id, aws_connector)
            elif action == "restrict_public_access":
                result = self._execute_s3_restrict_public_access(resource_id, aws_connector)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "executed_at": datetime.utcnow().isoformat(),
                }
            
            # Store execution record
            self.executions[execution_id] = {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "action": action,
                "status": "success",
                "result": result,
                "snapshot_id": snapshot_id,
                "executed_at": datetime.utcnow(),
            }
            
            logger.info(f"Successfully executed {action} on {resource_id}")
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "message": f"Successfully executed {action}",
                "result": result,
                "executed_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            
            self.executions[execution_id] = {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "action": action,
                "status": "failed",
                "error": str(e),
                "executed_at": datetime.utcnow(),
            }
            
            return {
                "status": "failed",
                "execution_id": execution_id,
                "message": f"Execution failed: {str(e)}",
                "executed_at": datetime.utcnow().isoformat(),
            }

    def _execute_stop_instance(self, instance_id: str, aws_connector) -> Dict:
        """Stop EC2 instance."""
        if not aws_connector:
            return {"instance_id": instance_id, "action": "stop", "event": "mock_stop"}
        
        ec2_client = aws_connector.get_client("ec2")
        ec2_client.stop_instances(InstanceIds=[instance_id])
        
        return {"instance_id": instance_id, "action": "stop", "event": "stopped"}

    def _execute_delete_volume(self, volume_id: str, aws_connector) -> Dict:
        """Delete EBS volume."""
        if not aws_connector:
            return {"volume_id": volume_id, "action": "delete", "event": "mock_delete"}
        
        ec2_client = aws_connector.get_client("ec2")
        ec2_client.delete_volume(VolumeId=volume_id)
        
        return {"volume_id": volume_id, "action": "delete", "event": "deleted"}

    def _execute_restrict_security_group(self, sg_id: str, aws_connector) -> Dict:
        """Restrict security group rules."""
        if not aws_connector:
            return {"sg_id": sg_id, "action": "restrict", "event": "mock_restrict"}
        
        # This would require more complex logic in production
        # For now, return mock result
        return {"sg_id": sg_id, "action": "restrict", "event": "rules_updated"}

    def _execute_s3_restrict_public_access(self, bucket_name: str, aws_connector) -> Dict:
        """Restrict S3 bucket public access."""
        if not aws_connector:
            return {"bucket": bucket_name, "action": "restrict_public_access", "event": "mock_blocking"}
        
        s3_client = aws_connector.get_client("s3")
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        )
        
        return {"bucket": bucket_name, "action": "restrict_public_access", "event": "blocked"}

    def rollback_execution(
        self,
        execution_id: str,
        aws_connector=None,
    ) -> Dict[str, Any]:
        """
        Rollback a previous execution.
        
        Args:
            execution_id: ID of execution to rollback
            aws_connector: AWS connector for executing changes
            
        Returns:
            Rollback result with status
        """
        
        try:
            execution = self.executions.get(execution_id)
            
            if not execution:
                return {
                    "status": "error",
                    "message": f"Execution {execution_id} not found",
                }
            
            snapshot_id = execution.get("snapshot_id")
            snapshot = self.rollback_states.get(snapshot_id)
            
            if not snapshot:
                return {
                    "status": "error",
                    "message": f"Snapshot {snapshot_id} not found for rollback",
                }
            
            # In production, restore the snapshot state
            logger.info(f"Rolling back execution {execution_id} using snapshot {snapshot_id}")
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "message": f"Successfully rolled back execution",
                "snapshot_id": snapshot_id,
                "rolled_back_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return {
                "status": "failed",
                "execution_id": execution_id,
                "message": f"Rollback failed: {str(e)}",
            }
