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

"""AWS GuardDuty MCP Server implementation."""

from __future__ import annotations

import json
from awslabs.aws_guardduty_mcp_server.aws_client import get_guardduty_client
from awslabs.aws_guardduty_mcp_server.consts import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_SORT_ATTRIBUTE,
    DEFAULT_SORT_ORDER,
    MAX_FINDINGS_PAGE_SIZE,
    MCP_SERVER_NAME,
)
from awslabs.aws_guardduty_mcp_server.errors import (
    GuardDutyValidationError,
    handle_guardduty_error,
)
from awslabs.aws_guardduty_mcp_server.models import (
    GetFindingsResponse,
    GuardDutyDetector,
    GuardDutyFinding,
    GuardDutyFindingSummary,
    ListDetectorsResponse,
    ListFindingsResponse,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Any, Dict, List, Optional


mcp = FastMCP(
    MCP_SERVER_NAME,
    instructions="""
    # AWS GuardDuty MCP Server

    This is a read-only MCP server for GuardDuty triage workflows. Use it to pull findings,
    return structured security data to an LLM, and support downstream classification,
    summarization, and incident response analysis.

    ## Recommended workflow
    1. Call `list_detectors` to discover the detector for the target region.
    2. Call `list_findings` to retrieve a page of findings with optional severity/status filters.
    3. Call `get_findings` for full raw finding details when deeper LLM analysis is needed.

    ## Important notes
    - Requires AWS credentials with GuardDuty read permissions.
    - This server does not mutate GuardDuty state.
    - Finding data may contain sensitive account, network, and workload details.
    """,
    dependencies=['pydantic', 'loguru', 'boto3', 'botocore', 'mcp[cli]'],
)


def _resolve_detector_id(client: Any, detector_id: Optional[str], region: Optional[str]) -> str:
    """Resolve a detector ID or infer the only available detector in-region."""
    if detector_id:
        return detector_id

    response = client.list_detectors()
    detector_ids = response.get('DetectorIds', [])
    if not detector_ids:
        raise GuardDutyValidationError(
            f'No GuardDuty detector found in region {region or "default"}'
        )
    if len(detector_ids) > 1:
        raise GuardDutyValidationError(
            'Multiple GuardDuty detectors found. Pass detector_id explicitly.'
        )
    return detector_ids[0]


def _merge_finding_criteria(
    raw_finding_criteria: Optional[str],
    severity_min: Optional[float],
    severity_max: Optional[float],
    archived: Optional[bool],
) -> Optional[Dict[str, Any]]:
    """Merge optional convenience filters into GuardDuty finding criteria."""
    criterion: Dict[str, Any] = {}

    if raw_finding_criteria:
        parsed = json.loads(raw_finding_criteria)
        criterion = parsed.get('Criterion', parsed)
        if not isinstance(criterion, dict):
            raise GuardDutyValidationError('finding_criteria_json must be a JSON object')

    if severity_min is not None or severity_max is not None:
        severity_criterion = criterion.setdefault('severity', {})
        if severity_min is not None:
            severity_criterion['Gte'] = severity_min
        if severity_max is not None:
            severity_criterion['Lte'] = severity_max

    if archived is not None:
        criterion['service.archived'] = {'Eq': ['true' if archived else 'false']}

    if not criterion:
        return None

    return {'Criterion': criterion}


def _to_finding_summary(finding: Dict[str, Any]) -> GuardDutyFindingSummary:
    """Convert a raw GuardDuty finding into a compact summary."""
    resource = finding.get('Resource') or {}
    return GuardDutyFindingSummary(
        finding_id=finding.get('Id', ''),
        severity=finding.get('Severity'),
        title=finding.get('Title'),
        type=finding.get('Type'),
        region=finding.get('Region'),
        account_id=finding.get('AccountId'),
        resource_type=resource.get('ResourceType'),
        updated_at=finding.get('UpdatedAt'),
    )


def _to_finding(finding: Dict[str, Any]) -> GuardDutyFinding:
    """Convert a raw GuardDuty finding into a structured MCP model."""
    resource = finding.get('Resource') or {}
    service = finding.get('Service') or {}
    return GuardDutyFinding(
        account_id=finding.get('AccountId'),
        arn=finding.get('Arn'),
        confidence=finding.get('Confidence'),
        created_at=finding.get('CreatedAt'),
        description=finding.get('Description'),
        finding_id=finding.get('Id', ''),
        region=finding.get('Region'),
        resource_type=resource.get('ResourceType'),
        resource=resource,
        service=service,
        severity=finding.get('Severity'),
        title=finding.get('Title'),
        type=finding.get('Type'),
        updated_at=finding.get('UpdatedAt'),
    )


@mcp.tool()
async def list_detectors(
    ctx: CallToolResult,
    region: Optional[str] = Field(
        default=None, description='AWS region to query, for example us-east-1'
    ),
) -> ListDetectorsResponse:
    """List GuardDuty detectors in the selected region."""
    try:
        logger.info(f'Listing GuardDuty detectors for region={region}')
        client = get_guardduty_client(region=region)
        response = client.list_detectors()
        detectors = [
            GuardDutyDetector(detector_id=detector_id, region=region)
            for detector_id in response.get('DetectorIds', [])
        ]
        return ListDetectorsResponse(detectors=detectors, count=len(detectors))
    except Exception as e:
        error = handle_guardduty_error(e)
        logger.error(f'Error listing GuardDuty detectors: {error}')
        raise error


@mcp.tool()
async def list_findings(
    ctx: CallToolResult,
    detector_id: Optional[str] = Field(
        default=None,
        description='GuardDuty detector ID. If omitted, the server will use the only detector in-region.',
    ),
    region: Optional[str] = Field(
        default=None, description='AWS region to query, for example us-east-1'
    ),
    max_results: int = Field(
        default=DEFAULT_MAX_RESULTS, description='Number of findings to return, max 50'
    ),
    next_token: Optional[str] = Field(default=None, description='Pagination token from a prior response'),
    severity_min: Optional[float] = Field(
        default=None, description='Minimum GuardDuty severity score, for example 4 or 7'
    ),
    severity_max: Optional[float] = Field(
        default=None, description='Maximum GuardDuty severity score, for example 8.9'
    ),
    archived: Optional[bool] = Field(
        default=False, description='Whether to return archived findings instead of active findings'
    ),
    finding_criteria_json: Optional[str] = Field(
        default=None,
        description='Raw GuardDuty FindingCriteria JSON to merge with convenience filters',
    ),
    sort_attribute_name: Optional[str] = Field(
        default=DEFAULT_SORT_ATTRIBUTE,
        description='GuardDuty sort attribute, for example updatedAt',
    ),
    sort_order: str = Field(default=DEFAULT_SORT_ORDER, description='Sort order ASC or DESC'),
) -> ListFindingsResponse:
    """List GuardDuty findings and include compact summaries for LLM triage."""
    try:
        if max_results < 1 or max_results > MAX_FINDINGS_PAGE_SIZE:
            raise GuardDutyValidationError(
                f'max_results must be between 1 and {MAX_FINDINGS_PAGE_SIZE}'
            )
        if sort_order not in {'ASC', 'DESC'}:
            raise GuardDutyValidationError('sort_order must be ASC or DESC')

        client = get_guardduty_client(region=region)
        resolved_detector_id = _resolve_detector_id(client, detector_id, region)
        finding_criteria = _merge_finding_criteria(
            finding_criteria_json, severity_min, severity_max, archived
        )

        request: Dict[str, Any] = {
            'DetectorId': resolved_detector_id,
            'MaxResults': max_results,
            'SortCriteria': {'AttributeName': sort_attribute_name, 'OrderBy': sort_order},
        }
        if next_token:
            request['NextToken'] = next_token
        if finding_criteria:
            request['FindingCriteria'] = finding_criteria

        logger.info(
            'Listing GuardDuty findings detector_id={} region={} max_results={}',
            resolved_detector_id,
            region,
            max_results,
        )
        list_response = client.list_findings(**request)
        finding_ids: List[str] = list_response.get('FindingIds', [])

        findings: List[GuardDutyFindingSummary] = []
        if finding_ids:
            detail_response = client.get_findings(
                DetectorId=resolved_detector_id,
                FindingIds=finding_ids,
                SortCriteria={'AttributeName': sort_attribute_name, 'OrderBy': sort_order},
            )
            findings = [_to_finding_summary(item) for item in detail_response.get('Findings', [])]

        return ListFindingsResponse(
            detector_id=resolved_detector_id,
            finding_ids=finding_ids,
            findings=findings,
            count=len(finding_ids),
            next_token=list_response.get('NextToken'),
        )
    except Exception as e:
        error = handle_guardduty_error(e)
        logger.error(f'Error listing GuardDuty findings: {error}')
        raise error


@mcp.tool()
async def get_findings(
    ctx: CallToolResult,
    finding_ids: List[str] = Field(..., description='GuardDuty finding IDs to retrieve'),
    detector_id: Optional[str] = Field(
        default=None,
        description='GuardDuty detector ID. If omitted, the server will use the only detector in-region.',
    ),
    region: Optional[str] = Field(
        default=None, description='AWS region to query, for example us-east-1'
    ),
    sort_attribute_name: Optional[str] = Field(
        default=DEFAULT_SORT_ATTRIBUTE,
        description='GuardDuty sort attribute, for example updatedAt',
    ),
    sort_order: str = Field(default=DEFAULT_SORT_ORDER, description='Sort order ASC or DESC'),
) -> GetFindingsResponse:
    """Fetch full GuardDuty findings for downstream LLM analysis."""
    try:
        if not finding_ids:
            raise GuardDutyValidationError('finding_ids must not be empty')
        if sort_order not in {'ASC', 'DESC'}:
            raise GuardDutyValidationError('sort_order must be ASC or DESC')

        client = get_guardduty_client(region=region)
        resolved_detector_id = _resolve_detector_id(client, detector_id, region)

        logger.info(
            'Getting GuardDuty findings detector_id={} region={} count={}',
            resolved_detector_id,
            region,
            len(finding_ids),
        )
        response = client.get_findings(
            DetectorId=resolved_detector_id,
            FindingIds=finding_ids,
            SortCriteria={'AttributeName': sort_attribute_name, 'OrderBy': sort_order},
        )
        findings = [_to_finding(item) for item in response.get('Findings', [])]

        return GetFindingsResponse(
            detector_id=resolved_detector_id, findings=findings, count=len(findings)
        )
    except Exception as e:
        error = handle_guardduty_error(e)
        logger.error(f'Error getting GuardDuty findings: {error}')
        raise error


def main():
    """Run the GuardDuty MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
