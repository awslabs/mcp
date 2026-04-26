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

"""Comprehensive tests for Inspector MCP server tools."""

import httpx
import pytest
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
from awslabs.inspector_mcp_server.tools import InspectorTools
from datetime import datetime, timezone
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch


class TestInspectorToolsInitialization:
    """Test Inspector tools initialization and client management."""

    def test_initialization(self):
        """Test InspectorTools initialization."""
        tools = InspectorTools()
        assert tools is not None

    @patch('boto3.Session')
    def test_get_inspector_client_without_profile(self, mock_session):
        """Test _get_inspector_client without AWS_PROFILE."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client

        tools = InspectorTools()

        with patch.dict('os.environ', {}, clear=True):
            client = tools._get_inspector_client('us-west-2')

        assert client == mock_client
        mock_session.assert_called_once_with(region_name='us-west-2')
        mock_session.return_value.client.assert_called_once()

    @patch('boto3.Session')
    def test_get_inspector_client_with_profile(self, mock_session):
        """Test _get_inspector_client with AWS_PROFILE set."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client

        tools = InspectorTools()

        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
            client = tools._get_inspector_client('eu-west-1')

        assert client == mock_client
        mock_session.assert_called_once_with(profile_name='test-profile', region_name='eu-west-1')

    @patch('boto3.Session')
    def test_get_inspector_client_error_handling(self, mock_session):
        """Test _get_inspector_client error handling."""
        mock_session.side_effect = Exception('AWS credentials error')

        tools = InspectorTools()

        with pytest.raises(Exception, match='AWS credentials error'):
            tools._get_inspector_client('us-east-1')


class TestListFindings:
    """Test the list_findings tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_findings(self):
        """Sample Inspector findings for testing."""
        return [
            {
                'findingArn': 'arn:aws:inspector2:us-east-1:123456789012:finding/f-1',
                'awsAccountId': '123456789012',
                'description': 'CVE-2023-1234 in package foo',
                'firstObservedAt': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                'lastObservedAt': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                'severity': 'HIGH',
                'status': 'ACTIVE',
                'title': 'CVE-2023-1234 - foo',
                'type': 'PACKAGE_VULNERABILITY',
                'inspectorScore': 8.5,
                'fixAvailable': 'YES',
                'resources': [
                    {
                        'type': 'AWS_EC2_INSTANCE',
                        'id': 'i-1234567890abcdef0',
                    }
                ],
                'remediation': {
                    'recommendation': {
                        'text': 'Update foo to version 2.0.0',
                    }
                },
            },
            {
                'findingArn': 'arn:aws:inspector2:us-east-1:123456789012:finding/f-2',
                'awsAccountId': '123456789012',
                'description': 'Network path to port 22',
                'firstObservedAt': datetime(2024, 1, 5, 8, 0, 0, tzinfo=timezone.utc),
                'lastObservedAt': datetime(2024, 1, 20, 8, 0, 0, tzinfo=timezone.utc),
                'severity': 'MEDIUM',
                'status': 'ACTIVE',
                'title': 'Port 22 reachable from internet',
                'type': 'NETWORK_REACHABILITY',
                'inspectorScore': 5.0,
                'resources': [
                    {
                        'type': 'AWS_EC2_INSTANCE',
                        'id': 'i-abcdef1234567890',
                    }
                ],
            },
        ]

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_basic(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test basic list_findings functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {
            'findings': sample_findings,
            'nextToken': 'next-token-123',
        }

        result = await tools.list_findings(mock_context)

        assert len(result['findings']) == 2
        assert result['next_token'] == 'next-token-123'
        assert result['findings'][0]['title'] == 'CVE-2023-1234 - foo'
        assert result['findings'][1]['severity'] == 'MEDIUM'

        mock_client.list_findings.assert_called_once()
        call_kwargs = mock_client.list_findings.call_args[1]
        assert call_kwargs['maxResults'] == 10
        assert 'sortCriteria' in call_kwargs

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_severity_filter(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings with severity filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {
            'findings': [sample_findings[0]],
        }

        result = await tools.list_findings(mock_context, severity='HIGH')

        assert len(result['findings']) == 1
        call_kwargs = mock_client.list_findings.call_args[1]
        assert 'filterCriteria' in call_kwargs
        assert 'severity' in call_kwargs['filterCriteria']
        assert call_kwargs['filterCriteria']['severity'][0]['value'] == 'HIGH'
        assert call_kwargs['filterCriteria']['severity'][0]['comparison'] == 'EQUALS'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_resource_type_filter(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings with resource type filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': sample_findings}

        result = await tools.list_findings(mock_context, resource_type='AWS_EC2_INSTANCE')

        assert len(result['findings']) == 2
        call_kwargs = mock_client.list_findings.call_args[1]
        assert 'resourceType' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_finding_type_filter(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings with finding type filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {
            'findings': [sample_findings[1]],
        }

        result = await tools.list_findings(mock_context, finding_type='NETWORK_REACHABILITY')

        assert len(result['findings']) == 1
        call_kwargs = mock_client.list_findings.call_args[1]
        assert 'findingType' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_title_filter(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings with title filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {
            'findings': [sample_findings[0]],
        }

        result = await tools.list_findings(mock_context, title_filter='CVE-2023')

        assert len(result['findings']) == 1
        call_kwargs = mock_client.list_findings.call_args[1]
        assert 'title' in call_kwargs['filterCriteria']
        assert call_kwargs['filterCriteria']['title'][0]['comparison'] == 'PREFIX'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_time_range(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings with time range filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': sample_findings}

        result = await tools.list_findings(
            mock_context,
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-31T23:59:59Z',
        )

        assert len(result['findings']) == 2
        call_kwargs = mock_client.list_findings.call_args[1]
        assert 'lastObservedAt' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_pagination(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings with pagination token."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {
            'findings': sample_findings,
            'nextToken': 'new-token-456',
        }

        result = await tools.list_findings(mock_context, next_token='previous-token-123')

        assert len(result['findings']) == 2
        assert result['next_token'] == 'new-token-456'
        call_kwargs = mock_client.list_findings.call_args[1]
        assert call_kwargs['nextToken'] == 'previous-token-123'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_last_page(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings when response has no NextToken (last page)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {
            'findings': sample_findings,
        }

        result = await tools.list_findings(mock_context)

        assert len(result['findings']) == 2
        assert result['next_token'] is None

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_different_region(
        self, mock_get_client, tools, mock_context, sample_findings
    ):
        """Test list_findings with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': sample_findings}

        result = await tools.list_findings(mock_context, region='eu-west-1')

        assert len(result['findings']) == 2
        mock_get_client.assert_called_with('eu-west-1')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_max_results_boundary(self, mock_get_client, tools, mock_context):
        """Test list_findings max_results boundary conditions."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': []}

        test_cases = [
            (None, 10),  # Default
            (1, 1),  # Minimum
            (100, 100),  # Maximum
            (0, 1),  # Below minimum
            (200, 100),  # Above maximum
        ]

        for input_val, expected_val in test_cases:
            await tools.list_findings(mock_context, max_results=input_val)
            call_kwargs = mock_client.list_findings.call_args[1]
            assert call_kwargs['maxResults'] == expected_val

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_empty_results(self, mock_get_client, tools, mock_context):
        """Test list_findings with empty results."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': []}

        result = await tools.list_findings(mock_context)

        assert len(result['findings']) == 0
        assert result['next_token'] is None

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_error_handling(self, mock_get_client, tools, mock_context):
        """Test list_findings error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.side_effect = Exception('AWS Error')

        with pytest.raises(Exception, match='AWS Error'):
            await tools.list_findings(mock_context)

        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_all_filters(self, mock_get_client, tools, mock_context):
        """Test list_findings with all filters applied."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': []}

        await tools.list_findings(
            mock_context,
            severity='CRITICAL',
            resource_type='AWS_EC2_INSTANCE',
            finding_type='PACKAGE_VULNERABILITY',
            title_filter='CVE',
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-12-31T23:59:59Z',
            max_results=50,
        )

        call_kwargs = mock_client.list_findings.call_args[1]
        fc = call_kwargs['filterCriteria']
        assert 'severity' in fc
        assert 'resourceType' in fc
        assert 'findingType' in fc
        assert 'title' in fc
        assert 'lastObservedAt' in fc
        assert call_kwargs['maxResults'] == 50


class TestGetFindingDetails:
    """Test the get_finding_details tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_finding_detail(self):
        """Sample detailed Inspector finding for testing."""
        return {
            'findingArn': 'arn:aws:inspector2:us-east-1:123456789012:finding/f-1',
            'awsAccountId': '123456789012',
            'description': 'CVE-2023-1234 in package foo',
            'firstObservedAt': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            'lastObservedAt': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            'severity': 'HIGH',
            'status': 'ACTIVE',
            'title': 'CVE-2023-1234 - foo',
            'type': 'PACKAGE_VULNERABILITY',
            'inspectorScore': 8.5,
            'inspectorScoreDetails': {
                'adjustedCvss': {
                    'score': 8.5,
                    'scoreSource': 'NVD',
                    'version': '3.1',
                }
            },
            'packageVulnerabilityDetails': {
                'vulnerabilityId': 'CVE-2023-1234',
                'source': 'NVD',
                'cvss': [{'baseScore': 8.5, 'source': 'NVD', 'version': '3.1'}],
                'vulnerablePackages': [
                    {
                        'name': 'foo',
                        'version': '1.0.0',
                        'fixedInVersion': '2.0.0',
                    }
                ],
            },
            'fixAvailable': 'YES',
            'resources': [
                {
                    'type': 'AWS_EC2_INSTANCE',
                    'id': 'i-1234567890abcdef0',
                }
            ],
            'remediation': {
                'recommendation': {
                    'text': 'Update foo to version 2.0.0',
                }
            },
        }

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_finding_details_basic(
        self, mock_get_client, tools, mock_context, sample_finding_detail
    ):
        """Test basic get_finding_details functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_findings.return_value = {
            'findings': [sample_finding_detail],
            'failedFindings': [],
        }

        finding_arn = 'arn:aws:inspector2:us-east-1:123456789012:finding/f-1'
        result = await tools.get_finding_details(mock_context, finding_arn=finding_arn)

        assert result['finding'] is not None
        assert result['finding']['title'] == 'CVE-2023-1234 - foo'
        assert result['finding']['severity'] == 'HIGH'
        assert result['finding']['inspector_score'] == 8.5
        assert result['finding']['package_vulnerability_details'] is not None
        assert result['failed_findings'] == []

        mock_client.batch_get_findings.assert_called_once_with(findingArns=[finding_arn])

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_finding_details_not_found(self, mock_get_client, tools, mock_context):
        """Test get_finding_details when finding is not found."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_findings.return_value = {
            'findings': [],
            'failedFindings': [
                {
                    'findingArn': 'arn:aws:inspector2:us-east-1:123:finding/missing',
                    'errorCode': 'FINDING_NOT_FOUND',
                    'errorMessage': 'Finding not found',
                }
            ],
        }

        result = await tools.get_finding_details(
            mock_context,
            finding_arn='arn:aws:inspector2:us-east-1:123:finding/missing',
        )

        assert result['finding'] is None
        assert len(result['failed_findings']) == 1
        assert result['failed_findings'][0]['errorCode'] == 'FINDING_NOT_FOUND'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_finding_details_different_region(
        self, mock_get_client, tools, mock_context, sample_finding_detail
    ):
        """Test get_finding_details with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_findings.return_value = {
            'findings': [sample_finding_detail],
            'failedFindings': [],
        }

        finding_arn = 'arn:aws:inspector2:eu-west-1:123456789012:finding/f-1'
        result = await tools.get_finding_details(
            mock_context, finding_arn=finding_arn, region='eu-west-1'
        )

        assert result['finding'] is not None
        mock_get_client.assert_called_with('eu-west-1')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_finding_details_error_handling(self, mock_get_client, tools, mock_context):
        """Test get_finding_details error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_findings.side_effect = Exception('Access denied')

        with pytest.raises(Exception, match='Access denied'):
            await tools.get_finding_details(
                mock_context,
                finding_arn='arn:aws:inspector2:us-east-1:123:finding/f-1',
            )

        mock_context.error.assert_called_once()


class TestListFindingAggregations:
    """Test the list_finding_aggregations tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_severity_aggregation(self):
        """Sample severity aggregation response."""
        return {
            'aggregationType': 'SEVERITY',
            'responses': [
                {
                    'severityCount': {
                        'all': 100,
                        'critical': 5,
                        'high': 20,
                        'medium': 45,
                        'informational': 30,
                    }
                }
            ],
        }

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_finding_aggregations_basic(
        self, mock_get_client, tools, mock_context, sample_severity_aggregation
    ):
        """Test basic list_finding_aggregations functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_finding_aggregations.return_value = sample_severity_aggregation

        result = await tools.list_finding_aggregations(mock_context, aggregation_type='SEVERITY')

        assert result['aggregation_type'] == 'SEVERITY'
        assert result['counts'] is not None
        assert len(result['counts']) == 1

        mock_client.list_finding_aggregations.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_finding_aggregations_account_id(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_finding_aggregations by ACCOUNT_ID."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_finding_aggregations.return_value = {
            'aggregationType': 'ACCOUNT_ID',
            'responses': [
                {'accountId': '123456789012', 'severityCounts': {'critical': 2}},
                {'accountId': '987654321098', 'severityCounts': {'critical': 1}},
            ],
        }

        result = await tools.list_finding_aggregations(mock_context, aggregation_type='ACCOUNT_ID')

        assert result['aggregation_type'] == 'ACCOUNT_ID'
        assert len(result['counts']) == 2

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_finding_aggregations_with_pagination(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_finding_aggregations with pagination."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_finding_aggregations.return_value = {
            'aggregationType': 'TITLE',
            'responses': [{'titleSeverityCounts': {'critical': 1}}],
            'nextToken': 'next-agg-token',
        }

        result = await tools.list_finding_aggregations(
            mock_context,
            aggregation_type='TITLE',
            next_token='prev-agg-token',
        )

        assert result['next_token'] == 'next-agg-token'
        call_kwargs = mock_client.list_finding_aggregations.call_args[1]
        assert call_kwargs['nextToken'] == 'prev-agg-token'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_finding_aggregations_different_region(
        self, mock_get_client, tools, mock_context, sample_severity_aggregation
    ):
        """Test list_finding_aggregations with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_finding_aggregations.return_value = sample_severity_aggregation

        result = await tools.list_finding_aggregations(
            mock_context, aggregation_type='SEVERITY', region='ap-southeast-1'
        )

        assert result['aggregation_type'] == 'SEVERITY'
        mock_get_client.assert_called_with('ap-southeast-1')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_finding_aggregations_max_results(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_finding_aggregations max_results validation."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_finding_aggregations.return_value = {
            'aggregationType': 'SEVERITY',
            'responses': [],
        }

        await tools.list_finding_aggregations(
            mock_context, aggregation_type='SEVERITY', max_results=50
        )

        call_kwargs = mock_client.list_finding_aggregations.call_args[1]
        assert call_kwargs['maxResults'] == 50

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_finding_aggregations_error_handling(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_finding_aggregations error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_finding_aggregations.side_effect = Exception('Service error')

        with pytest.raises(Exception, match='Service error'):
            await tools.list_finding_aggregations(mock_context, aggregation_type='SEVERITY')

        mock_context.error.assert_called_once()


class TestListCoverage:
    """Test the list_coverage tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_coverage(self):
        """Sample coverage resources for testing."""
        return [
            {
                'accountId': '123456789012',
                'resourceId': 'i-1234567890abcdef0',
                'resourceType': 'AWS_EC2_INSTANCE',
                'scanStatus': {
                    'statusCode': 'ACTIVE',
                    'reason': 'SUCCESSFUL',
                },
                'scanType': 'PACKAGE',
            },
            {
                'accountId': '123456789012',
                'resourceId': 'arn:aws:ecr:us-east-1:123456789012:repository/my-repo',
                'resourceType': 'AWS_ECR_CONTAINER_IMAGE',
                'scanStatus': {
                    'statusCode': 'ACTIVE',
                    'reason': 'SUCCESSFUL',
                },
                'scanType': 'PACKAGE',
            },
        ]

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_basic(
        self, mock_get_client, tools, mock_context, sample_coverage
    ):
        """Test basic list_coverage functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.return_value = {
            'coveredResources': sample_coverage,
            'nextToken': 'cov-token-123',
        }

        result = await tools.list_coverage(mock_context)

        assert len(result['covered_resources']) == 2
        assert result['next_token'] == 'cov-token-123'
        assert result['covered_resources'][0]['resource_type'] == 'AWS_EC2_INSTANCE'

        mock_client.list_coverage.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_with_resource_type_filter(
        self, mock_get_client, tools, mock_context, sample_coverage
    ):
        """Test list_coverage with resource type filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.return_value = {
            'coveredResources': [sample_coverage[0]],
        }

        result = await tools.list_coverage(mock_context, resource_type='AWS_EC2_INSTANCE')

        assert len(result['covered_resources']) == 1
        call_kwargs = mock_client.list_coverage.call_args[1]
        assert 'filterCriteria' in call_kwargs
        assert 'resourceType' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_with_scan_status_filter(
        self, mock_get_client, tools, mock_context, sample_coverage
    ):
        """Test list_coverage with scan status filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.return_value = {
            'coveredResources': sample_coverage,
        }

        await tools.list_coverage(mock_context, scan_status='ACTIVE')

        call_kwargs = mock_client.list_coverage.call_args[1]
        assert 'scanStatusCode' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_with_account_id_filter(
        self, mock_get_client, tools, mock_context, sample_coverage
    ):
        """Test list_coverage with account ID filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.return_value = {
            'coveredResources': sample_coverage,
        }

        await tools.list_coverage(mock_context, account_id='123456789012')

        call_kwargs = mock_client.list_coverage.call_args[1]
        assert 'accountId' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_with_pagination(
        self, mock_get_client, tools, mock_context, sample_coverage
    ):
        """Test list_coverage with pagination."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.return_value = {
            'coveredResources': sample_coverage,
            'nextToken': 'new-cov-token',
        }

        result = await tools.list_coverage(mock_context, next_token='prev-cov-token')

        assert result['next_token'] == 'new-cov-token'
        call_kwargs = mock_client.list_coverage.call_args[1]
        assert call_kwargs['nextToken'] == 'prev-cov-token'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_empty_results(self, mock_get_client, tools, mock_context):
        """Test list_coverage with empty results."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.return_value = {'coveredResources': []}

        result = await tools.list_coverage(mock_context)

        assert len(result['covered_resources']) == 0
        assert result['next_token'] is None

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_different_region(
        self, mock_get_client, tools, mock_context, sample_coverage
    ):
        """Test list_coverage with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.return_value = {
            'coveredResources': sample_coverage,
        }

        await tools.list_coverage(mock_context, region='us-west-2')

        mock_get_client.assert_called_with('us-west-2')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_error_handling(self, mock_get_client, tools, mock_context):
        """Test list_coverage error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage.side_effect = Exception('Coverage error')

        with pytest.raises(Exception, match='Coverage error'):
            await tools.list_coverage(mock_context)

        mock_context.error.assert_called_once()


class TestListCoverageStatistics:
    """Test the list_coverage_statistics tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_coverage_statistics(self):
        """Sample coverage statistics response."""
        return {
            'totalCounts': 150,
            'countsByGroup': [
                {'count': 80, 'groupKey': 'AWS_EC2_INSTANCE'},
                {'count': 50, 'groupKey': 'AWS_ECR_CONTAINER_IMAGE'},
                {'count': 20, 'groupKey': 'AWS_LAMBDA_FUNCTION'},
            ],
        }

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_statistics_basic(
        self, mock_get_client, tools, mock_context, sample_coverage_statistics
    ):
        """Test basic list_coverage_statistics functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage_statistics.return_value = sample_coverage_statistics

        result = await tools.list_coverage_statistics(mock_context)

        assert result['total_counts'] == 150
        assert len(result['counts_by_group']) == 3

        mock_client.list_coverage_statistics.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_statistics_with_group_by(
        self, mock_get_client, tools, mock_context, sample_coverage_statistics
    ):
        """Test list_coverage_statistics with group_by parameter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage_statistics.return_value = sample_coverage_statistics

        await tools.list_coverage_statistics(mock_context, group_by='RESOURCE_TYPE')

        call_kwargs = mock_client.list_coverage_statistics.call_args[1]
        assert call_kwargs['groupBy'] == 'RESOURCE_TYPE'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_statistics_with_resource_type(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_coverage_statistics with resource type filter."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage_statistics.return_value = {
            'totalCounts': 80,
            'countsByGroup': [],
        }

        await tools.list_coverage_statistics(mock_context, resource_type='AWS_EC2_INSTANCE')

        call_kwargs = mock_client.list_coverage_statistics.call_args[1]
        assert 'filterCriteria' in call_kwargs
        assert 'resourceType' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_statistics_different_region(
        self, mock_get_client, tools, mock_context, sample_coverage_statistics
    ):
        """Test list_coverage_statistics with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage_statistics.return_value = sample_coverage_statistics

        await tools.list_coverage_statistics(mock_context, region='ap-northeast-1')

        mock_get_client.assert_called_with('ap-northeast-1')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_statistics_error_handling(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_coverage_statistics error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_coverage_statistics.side_effect = Exception('Statistics error')

        with pytest.raises(Exception, match='Statistics error'):
            await tools.list_coverage_statistics(mock_context)

        mock_context.error.assert_called_once()


class TestGetAccountStatus:
    """Test the get_account_status tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_account_status(self):
        """Sample account status response."""
        return {
            'accounts': [
                {
                    'accountId': '123456789012',
                    'resourceState': {
                        'ec2': {'status': 'ENABLED'},
                        'ecr': {'status': 'ENABLED'},
                        'lambda': {'status': 'ENABLED'},
                    },
                    'state': {
                        'status': 'ENABLED',
                    },
                }
            ],
            'failedAccounts': [],
        }

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_account_status_basic(
        self, mock_get_client, tools, mock_context, sample_account_status
    ):
        """Test basic get_account_status functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_account_status.return_value = sample_account_status

        result = await tools.get_account_status(mock_context)

        assert len(result['accounts']) == 1
        assert result['accounts'][0]['account_id'] == '123456789012'
        assert result['failed_accounts'] == []

        mock_client.batch_get_account_status.assert_called_once_with()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_account_status_with_account_ids(
        self, mock_get_client, tools, mock_context, sample_account_status
    ):
        """Test get_account_status with specific account IDs."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_account_status.return_value = sample_account_status

        await tools.get_account_status(mock_context, account_ids=['123456789012', '987654321098'])

        mock_client.batch_get_account_status.assert_called_once_with(
            accountIds=['123456789012', '987654321098']
        )

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_account_status_with_failed_accounts(
        self, mock_get_client, tools, mock_context
    ):
        """Test get_account_status with failed account lookups."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_account_status.return_value = {
            'accounts': [],
            'failedAccounts': [
                {
                    'accountId': '111111111111',
                    'errorCode': 'ACCESS_DENIED',
                    'errorMessage': 'Access denied for account',
                }
            ],
        }

        result = await tools.get_account_status(mock_context, account_ids=['111111111111'])

        assert len(result['accounts']) == 0
        assert len(result['failed_accounts']) == 1
        assert result['failed_accounts'][0]['errorCode'] == 'ACCESS_DENIED'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_account_status_different_region(
        self, mock_get_client, tools, mock_context, sample_account_status
    ):
        """Test get_account_status with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_account_status.return_value = sample_account_status

        await tools.get_account_status(mock_context, region='eu-central-1')

        mock_get_client.assert_called_with('eu-central-1')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_get_account_status_error_handling(self, mock_get_client, tools, mock_context):
        """Test get_account_status error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.batch_get_account_status.side_effect = Exception('Account error')

        with pytest.raises(Exception, match='Account error'):
            await tools.get_account_status(mock_context)

        mock_context.error.assert_called_once()


class TestCreateFindingsReport:
    """Test the create_findings_report tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    @patch('time.sleep')
    async def test_create_findings_report_basic(
        self, mock_sleep, mock_get_client, tools, mock_context
    ):
        """Test basic create_findings_report functionality with polling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.create_findings_report.return_value = {
            'reportId': 'report-123',
        }
        mock_client.get_findings_report_status.return_value = {
            'status': 'SUCCEEDED',
        }

        result = await tools.create_findings_report(
            mock_context,
            s3_bucket_name='my-bucket',
            s3_key_prefix='reports/',
            kms_key_arn='arn:aws:kms:us-east-1:123:key/key-id',
        )

        assert result['report_id'] == 'report-123'
        assert result['status'] == 'SUCCEEDED'
        assert result['s3_destination']['bucketName'] == 'my-bucket'

        mock_client.create_findings_report.assert_called_once()
        mock_client.get_findings_report_status.assert_called()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_create_findings_report_no_polling(self, mock_get_client, tools, mock_context):
        """Test create_findings_report without polling for completion."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.create_findings_report.return_value = {
            'reportId': 'report-456',
        }

        result = await tools.create_findings_report(
            mock_context,
            s3_bucket_name='my-bucket',
            s3_key_prefix='reports/',
            kms_key_arn='arn:aws:kms:us-east-1:123:key/key-id',
            poll_for_completion=False,
        )

        assert result['report_id'] == 'report-456'
        assert result['status'] == 'IN_PROGRESS'

        mock_client.create_findings_report.assert_called_once()
        mock_client.get_findings_report_status.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    @patch('time.sleep')
    async def test_create_findings_report_with_filters(
        self, mock_sleep, mock_get_client, tools, mock_context
    ):
        """Test create_findings_report with severity and resource type filters."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.create_findings_report.return_value = {
            'reportId': 'report-789',
        }
        mock_client.get_findings_report_status.return_value = {
            'status': 'SUCCEEDED',
        }

        result = await tools.create_findings_report(
            mock_context,
            s3_bucket_name='my-bucket',
            s3_key_prefix='reports/',
            kms_key_arn='arn:aws:kms:us-east-1:123:key/key-id',
            severity='CRITICAL',
            resource_type='AWS_EC2_INSTANCE',
            report_format='CSV',
        )

        assert result['report_id'] == 'report-789'
        call_kwargs = mock_client.create_findings_report.call_args[1]
        assert call_kwargs['reportFormat'] == 'CSV'
        assert 'filterCriteria' in call_kwargs
        assert 'severity' in call_kwargs['filterCriteria']
        assert 'resourceType' in call_kwargs['filterCriteria']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    @patch('time.sleep')
    async def test_create_findings_report_failed(
        self, mock_sleep, mock_get_client, tools, mock_context
    ):
        """Test create_findings_report when report generation fails."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.create_findings_report.return_value = {
            'reportId': 'report-fail',
        }
        mock_client.get_findings_report_status.return_value = {
            'status': 'FAILED',
            'errorMessage': 'S3 bucket not accessible',
        }

        result = await tools.create_findings_report(
            mock_context,
            s3_bucket_name='bad-bucket',
            s3_key_prefix='reports/',
            kms_key_arn='arn:aws:kms:us-east-1:123:key/key-id',
        )

        assert result['report_id'] == 'report-fail'
        assert result['status'] == 'FAILED'
        assert result['error_message'] == 'S3 bucket not accessible'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    @patch('time.sleep')
    async def test_create_findings_report_timeout(
        self, mock_sleep, mock_get_client, tools, mock_context
    ):
        """Test create_findings_report when report generation times out."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.create_findings_report.return_value = {
            'reportId': 'report-timeout',
        }
        # Always return IN_PROGRESS to trigger timeout
        mock_client.get_findings_report_status.return_value = {
            'status': 'IN_PROGRESS',
        }

        result = await tools.create_findings_report(
            mock_context,
            s3_bucket_name='my-bucket',
            s3_key_prefix='reports/',
            kms_key_arn='arn:aws:kms:us-east-1:123:key/key-id',
        )

        assert result['report_id'] == 'report-timeout'
        assert result['status'] == 'IN_PROGRESS'
        # Verify polling occurred multiple times
        assert mock_client.get_findings_report_status.call_count > 1

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_create_findings_report_different_region(
        self, mock_get_client, tools, mock_context
    ):
        """Test create_findings_report with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.create_findings_report.return_value = {
            'reportId': 'report-region',
        }

        await tools.create_findings_report(
            mock_context,
            s3_bucket_name='my-bucket',
            s3_key_prefix='reports/',
            kms_key_arn='arn:aws:kms:eu-west-1:123:key/key-id',
            poll_for_completion=False,
            region='eu-west-1',
        )

        mock_get_client.assert_called_with('eu-west-1')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_create_findings_report_error_handling(
        self, mock_get_client, tools, mock_context
    ):
        """Test create_findings_report error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.create_findings_report.side_effect = Exception('Report creation error')

        with pytest.raises(Exception, match='Report creation error'):
            await tools.create_findings_report(
                mock_context,
                s3_bucket_name='my-bucket',
                s3_key_prefix='reports/',
                kms_key_arn='arn:aws:kms:us-east-1:123:key/key-id',
            )

        mock_context.error.assert_called_once()


class TestToolRegistration:
    """Test tool registration functionality."""

    def test_register_tools(self):
        """Test that all tools are registered with MCP server."""
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        tools = InspectorTools()
        tools.register(mock_mcp)

        expected_calls = [
            call(name='list_findings'),
            call(name='get_finding_details'),
            call(name='list_finding_aggregations'),
            call(name='list_coverage'),
            call(name='list_coverage_statistics'),
            call(name='get_account_status'),
            call(name='create_findings_report'),
            call(name='get_cve_details'),
            call(name='explain_finding'),
            call(name='generate_security_summary'),
            call(name='generate_findings_digest'),
        ]

        assert mock_mcp.tool.call_count == 11
        mock_mcp.tool.assert_has_calls(expected_calls, any_order=True)

        # Verify decorators were applied
        assert mock_tool_decorator.call_count == 11


class TestModels:
    """Test Pydantic models."""

    def test_finding_model(self):
        """Test Finding model creation and validation."""
        data = {
            'findingArn': 'arn:aws:inspector2:us-east-1:123:finding/f-1',
            'severity': 'HIGH',
            'status': 'ACTIVE',
            'title': 'CVE-2023-1234',
            'type': 'PACKAGE_VULNERABILITY',
            'inspectorScore': 8.5,
        }

        finding = Finding.model_validate(data)
        assert finding.finding_arn == data['findingArn']
        assert finding.severity == 'HIGH'
        assert finding.inspector_score == 8.5

        # Test exclude_none
        result_dict = finding.model_dump()
        assert 'description' not in result_dict
        assert 'network_reachability_details' not in result_dict

    def test_finding_model_with_snake_case(self):
        """Test Finding model with snake_case field names."""
        data = {
            'finding_arn': 'arn:aws:inspector2:us-east-1:123:finding/f-1',
            'severity': 'CRITICAL',
            'status': 'ACTIVE',
            'title': 'Test Finding',
        }

        finding = Finding.model_validate(data)
        assert finding.finding_arn == data['finding_arn']
        assert finding.severity == 'CRITICAL'

    def test_finding_detail_model(self):
        """Test FindingDetail model creation."""
        data = {
            'findingArn': 'arn:aws:inspector2:us-east-1:123:finding/f-1',
            'severity': 'HIGH',
            'title': 'CVE-2023-1234',
            'packageVulnerabilityDetails': {
                'vulnerabilityId': 'CVE-2023-1234',
                'cvss': [{'baseScore': 8.5}],
            },
        }

        detail = FindingDetail.model_validate(data)
        assert detail.package_vulnerability_details is not None
        assert detail.package_vulnerability_details['vulnerabilityId'] == 'CVE-2023-1234'

    def test_finding_aggregation_model(self):
        """Test FindingAggregation model creation."""
        aggregation = FindingAggregation(
            aggregation_type='SEVERITY',
            counts=[{'critical': 5, 'high': 20}],
        )

        assert aggregation.aggregation_type == 'SEVERITY'
        result_dict = aggregation.model_dump()
        assert 'next_token' not in result_dict

    def test_coverage_resource_model(self):
        """Test CoverageResource model with aliases."""
        data = {
            'accountId': '123456789012',
            'resourceId': 'i-1234567890',
            'resourceType': 'AWS_EC2_INSTANCE',
            'scanStatus': {'statusCode': 'ACTIVE', 'reason': 'SUCCESSFUL'},
            'scanType': 'PACKAGE',
        }

        resource = CoverageResource.model_validate(data)
        assert resource.account_id == '123456789012'
        assert resource.resource_type == 'AWS_EC2_INSTANCE'
        assert resource.scan_type == 'PACKAGE'

    def test_account_status_model(self):
        """Test AccountStatus model with aliases."""
        data = {
            'accountId': '123456789012',
            'state': {'status': 'ENABLED'},
            'resourceState': {
                'ec2': {'status': 'ENABLED'},
                'ecr': {'status': 'ENABLED'},
            },
        }

        status = AccountStatus.model_validate(data)
        assert status.account_id == '123456789012'
        assert status.state == {'status': 'ENABLED'}

    def test_report_result_model(self):
        """Test ReportResult model creation."""
        report = ReportResult(
            report_id='report-123',
            status='SUCCEEDED',
            report_format='JSON',
            s3_destination={'bucketName': 'my-bucket', 'keyPrefix': 'reports/'},
        )

        assert report.report_id == 'report-123'
        assert report.status == 'SUCCEEDED'

        result_dict = report.model_dump()
        assert 'error_message' not in result_dict
        assert 'filter_criteria' not in result_dict

    def test_finding_datetime_serialization(self):
        """Test Finding model datetime serialization."""
        data = {
            'findingArn': 'arn:aws:inspector2:us-east-1:123:finding/f-1',
            'firstObservedAt': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            'lastObservedAt': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        }

        finding = Finding.model_validate(data)
        result_dict = finding.model_dump()
        assert result_dict['first_observed_at'] == '2024-01-01T12:00:00+00:00'
        assert result_dict['last_observed_at'] == '2024-01-15T12:00:00+00:00'

    def test_cvss_metrics_model(self):
        """Test CvssMetrics model creation and exclude_none."""
        metrics = CvssMetrics(
            base_score=9.8,
            base_severity='CRITICAL',
            vector_string='CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
            attack_vector='NETWORK',
        )

        assert metrics.base_score == 9.8
        result_dict = metrics.model_dump()
        assert 'attack_complexity' not in result_dict
        assert result_dict['base_severity'] == 'CRITICAL'

    def test_cve_reference_model(self):
        """Test CveReference model creation."""
        ref = CveReference(
            url='https://example.com/advisory',
            source='example.com',
            tags=['Vendor Advisory'],
        )

        assert ref.url == 'https://example.com/advisory'
        result_dict = ref.model_dump()
        assert result_dict['tags'] == ['Vendor Advisory']

    def test_affected_version_model(self):
        """Test AffectedVersion model creation."""
        version = AffectedVersion(
            criteria='cpe:2.3:a:vendor:product:*:*:*:*:*:*:*:*',
            version_end_excluding='2.0.0',
        )

        assert version.version_end_excluding == '2.0.0'
        result_dict = version.model_dump()
        assert 'version_start_including' not in result_dict

    def test_cve_details_model(self):
        """Test CveDetails model creation."""
        details = CveDetails(
            cve_id='CVE-2023-1234',
            description='A test vulnerability',
            nvd_url='https://nvd.nist.gov/vuln/detail/CVE-2023-1234',
            cvss_v31=CvssMetrics(base_score=9.8, base_severity='CRITICAL'),
            weaknesses=['CWE-79'],
        )

        assert details.cve_id == 'CVE-2023-1234'
        result_dict = details.model_dump()
        assert result_dict['cvss_v31']['base_score'] == 9.8
        assert 'cvss_v2' not in result_dict

    def test_finding_explanation_model(self):
        """Test FindingExplanation model creation."""
        explanation = FindingExplanation(
            finding_arn='arn:aws:inspector2:us-east-1:123:finding/f-1',
            title='CVE-2023-1234',
            severity='HIGH',
            cve_ids=['CVE-2023-1234'],
            cve_links=['https://nvd.nist.gov/vuln/detail/CVE-2023-1234'],
        )

        assert explanation.finding_arn == 'arn:aws:inspector2:us-east-1:123:finding/f-1'
        result_dict = explanation.model_dump()
        assert 'description' not in result_dict
        assert result_dict['cve_ids'] == ['CVE-2023-1234']

    def test_security_summary_model(self):
        """Test SecuritySummary model creation."""
        summary = SecuritySummary(
            generated_at='2024-01-01T00:00:00+00:00',
            region='us-east-1',
            account_status={'accounts': []},
        )

        assert summary.region == 'us-east-1'
        result_dict = summary.model_dump()
        assert 'coverage_statistics' not in result_dict

    def test_digest_finding_model(self):
        """Test DigestFinding model creation."""
        digest_finding = DigestFinding(
            finding_arn='arn:aws:inspector2:us-east-1:123:finding/f-1',
            title='CVE-2023-1234',
            severity='HIGH',
            status='ACTIVE',
            cve_ids=['CVE-2023-1234'],
        )

        assert digest_finding.severity == 'HIGH'
        result_dict = digest_finding.model_dump()
        assert 'inspector_score' not in result_dict

    def test_findings_digest_model(self):
        """Test FindingsDigest model creation."""
        digest = FindingsDigest(
            generated_at='2024-01-01T00:00:00+00:00',
            region='us-east-1',
            time_range={'start_time': '2024-01-01T00:00:00Z', 'end_time': '2024-01-31T23:59:59Z'},
            total_findings=2,
            severity_breakdown={'HIGH': 1, 'MEDIUM': 1},
            findings=[
                DigestFinding(
                    finding_arn='arn:aws:inspector2:us-east-1:123:finding/f-1',
                    severity='HIGH',
                ),
            ],
        )

        assert digest.total_findings == 2
        result_dict = digest.model_dump()
        assert result_dict['severity_breakdown'] == {'HIGH': 1, 'MEDIUM': 1}
        assert len(result_dict['findings']) == 1


class TestFetchCveFromNvd:
    """Test the _fetch_cve_from_nvd private helper."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def sample_nvd_response(self):
        """Sample NVD API response for testing."""
        return {
            'vulnerabilities': [
                {
                    'cve': {
                        'id': 'CVE-2023-1234',
                        'published': '2023-03-15T10:00:00.000',
                        'lastModified': '2023-04-01T12:00:00.000',
                        'descriptions': [
                            {'lang': 'en', 'value': 'A critical vulnerability in test package'},
                            {'lang': 'es', 'value': 'Una vulnerabilidad critica'},
                        ],
                        'metrics': {
                            'cvssMetricV31': [
                                {
                                    'cvssData': {
                                        'baseScore': 9.8,
                                        'baseSeverity': 'CRITICAL',
                                        'vectorString': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
                                        'attackVector': 'NETWORK',
                                        'attackComplexity': 'LOW',
                                        'privilegesRequired': 'NONE',
                                        'userInteraction': 'NONE',
                                        'scope': 'UNCHANGED',
                                        'confidentialityImpact': 'HIGH',
                                        'integrityImpact': 'HIGH',
                                        'availabilityImpact': 'HIGH',
                                    },
                                    'exploitabilityScore': 3.9,
                                    'impactScore': 5.9,
                                }
                            ],
                        },
                        'weaknesses': [
                            {
                                'description': [
                                    {'lang': 'en', 'value': 'CWE-79'},
                                ]
                            }
                        ],
                        'configurations': [
                            {
                                'nodes': [
                                    {
                                        'cpeMatch': [
                                            {
                                                'criteria': 'cpe:2.3:a:vendor:product:*:*:*:*:*:*:*:*',
                                                'versionEndExcluding': '2.0.0',
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                        'references': [
                            {
                                'url': 'https://example.com/advisory/123',
                                'source': 'example.com',
                                'tags': ['Vendor Advisory'],
                            }
                        ],
                    }
                }
            ]
        }

    @pytest.mark.asyncio
    @patch('awslabs.inspector_mcp_server.tools.httpx.AsyncClient')
    async def test_fetch_basic(self, mock_client_class, tools, sample_nvd_response):
        """Test basic CVE fetch from NVD."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_nvd_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await tools._fetch_cve_from_nvd('CVE-2023-1234')

        assert result is not None
        assert result.cve_id == 'CVE-2023-1234'
        assert result.description == 'A critical vulnerability in test package'
        assert result.nvd_url == 'https://nvd.nist.gov/vuln/detail/CVE-2023-1234'
        assert result.cvss_v31 is not None
        assert result.cvss_v31.base_score == 9.8
        assert result.cvss_v31.base_severity == 'CRITICAL'
        assert result.cvss_v31.attack_vector == 'NETWORK'
        assert result.cvss_v31.exploitability_score == 3.9
        assert result.weaknesses == ['CWE-79']
        assert result.affected_versions is not None
        assert len(result.affected_versions) == 1
        assert result.affected_versions[0].version_end_excluding == '2.0.0'
        assert result.references is not None
        assert len(result.references) == 1
        assert result.references[0].url == 'https://example.com/advisory/123'

    @pytest.mark.asyncio
    @patch('awslabs.inspector_mcp_server.tools.httpx.AsyncClient')
    async def test_fetch_not_found(self, mock_client_class, tools):
        """Test CVE fetch when NVD returns 404."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            '404 Not Found', request=MagicMock(), response=MagicMock(status_code=404)
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await tools._fetch_cve_from_nvd('CVE-2099-99999')

        assert result is None

    @pytest.mark.asyncio
    @patch('awslabs.inspector_mcp_server.tools.httpx.AsyncClient')
    async def test_fetch_network_error(self, mock_client_class, tools):
        """Test CVE fetch with network error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError('Connection refused')
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await tools._fetch_cve_from_nvd('CVE-2023-1234')

        assert result is None

    @pytest.mark.asyncio
    @patch('awslabs.inspector_mcp_server.tools.httpx.AsyncClient')
    async def test_fetch_no_cvss_v31(self, mock_client_class, tools):
        """Test CVE fetch with only CVSS v2 metrics."""
        nvd_response = {
            'vulnerabilities': [
                {
                    'cve': {
                        'id': 'CVE-2020-1234',
                        'descriptions': [
                            {'lang': 'en', 'value': 'An old vulnerability'},
                        ],
                        'metrics': {
                            'cvssMetricV2': [
                                {
                                    'cvssData': {
                                        'baseScore': 7.5,
                                        'vectorString': 'AV:N/AC:L/Au:N/C:P/I:P/A:P',
                                        'accessVector': 'NETWORK',
                                        'accessComplexity': 'LOW',
                                    },
                                    'baseSeverity': 'HIGH',
                                    'exploitabilityScore': 10.0,
                                    'impactScore': 6.4,
                                }
                            ],
                        },
                        'weaknesses': [],
                        'references': [],
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = nvd_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await tools._fetch_cve_from_nvd('CVE-2020-1234')

        assert result is not None
        assert result.cvss_v31 is None
        assert result.cvss_v2 is not None
        assert result.cvss_v2.base_score == 7.5
        assert result.cvss_v2.base_severity == 'HIGH'
        assert result.cvss_v2.attack_vector == 'NETWORK'

    @pytest.mark.asyncio
    @patch('awslabs.inspector_mcp_server.tools.httpx.AsyncClient')
    async def test_fetch_minimal_response(self, mock_client_class, tools):
        """Test CVE fetch with minimal/sparse data."""
        nvd_response = {
            'vulnerabilities': [
                {
                    'cve': {
                        'id': 'CVE-2023-9999',
                        'descriptions': [],
                        'metrics': {},
                        'weaknesses': [],
                        'references': [],
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = nvd_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await tools._fetch_cve_from_nvd('CVE-2023-9999')

        assert result is not None
        assert result.cve_id == 'CVE-2023-9999'
        assert result.description is None
        assert result.cvss_v31 is None
        assert result.cvss_v2 is None
        assert result.weaknesses is None
        assert result.affected_versions is None
        assert result.references is None


class TestGetCveDetails:
    """Test the get_cve_details tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_fetch_cve_from_nvd')
    async def test_basic(self, mock_fetch, tools, mock_context):
        """Test basic get_cve_details functionality."""
        mock_fetch.return_value = CveDetails(
            cve_id='CVE-2023-1234',
            description='A test vulnerability',
            nvd_url='https://nvd.nist.gov/vuln/detail/CVE-2023-1234',
            cvss_v31=CvssMetrics(base_score=9.8, base_severity='CRITICAL'),
        )

        result = await tools.get_cve_details(mock_context, cve_id='CVE-2023-1234')

        assert result['cve_id'] == 'CVE-2023-1234'
        assert result['description'] == 'A test vulnerability'
        assert result['cvss_v31']['base_score'] == 9.8
        mock_fetch.assert_called_once_with('CVE-2023-1234')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_fetch_cve_from_nvd')
    async def test_not_found(self, mock_fetch, tools, mock_context):
        """Test get_cve_details when CVE is not found."""
        mock_fetch.return_value = None

        result = await tools.get_cve_details(mock_context, cve_id='CVE-2099-99999')

        assert 'error' in result
        assert 'not found' in result['error']

    @pytest.mark.asyncio
    async def test_invalid_cve_format(self, tools, mock_context):
        """Test get_cve_details with invalid CVE format."""
        result = await tools.get_cve_details(mock_context, cve_id='invalid-cve')

        assert 'error' in result
        assert 'Invalid CVE ID format' in result['error']

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_fetch_cve_from_nvd')
    async def test_error_handling(self, mock_fetch, tools, mock_context):
        """Test get_cve_details error handling."""
        mock_fetch.side_effect = Exception('Unexpected error')

        with pytest.raises(Exception, match='Unexpected error'):
            await tools.get_cve_details(mock_context, cve_id='CVE-2023-1234')

        mock_context.error.assert_called_once()


class TestExplainFinding:
    """Test the explain_finding tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_finding_with_cve(self):
        """Sample finding with package vulnerability details."""
        return {
            'finding': {
                'finding_arn': 'arn:aws:inspector2:us-east-1:123:finding/f-1',
                'title': 'CVE-2023-1234 - foo',
                'severity': 'HIGH',
                'description': 'CVE-2023-1234 in package foo',
                'type': 'PACKAGE_VULNERABILITY',
                'inspector_score': 8.5,
                'exploit_available': 'YES',
                'fix_available': 'YES',
                'remediation': {'recommendation': {'text': 'Update foo to 2.0.0'}},
                'resources': [{'type': 'AWS_EC2_INSTANCE', 'id': 'i-1234567890abcdef0'}],
                'package_vulnerability_details': {
                    'vulnerabilityId': 'CVE-2023-1234',
                    'relatedVulnerabilities': ['CVE-2023-5678'],
                },
            },
            'failed_findings': [],
        }

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_fetch_cve_from_nvd')
    @patch.object(InspectorTools, 'get_finding_details')
    async def test_basic(
        self, mock_get_finding, mock_fetch_cve, tools, mock_context, sample_finding_with_cve
    ):
        """Test basic explain_finding functionality."""
        mock_get_finding.return_value = sample_finding_with_cve
        mock_fetch_cve.return_value = CveDetails(
            cve_id='CVE-2023-1234',
            description='A critical vuln',
            nvd_url='https://nvd.nist.gov/vuln/detail/CVE-2023-1234',
        )

        finding_arn = 'arn:aws:inspector2:us-east-1:123:finding/f-1'
        result = await tools.explain_finding(mock_context, finding_arn=finding_arn)

        assert result['finding_arn'] == finding_arn
        assert result['title'] == 'CVE-2023-1234 - foo'
        assert result['severity'] == 'HIGH'
        assert result['resource_type'] == 'AWS_EC2_INSTANCE'
        assert result['resource_id'] == 'i-1234567890abcdef0'
        assert result['cve_details']['cve_id'] == 'CVE-2023-1234'
        assert result['cve_ids'] == ['CVE-2023-1234', 'CVE-2023-5678']
        assert len(result['cve_links']) == 2

        mock_get_finding.assert_called_once_with(
            mock_context, finding_arn=finding_arn, region='us-east-1'
        )
        mock_fetch_cve.assert_called_once_with('CVE-2023-1234')

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_fetch_cve_from_nvd')
    @patch.object(InspectorTools, 'get_finding_details')
    async def test_no_cve(self, mock_get_finding, mock_fetch_cve, tools, mock_context):
        """Test explain_finding for a non-package finding (no CVE)."""
        mock_get_finding.return_value = {
            'finding': {
                'finding_arn': 'arn:aws:inspector2:us-east-1:123:finding/f-2',
                'title': 'Port 22 reachable',
                'severity': 'MEDIUM',
                'type': 'NETWORK_REACHABILITY',
                'resources': [{'type': 'AWS_EC2_INSTANCE', 'id': 'i-abcdef'}],
            },
            'failed_findings': [],
        }

        result = await tools.explain_finding(
            mock_context,
            finding_arn='arn:aws:inspector2:us-east-1:123:finding/f-2',
        )

        assert result['title'] == 'Port 22 reachable'
        assert 'cve_details' not in result
        assert 'cve_ids' not in result
        mock_fetch_cve.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_fetch_cve_from_nvd')
    @patch.object(InspectorTools, 'get_finding_details')
    async def test_cve_lookup_fails(
        self, mock_get_finding, mock_fetch_cve, tools, mock_context, sample_finding_with_cve
    ):
        """Test explain_finding when CVE lookup fails."""
        mock_get_finding.return_value = sample_finding_with_cve
        mock_fetch_cve.return_value = None

        result = await tools.explain_finding(
            mock_context,
            finding_arn='arn:aws:inspector2:us-east-1:123:finding/f-1',
        )

        assert result['title'] == 'CVE-2023-1234 - foo'
        assert 'cve_details' not in result
        assert result['cve_ids'] == ['CVE-2023-1234', 'CVE-2023-5678']
        assert result['cve_links'] is not None

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'get_finding_details')
    async def test_finding_not_found(self, mock_get_finding, tools, mock_context):
        """Test explain_finding when finding is not found."""
        mock_get_finding.return_value = {
            'finding': None,
            'failed_findings': [{'findingArn': 'arn:missing', 'errorCode': 'FINDING_NOT_FOUND'}],
        }

        result = await tools.explain_finding(
            mock_context,
            finding_arn='arn:missing',
        )

        assert 'error' in result

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'get_finding_details')
    async def test_error_handling(self, mock_get_finding, tools, mock_context):
        """Test explain_finding error handling."""
        mock_get_finding.side_effect = Exception('API error')

        with pytest.raises(Exception, match='API error'):
            await tools.explain_finding(
                mock_context,
                finding_arn='arn:aws:inspector2:us-east-1:123:finding/f-1',
            )

        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_fetch_cve_from_nvd')
    @patch.object(InspectorTools, 'get_finding_details')
    async def test_region_passthrough(
        self, mock_get_finding, mock_fetch_cve, tools, mock_context, sample_finding_with_cve
    ):
        """Test explain_finding passes region to get_finding_details."""
        mock_get_finding.return_value = sample_finding_with_cve
        mock_fetch_cve.return_value = None

        await tools.explain_finding(
            mock_context,
            finding_arn='arn:aws:inspector2:eu-west-1:123:finding/f-1',
            region='eu-west-1',
        )

        mock_get_finding.assert_called_once_with(
            mock_context,
            finding_arn='arn:aws:inspector2:eu-west-1:123:finding/f-1',
            region='eu-west-1',
        )


class TestGenerateSecuritySummary:
    """Test the generate_security_summary tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    @patch.object(InspectorTools, 'list_finding_aggregations')
    @patch.object(InspectorTools, 'list_coverage_statistics')
    @patch.object(InspectorTools, 'get_account_status')
    async def test_basic(
        self,
        mock_account_status,
        mock_coverage_stats,
        mock_aggregations,
        mock_findings,
        tools,
        mock_context,
    ):
        """Test basic generate_security_summary functionality."""
        mock_account_status.return_value = {'accounts': [{'account_id': '123'}]}
        mock_coverage_stats.return_value = {'total_counts': 50}
        mock_aggregations.return_value = {'aggregation_type': 'SEVERITY', 'counts': []}
        mock_findings.return_value = {
            'findings': [{'title': 'Critical vuln', 'severity': 'CRITICAL'}]
        }

        result = await tools.generate_security_summary(mock_context)

        assert 'generated_at' in result
        assert result['region'] == 'us-east-1'
        assert result['account_status'] is not None
        assert result['coverage_statistics'] is not None
        assert result['finding_counts_by_severity'] is not None
        assert result['top_critical_findings'] is not None
        assert len(result['top_critical_findings']) == 1

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    @patch.object(InspectorTools, 'list_finding_aggregations')
    @patch.object(InspectorTools, 'list_coverage_statistics')
    @patch.object(InspectorTools, 'get_account_status')
    async def test_partial_failure(
        self,
        mock_account_status,
        mock_coverage_stats,
        mock_aggregations,
        mock_findings,
        tools,
        mock_context,
    ):
        """Test generate_security_summary with partial failures."""
        mock_account_status.return_value = {'accounts': [{'account_id': '123'}]}
        mock_coverage_stats.side_effect = Exception('Coverage error')
        mock_aggregations.return_value = {'aggregation_type': 'SEVERITY', 'counts': []}
        mock_findings.side_effect = Exception('Findings error')

        result = await tools.generate_security_summary(mock_context)

        assert result['account_status'] is not None
        assert 'coverage_statistics' not in result
        assert result['finding_counts_by_severity'] is not None
        assert 'top_critical_findings' not in result

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    @patch.object(InspectorTools, 'list_finding_aggregations')
    @patch.object(InspectorTools, 'list_coverage_statistics')
    @patch.object(InspectorTools, 'get_account_status')
    async def test_all_fail(
        self,
        mock_account_status,
        mock_coverage_stats,
        mock_aggregations,
        mock_findings,
        tools,
        mock_context,
    ):
        """Test generate_security_summary when all internal calls fail."""
        mock_account_status.side_effect = Exception('Account error')
        mock_coverage_stats.side_effect = Exception('Coverage error')
        mock_aggregations.side_effect = Exception('Aggregation error')
        mock_findings.side_effect = Exception('Findings error')

        result = await tools.generate_security_summary(mock_context)

        assert 'generated_at' in result
        assert result['region'] == 'us-east-1'
        assert 'account_status' not in result
        assert 'coverage_statistics' not in result
        assert 'finding_counts_by_severity' not in result
        assert 'top_critical_findings' not in result

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    @patch.object(InspectorTools, 'list_finding_aggregations')
    @patch.object(InspectorTools, 'list_coverage_statistics')
    @patch.object(InspectorTools, 'get_account_status')
    async def test_custom_top_count(
        self,
        mock_account_status,
        mock_coverage_stats,
        mock_aggregations,
        mock_findings,
        tools,
        mock_context,
    ):
        """Test generate_security_summary with custom top_critical_count."""
        mock_account_status.return_value = {'accounts': []}
        mock_coverage_stats.return_value = {'total_counts': 0}
        mock_aggregations.return_value = {'aggregation_type': 'SEVERITY', 'counts': []}
        mock_findings.return_value = {'findings': []}

        await tools.generate_security_summary(mock_context, top_critical_count=10)

        mock_findings.assert_called_once_with(
            mock_context, severity='CRITICAL', max_results=10, region='us-east-1'
        )

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    @patch.object(InspectorTools, 'list_finding_aggregations')
    @patch.object(InspectorTools, 'list_coverage_statistics')
    @patch.object(InspectorTools, 'get_account_status')
    async def test_region_passthrough(
        self,
        mock_account_status,
        mock_coverage_stats,
        mock_aggregations,
        mock_findings,
        tools,
        mock_context,
    ):
        """Test generate_security_summary passes region to all internal calls."""
        mock_account_status.return_value = {'accounts': []}
        mock_coverage_stats.return_value = {'total_counts': 0}
        mock_aggregations.return_value = {'aggregation_type': 'SEVERITY', 'counts': []}
        mock_findings.return_value = {'findings': []}

        await tools.generate_security_summary(mock_context, region='eu-west-1')

        mock_account_status.assert_called_once_with(mock_context, region='eu-west-1')
        mock_coverage_stats.assert_called_once_with(mock_context, region='eu-west-1')
        mock_aggregations.assert_called_once_with(
            mock_context, aggregation_type='SEVERITY', region='eu-west-1'
        )
        mock_findings.assert_called_once_with(
            mock_context, severity='CRITICAL', max_results=5, region='eu-west-1'
        )


class TestGenerateFindingsDigest:
    """Test the generate_findings_digest tool."""

    @pytest.fixture
    def tools(self):
        """Create InspectorTools instance."""
        return InspectorTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_findings_response(self):
        """Sample findings response for digest testing."""
        return {
            'findings': [
                {
                    'finding_arn': 'arn:aws:inspector2:us-east-1:123:finding/f-1',
                    'title': 'CVE-2023-1234 - foo',
                    'severity': 'CRITICAL',
                    'status': 'ACTIVE',
                    'type': 'PACKAGE_VULNERABILITY',
                    'inspector_score': 9.8,
                    'exploit_available': 'YES',
                    'fix_available': 'YES',
                    'resources': [{'type': 'AWS_EC2_INSTANCE', 'id': 'i-123'}],
                    'package_vulnerability_details': {
                        'vulnerabilityId': 'CVE-2023-1234',
                    },
                    'remediation': {'recommendation': {'text': 'Update foo'}},
                },
                {
                    'finding_arn': 'arn:aws:inspector2:us-east-1:123:finding/f-2',
                    'title': 'Port 22 open',
                    'severity': 'HIGH',
                    'status': 'ACTIVE',
                    'type': 'NETWORK_REACHABILITY',
                    'resources': [{'type': 'AWS_EC2_INSTANCE', 'id': 'i-456'}],
                },
            ],
        }

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    async def test_basic(self, mock_list_findings, tools, mock_context, sample_findings_response):
        """Test basic generate_findings_digest functionality."""
        mock_list_findings.return_value = sample_findings_response

        result = await tools.generate_findings_digest(
            mock_context,
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-31T23:59:59Z',
        )

        assert 'generated_at' in result
        assert result['region'] == 'us-east-1'
        assert result['time_range']['start_time'] == '2024-01-01T00:00:00Z'
        assert result['time_range']['end_time'] == '2024-01-31T23:59:59Z'
        assert result['total_findings'] == 2
        assert len(result['findings']) == 2
        assert result['findings'][0]['title'] == 'CVE-2023-1234 - foo'
        assert result['findings'][0]['cve_ids'] == ['CVE-2023-1234']
        assert result['findings'][0]['cve_links'] == [
            'https://nvd.nist.gov/vuln/detail/CVE-2023-1234'
        ]
        assert result['findings'][0]['resource_type'] == 'AWS_EC2_INSTANCE'
        assert result['findings'][1]['title'] == 'Port 22 open'
        assert 'cve_ids' not in result['findings'][1]

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    async def test_empty(self, mock_list_findings, tools, mock_context):
        """Test generate_findings_digest with no findings."""
        mock_list_findings.return_value = {'findings': []}

        result = await tools.generate_findings_digest(
            mock_context,
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-31T23:59:59Z',
        )

        assert result['total_findings'] == 0
        assert result['findings'] == []
        assert result['severity_breakdown'] == {}

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    async def test_severity_filter(self, mock_list_findings, tools, mock_context):
        """Test generate_findings_digest with severity filter."""
        mock_list_findings.return_value = {'findings': []}

        await tools.generate_findings_digest(
            mock_context,
            start_time='2024-01-01T00:00:00Z',
            severity='CRITICAL',
        )

        mock_list_findings.assert_called_once()
        call_kwargs = mock_list_findings.call_args[1]
        assert call_kwargs['severity'] == 'CRITICAL'

    @pytest.mark.asyncio
    @patch('awslabs.inspector_mcp_server.tools.datetime')
    @patch.object(InspectorTools, 'list_findings')
    async def test_default_end_time(self, mock_list_findings, mock_datetime, tools, mock_context):
        """Test generate_findings_digest defaults end_time to now."""
        fixed_now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_list_findings.return_value = {'findings': []}

        await tools.generate_findings_digest(
            mock_context,
            start_time='2024-01-01T00:00:00Z',
        )

        call_kwargs = mock_list_findings.call_args[1]
        assert call_kwargs['end_time'] == fixed_now.isoformat()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    async def test_severity_breakdown(
        self, mock_list_findings, tools, mock_context, sample_findings_response
    ):
        """Test generate_findings_digest severity breakdown counts."""
        mock_list_findings.return_value = sample_findings_response

        result = await tools.generate_findings_digest(
            mock_context,
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-31T23:59:59Z',
        )

        assert result['severity_breakdown'] == {'CRITICAL': 1, 'HIGH': 1}

    @pytest.mark.asyncio
    @patch.object(InspectorTools, 'list_findings')
    async def test_error_handling(self, mock_list_findings, tools, mock_context):
        """Test generate_findings_digest error handling."""
        mock_list_findings.side_effect = Exception('API error')

        with pytest.raises(Exception, match='API error'):
            await tools.generate_findings_digest(
                mock_context,
                start_time='2024-01-01T00:00:00Z',
            )

        mock_context.error.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])
