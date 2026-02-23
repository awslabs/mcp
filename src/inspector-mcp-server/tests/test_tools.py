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

import pytest
from awslabs.inspector_mcp_server.models import (
    AccountStatus,
    CoverageResource,
    Finding,
    FindingAggregation,
    FindingDetail,
    ReportResult,
)
from awslabs.inspector_mcp_server.tools import InspectorTools
from datetime import datetime, timezone
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, Mock, call, patch


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

        result = await tools.list_findings(
            mock_context, resource_type='AWS_EC2_INSTANCE'
        )

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

        result = await tools.list_findings(
            mock_context, finding_type='NETWORK_REACHABILITY'
        )

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

        result = await tools.list_findings(
            mock_context, next_token='previous-token-123'
        )

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
    async def test_list_findings_max_results_boundary(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_findings max_results boundary conditions."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': []}

        test_cases = [
            (None, 10),   # Default
            (1, 1),       # Minimum
            (100, 100),   # Maximum
            (0, 1),       # Below minimum
            (200, 100),   # Above maximum
        ]

        for input_val, expected_val in test_cases:
            await tools.list_findings(mock_context, max_results=input_val)
            call_kwargs = mock_client.list_findings.call_args[1]
            assert call_kwargs['maxResults'] == expected_val

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_empty_results(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_findings with empty results."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.return_value = {'findings': []}

        result = await tools.list_findings(mock_context)

        assert len(result['findings']) == 0
        assert result['next_token'] is None

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_error_handling(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_findings error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_findings.side_effect = Exception('AWS Error')

        with pytest.raises(Exception, match='AWS Error'):
            await tools.list_findings(mock_context)

        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_findings_with_all_filters(
        self, mock_get_client, tools, mock_context
    ):
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
    async def test_get_finding_details_not_found(
        self, mock_get_client, tools, mock_context
    ):
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
    async def test_get_finding_details_error_handling(
        self, mock_get_client, tools, mock_context
    ):
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

        result = await tools.list_finding_aggregations(
            mock_context, aggregation_type='SEVERITY'
        )

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

        result = await tools.list_finding_aggregations(
            mock_context, aggregation_type='ACCOUNT_ID'
        )

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
            await tools.list_finding_aggregations(
                mock_context, aggregation_type='SEVERITY'
            )

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

        result = await tools.list_coverage(
            mock_context, resource_type='AWS_EC2_INSTANCE'
        )

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

        result = await tools.list_coverage(
            mock_context, next_token='prev-cov-token'
        )

        assert result['next_token'] == 'new-cov-token'
        call_kwargs = mock_client.list_coverage.call_args[1]
        assert call_kwargs['nextToken'] == 'prev-cov-token'

    @pytest.mark.asyncio
    @patch.object(InspectorTools, '_get_inspector_client')
    async def test_list_coverage_empty_results(
        self, mock_get_client, tools, mock_context
    ):
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
    async def test_list_coverage_error_handling(
        self, mock_get_client, tools, mock_context
    ):
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

        await tools.list_coverage_statistics(
            mock_context, group_by='RESOURCE_TYPE'
        )

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

        await tools.list_coverage_statistics(
            mock_context, resource_type='AWS_EC2_INSTANCE'
        )

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

        await tools.list_coverage_statistics(
            mock_context, region='ap-northeast-1'
        )

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

        await tools.get_account_status(
            mock_context, account_ids=['123456789012', '987654321098']
        )

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

        result = await tools.get_account_status(
            mock_context, account_ids=['111111111111']
        )

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
    async def test_get_account_status_error_handling(
        self, mock_get_client, tools, mock_context
    ):
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
    async def test_create_findings_report_no_polling(
        self, mock_get_client, tools, mock_context
    ):
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
        ]

        assert mock_mcp.tool.call_count == 7
        mock_mcp.tool.assert_has_calls(expected_calls, any_order=True)

        # Verify decorators were applied
        assert mock_tool_decorator.call_count == 7


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


if __name__ == '__main__':
    pytest.main([__file__])
