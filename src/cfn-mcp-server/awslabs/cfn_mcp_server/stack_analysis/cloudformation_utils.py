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
from awslabs.cfn_mcp_server.aws_client import get_aws_client
from awslabs.cfn_mcp_server.errors import ClientError, ServerError, handle_aws_api_error
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class CloudFormationUtils:
    """Utility class for CloudFormation API operations."""

    def __init__(self, region: Optional[str] = None, resource_scan_id: Optional[str] = None):
        """Initialize the CloudFormationUtils with the specified AWS region and store the resource scan ID."""
        self.region = region
        self._cfn_client = None
        self.resource_scan_id = resource_scan_id

    @property
    def cfn_client(self):
        """Lazy-loaded CloudFormation client."""
        if self._cfn_client is None:
            try:
                self._cfn_client = get_aws_client('cloudformation', self.region)
            except Exception as e:
                error = handle_aws_api_error(e)
                raise error
        return self._cfn_client

    # Cloudformation API's Access point: Helper methods
    def list_stacks(self) -> List[Dict[str, Any]]:
        """List CloudFormation stacks in the AWS account.

        Returns:
            List of active stacks (excludes deleted stacks)
        """
        response = self.cfn_client.list_stacks(
            StackStatusFilter=[
                'CREATE_COMPLETE',
                'UPDATE_COMPLETE',
                'UPDATE_ROLLBACK_COMPLETE',
                'CREATE_IN_PROGRESS',
                'UPDATE_IN_PROGRESS',
                'UPDATE_ROLLBACK_IN_PROGRESS',
                'ROLLBACK_COMPLETE',
                'CREATE_FAILED',
                'UPDATE_FAILED',
                'UPDATE_ROLLBACK_FAILED',
                'ROLLBACK_FAILED',
            ]
        )
        return response.get('StackSummaries', [])

    def describe_stack(self, stack_name: str) -> Dict[str, Any]:
        """Describe a CloudFormation stack.

        Args:
            stack_name: Name of the stack to describe

        Returns:
            Stack description

        Raises:
            ClientError: If the stack doesn't exist or other API errors occur
        """
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            stacks = response.get('Stacks', [])
            if not stacks:
                raise ClientError(f'Stack "{stack_name}" not found')
            return stacks[0]
        except Exception as e:
            # Check if it's a stack not found error
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            if error_code == 'ValidationError' or 'does not exist' in str(e):
                raise ClientError(f'Stack "{stack_name}" not found')
            else:
                raise handle_aws_api_error(e)

    def list_stack_resources(self, stack_name: str) -> List[Dict[str, Any]]:
        """List resources in a CloudFormation stack.

        Args:
            stack_name: Name of the stack
        Returns:
            List of stack resources
        """
        response = self.cfn_client.list_stack_resources(StackName=stack_name)
        return response.get('StackResourceSummaries', [])

    def get_stack_template(self, stack_name: str) -> Dict[str, Any]:
        """Get the template for a CloudFormation stack.

        Args:
            stack_name: Name of the stack

        Returns:
            Dict containing the stack template
        """
        response = self.cfn_client.get_template(StackName=stack_name)
        return response.get('TemplateBody', {})

    # Resource Scan API methods
    def start_resource_scan(self, resource_types: Optional[List] = None) -> str:
        """Start a new resource scan and return the scan ID.

        Returns:
            Resource scan ID
        """
        try:
            logger.info('Starting resource scan...')
            logger.info(f'Received resource_type: {resource_types} (type: {type(resource_types)})')

            if resource_types and len(resource_types) > 0:
                logger.info(f'Starting resource scan with filters: {resource_types}')
                response = self.cfn_client.start_resource_scan(
                    ScanFilters=[{'Types': resource_types}]
                )
            else:
                response = self.cfn_client.start_resource_scan()

            scan_id = response['ResourceScanId']
            if not scan_id:
                raise ServerError('Resource scan ID not returned by AWS API')

            self.resource_scan_id = scan_id
            logger.info(f'Resource scan started with ID: {self.resource_scan_id}')
            return scan_id
        except Exception as e:
            logger.error(f'Error starting resource scan: {str(e)}')
            raise handle_aws_api_error(e)

    def list_resource_scans(self) -> List[Dict[str, Any]]:
        """List all resource scans in chronological order (newest first).

        Returns:
            List of resource scans with their details
        """
        try:
            logger.info('Listing resource scans...')

            # Use paginator to handle large result sets
            paginator = self.cfn_client.get_paginator('list_resource_scans')
            page_iterator = paginator.paginate()

            all_scans = []
            for page in page_iterator:
                # The correct key is 'ResourceScanSummaries', not 'ResourceScans'
                scans = page.get('ResourceScanSummaries', [])
                all_scans.extend(scans)
                logger.debug(f'Retrieved {len(scans)} scans from page')

            logger.info(f'Total resource scans found: {len(all_scans)}')
            return all_scans

        except Exception as e:
            logger.error(f'Error listing resource scans: {str(e)}')
            raise handle_aws_api_error(e)

    def get_resource_scan_status(self, scan_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the status of a resource scan.

        Args:
            scan_id: Resource scan ID (uses stored ID if not provided)

        Returns:
            Resource scan status information
        """
        effective_scan_id: Optional[str] = scan_id or self.resource_scan_id
        if not effective_scan_id:
            raise ClientError('No resource scan ID available')

        try:
            response = self.cfn_client.describe_resource_scan(ResourceScanId=effective_scan_id)
            return response
        except Exception as e:
            logger.error(f'Error getting resource scan status: {str(e)}')
            raise handle_aws_api_error(e)

    def list_resource_scan_resources(self, scan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all resources found in the resource scan.

        Args:
            scan_id: Resource scan ID (uses stored ID if not provided)

        Returns:
            List of all resources found in the scan
        """
        effective_scan_id: Optional[str] = scan_id or self.resource_scan_id
        if not effective_scan_id:
            raise ClientError('No resource scan ID available')

        try:
            logger.info(f'Listing resources from scan {effective_scan_id}')

            # Use paginator to handle large result sets
            paginator = self.cfn_client.get_paginator('list_resource_scan_resources')
            page_iterator = paginator.paginate(ResourceScanId=effective_scan_id)

            all_resources = []
            for page in page_iterator:
                resources = page.get('Resources', [])
                all_resources.extend(resources)
                logger.debug(f'Retrieved {len(resources)} resources from page')

            logger.info(f'Total resources found in scan: {len(all_resources)}')
            return all_resources

        except Exception as e:
            logger.error(f'Error listing resource scan resources: {str(e)}')
            raise handle_aws_api_error(e)

    def list_resource_scan_resources_with_filters(
        self,
        scan_id: Optional[str] = None,
        resource_identifier: Optional[str] = None,
        resource_type_prefix: Optional[str] = None,
        tag_key: Optional[str] = None,
        tag_value: Optional[str] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List resources from resource scan with advanced filtering options.

        Args:
            scan_id: Resource scan ID (uses stored ID if not provided)
            resource_identifier: Filter by resource identifier
            resource_type_prefix: Filter by resource type prefix (e.g., "AWS::S3::")
            tag_key: Filter by tag key
            tag_value: Filter by tag value (requires tag_key)
            max_results: Maximum number of results to return (1-100)
            next_token: Token for pagination

        Returns:
            Dict containing resources and pagination information
        """
        effective_scan_id: Optional[str] = scan_id or self.resource_scan_id
        if not effective_scan_id:
            raise ClientError('No resource scan ID available')

        try:
            # Build the API call parameters
            params: Dict[str, Any] = {'ResourceScanId': effective_scan_id}

            if resource_identifier:
                params['ResourceIdentifier'] = resource_identifier
            if resource_type_prefix:
                params['ResourceTypePrefix'] = resource_type_prefix
            if tag_key:
                params['TagKey'] = tag_key
            if tag_value:
                params['TagValue'] = tag_value
            if max_results:
                if max_results < 1 or max_results > 100:
                    raise ClientError('max_results must be between 1 and 100')
                params['MaxResults'] = max_results
            if next_token:
                params['NextToken'] = next_token

            logger.info(f'Listing resources from scan {effective_scan_id} with filters: {params}')

            response = self.cfn_client.list_resource_scan_resources(**params)

            return {
                'resources': response.get('Resources', []),
                'next_token': response.get('NextToken'),
                'scan_id': effective_scan_id,
                'filters_applied': {
                    key: value for key, value in params.items() if key != 'ResourceScanId'
                },
            }

        except Exception as e:
            logger.error(f'Error listing resource scan resources with filters: {str(e)}')
            raise handle_aws_api_error(e)

    def list_resource_scan_related_resources(
        self, resources: List[Dict[str, Any]], scan_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List related resources for the specified resources from a resource scan.

        Args:
            resources: List of resource identifiers to find related resources for.
                      Each resource should have 'ResourceType' and 'ResourceIdentifier' keys.
            scan_id: Resource scan ID (uses stored ID if not provided)

        Returns:
            List of related resources found in the scan
        """
        effective_scan_id: Optional[str] = scan_id or self.resource_scan_id
        if not effective_scan_id:
            raise ClientError('No resource scan ID available')

        if not resources:
            logger.warning('No resources provided for related resource lookup')
            return []

        try:
            logger.info(
                f'Finding related resources for {len(resources)} resources in scan {effective_scan_id}'
            )

            # Use paginator to handle large result sets
            paginator = self.cfn_client.get_paginator('list_resource_scan_related_resources')
            page_iterator = paginator.paginate(
                ResourceScanId=effective_scan_id, Resources=resources
            )

            all_related_resources = []
            for page in page_iterator:
                related_resources = page.get('RelatedResources', [])
                all_related_resources.extend(related_resources)
                logger.debug(f'Retrieved {len(related_resources)} related resources from page')

            logger.info(f'Total related resources found: {len(all_related_resources)}')
            return all_related_resources

        except Exception as e:
            logger.error(f'Error listing resource scan related resources: {str(e)}')
            raise handle_aws_api_error(e)
