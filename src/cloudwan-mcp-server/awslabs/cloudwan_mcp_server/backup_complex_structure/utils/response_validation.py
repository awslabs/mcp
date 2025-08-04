"""
Response validation utilities for MCP tools.

This module provides comprehensive validation for AWS API responses and MCP tool outputs
to ensure that tools return meaningful data or clear error messages.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ResponseValidationError(Exception):
    """Exception raised when response validation fails."""

    pass


class APIResponseStatus(BaseModel):
    """Status of an AWS API response."""

    success: bool
    service: str
    operation: str
    region: str
    timestamp: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    response_size: int = 0  # Number of items returned
    response_metadata: Dict[str, Any] = {}


class ValidationResult(BaseModel):
    """Result of response validation."""

    is_valid: bool
    has_data: bool
    error_message: Optional[str] = None
    warning_messages: List[str] = []
    api_statuses: List[APIResponseStatus] = []
    total_items_found: int = 0
    regions_searched: List[str] = []
    successful_regions: List[str] = []
    failed_regions: List[str] = []


class ResponseValidator:
    """Comprehensive response validator for MCP tools."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate_aws_api_response(
        self,
        response: Dict[str, Any],
        service: str,
        operation: str,
        region: str,
        expected_keys: Optional[List[str]] = None,
    ) -> APIResponseStatus:
        """
        Validate a single AWS API response.

        Args:
            response: AWS API response dictionary
            service: AWS service name
            operation: API operation name
            region: AWS region
            expected_keys: List of expected response keys

        Returns:
            APIResponseStatus with validation results
        """
        timestamp = datetime.utcnow().isoformat()

        if not response:
            return APIResponseStatus(
                success=False,
                service=service,
                operation=operation,
                region=region,
                timestamp=timestamp,
                error_message="Empty response from AWS API",
            )

        # Check for AWS error response structure
        if "Error" in response:
            error_info = response["Error"]
            return APIResponseStatus(
                success=False,
                service=service,
                operation=operation,
                region=region,
                timestamp=timestamp,
                error_code=error_info.get("Code", "Unknown"),
                error_message=error_info.get("Message", "Unknown AWS error"),
            )

        # Validate expected keys if provided
        if expected_keys:
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                return APIResponseStatus(
                    success=False,
                    service=service,
                    operation=operation,
                    region=region,
                    timestamp=timestamp,
                    error_message=f"Missing expected keys in response: {missing_keys}",
                )

        # Count response items
        response_size = self._count_response_items(response, service, operation)

        return APIResponseStatus(
            success=True,
            service=service,
            operation=operation,
            region=region,
            timestamp=timestamp,
            response_size=response_size,
            response_metadata=response.get("ResponseMetadata", {}),
        )

    def _count_response_items(self, response: Dict[str, Any], service: str, operation: str) -> int:
        """Count the number of items in an AWS API response."""

        # Define common patterns for different services
        count_patterns = {
            "ec2": {
                "describe_vpcs": "Vpcs",
                "describe_subnets": "Subnets",
                "describe_instances": "Reservations",
                "describe_network_interfaces": "NetworkInterfaces",
                "describe_route_tables": "RouteTables",
                "describe_security_groups": "SecurityGroups",
                "describe_internet_gateways": "InternetGateways",
                "describe_nat_gateways": "NatGateways",
                "describe_vpc_endpoints": "VpcEndpoints",
            },
            "networkmanager": {
                # 'get_global_networks': 'GlobalNetworks',  # Removed - invalid method
                "list_core_networks": "CoreNetworks",
                "list_attachments": "Attachments",
                "describe_global_networks": "GlobalNetworks",
            },
            "elbv2": {
                "describe_load_balancers": "LoadBalancers",
                "describe_target_groups": "TargetGroups",
            },
            "rds": {
                "describe_db_instances": "DBInstances",
                "describe_db_clusters": "DBClusters",
            },
            "ecs": {
                "list_clusters": "clusterArns",
                "list_services": "serviceArns",
                "list_tasks": "taskArns",
            },
        }

        # Get the expected response key for this service/operation
        service_patterns = count_patterns.get(service, {})
        response_key = service_patterns.get(operation.lower())

        if response_key and response_key in response:
            items = response[response_key]
            if isinstance(items, list):
                return len(items)
            elif isinstance(items, dict):
                return 1

        # Fallback: count all list-type values
        total_items = 0
        for value in response.values():
            if isinstance(value, list):
                total_items += len(value)
            elif isinstance(value, dict) and value:
                total_items += 1

        return total_items

    def validate_multi_region_response(
        self,
        region_results: Dict[str, Any],
        service: str,
        operation: str,
        expected_regions: List[str],
    ) -> ValidationResult:
        """
        Validate multi-region operation results.

        Args:
            region_results: Dictionary mapping region to result
            service: AWS service name
            operation: API operation name
            expected_regions: List of regions that should have been queried

        Returns:
            ValidationResult with comprehensive validation information
        """
        api_statuses = []
        successful_regions = []
        failed_regions = []
        total_items = 0
        warning_messages = []

        # Validate each region's response
        for region in expected_regions:
            if region not in region_results:
                api_statuses.append(
                    APIResponseStatus(
                        success=False,
                        service=service,
                        operation=operation,
                        region=region,
                        timestamp=datetime.utcnow().isoformat(),
                        error_message=f"No result for region {region}",
                    )
                )
                failed_regions.append(region)
                continue

            result = region_results[region]

            # Check if result is an error
            if isinstance(result, dict) and "error" in result:
                api_statuses.append(
                    APIResponseStatus(
                        success=False,
                        service=service,
                        operation=operation,
                        region=region,
                        timestamp=datetime.utcnow().isoformat(),
                        error_code=result.get("error_code", "Unknown"),
                        error_message=result.get("error", "Unknown error"),
                    )
                )
                failed_regions.append(region)
                continue

            # Validate successful response
            if isinstance(result, dict):
                status = self.validate_aws_api_response(result, service, operation, region)
                api_statuses.append(status)

                if status.success:
                    successful_regions.append(region)
                    total_items += status.response_size
                else:
                    failed_regions.append(region)
            else:
                # Result is not a dictionary, might be empty list or None
                if result:
                    successful_regions.append(region)
                    total_items += len(result) if isinstance(result, list) else 1
                else:
                    api_statuses.append(
                        APIResponseStatus(
                            success=True,
                            service=service,
                            operation=operation,
                            region=region,
                            timestamp=datetime.utcnow().isoformat(),
                            response_size=0,
                        )
                    )
                    successful_regions.append(region)
                    warning_messages.append(f"Region {region} returned empty result")

        # Determine overall validation result
        has_data = total_items > 0
        is_valid = len(successful_regions) > 0  # At least one region succeeded

        error_message = None
        if not is_valid:
            error_message = f"All regions failed for {service}.{operation}"
        elif len(failed_regions) == len(expected_regions):
            error_message = f"No successful responses for {service}.{operation}"

        return ValidationResult(
            is_valid=is_valid,
            has_data=has_data,
            error_message=error_message,
            warning_messages=warning_messages,
            api_statuses=api_statuses,
            total_items_found=total_items,
            regions_searched=expected_regions,
            successful_regions=successful_regions,
            failed_regions=failed_regions,
        )

    def validate_discovery_response(
        self, response_data: Any, expected_data_keys: List[str], tool_name: str
    ) -> ValidationResult:
        """
        Validate a discovery tool response.

        Args:
            response_data: The response data from discovery tool
            expected_data_keys: Keys expected to contain data arrays
            tool_name: Name of the discovery tool

        Returns:
            ValidationResult with validation information
        """
        timestamp = datetime.utcnow().isoformat()

        if not response_data:
            return ValidationResult(
                is_valid=False,
                has_data=False,
                error_message=f"{tool_name} returned empty response",
            )

        if isinstance(response_data, str):
            try:
                import json

                response_data = json.loads(response_data)
            except (json.JSONDecodeError, ValueError) as e:
                return ValidationResult(
                    is_valid=False,
                    has_data=False,
                    error_message=f"{tool_name} returned invalid JSON: {str(e)}",
                )

        if not isinstance(response_data, dict):
            return ValidationResult(
                is_valid=False,
                has_data=False,
                error_message=f"{tool_name} response is not a dictionary",
            )

        # Check for error fields
        if "error" in response_data:
            return ValidationResult(
                is_valid=False,
                has_data=False,
                error_message=f"{tool_name} returned error: {response_data['error']}",
            )

        # Count items in expected data keys
        total_items = 0
        warning_messages = []

        for key in expected_data_keys:
            if key in response_data:
                data = response_data[key]
                if isinstance(data, list):
                    total_items += len(data)
                    if len(data) == 0:
                        warning_messages.append(f"No items found in {key}")
                elif data:
                    total_items += 1

        has_data = total_items > 0

        return ValidationResult(
            is_valid=True,
            has_data=has_data,
            warning_messages=warning_messages,
            total_items_found=total_items,
        )

    def create_enhanced_error_response(
        self,
        validation_result: ValidationResult,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create an enhanced error response with detailed validation information.

        Args:
            validation_result: Result from validation
            tool_name: Name of the tool
            context: Additional context information

        Returns:
            Enhanced error response dictionary
        """
        timestamp = datetime.utcnow().isoformat()

        response = {
            "tool_name": tool_name,
            "timestamp": timestamp,
            "success": validation_result.is_valid,
            "has_data": validation_result.has_data,
            "validation_summary": {
                "total_items_found": validation_result.total_items_found,
                "regions_searched": validation_result.regions_searched,
                "successful_regions": validation_result.successful_regions,
                "failed_regions": validation_result.failed_regions,
                "warnings": validation_result.warning_messages,
            },
        }

        if validation_result.error_message:
            response["error"] = validation_result.error_message

        if validation_result.api_statuses:
            response["api_call_details"] = [
                {
                    "service": status.service,
                    "operation": status.operation,
                    "region": status.region,
                    "success": status.success,
                    "items_returned": status.response_size,
                    "error_code": status.error_code,
                    "error_message": status.error_message,
                }
                for status in validation_result.api_statuses
            ]

        if context:
            response["context"] = context

        return response

    def handle_client_error(
        self, error: ClientError, service: str, operation: str, region: str
    ) -> APIResponseStatus:
        """
        Handle and classify AWS ClientError exceptions.

        Args:
            error: AWS ClientError exception
            service: AWS service name
            operation: API operation name
            region: AWS region

        Returns:
            APIResponseStatus with error information
        """
        error_response = error.response.get("Error", {})
        error_code = error_response.get("Code", "Unknown")
        error_message = error_response.get("Message", str(error))

        # Classify common error types
        classification = self._classify_aws_error(error_code)

        return APIResponseStatus(
            success=False,
            service=service,
            operation=operation,
            region=region,
            timestamp=datetime.utcnow().isoformat(),
            error_code=error_code,
            error_message=f"[{classification}] {error_message}",
        )

    def _classify_aws_error(self, error_code: str) -> str:
        """Classify AWS error codes into categories."""

        access_errors = {
            "AccessDenied",
            "UnauthorizedOperation",
            "Forbidden",
            "InvalidUserID.NotFound",
            "InvalidAccessKeyId",
        }

        resource_errors = {
            "InvalidInstanceID.NotFound",
            "InvalidVpcID.NotFound",
            "InvalidSubnetID.NotFound",
            "ResourceNotFound",
        }

        quota_errors = {"RequestLimitExceeded", "Throttling", "TooManyRequests"}

        if error_code in access_errors:
            return "ACCESS_DENIED"
        elif error_code in resource_errors:
            return "RESOURCE_NOT_FOUND"
        elif error_code in quota_errors:
            return "RATE_LIMITED"
        else:
            return "API_ERROR"


# Global response validator instance
response_validator = ResponseValidator()
