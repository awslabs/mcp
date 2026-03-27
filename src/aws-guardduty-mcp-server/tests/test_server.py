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

"""Tests for the GuardDuty MCP server."""

from __future__ import annotations

import pytest
from awslabs.aws_guardduty_mcp_server.aws_client import get_guardduty_client
from awslabs.aws_guardduty_mcp_server.errors import (
    GuardDutyPermissionError,
    GuardDutyValidationError,
    handle_guardduty_error,
)
from botocore.exceptions import ClientError as BotoClientError
from unittest.mock import AsyncMock, Mock, patch


def test_get_guardduty_client():
    """GuardDuty client creation uses the expected user agent."""
    with patch('boto3.client') as mock_client:
        mock_client.return_value = Mock()
        client = get_guardduty_client(region='us-east-1')

        assert client is not None
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 'guardduty'
        assert kwargs['region_name'] == 'us-east-1'
        assert kwargs['config'].user_agent_extra == 'awslabs-aws-guardduty-mcp-server/0.1.0'


def test_handle_guardduty_error_access_denied():
    """Access denied maps to a permission error."""
    error_response = {
        'Error': {
            'Code': 'AccessDeniedException',
            'Message': 'not authorized',
        }
    }
    boto_error = BotoClientError(error_response, 'ListFindings')

    handled = handle_guardduty_error(boto_error)

    assert isinstance(handled, GuardDutyPermissionError)
    assert 'Access denied' in str(handled)


@pytest.mark.asyncio
async def test_list_detectors():
    """Detector listing returns normalized detector models."""
    from awslabs.aws_guardduty_mcp_server.server import list_detectors

    mock_ctx = AsyncMock()

    with patch('awslabs.aws_guardduty_mcp_server.server.get_guardduty_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_detectors.return_value = {'DetectorIds': ['det-123']}
        mock_get_client.return_value = mock_client

        result = await list_detectors(mock_ctx, region='us-west-2')

        assert result.count == 1
        assert result.detectors[0].detector_id == 'det-123'
        assert result.detectors[0].region == 'us-west-2'


@pytest.mark.asyncio
async def test_list_findings_with_auto_detector_and_details():
    """Finding listing auto-resolves the detector and expands summaries."""
    from awslabs.aws_guardduty_mcp_server.server import list_findings

    mock_ctx = AsyncMock()

    finding = {
        'Id': 'finding-1',
        'Severity': 8.2,
        'Title': 'CryptoCurrency:EC2/BitcoinTool.B!DNS',
        'Type': 'CryptoCurrency:EC2/BitcoinTool.B!DNS',
        'Region': 'us-east-1',
        'AccountId': '123456789012',
        'UpdatedAt': '2026-03-06T00:00:00Z',
        'Resource': {'ResourceType': 'Instance'},
    }

    with patch('awslabs.aws_guardduty_mcp_server.server.get_guardduty_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_detectors.return_value = {'DetectorIds': ['det-123']}
        mock_client.list_findings.return_value = {'FindingIds': ['finding-1']}
        mock_client.get_findings.return_value = {'Findings': [finding]}
        mock_get_client.return_value = mock_client

        result = await list_findings(
            mock_ctx,
            region='us-east-1',
            severity_min=7,
            archived=False,
        )

        assert result.detector_id == 'det-123'
        assert result.count == 1
        assert result.finding_ids == ['finding-1']
        assert result.findings[0].finding_id == 'finding-1'

        _, kwargs = mock_client.list_findings.call_args
        assert kwargs['FindingCriteria']['Criterion']['severity']['Gte'] == 7
        assert kwargs['FindingCriteria']['Criterion']['service.archived']['Eq'] == ['false']


@pytest.mark.asyncio
async def test_list_findings_rejects_invalid_max_results():
    """Finding list enforces GuardDuty max page size."""
    from awslabs.aws_guardduty_mcp_server.server import list_findings

    mock_ctx = AsyncMock()

    with pytest.raises(GuardDutyValidationError):
        await list_findings(mock_ctx, max_results=51)


@pytest.mark.asyncio
async def test_get_findings():
    """Full finding retrieval returns normalized finding payloads."""
    from awslabs.aws_guardduty_mcp_server.server import get_findings

    mock_ctx = AsyncMock()
    raw_finding = {
        'Id': 'finding-1',
        'Severity': 5.3,
        'Title': 'Recon:IAMUser/MaliciousIPCaller.Custom',
        'Type': 'Recon:IAMUser/MaliciousIPCaller.Custom',
        'Region': 'us-east-1',
        'AccountId': '123456789012',
        'CreatedAt': '2026-03-06T00:00:00Z',
        'UpdatedAt': '2026-03-06T01:00:00Z',
        'Description': 'Example finding',
        'Resource': {'ResourceType': 'AccessKey'},
        'Service': {'Archived': False},
    }

    with patch('awslabs.aws_guardduty_mcp_server.server.get_guardduty_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_detectors.return_value = {'DetectorIds': ['det-123']}
        mock_client.get_findings.return_value = {'Findings': [raw_finding]}
        mock_get_client.return_value = mock_client

        result = await get_findings(mock_ctx, finding_ids=['finding-1'], region='us-east-1')

        assert result.detector_id == 'det-123'
        assert result.count == 1
        assert result.findings[0].finding_id == 'finding-1'
        assert result.findings[0].resource_type == 'AccessKey'
