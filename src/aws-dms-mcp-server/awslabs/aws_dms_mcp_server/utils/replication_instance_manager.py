"""
Replication Instance Manager.

Handles business logic for AWS DMS replication instance operations.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .dms_client import DMSClient
from .response_formatter import ResponseFormatter
from ..exceptions import DMSInvalidParameterException, DMSResourceNotFoundException


class ReplicationInstanceManager:
    """Manager for replication instance operations."""
    
    def __init__(self, client: DMSClient):
        """
        Initialize replication instance manager.
        
        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug("Initialized ReplicationInstanceManager")
    
    def list_instances(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List replication instances with optional filtering.
        
        Args:
            filters: Optional filters for instance selection
            max_results: Maximum results per page
            marker: Pagination token
        
        Returns:
            Dictionary with instances list and pagination info
        """
        logger.info("Listing replication instances", filters=filters)
        
        # Build API parameters
        params = {
            "MaxRecords": max_results
        }
        
        if filters:
            params["Filters"] = filters
        
        if marker:
            params["Marker"] = marker
        
        # Call API
        response = self.client.call_api("describe_replication_instances", **params)
        
        # Format instances
        instances = response.get("ReplicationInstances", [])
        formatted_instances = [
            ResponseFormatter.format_instance(instance)
            for instance in instances
        ]
        
        result = {
            "success": True,
            "data": {
                "instances": formatted_instances,
                "count": len(formatted_instances)
            },
            "error": None
        }
        
        # Add pagination info
        if response.get("Marker"):
            result["data"]["next_marker"] = response["Marker"]
        
        logger.info(f"Retrieved {len(formatted_instances)} replication instances")
        return result
    
    def create_instance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new replication instance.
        
        Args:
            params: Instance creation parameters
        
        Returns:
            Created instance details
        """
        logger.info("Creating replication instance", identifier=params.get("replication_instance_identifier"))
        
        # Validate required parameters
        required_params = ["ReplicationInstanceIdentifier", "ReplicationInstanceClass"]
        for param in required_params:
            if param not in params:
                raise DMSInvalidParameterException(
                    message=f"Missing required parameter: {param}",
                    details={"missing_param": param}
                )
        
        # Validate instance class
        instance_class = params.get("ReplicationInstanceClass")
        if not self.validate_instance_class(instance_class):
            raise DMSInvalidParameterException(
                message=f"Invalid instance class: {instance_class}",
                details={"invalid_class": instance_class}
            )
        
        # Call API
        response = self.client.call_api("create_replication_instance", **params)
        
        # Format response
        instance = response.get("ReplicationInstance", {})
        formatted_instance = ResponseFormatter.format_instance(instance)
        
        result = {
            "success": True,
            "data": {
                "instance": formatted_instance,
                "message": "Replication instance creation initiated"
            },
            "error": None
        }
        
        logger.info(f"Created replication instance: {formatted_instance.get('identifier')}")
        return result
    
    def get_instance_details(self, instance_arn: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific instance.
        
        Args:
            instance_arn: Instance ARN
        
        Returns:
            Instance details
        """
        logger.info("Getting instance details", arn=instance_arn)
        
        # Filter by ARN
        filters = [{
            "Name": "replication-instance-arn",
            "Values": [instance_arn]
        }]
        
        # Call API
        response = self.client.call_api(
            "describe_replication_instances",
            Filters=filters
        )
        
        instances = response.get("ReplicationInstances", [])
        
        if not instances:
            raise DMSResourceNotFoundException(
                message=f"Replication instance not found: {instance_arn}",
                details={"arn": instance_arn}
            )
        
        # Format and return first (should be only) instance
        formatted_instance = ResponseFormatter.format_instance(instances[0])
        
        return {
            "success": True,
            "data": formatted_instance,
            "error": None
        }
    
    def validate_instance_class(self, instance_class: str) -> bool:
        """
        Validate instance class is supported.
        
        Args:
            instance_class: Instance class to validate
        
        Returns:
            True if valid
        """
        # Common DMS instance classes
        valid_classes = [
            "dms.t2.micro", "dms.t2.small", "dms.t2.medium", "dms.t2.large",
            "dms.t3.micro", "dms.t3.small", "dms.t3.medium", "dms.t3.large",
            "dms.c4.large", "dms.c4.xlarge", "dms.c4.2xlarge", "dms.c4.4xlarge",
            "dms.c5.large", "dms.c5.xlarge", "dms.c5.2xlarge", "dms.c5.4xlarge",
            "dms.r4.large", "dms.r4.xlarge", "dms.r4.2xlarge", "dms.r4.4xlarge",
            "dms.r5.large", "dms.r5.xlarge", "dms.r5.2xlarge", "dms.r5.4xlarge"
        ]
        
        return instance_class in valid_classes


# TODO: Add instance status monitoring
# TODO: Add instance modification support
# TODO: Add instance deletion support