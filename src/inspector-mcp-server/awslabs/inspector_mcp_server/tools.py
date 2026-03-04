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
import httpx
import os
import re
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
    AffectedVersion,
    CoverageResource,
    CveDetails,
    CveReference,
    CvssMetrics,
    DigestFinding,
    Finding,
    FindingAggregation,
    FindingDetail,
    FindingExplanation,
    FindingsDigest,
    ReportResult,
    SecuritySummary,
)
from botocore.config import Config
from datetime import datetime, timezone
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
        mcp.tool(name='get_cve_details')(self.get_cve_details)
        mcp.tool(name='explain_finding')(self.explain_finding)
        mcp.tool(name='generate_security_summary')(self.generate_security_summary)
        mcp.tool(name='generate_findings_digest')(self.generate_findings_digest)

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

    async def _fetch_cve_from_nvd(self, cve_id: str) -> Optional[CveDetails]:
        """Fetch CVE details from the NVD API.

        Args:
            cve_id: The CVE identifier (e.g. CVE-2023-1234)

        Returns:
            CveDetails model or None on failure
        """
        try:
            url = f'https://services.nvd.nist.gov/rest/json/cves/2.0/{cve_id}'
            headers = {
                'User-Agent': f'awslabs/mcp/inspector-mcp-server/{MCP_SERVER_VERSION}',
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

            data = response.json()
            vulnerabilities = data.get('vulnerabilities', [])
            if not vulnerabilities:
                return None

            cve_data = vulnerabilities[0].get('cve', {})

            # Extract English description
            description = None
            for desc in cve_data.get('descriptions', []):
                if desc.get('lang') == 'en':
                    description = desc.get('value')
                    break

            # Extract CVSS v3.1 metrics
            cvss_v31 = None
            cvss_v2 = None
            metrics = cve_data.get('metrics', {})

            cvss_v31_data = metrics.get('cvssMetricV31', [])
            if cvss_v31_data:
                cvss = cvss_v31_data[0].get('cvssData', {})
                cvss_v31 = CvssMetrics(
                    base_score=cvss.get('baseScore'),
                    base_severity=cvss.get('baseSeverity'),
                    vector_string=cvss.get('vectorString'),
                    attack_vector=cvss.get('attackVector'),
                    attack_complexity=cvss.get('attackComplexity'),
                    privileges_required=cvss.get('privilegesRequired'),
                    user_interaction=cvss.get('userInteraction'),
                    scope=cvss.get('scope'),
                    confidentiality_impact=cvss.get('confidentialityImpact'),
                    integrity_impact=cvss.get('integrityImpact'),
                    availability_impact=cvss.get('availabilityImpact'),
                    exploitability_score=cvss_v31_data[0].get('exploitabilityScore'),
                    impact_score=cvss_v31_data[0].get('impactScore'),
                )

            # Fallback to CVSS v2
            cvss_v2_data = metrics.get('cvssMetricV2', [])
            if cvss_v2_data:
                cvss = cvss_v2_data[0].get('cvssData', {})
                cvss_v2 = CvssMetrics(
                    base_score=cvss.get('baseScore'),
                    base_severity=cvss_v2_data[0].get('baseSeverity'),
                    vector_string=cvss.get('vectorString'),
                    attack_vector=cvss.get('accessVector'),
                    attack_complexity=cvss.get('accessComplexity'),
                    exploitability_score=cvss_v2_data[0].get('exploitabilityScore'),
                    impact_score=cvss_v2_data[0].get('impactScore'),
                )

            # Extract weaknesses (CWE IDs)
            weaknesses = []
            for weakness in cve_data.get('weaknesses', []):
                for desc in weakness.get('description', []):
                    value = desc.get('value')
                    if value and value != 'NVD-CWE-noinfo' and value != 'NVD-CWE-Other':
                        weaknesses.append(value)

            # Extract affected versions from configurations
            affected_versions = []
            for config in cve_data.get('configurations', []):
                for node in config.get('nodes', []):
                    for cpe_match in node.get('cpeMatch', []):
                        affected_versions.append(
                            AffectedVersion(
                                criteria=cpe_match.get('criteria'),
                                version_start_including=cpe_match.get('versionStartIncluding'),
                                version_end_excluding=cpe_match.get('versionEndExcluding'),
                                version_end_including=cpe_match.get('versionEndIncluding'),
                            )
                        )

            # Extract references
            references = []
            for ref in cve_data.get('references', []):
                references.append(
                    CveReference(
                        url=ref.get('url'),
                        source=ref.get('source'),
                        tags=ref.get('tags'),
                    )
                )

            return CveDetails(
                cve_id=cve_id,
                description=description,
                published=cve_data.get('published'),
                last_modified=cve_data.get('lastModified'),
                nvd_url=f'https://nvd.nist.gov/vuln/detail/{cve_id}',
                cvss_v31=cvss_v31,
                cvss_v2=cvss_v2,
                weaknesses=weaknesses if weaknesses else None,
                affected_versions=affected_versions if affected_versions else None,
                references=references if references else None,
            )

        except Exception as e:
            logger.error(f'Error fetching CVE {cve_id} from NVD: {str(e)}')
            return None

    async def get_cve_details(
        self,
        ctx: Context,
        cve_id: Annotated[
            str,
            Field(description='The CVE identifier (e.g. CVE-2023-1234)'),
        ],
        region: Annotated[
            str,
            Field(description='AWS region (unused, kept for consistency). Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Look up detailed CVE information from the National Vulnerability Database (NVD).

        Retrieves CVSS scores, affected versions, weakness classifications, and references
        for a specific CVE identifier.

        Returns:
        --------
        Dictionary containing:
            - cve_id: The CVE identifier
            - description: Vulnerability description
            - cvss_v31/cvss_v2: CVSS score breakdowns
            - weaknesses: CWE identifiers
            - affected_versions: Affected product versions
            - references: External reference links
        """
        try:
            if not re.match(r'^CVE-\d{4}-\d{4,}$', cve_id):
                return {
                    'error': f'Invalid CVE ID format: {cve_id}. Expected format: CVE-YYYY-NNNNN'
                }

            cve_details = await self._fetch_cve_from_nvd(cve_id)

            if cve_details is None:
                return {'error': f'CVE {cve_id} not found or could not be retrieved from NVD'}

            return cve_details.model_dump()

        except Exception as e:
            logger.error(f'Error in get_cve_details: {str(e)}')
            await ctx.error(f'Error getting CVE details: {str(e)}')
            raise

    async def explain_finding(
        self,
        ctx: Context,
        finding_arn: Annotated[
            str,
            Field(description='The ARN of the finding to explain'),
        ],
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Get a comprehensive explanation of an Inspector finding with CVE enrichment.

        Retrieves full finding details and enriches package vulnerability findings
        with CVE data from the NVD, including CVSS scores, affected versions,
        and remediation references.

        Returns:
        --------
        Dictionary containing:
            - finding_arn: The finding ARN
            - title, severity, description: Finding basics
            - resource_type, resource_id: Affected resource info
            - cve_details: Enriched CVE data from NVD (if applicable)
            - cve_ids, cve_links: All associated CVE identifiers and NVD links
            - remediation: Remediation guidance
        """
        try:
            finding_result = await self.get_finding_details(
                ctx, finding_arn=finding_arn, region=region
            )
            finding = finding_result.get('finding')

            if finding is None:
                return {
                    'error': f'Finding {finding_arn} not found',
                    'failed_findings': finding_result.get('failed_findings', []),
                }

            # Extract CVE IDs
            cve_ids = []
            pkg_vuln = finding.get('package_vulnerability_details')
            if pkg_vuln:
                primary_cve = pkg_vuln.get('vulnerabilityId')
                if primary_cve and primary_cve.startswith('CVE-'):
                    cve_ids.append(primary_cve)
                for related in pkg_vuln.get('relatedVulnerabilities', []):
                    if related.startswith('CVE-') and related not in cve_ids:
                        cve_ids.append(related)

            # Fetch CVE details for primary CVE
            cve_details = None
            if cve_ids:
                cve_details = await self._fetch_cve_from_nvd(cve_ids[0])

            # Build NVD links
            cve_links = (
                [f'https://nvd.nist.gov/vuln/detail/{cve}' for cve in cve_ids] if cve_ids else None
            )

            # Extract resource info
            resource_type = None
            resource_id = None
            resources = finding.get('resources', [])
            if resources:
                resource_type = resources[0].get('type')
                resource_id = resources[0].get('id')

            explanation = FindingExplanation(
                finding_arn=finding_arn,
                title=finding.get('title'),
                severity=finding.get('severity'),
                description=finding.get('description'),
                finding_type=finding.get('type'),
                resource_type=resource_type,
                resource_id=resource_id,
                inspector_score=finding.get('inspector_score'),
                exploit_available=finding.get('exploit_available'),
                fix_available=finding.get('fix_available'),
                remediation=finding.get('remediation'),
                cve_details=cve_details,
                cve_ids=cve_ids if cve_ids else None,
                cve_links=cve_links,
            )

            return explanation.model_dump()

        except Exception as e:
            logger.error(f'Error in explain_finding: {str(e)}')
            await ctx.error(f'Error explaining finding: {str(e)}')
            raise

    async def generate_security_summary(
        self,
        ctx: Context,
        top_critical_count: Annotated[
            Optional[int],
            Field(description='Number of top critical findings to include (default: 5)'),
        ] = 5,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Generate a comprehensive security posture summary.

        Composes multiple Inspector queries into a single security overview including
        account scanning status, coverage statistics, finding severity counts,
        and top critical findings.

        Returns:
        --------
        Dictionary containing:
            - generated_at: Timestamp of report generation
            - region: AWS region queried
            - account_status: Inspector scanning enablement status
            - coverage_statistics: Scan coverage across resources
            - finding_counts_by_severity: Findings aggregated by severity
            - top_critical_findings: Most severe findings
        """
        try:
            generated_at = datetime.now(timezone.utc).isoformat()

            # Fetch account status
            account_status = None
            try:
                account_status = await self.get_account_status(ctx, region=region)
            except Exception as e:
                logger.error(f'Error fetching account status for security summary: {str(e)}')

            # Fetch coverage statistics
            coverage_statistics = None
            try:
                coverage_statistics = await self.list_coverage_statistics(ctx, region=region)
            except Exception as e:
                logger.error(f'Error fetching coverage statistics for security summary: {str(e)}')

            # Fetch finding counts by severity
            finding_counts_by_severity = None
            try:
                finding_counts_by_severity = await self.list_finding_aggregations(
                    ctx, aggregation_type='SEVERITY', region=region
                )
            except Exception as e:
                logger.error(f'Error fetching finding aggregations for security summary: {str(e)}')

            # Fetch top critical findings
            top_critical_findings = None
            try:
                critical_result = await self.list_findings(
                    ctx, severity='CRITICAL', max_results=top_critical_count, region=region
                )
                top_critical_findings = critical_result.get('findings')
            except Exception as e:
                logger.error(f'Error fetching critical findings for security summary: {str(e)}')

            summary = SecuritySummary(
                generated_at=generated_at,
                region=region,
                account_status=account_status,
                coverage_statistics=coverage_statistics,
                finding_counts_by_severity=finding_counts_by_severity,
                top_critical_findings=top_critical_findings,
            )

            return summary.model_dump()

        except Exception as e:
            logger.error(f'Error in generate_security_summary: {str(e)}')
            await ctx.error(f'Error generating security summary: {str(e)}')
            raise

    async def generate_findings_digest(
        self,
        ctx: Context,
        start_time: Annotated[
            str,
            Field(description='Start time for findings in ISO format (e.g. 2024-01-01T00:00:00Z)'),
        ],
        end_time: Annotated[
            Optional[str],
            Field(
                description='End time for findings in ISO format. Defaults to current UTC time.'
            ),
        ] = None,
        severity: Annotated[
            Optional[Literal['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL', 'UNTRIAGED']],
            Field(description='Filter digest findings by severity level'),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='Maximum number of findings to include (1-100, default: 25)'),
        ] = 25,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Generate a findings digest for a specific time range.

        Retrieves findings within the specified time range and enriches each with
        CVE links and resource information for a concise summary view.

        Returns:
        --------
        Dictionary containing:
            - generated_at: Timestamp of digest generation
            - region: AWS region queried
            - time_range: Start and end times of the digest window
            - total_findings: Total number of findings returned
            - severity_breakdown: Count of findings by severity
            - findings: List of enriched finding summaries
        """
        try:
            if end_time is None:
                end_time = datetime.now(timezone.utc).isoformat()

            findings_result = await self.list_findings(
                ctx,
                start_time=start_time,
                end_time=end_time,
                severity=severity,
                max_results=max_results,
                region=region,
            )

            raw_findings = findings_result.get('findings', [])

            # Build digest findings
            digest_findings = []
            severity_breakdown: Dict[str, int] = {}

            for f in raw_findings:
                # Count severity
                sev = f.get('severity', 'UNKNOWN')
                severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

                # Extract CVE IDs
                cve_ids = []
                pkg_vuln = f.get('package_vulnerability_details')
                if pkg_vuln:
                    primary_cve = pkg_vuln.get('vulnerabilityId')
                    if primary_cve and primary_cve.startswith('CVE-'):
                        cve_ids.append(primary_cve)
                    for related in pkg_vuln.get('relatedVulnerabilities', []):
                        if related.startswith('CVE-') and related not in cve_ids:
                            cve_ids.append(related)

                cve_links = (
                    [f'https://nvd.nist.gov/vuln/detail/{cve}' for cve in cve_ids]
                    if cve_ids
                    else None
                )

                # Extract resource info
                resource_type = None
                resource_id = None
                resources = f.get('resources', [])
                if resources:
                    resource_type = resources[0].get('type')
                    resource_id = resources[0].get('id')

                digest_findings.append(
                    DigestFinding(
                        finding_arn=f.get('finding_arn'),
                        title=f.get('title'),
                        severity=sev,
                        status=f.get('status'),
                        type=f.get('type'),
                        inspector_score=f.get('inspector_score'),
                        exploit_available=f.get('exploit_available'),
                        fix_available=f.get('fix_available'),
                        resource_type=resource_type,
                        resource_id=resource_id,
                        cve_ids=cve_ids if cve_ids else None,
                        cve_links=cve_links,
                        remediation=f.get('remediation'),
                    )
                )

            digest = FindingsDigest(
                generated_at=datetime.now(timezone.utc).isoformat(),
                region=region,
                time_range={'start_time': start_time, 'end_time': end_time},
                total_findings=len(digest_findings),
                severity_breakdown=severity_breakdown,
                findings=digest_findings,
            )

            return digest.model_dump()

        except Exception as e:
            logger.error(f'Error in generate_findings_digest: {str(e)}')
            await ctx.error(f'Error generating findings digest: {str(e)}')
            raise
