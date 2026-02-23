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

"""Inspector tools for MCP server."""

import boto3
import os
import time
from awslabs.inspector_mcp_server import MCP_SERVER_VERSION
from awslabs.inspector_mcp_server.common import (
    build_date_filter,
    build_string_filter,
    remove_null_values,
    validate_max_results,
)
from awslabs.inspector_mcp_server.models import (
    AccountStatus,
    CoverageResource,
    Finding,
    FindingAggregation,
    FindingDetail,
    ReportResult,
)
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List, Literal, Optional


class InspectorTools:
    """Inspector tools for MCP server."""

    def __init__(self):
        """Initialize the Inspector tools."""
        pass

    def _get_inspector_client(self, region: str):
        """Create an Inspector2 client for the specified region."""
        config = Config(user_agent_extra=f'awslabs/mcp/inspector-mcp-server/{MCP_SERVER_VERSION}')

        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                return boto3.Session(profile_name=aws_profile, region_name=region).client(
                    'inspector2', config=config
                )
            else:
                return boto3.Session(region_name=region).client('inspector2', config=config)
        except Exception as e:
            logger.error(f'Error creating Inspector client for region {region}: {str(e)}')
            raise

    def register(self, mcp):
        """Register all Inspector tools with the MCP server."""
        mcp.tool(name='list_findings')(self.list_findings)
        mcp.tool(name='get_finding_details')(self.get_finding_details)
        mcp.tool(name='list_finding_aggregations')(self.list_finding_aggregations)
        mcp.tool(name='list_coverage')(self.list_coverage)
        mcp.tool(name='list_coverage_statistics')(self.list_coverage_statistics)
        mcp.tool(name='get_account_status')(self.get_account_status)
        mcp.tool(name='create_findings_report')(self.create_findings_report)

    async def list_findings(
        self,
        ctx: Context,
        severity: Annotated[
            Optional[Literal['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL', 'UNTRIAGED']],
            Field(description='Filter findings by severity level'),
        ] = None,
        resource_type: Annotated[
            Optional[
                Literal[
                    'AWS_EC2_INSTANCE',
                    'AWS_ECR_CONTAINER_IMAGE',
                    'AWS_LAMBDA_FUNCTION',
                ]
            ],
            Field(description='Filter findings by resource type'),
        ] = None,
        finding_type: Annotated[
            Optional[
                Literal[
                    'NETWORK_REACHABILITY',
                    'PACKAGE_VULNERABILITY',
                    'CODE_VULNERABILITY',
                ]
            ],
            Field(description='Filter findings by finding type'),
        ] = None,
        title_filter: Annotated[
            Optional[str],
            Field(description='Filter findings by title substring match'),
        ] = None,
        start_time: Annotated[
            Optional[str],
            Field(
                description='Start time for findings filter in ISO format (e.g. 2024-01-01T00:00:00Z)'
            ),
        ] = None,
        end_time: Annotated[
            Optional[str],
            Field(
                description='End time for findings filter in ISO format (e.g. 2024-12-31T23:59:59Z)'
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='Maximum number of findings to return (1-100, default: 10)'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='Token for pagination to fetch the next page of findings'),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """List Amazon Inspector findings with optional filters.

        Retrieve and filter Inspector findings by severity, resource type, finding type,
        title, and time range. Findings include vulnerability details, affected resources,
        remediation guidance, and severity scores.

        Returns:
        --------
        Dictionary containing:
            - findings: List of findings with key fields (title, severity, resource, status, remediation)
            - next_token: Token for pagination if more results available
        """
        try:
            inspector_client = self._get_inspector_client(region)

            max_results = validate_max_results(max_results, default=10, max_allowed=100)

            # Build filter criteria
            filter_criteria: Dict[str, Any] = {}

            if severity:
                filter_criteria['severity'] = build_string_filter([severity])

            if resource_type:
                filter_criteria['resourceType'] = build_string_filter([resource_type])

            if finding_type:
                filter_criteria['findingType'] = build_string_filter([finding_type])

            if title_filter:
                filter_criteria['title'] = build_string_filter([title_filter], 'PREFIX')

            if start_time or end_time:
                filter_criteria['lastObservedAt'] = build_date_filter(start_time, end_time)

            # Build API parameters
            params: Dict[str, Any] = {
                'maxResults': max_results,
                'sortCriteria': {
                    'field': 'SEVERITY',
                    'sortOrder': 'DESC',
                },
            }

            if filter_criteria:
                params['filterCriteria'] = filter_criteria

            if next_token:
                params['nextToken'] = next_token

            logger.info(f'Listing Inspector findings in region {region}')

            response = inspector_client.list_findings(**remove_null_values(params))

            # Parse findings into models
            findings = []
            for finding_data in response.get('findings', []):
                finding = Finding.model_validate(finding_data)
                findings.append(finding.model_dump())

            result: Dict[str, Any] = {
                'findings': findings,
                'next_token': response.get('nextToken'),
            }

            logger.info(
                f'Successfully retrieved {len(findings)} Inspector findings from region {region}'
            )
            return result

        except Exception as e:
            logger.error(f'Error in list_findings: {str(e)}')
            await ctx.error(f'Error listing Inspector findings: {str(e)}')
            raise

    async def get_finding_details(
        self,
        ctx: Context,
        finding_arn: Annotated[
            str,
            Field(description='The ARN of the finding to retrieve details for'),
        ],
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Get full details for a specific Inspector finding by its ARN.

        Retrieves complete finding details including package vulnerability info,
        network reachability paths, CVSS scores, and remediation guidance.

        Returns:
        --------
        Dictionary containing:
            - finding: Complete finding detail with vulnerability info, CVSS scores, remediation
            - failed_findings: List of any findings that could not be retrieved
        """
        try:
            inspector_client = self._get_inspector_client(region)

            logger.info(f'Getting finding details for {finding_arn} in region {region}')

            response = inspector_client.batch_get_findings(findingArns=[finding_arn])

            result: Dict[str, Any] = {
                'finding': None,
                'failed_findings': response.get('failedFindings', []),
            }

            findings = response.get('findings', [])
            if findings:
                finding = FindingDetail.model_validate(findings[0])
                result['finding'] = finding.model_dump()

            logger.info(f'Successfully retrieved finding details for {finding_arn}')
            return result

        except Exception as e:
            logger.error(f'Error in get_finding_details: {str(e)}')
            await ctx.error(f'Error getting finding details: {str(e)}')
            raise

    async def list_finding_aggregations(
        self,
        ctx: Context,
        aggregation_type: Annotated[
            Literal[
                'SEVERITY',
                'ACCOUNT_ID',
                'RESOURCE_TYPE',
                'FINDING_TYPE',
                'AMI',
                'ECR_REPOSITORY',
                'LAMBDA_FUNCTION',
                'PACKAGE',
                'TITLE',
            ],
            Field(description='Dimension to aggregate findings by'),
        ],
        resource_type: Annotated[
            Optional[
                Literal[
                    'AWS_EC2_INSTANCE',
                    'AWS_ECR_CONTAINER_IMAGE',
                    'AWS_LAMBDA_FUNCTION',
                ]
            ],
            Field(description='Filter aggregation by resource type'),
        ] = None,
        severity: Annotated[
            Optional[Literal['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL', 'UNTRIAGED']],
            Field(description='Filter aggregation by severity level'),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='Maximum number of aggregation results (1-100, default: 10)'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='Token for pagination'),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Aggregate Inspector findings by a specified dimension.

        Provides summary counts of findings grouped by severity, account, resource type,
        finding type, AMI, ECR repository, Lambda function, package, or title.
        Useful for dashboard views and posture overview.

        Returns:
        --------
        Dictionary containing:
            - aggregation_type: The dimension used for aggregation
            - counts: List of aggregation counts
            - next_token: Token for pagination if more results available
        """
        try:
            inspector_client = self._get_inspector_client(region)

            max_results = validate_max_results(max_results, default=10, max_allowed=100)

            params: Dict[str, Any] = {
                'aggregationType': aggregation_type,
                'maxResults': max_results,
            }

            # Build account aggregation request based on type
            aggregation_request: Dict[str, Any] = {}
            type_key_map = {
                'SEVERITY': 'severityAggregation',
                'ACCOUNT_ID': 'accountAggregation',
                'RESOURCE_TYPE': 'resourceTypeAggregation',
                'FINDING_TYPE': 'findingTypeAggregation',
                'AMI': 'amiAggregation',
                'ECR_REPOSITORY': 'ecrRepositoryAggregation',
                'LAMBDA_FUNCTION': 'lambdaFunctionAggregation',
                'PACKAGE': 'packageAggregation',
                'TITLE': 'titleAggregation',
            }

            key = type_key_map.get(aggregation_type)
            if key:
                agg_config: Dict[str, Any] = {}
                if resource_type and key == 'findingTypeAggregation':
                    agg_config['resourceType'] = build_string_filter([resource_type])
                if severity and key == 'titleAggregation':
                    agg_config['severity'] = build_string_filter([severity])
                aggregation_request[key] = agg_config

            if aggregation_request:
                params['aggregationRequest'] = aggregation_request

            if next_token:
                params['nextToken'] = next_token

            logger.info(f'Listing finding aggregations by {aggregation_type} in region {region}')

            response = inspector_client.list_finding_aggregations(**remove_null_values(params))

            # Extract aggregation responses
            counts = response.get('responses', [])

            aggregation = FindingAggregation(
                aggregation_type=aggregation_type,
                counts=counts,
                next_token=response.get('nextToken'),
            )

            logger.info(
                f'Successfully retrieved {len(counts)} aggregation results from region {region}'
            )
            return aggregation.model_dump()

        except Exception as e:
            logger.error(f'Error in list_finding_aggregations: {str(e)}')
            await ctx.error(f'Error listing finding aggregations: {str(e)}')
            raise

    async def list_coverage(
        self,
        ctx: Context,
        resource_type: Annotated[
            Optional[
                Literal[
                    'AWS_EC2_INSTANCE',
                    'AWS_ECR_CONTAINER_IMAGE',
                    'AWS_ECR_REPOSITORY',
                    'AWS_LAMBDA_FUNCTION',
                ]
            ],
            Field(description='Filter coverage by resource type'),
        ] = None,
        scan_status: Annotated[
            Optional[Literal['ACTIVE', 'INACTIVE']],
            Field(description='Filter coverage by scan status'),
        ] = None,
        account_id: Annotated[
            Optional[str],
            Field(description='Filter coverage by AWS account ID'),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='Maximum number of coverage results (1-100, default: 10)'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='Token for pagination'),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """List resources being scanned by Inspector and their scan status.

        Shows which resources (EC2 instances, ECR images, Lambda functions) are being
        actively scanned and the status of their scans.

        Returns:
        --------
        Dictionary containing:
            - covered_resources: List of resources with their scan type and status
            - next_token: Token for pagination if more results available
        """
        try:
            inspector_client = self._get_inspector_client(region)

            max_results = validate_max_results(max_results, default=10, max_allowed=100)

            params: Dict[str, Any] = {
                'maxResults': max_results,
            }

            # Build filter criteria
            filter_criteria: Dict[str, Any] = {}

            if resource_type:
                filter_criteria['resourceType'] = build_string_filter([resource_type])

            if scan_status:
                filter_criteria['scanStatusCode'] = build_string_filter([scan_status])

            if account_id:
                filter_criteria['accountId'] = build_string_filter([account_id])

            if filter_criteria:
                params['filterCriteria'] = filter_criteria

            if next_token:
                params['nextToken'] = next_token

            logger.info(f'Listing Inspector coverage in region {region}')

            response = inspector_client.list_coverage(**remove_null_values(params))

            # Parse coverage resources
            covered_resources = []
            for resource_data in response.get('coveredResources', []):
                resource = CoverageResource.model_validate(resource_data)
                covered_resources.append(resource.model_dump())

            result: Dict[str, Any] = {
                'covered_resources': covered_resources,
                'next_token': response.get('nextToken'),
            }

            logger.info(
                f'Successfully retrieved {len(covered_resources)} coverage results '
                f'from region {region}'
            )
            return result

        except Exception as e:
            logger.error(f'Error in list_coverage: {str(e)}')
            await ctx.error(f'Error listing Inspector coverage: {str(e)}')
            raise

    async def list_coverage_statistics(
        self,
        ctx: Context,
        group_by: Annotated[
            Optional[
                Literal[
                    'ACCOUNT_ID',
                    'RESOURCE_TYPE',
                    'SCAN_STATUS_CODE',
                    'SCAN_STATUS_REASON',
                ]
            ],
            Field(description='Dimension to group coverage statistics by'),
        ] = None,
        resource_type: Annotated[
            Optional[
                Literal[
                    'AWS_EC2_INSTANCE',
                    'AWS_ECR_CONTAINER_IMAGE',
                    'AWS_ECR_REPOSITORY',
                    'AWS_LAMBDA_FUNCTION',
                ]
            ],
            Field(description='Filter statistics by resource type'),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Get summary statistics of Inspector scan coverage across resources.

        Provides counts of scanned resources grouped by account, resource type,
        scan status code, or scan status reason.

        Returns:
        --------
        Dictionary containing:
            - total_counts: Total count of covered resources
            - counts_by_group: Coverage counts grouped by the requested dimension
        """
        try:
            inspector_client = self._get_inspector_client(region)

            params: Dict[str, Any] = {}

            if group_by:
                params['groupBy'] = group_by

            # Build filter criteria
            filter_criteria: Dict[str, Any] = {}

            if resource_type:
                filter_criteria['resourceType'] = build_string_filter([resource_type])

            if filter_criteria:
                params['filterCriteria'] = filter_criteria

            logger.info(f'Listing coverage statistics in region {region}')

            response = inspector_client.list_coverage_statistics(**remove_null_values(params))

            result: Dict[str, Any] = {
                'total_counts': response.get('totalCounts'),
                'counts_by_group': response.get('countsByGroup', []),
            }

            logger.info(f'Successfully retrieved coverage statistics from region {region}')
            return result

        except Exception as e:
            logger.error(f'Error in list_coverage_statistics: {str(e)}')
            await ctx.error(f'Error listing coverage statistics: {str(e)}')
            raise

    async def get_account_status(
        self,
        ctx: Context,
        account_ids: Annotated[
            Optional[List[str]],
            Field(
                description='List of AWS account IDs to check. Defaults to the current account if not specified.'
            ),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Check Inspector scanning status for AWS accounts.

        Retrieves the Inspector scanning enablement status for one or more accounts,
        including which scan types (EC2, ECR, Lambda) are enabled.

        Returns:
        --------
        Dictionary containing:
            - accounts: List of account statuses with scan type enablement info
            - failed_accounts: List of accounts that could not be queried
        """
        try:
            inspector_client = self._get_inspector_client(region)

            params: Dict[str, Any] = {}

            if account_ids:
                params['accountIds'] = account_ids

            logger.info(f'Getting Inspector account status in region {region}')

            response = inspector_client.batch_get_account_status(**params)

            # Parse account statuses
            accounts = []
            for account_data in response.get('accounts', []):
                account = AccountStatus.model_validate(account_data)
                accounts.append(account.model_dump())

            result: Dict[str, Any] = {
                'accounts': accounts,
                'failed_accounts': response.get('failedAccounts', []),
            }

            logger.info(
                f'Successfully retrieved status for {len(accounts)} accounts from region {region}'
            )
            return result

        except Exception as e:
            logger.error(f'Error in get_account_status: {str(e)}')
            await ctx.error(f'Error getting account status: {str(e)}')
            raise

    async def create_findings_report(
        self,
        ctx: Context,
        s3_bucket_name: Annotated[
            str,
            Field(description='S3 bucket name for the report destination'),
        ],
        s3_key_prefix: Annotated[
            str,
            Field(description='S3 key prefix for the report files'),
        ],
        kms_key_arn: Annotated[
            str,
            Field(description='KMS key ARN for encrypting the report'),
        ],
        report_format: Annotated[
            Literal['CSV', 'JSON'],
            Field(description='Format of the report (CSV or JSON)'),
        ] = 'JSON',
        severity: Annotated[
            Optional[Literal['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL', 'UNTRIAGED']],
            Field(description='Filter report findings by severity'),
        ] = None,
        resource_type: Annotated[
            Optional[
                Literal[
                    'AWS_EC2_INSTANCE',
                    'AWS_ECR_CONTAINER_IMAGE',
                    'AWS_LAMBDA_FUNCTION',
                ]
            ],
            Field(description='Filter report findings by resource type'),
        ] = None,
        poll_for_completion: Annotated[
            bool,
            Field(
                description='Whether to poll for report completion. If False, returns immediately with report ID. Default: True'
            ),
        ] = True,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Generate a findings report exported to S3.

        Creates an Inspector findings report and exports it to the specified S3 bucket.
        Can optionally poll for completion.

        Returns:
        --------
        Dictionary containing:
            - report_id: Unique identifier for the report
            - status: Current status of the report generation
            - error_message: Error details if report generation failed
        """
        try:
            inspector_client = self._get_inspector_client(region)

            # Build filter criteria
            filter_criteria: Dict[str, Any] = {}

            if severity:
                filter_criteria['severity'] = build_string_filter([severity])

            if resource_type:
                filter_criteria['resourceType'] = build_string_filter([resource_type])

            # Build S3 destination
            s3_destination: Dict[str, str] = {
                'bucketName': s3_bucket_name,
                'keyPrefix': s3_key_prefix,
                'kmsKeyArn': kms_key_arn,
            }

            params: Dict[str, Any] = {
                'reportFormat': report_format,
                's3Destination': s3_destination,
            }

            if filter_criteria:
                params['filterCriteria'] = filter_criteria

            logger.info(f'Creating findings report in region {region}')

            response = inspector_client.create_findings_report(**params)
            report_id = response['reportId']

            logger.info(f'Created findings report with ID: {report_id}')

            if not poll_for_completion:
                report = ReportResult(
                    report_id=report_id,
                    status='IN_PROGRESS',
                    report_format=report_format,
                    s3_destination=s3_destination,
                )
                return report.model_dump()

            # Poll for completion
            max_wait_time = 300  # 5 minutes
            poll_interval = 5  # 5 seconds
            elapsed_time = 0
            status = 'IN_PROGRESS'
            error_message = None

            while elapsed_time < max_wait_time:
                status_response = inspector_client.get_findings_report_status(reportId=report_id)
                status = status_response.get('status', 'UNKNOWN')

                if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    error_message = status_response.get('errorMessage')
                    break

                time.sleep(poll_interval)
                elapsed_time += poll_interval

            report = ReportResult(
                report_id=report_id,
                status=status,
                error_message=error_message,
                filter_criteria=filter_criteria if filter_criteria else None,
                report_format=report_format,
                s3_destination=s3_destination,
            )

            logger.info(f'Report {report_id} status: {status}')
            return report.model_dump()

        except Exception as e:
            logger.error(f'Error in create_findings_report: {str(e)}')
            await ctx.error(f'Error creating findings report: {str(e)}')
            raise
