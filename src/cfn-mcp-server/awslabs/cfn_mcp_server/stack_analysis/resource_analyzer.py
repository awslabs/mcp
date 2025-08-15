# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from awslabs.cfn_mcp_server.errors import ServerError
from awslabs.cfn_mcp_server.stack_analysis.cloudformation_utils import CloudFormationUtils
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class ResourceMatchResult:
    """Represents the result of matching a physical resource ID to a scanned resource.

    Stores data from StackResourceInfo for both matched and unmatched resources.
    """

    matched: bool
    resource_type: str
    logical_resource_id: str
    physical_resource_id: str
    resource_status: str
    # Optional fields for matched resources from scan data
    resource_identifier: Optional[Dict[str, Any]] = None

    # Optional fields for scanned resources
    # These fields are used to store additional information from the scanned resources for further analysis
    # such as whether the resource is managed by a stack input or its scanned resource type
    managed_by_stack_input: Optional[bool] = None
    scanned_resource_type: Optional[str] = None


@dataclass
class StackResourceInfo:
    """Represents the information of a stack resource."""

    logical_resource_id: str
    physical_resource_id: str
    resource_type: str
    resource_status: str


class ResourceAnalyzer:
    """Matches physical resource IDs to scanned resources."""

    def __init__(self, region: Optional[str] = None):
        """Initializes the ResourceMatcher."""
        self.cfn_utils = CloudFormationUtils(region)
        self.stack_resources = {}  # physical_id -> StackResourceInfo
        self.scanned_resources_by_id = {}  # physical_id -> list of matching resources

    def match_stack_to_scan(
        self, stack_name: str, resource_scan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Match resources in a CloudFormation stack to scanned resources.

        Args:
            stack_name: Name of the CloudFormation stack to analyze
            resource_scan_id: Optional resource scan ID (will use existing or start new scan if not provided)

        Returns:
            Dictionary with matched and unmatched ResourceMatchResult objects
        """
        logger.info(f'Matching stack resources for: {stack_name}')

        try:
            # Set resource scan ID if provided
            if resource_scan_id:
                self.cfn_utils.resource_scan_id = resource_scan_id

            # Get stack resources from CloudFormation API (list-stack-resources)
            stack_resources_data = self.cfn_utils.list_stack_resources(stack_name)
            logger.info(f'Found {len(stack_resources_data)} resources in stack')

            # Ensure we have a resource scan ID - use latest existing scan
            if not self.cfn_utils.resource_scan_id:
                logger.info('No resource scan ID provided, looking for latest scan...')
                try:
                    scans = self.cfn_utils.list_resource_scans()
                    if scans and len(scans) > 0:
                        # Assuming scans are returned in chronological order, get latest
                        latest_scan = scans[0]
                        self.cfn_utils.resource_scan_id = latest_scan.get('ResourceScanId')
                        logger.info(
                            f'Using latest resource scan with ID: {self.cfn_utils.resource_scan_id}'
                        )
                except ServerError as e:
                    logger.error(f'Failed to get latest resource scan: {str(e)}')
                    return {
                        'stack_name': stack_name,
                        'resource_scan_id': None,
                        'matched_resources': [],
                        'unmatched_resources': [],
                        'error': f'Unable to get latest resource scan: {str(e)}',
                    }

            # Get scanned resources from Resource Scan API (list-resource-scan-resources)
            try:
                scanned_resources_data = self.cfn_utils.list_resource_scan_resources()
                logger.info(f'Found {len(scanned_resources_data)} resources in scan')
            except ServerError as e:
                logger.error(f'Error listing scanned resources: {str(e)}')
                # Return basic analysis without scan data
                return {
                    'stack_name': stack_name,
                    'resource_scan_id': self.cfn_utils.resource_scan_id,
                    'matched_resources': [],
                    'unmatched_resources': [],
                    'error': f'Unable to list scanned resources: {str(e)}',
                }

            # Process resources
            self._process_stack_resources(stack_resources_data)
            self._process_scanned_resources(scanned_resources_data)

            # Get resources using the new combined method
            resources = self._get_resources()

            # Return matching results
            return {
                'stack_name': stack_name,
                'resource_scan_id': self.cfn_utils.resource_scan_id,
                'matched_resources': resources['matched_resources'],
                'unmatched_resources': resources['unmatched_resources'],
            }

        except ServerError as e:
            logger.error(f'Error in match_stack_to_scan: {str(e)}')
            return {
                'stack_name': stack_name,
                'resource_scan_id': self.cfn_utils.resource_scan_id,
                'matched_resources': [],
                'unmatched_resources': [],
                'error': str(e),
            }

    def get_related_resources(
        self, resources: List[Dict[str, Any]], resource_scan_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get related resources for the specified resources from a resource scan.

        Args:
            resources: List of resource identifiers to find related resources for
            resource_scan_id: Optional resource scan ID (will use existing if not provided)

        Returns:
            List of related resources found in the scan
        """
        logger.info(f'Getting related resources for {len(resources)} resources')

        if not resources:
            logger.info('No resources provided, returning empty list')
            return []

        try:
            # Set resource scan ID if provided
            if resource_scan_id:
                self.cfn_utils.resource_scan_id = resource_scan_id

            # Ensure we have a resource scan ID
            if not self.cfn_utils.resource_scan_id:
                logger.warning('No resource scan ID available for related resources lookup')
                return []

            # Handle pagination here without changing cloudformation_utils
            all_related_resources = []
            next_token = None

            while True:
                response = self.cfn_utils.list_resource_scan_related_resources(
                    resources=resources, scan_id=resource_scan_id, next_token=next_token
                )

                related_resources = response.get('RelatedResources', [])
                all_related_resources.extend(related_resources)

                next_token = response.get('NextToken')
                if not next_token:
                    break

            logger.info(f'Found {len(all_related_resources)} related resources')
            return all_related_resources

        except ServerError as e:
            logger.error(f'Error getting related resources: {str(e)}')
            return []

    def _get_resources(self) -> Dict[str, List[ResourceMatchResult]]:
        """Get both matched and unmatched resources as lists of ResourceMatchResult objects.

        Returns:
            Dictionary containing matched and unmatched resources
        """
        matched = []
        unmatched = []

        # Process all stack resources in a single loop
        for physical_id, stack_resource in self.stack_resources.items():
            if physical_id in self.scanned_resources_by_id:
                # Resource is matched - create a matched ResourceMatchResult
                scanned_resource = self.scanned_resources_by_id[physical_id]

                result = ResourceMatchResult(
                    matched=True,
                    resource_type=stack_resource.resource_type,
                    logical_resource_id=stack_resource.logical_resource_id,
                    physical_resource_id=stack_resource.physical_resource_id,
                    resource_status=stack_resource.resource_status,
                    resource_identifier=scanned_resource[0].resource_identifier,
                    managed_by_stack_input=scanned_resource[0].managed_by_stack_input,
                    scanned_resource_type=scanned_resource[0].scanned_resource_type,
                )
                matched.append(result)
            else:
                # Resource is unmatched - create an unmatched ResourceMatchResult
                result = ResourceMatchResult(
                    matched=False,
                    resource_type=stack_resource.resource_type,
                    logical_resource_id=stack_resource.logical_resource_id,
                    physical_resource_id=stack_resource.physical_resource_id,
                    resource_status=stack_resource.resource_status,
                    resource_identifier=None,
                    managed_by_stack_input=True,
                    scanned_resource_type=None,
                )
                unmatched.append(result)

        return {'matched_resources': matched, 'unmatched_resources': unmatched}

    def _process_stack_resources(self, stack_resources_data: List[Dict[str, Any]]):
        """Process stack resources and store them in a dictionary."""
        self.stack_resources.clear()  # Clear previous data

        for resource in stack_resources_data:
            physical_id = resource['PhysicalResourceId']
            if not physical_id:
                logger.warning(
                    f'Resource {resource["LogicalResourceId"]} has no PhysicalResourceId, skipping'
                )
                continue

            # Store stack resource information
            self.stack_resources[physical_id] = StackResourceInfo(
                logical_resource_id=resource['LogicalResourceId'],
                physical_resource_id=physical_id,
                resource_type=resource['ResourceType'],
                resource_status=resource['ResourceStatus'],
            )

    def _process_scanned_resources(self, scanned_resources_data: List[Dict[str, Any]]):
        """Process scanned resources and store them preserving all entries."""
        self.scanned_resources_by_id.clear()

        for resource in scanned_resources_data:
            resource_identifier = resource.get('ResourceIdentifier', {})
            resource_type = resource.get('ResourceType', '')

            # Extract physical ID from resource identifier
            physical_id = self._extract_physical_id(resource_identifier, resource_type)
            logger.debug(
                f'Extracted physical ID: {physical_id} for resource type: {resource_type}'
            )

            if physical_id:
                # Create ResourceMatchResult object
                match_result = ResourceMatchResult(
                    matched=True,
                    resource_type=resource_type,
                    logical_resource_id=resource.get('LogicalResourceId', ''),
                    physical_resource_id=physical_id,
                    resource_status=resource.get('ResourceStatus', ''),
                    resource_identifier=resource_identifier,
                    scanned_resource_type=resource_type,
                )
                # Group resources by physical ID using ResourceMatchResult objects
                if physical_id not in self.scanned_resources_by_id:
                    self.scanned_resources_by_id[physical_id] = []
                self.scanned_resources_by_id[physical_id].append(match_result)
                logger.debug(f'Processed scanned resource: {physical_id} ({resource_type})')

    # Extract physical ID from resource identifier based on field types
    # This method will just extract the physical ID from the resource identifier
    # based on common fields that are typically used to identify resources, logic can be improved later
    def _extract_physical_id(
        self, resource_identifier: Dict[str, Any], resource_type: str
    ) -> Optional[str]:
        """Extract physical ID from resource identifier based on resource type."""
        if not resource_identifier:
            return None

        # Try common ID fields
        common_id_fields = [
            'Id',
            'Arn',
            'Name',
            'FunctionName',
            'BucketName',
            'QueueUrl',
            'RoleName',
            'PolicyArn',
            'KeyId',
            'ClusterName',
            'DBInstanceIdentifier',
            'InstanceId',
            'VpcId',
            'SubnetId',
            'GroupId',
            'ApplicationName',
        ]

        for field in common_id_fields:
            if field in resource_identifier:
                return resource_identifier[field]

        # If no specific field found, try the first non-empty string value
        for value in resource_identifier.values():
            if isinstance(value, str) and value.strip():
                return value

        return None
