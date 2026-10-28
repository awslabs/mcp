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

"""Unit tests for the cost_anomaly_tools module.

These tests verify the functionality of AWS Cost Anomaly Detection tools, including:
- Retrieving cost anomalies with impact analysis and root cause identification
- Getting anomaly detectors configuration and monitoring settings
- Fetching anomaly subscriptions and notification preferences
- Handling date range filtering and severity thresholds for anomaly detection
- Error handling for missing subscriptions and invalid detector configurations
"""

import fastmcp
import importlib
import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools import (
    cost_anomaly_server,
    get_anomalies,
)
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import date, datetime, timezone
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    context.warning = AsyncMock()
    context.debug = AsyncMock()
    return context


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    mock_client = MagicMock()

    # Set up mock response for get_anomalies
    mock_client.get_anomalies.return_value = {
        'Anomalies': [
            {
                'AnomalyId': 'anomaly-123',
                'AnomalyStartDate': '2023-01-01',
                'AnomalyEndDate': '2023-01-03',
                'DimensionValue': 'Amazon EC2',
                'MonitorArn': 'arn:aws:ce::123456789012:anomalymonitor/monitor-1',
                'Feedback': None,
                'AnomalyScore': {
                    'CurrentScore': 90.0,
                    'MaxScore': 100.0,
                },
                'Impact': {
                    'TotalImpact': 250.0,
                    'TotalImpactPercentage': 35.0,
                    'MaxImpact': 100.0,
                    'TotalActualSpend': 1000.0,
                    'TotalExpectedSpend': 750.0,
                },
                'RootCauses': [
                    {
                        'Service': 'Amazon EC2',
                        'Region': 'us-east-1',
                        'LinkedAccount': '123456789012',
                        'LinkedAccountName': 'Development',
                        'UsageType': 'BoxUsage',
                        'Impact': {
                            'Contribution': 75.0,
                        },
                    },
                    {
                        'Service': 'Amazon EC2',
                        'Region': 'us-west-2',
                        'LinkedAccount': '123456789012',
                        'LinkedAccountName': 'Development',
                        'UsageType': 'BoxUsage',
                        'Impact': {
                            'Contribution': 25.0,
                        },
                    },
                ],
            },
            {
                'AnomalyId': 'anomaly-456',
                'AnomalyStartDate': '2023-01-05',
                'AnomalyEndDate': '2023-01-06',
                'DimensionValue': 'Amazon S3',
                'MonitorArn': 'arn:aws:ce::123456789012:anomalymonitor/monitor-2',
                'Feedback': 'YES',
                'AnomalyScore': {
                    'CurrentScore': 85.0,
                    'MaxScore': 100.0,
                },
                'Impact': {
                    'TotalImpact': 150.0,
                    'TotalImpactPercentage': 25.0,
                    'MaxImpact': 80.0,
                    'TotalActualSpend': 750.0,
                    'TotalExpectedSpend': 600.0,
                },
                'RootCauses': [
                    {
                        'Service': 'Amazon S3',
                        'Region': 'us-east-1',
                        'LinkedAccount': '123456789012',
                        'LinkedAccountName': 'Production',
                        'UsageType': 'DataTransfer-Out-Bytes',
                        'Impact': {
                            'Contribution': 100.0,
                        },
                    },
                ],
            },
        ],
        'NextPageToken': None,
    }

    return mock_client


@pytest.mark.asyncio
class TestGetAnomalies:
    """Tests for get_anomalies function."""

    async def test_get_anomalies_basic(self, mock_context, mock_ce_client):
        """Test get_anomalies with basic parameters."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'

        # Execute
        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            None,  # feedback
            None,  # max_items
            None,  # next_token
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        mock_ce_client.get_anomalies.assert_called_once()
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]

        assert 'DateInterval' in call_kwargs
        assert call_kwargs['DateInterval']['StartDate'] == '2023-01-01'
        assert call_kwargs['DateInterval']['EndDate'] == '2023-01-31'

        assert result['status'] == 'success'
        assert 'anomalies' in result['data']
        assert len(result['data']['anomalies']) == 2

    async def test_get_anomalies_with_monitor_arn(self, mock_context, mock_ce_client):
        """Test get_anomalies with monitor_arn parameter."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'
        monitor_arn = 'arn:aws:ce::123456789012:anomalymonitor/test-monitor'

        # Execute
        await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            monitor_arn,
            None,  # feedback
            None,  # max_items
            None,  # next_token
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert 'MonitorArn' in call_kwargs
        assert call_kwargs['MonitorArn'] == monitor_arn

    async def test_get_anomalies_with_feedback(self, mock_context, mock_ce_client):
        """Test get_anomalies with feedback parameter."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'
        feedback = 'YES'

        # Execute
        await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            feedback,
            None,  # max_items
            None,  # next_token
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert 'Feedback' in call_kwargs
        assert call_kwargs['Feedback'] == 'YES'

    async def test_get_anomalies_with_max_items(self, mock_context, mock_ce_client):
        """max_items below the page maximum sets the page size."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'
        max_items = 50

        # Execute
        await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            None,  # feedback
            max_items,
            None,  # next_token
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert 'MaxResults' in call_kwargs
        assert call_kwargs['MaxResults'] == 50

    async def test_get_anomalies_with_total_impact_filter(self, mock_context, mock_ce_client):
        """Test get_anomalies with total impact filter parameters."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'
        total_impact_operator = 'GREATER_THAN'
        total_impact_start = 100.0

        # Execute
        await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            None,  # feedback
            None,  # max_items
            None,  # next_token
            total_impact_operator,
            total_impact_start,
            None,  # total_impact_end
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert 'TotalImpact' in call_kwargs
        assert call_kwargs['TotalImpact']['NumericOperator'] == 'GREATER_THAN'
        assert call_kwargs['TotalImpact']['StartValue'] == 100.0

    async def test_get_anomalies_with_between_operator(self, mock_context, mock_ce_client):
        """Test get_anomalies with BETWEEN operator for total impact."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'
        total_impact_operator = 'BETWEEN'
        total_impact_start = 100.0
        total_impact_end = 500.0

        # Execute
        await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            None,  # feedback
            None,  # max_items
            None,  # next_token
            total_impact_operator,
            total_impact_start,
            total_impact_end,
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert 'TotalImpact' in call_kwargs
        assert call_kwargs['TotalImpact']['NumericOperator'] == 'BETWEEN'
        assert call_kwargs['TotalImpact']['StartValue'] == 100.0
        assert call_kwargs['TotalImpact']['EndValue'] == 500.0

    async def test_get_anomalies_with_pagination(self, mock_context, mock_ce_client):
        """Test get_anomalies handles pagination correctly."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'

        # Set up multi-page response
        mock_ce_client.get_anomalies.side_effect = [
            {
                'Anomalies': [{'AnomalyId': 'anomaly-1'}],
                'NextPageToken': 'page2token',
            },
            {
                'Anomalies': [{'AnomalyId': 'anomaly-2'}],
                'NextPageToken': None,
            },
        ]

        # Execute
        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            None,  # feedback
            None,  # max_items
            None,  # next_token
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        assert mock_ce_client.get_anomalies.call_count == 2
        assert len(result['data']['anomalies']) == 2

        # Every page requests the largest page size; the second call adds the token.
        calls = [c.kwargs for c in mock_ce_client.get_anomalies.call_args_list]
        assert calls[0]['MaxResults'] == 10000
        assert 'NextPageToken' not in calls[0]
        assert calls[1] == {**calls[0], 'NextPageToken': 'page2token'}
        assert 'complete_dataset' not in result['data']
        assert result['data']['pagination']['complete_dataset'] is True
        assert result['data']['pagination']['items_returned'] == 2

    async def test_get_anomalies_short_page_with_token_keeps_paging(
        self, mock_context, mock_ce_client
    ):
        """A short or empty page that carries a token does not end paging."""
        mock_ce_client.get_anomalies.side_effect = [
            {'Anomalies': [], 'NextPageToken': 't1'},
            {'Anomalies': [{'AnomalyId': 'a1'}]},
        ]

        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,
            None,
            5,
            None,
            None,
            None,
            None,
        )

        assert mock_ce_client.get_anomalies.call_count == 2
        assert [a['id'] for a in result['data']['anomalies']] == ['a1']
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_get_anomalies_max_items_stops_with_token(self, mock_context, mock_ce_client):
        """max_items stops before the next page could exceed it and returns the token."""
        mock_ce_client.get_anomalies.side_effect = [
            {'Anomalies': [{'AnomalyId': 'a1'}, {'AnomalyId': 'a2'}], 'NextPageToken': 't1'},
        ]

        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,
            None,
            2,
            None,
            None,
            None,
            None,
        )

        mock_ce_client.get_anomalies.assert_called_once()
        assert mock_ce_client.get_anomalies.call_args.kwargs['MaxResults'] == 2
        data = result['data']
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 't1',
            'items_returned': 2,
        }

    async def test_get_anomalies_continuation_sends_caller_token(
        self, mock_context, mock_ce_client
    ):
        """A continuation sends the caller's token and otherwise identical params."""
        monitor = 'arn:aws:ce::123456789012:anomalymonitor/m'
        await get_anomalies(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            monitor,
            'YES',
            2,
            'caller-token',
            None,
            None,
            None,
        )

        mock_ce_client.get_anomalies.assert_called_once_with(
            DateInterval={'StartDate': '2023-01-01', 'EndDate': '2023-01-31'},
            MonitorArn=monitor,
            Feedback='YES',
            MaxResults=2,
            NextPageToken='caller-token',
        )

    async def test_get_anomalies_invalid_next_token(self, mock_context, mock_ce_client):
        """A rejected caller token maps to invalid_next_token."""
        from botocore.exceptions import ClientError

        mock_ce_client.get_anomalies.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'expired'}},
            'GetAnomalies',
        )

        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,
            None,
            None,
            'stale',
            None,
            None,
            None,
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    async def test_get_anomalies_empty_next_token_tells_caller_to_omit_it(
        self, mock_context, mock_ce_client
    ):
        """An empty next_token fails before any request, with guidance to omit it."""
        from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
            add_retry_guidance,
        )

        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,
            None,
            None,
            '',
            None,
            None,
            None,
        )

        mock_ce_client.get_anomalies.assert_not_called()
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert 'Omit it to start from the first page' in result['message']
        assert add_retry_guidance(result)['retry_strategy'] == 'modify_request'

    @patch('awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools.handle_aws_error')
    async def test_get_anomalies_error_handling(
        self, mock_handle_aws_error, mock_context, mock_ce_client
    ):
        """Test get_anomalies error handling."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'

        error = Exception('API error')
        mock_ce_client.get_anomalies.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            None,  # feedback
            None,  # max_items
            None,  # next_token
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_anomalies', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


def test_cost_anomaly_server_initialization():
    """Test that the cost_anomaly_server is properly initialized."""
    # Verify the server name
    assert cost_anomaly_server.name == 'cost-anomaly-tools'

    # Verify the server instructions
    assert cost_anomaly_server.instructions and (
        'Tools for working with AWS Cost Anomaly Detection API' in cost_anomaly_server.instructions
    )


@pytest.mark.asyncio
async def test_description_documents_end_date_matching():
    """The description says the range matches end_date, so earlier-starting anomalies are kept."""
    tool = await cost_anomaly_server.get_tool('cost-anomaly')
    assert tool is not None
    description = ' '.join((tool.description or '').split())

    assert 'its end_date (the last day it was detected)' in description
    assert (
        'began before the range and was still being detected inside it is in range' in description
    )
    assert 'do not drop results whose start_date is before the range' in description


def _assert_validation_error(res):
    """Local validation failures carry a top-level classification."""
    assert res['error_type'] == 'validation_error'
    assert res['operation'] == 'cost_anomaly'
    assert res['service'] == 'Cost Explorer'


@pytest.fixture(scope='module', autouse=True)
def _restore_real_tool_module():
    """Reload the module with the real FastMCP.tool after this file's tests.

    _reload_cost_anomaly_with_identity_decorator() leaves the module's server with no registered tools;
    restoring it keeps later test files from seeing that state.
    """
    yield
    from awslabs.billing_cost_management_mcp_server.tools import cost_anomaly_tools as module

    importlib.reload(module)


def _reload_cost_anomaly_with_identity_decorator():
    """Reload cost_anomaly_tools with FastMCP.tool patched to return the original function unchanged (identity decorator).

    This exposes a callable 'cost_anomaly' we can invoke directly to cover routing branches.
    """
    from awslabs.billing_cost_management_mcp_server.tools import cost_anomaly_tools as ca_mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(ca_mod)
        return ca_mod


@pytest.mark.asyncio
class TestCostAnomalyFastMCP:
    """Test the actual FastMCP-wrapped cost_anomaly function directly."""

    async def test_ca_real_invalid_start_date_format(self, mock_context):
        """Test cost_anomaly with invalid start_date format."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly  # type: ignore[reportCallIssue]

        with patch.object(ca_mod, 'get_context_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            res = await real_fn(mock_context, start_date='invalid-date', end_date='2023-01-31')  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert 'Invalid start_date format' in res['message']
            assert res['data']['invalid_parameter'] == 'start_date'
            _assert_validation_error(res)

    async def test_ca_real_invalid_end_date_format(self, mock_context):
        """Test cost_anomaly with invalid end_date format."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with patch.object(ca_mod, 'get_context_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            res = await real_fn(mock_context, start_date='2023-01-01', end_date='bad-date')  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert 'Invalid end_date format' in res['message']
            assert res['data']['invalid_parameter'] == 'end_date'
            _assert_validation_error(res)

    async def test_ca_real_start_date_after_end_date(self, mock_context):
        """Test cost_anomaly with start_date after end_date."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with patch.object(ca_mod, 'get_context_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            res = await real_fn(mock_context, start_date='2023-01-31', end_date='2023-01-01')  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert 'start_date must be before or equal to end_date' in res['message']
            _assert_validation_error(res)

    async def test_ca_real_current_year_early_january_warning(self, mock_context):
        """Test cost_anomaly with current year data in early January triggers warning."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch.object(ca_mod, 'create_aws_client') as mock_create_client,
            patch.object(ca_mod, 'get_anomalies', new_callable=AsyncMock) as mock_get_anomalies,
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools.datetime'
            ) as mock_datetime,
        ):
            # Mock datetime to simulate early January
            from datetime import datetime

            mock_now = datetime(2024, 1, 5)  # January 5th
            mock_datetime.now.return_value = mock_now
            mock_datetime.strptime.side_effect = datetime.strptime

            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_create_client.return_value = mock_client
            mock_get_anomalies.return_value = {'status': 'success', 'data': {'anomalies': []}}

            res = await real_fn(mock_context, start_date='2024-01-01', end_date='2024-01-03')  # type: ignore[reportCallIssue]
            assert res['status'] == 'success'
            # Check that warning was logged
            mock_logger.warning.assert_called()
            warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
            assert any(
                'early January may return incomplete results' in warning
                for warning in warning_calls
            )

    async def test_ca_real_invalid_feedback(self, mock_context):
        """Test cost_anomaly with invalid feedback parameter."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with patch.object(ca_mod, 'get_context_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context,
                start_date='2023-01-01',
                end_date='2023-01-31',
                feedback='INVALID_FEEDBACK',
            )
            assert res['status'] == 'error'
            assert 'Invalid feedback value' in res['message']
            assert res['data']['invalid_parameter'] == 'feedback'
            _assert_validation_error(res)

    async def test_ca_real_invalid_total_impact_operator(self, mock_context):
        """Test cost_anomaly with invalid total_impact_operator."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with patch.object(ca_mod, 'get_context_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context,
                start_date='2023-01-01',
                end_date='2023-01-31',
                total_impact_operator='INVALID_OPERATOR',
            )
            assert res['status'] == 'error'
            assert 'Invalid total_impact_operator' in res['message']
            _assert_validation_error(res)

    async def test_ca_real_between_operator_missing_end_value(self, mock_context):
        """Test cost_anomaly with BETWEEN operator missing total_impact_end."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with patch.object(ca_mod, 'get_context_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context,
                start_date='2023-01-01',
                end_date='2023-01-31',
                total_impact_operator='BETWEEN',
                total_impact_start=100.0,
                # Missing total_impact_end
            )
            assert res['status'] == 'error'
            assert (
                'both total_impact_start and total_impact_end must be provided' in res['message']
            )
            _assert_validation_error(res)

    async def test_ca_real_value_error_handling(self, mock_context):
        """Test cost_anomaly ValueError handling."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools.datetime'
            ) as mock_datetime,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            # Make datetime.strptime raise ValueError
            mock_datetime.strptime.side_effect = ValueError('Invalid date format')

            res = await real_fn(mock_context, start_date='2023-01-01', end_date='2023-01-31')  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert 'Date validation error' in res['message']
            _assert_validation_error(res)

    @pytest.mark.parametrize(
        'code,message',
        [
            ('ValidationException', 'Invalid date range for 2024 data'),
            ('AccessDeniedException', 'not authorized'),
        ],
    )
    async def test_ca_real_service_error_returns_error_envelope(self, mock_context, code, message):
        """A service error from GetAnomalies comes back as an error response, not an exception."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch.object(ca_mod, 'create_aws_client') as mock_create_client,
            patch.object(ca_mod, '_utc_today', return_value=date(2024, 2, 1)),
        ):
            mock_get_logger.return_value = AsyncMock()

            from botocore.exceptions import ClientError

            mock_create_client.return_value.get_anomalies.side_effect = ClientError(
                error_response={'Error': {'Code': code, 'Message': message}},
                operation_name='GetAnomalies',
            )

            res = await real_fn(mock_context, start_date='2024-01-01', end_date='2024-01-31')  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert res['error_type'] == code
            assert message in res['message']

    @pytest.mark.parametrize(
        'error,error_type,message',
        [
            (
                ClientError(
                    {'Error': {'Code': 'AccessDeniedException', 'Message': 'not authorized'}},
                    'GetAnomalies',
                ),
                'AccessDeniedException',
                'not authorized',
            ),
            (NoCredentialsError(), 'aws_connection_error', 'NoCredentialsError'),
            (RuntimeError('boom'), 'unknown_runtimeerror', 'boom'),
        ],
        ids=['client-error', 'no-credentials', 'unexpected'],
    )
    async def test_ca_real_client_creation_error_returns_error_envelope(
        self, mock_context, error, error_type, message
    ):
        """An error creating the CE client is returned as cost_anomaly's error response."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger', return_value=AsyncMock()),
            patch.object(ca_mod, 'create_aws_client', side_effect=error) as create,
            patch.object(ca_mod, 'get_anomalies', new_callable=AsyncMock) as mock_get_anomalies,
            patch.object(ca_mod, '_utc_today', return_value=date(2024, 2, 1)),
        ):
            res = await real_fn(mock_context, start_date='2024-01-01', end_date='2024-01-31')  # type: ignore[reportCallIssue]

        create.assert_called_once_with('ce', region_name='us-east-1')
        mock_get_anomalies.assert_not_called()
        assert res['status'] == 'error'
        assert res['error_type'] == error_type
        assert message in res['message']
        assert res['operation'] == 'cost_anomaly'
        assert res['service'] == 'Cost Explorer'

    async def test_ca_real_successful_call(self, mock_context):
        """Test cost_anomaly successful call."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch.object(ca_mod, 'create_aws_client') as mock_create_client,
            patch.object(ca_mod, '_utc_today', return_value=date(2023, 2, 1)),
            patch.object(ca_mod, 'get_anomalies', new_callable=AsyncMock) as mock_get_anomalies,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_create_client.return_value = mock_client
            mock_get_anomalies.return_value = {'status': 'success', 'data': {'anomalies': []}}

            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context,
                start_date='2023-01-01',
                end_date='2023-01-31',
                monitor_arn='arn:aws:ce::123456789012:anomalymonitor/test',
                feedback='YES',
                max_items=50,
                next_token='tok',
                total_impact_operator='GREATER_THAN',
                total_impact_start=100.0,
            )
            assert res['status'] == 'success'
            mock_get_anomalies.assert_called_once()
            assert mock_get_anomalies.call_args.args[6:8] == (50, 'tok')


async def _call_with_today(mock_context, today, **kwargs):
    """Call the real cost_anomaly with UTC today pinned and a mocked CE client.

    Returns (response, client) so a test can read the DateInterval actually sent.
    """
    ca_mod = _reload_cost_anomaly_with_identity_decorator()
    mock_client = MagicMock()
    mock_client.get_anomalies.return_value = {'Anomalies': []}
    with (
        patch.object(ca_mod, 'get_context_logger', return_value=AsyncMock()),
        patch.object(ca_mod, 'create_aws_client', return_value=mock_client) as create,
        patch.object(ca_mod, '_utc_today', return_value=today),
    ):
        res = await ca_mod.cost_anomaly(mock_context, **kwargs)  # type: ignore[reportCallIssue]
    return res, mock_client, create


@pytest.mark.asyncio
class TestDateWindow:
    """GetAnomalies serves only UTC today minus 90 days through today; the tool limits to that."""

    TODAY = date(2026, 10, 28)

    async def test_start_before_window_is_limited(self, mock_context):
        """A start_date older than 90 days is moved to the window start, and the response says so."""
        res, client, _ = await _call_with_today(
            mock_context, self.TODAY, start_date='2026-06-30', end_date='2026-10-27'
        )
        assert res['status'] == 'success'
        assert client.get_anomalies.call_args.kwargs['DateInterval'] == {
            'StartDate': '2026-07-30',
            'EndDate': '2026-10-27',
        }
        assert res['data']['time_range'] == {
            'start_date': '2026-07-30',
            'end_date': '2026-10-27',
            'limited_from_request': True,
            'requested_start_date': '2026-06-30',
            'requested_end_date': '2026-10-27',
            'max_lookback_days': 90,
        }

    async def test_future_end_is_limited_to_today(self, mock_context):
        """An end_date after today (for example tomorrow) is limited to today, not rejected."""
        res, client, _ = await _call_with_today(
            mock_context, self.TODAY, start_date='2026-10-21', end_date='2026-10-29'
        )
        assert res['status'] == 'success'
        assert client.get_anomalies.call_args.kwargs['DateInterval']['EndDate'] == '2026-10-28'
        assert res['data']['time_range']['end_date'] == '2026-10-28'
        assert res['data']['time_range']['requested_end_date'] == '2026-10-29'
        assert res['data']['time_range']['limited_from_request'] is True

    async def test_window_edges_pass_unchanged(self, mock_context):
        """Both edges (today - 90 and today) are served, so a range on them is not limited."""
        res, client, _ = await _call_with_today(
            mock_context, self.TODAY, start_date='2026-07-30', end_date='2026-10-28'
        )
        assert res['status'] == 'success'
        assert client.get_anomalies.call_args.kwargs['DateInterval'] == {
            'StartDate': '2026-07-30',
            'EndDate': '2026-10-28',
        }
        assert res['data']['time_range']['limited_from_request'] is False

    @pytest.mark.parametrize(
        'start_date,end_date,sent_start,sent_end',
        [
            ('2026-06-01', '2026-07-30', '2026-07-30', '2026-07-30'),  # ends on the first day
            ('2026-10-28', '2026-10-30', '2026-10-28', '2026-10-28'),  # starts on today
            ('2026-06-01', '2026-11-15', '2026-07-30', '2026-10-28'),  # both ends limited
        ],
    )
    async def test_range_touching_window_is_limited_not_rejected(
        self, mock_context, start_date, end_date, sent_start, sent_end
    ):
        """A range sharing even one day with the window is limited to it, not rejected."""
        res, client, _ = await _call_with_today(
            mock_context, self.TODAY, start_date=start_date, end_date=end_date
        )
        assert res['status'] == 'success'
        assert client.get_anomalies.call_args.kwargs['DateInterval'] == {
            'StartDate': sent_start,
            'EndDate': sent_end,
        }
        assert res['data']['time_range']['limited_from_request'] is True

    async def test_time_range_precedes_anomalies(self, mock_context):
        """time_range sits ahead of the anomaly list, so a trimmed result still carries it."""
        res, _, _ = await _call_with_today(
            mock_context, self.TODAY, start_date='2026-10-01', end_date='2026-10-27'
        )
        keys = list(res['data'])
        assert keys.index('time_range') < keys.index('anomalies')

    @pytest.mark.parametrize(
        'start_date,end_date',
        [
            ('2026-06-01', '2026-07-29'),  # ends the day before the window opens
            ('2026-10-29', '2026-10-30'),  # starts after today
        ],
    )
    async def test_range_outside_window_is_rejected(self, mock_context, start_date, end_date):
        """A range with no day inside the window is a local error that states the window."""
        res, _, create = await _call_with_today(
            mock_context, self.TODAY, start_date=start_date, end_date=end_date
        )
        assert res['status'] == 'error'
        _assert_validation_error(res)
        assert '2026-07-30 to 2026-10-28' in res['message']
        assert res['data'] == {
            'start_date': start_date,
            'end_date': end_date,
            'earliest_start_date': '2026-07-30',
            'latest_end_date': '2026-10-28',
        }
        create.assert_not_called()

    async def test_today_is_utc_not_local(self, mock_context):
        """Today is the UTC date the service uses, not the host's local date.

        At 01:00 UTC on 2026-10-29 a host at UTC-7 still reads 2026-10-28; the service already
        serves 2026-10-29, so an end_date of 2026-10-29 is in range.
        """
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        utc_now = datetime(2026, 10, 29, 1, 0, tzinfo=timezone.utc)
        local_now = datetime(2026, 10, 28, 18, 0)
        mock_client = MagicMock()
        mock_client.get_anomalies.return_value = {'Anomalies': []}
        with (
            patch.object(ca_mod, 'get_context_logger', return_value=AsyncMock()),
            patch.object(ca_mod, 'create_aws_client', return_value=mock_client),
            patch.object(ca_mod, 'datetime') as mock_datetime,
        ):
            mock_datetime.now.side_effect = (
                lambda tz=None: utc_now if tz is not None else local_now
            )
            mock_datetime.strptime.side_effect = datetime.strptime
            res = await ca_mod.cost_anomaly(  # type: ignore[reportCallIssue]
                mock_context, start_date='2026-10-22', end_date='2026-10-29'
            )
        assert res['status'] == 'success'
        assert (
            mock_client.get_anomalies.call_args.kwargs['DateInterval']['EndDate'] == '2026-10-29'
        )
        assert res['data']['time_range']['limited_from_request'] is False


@pytest.mark.asyncio
async def test_description_documents_window_and_total_impact():
    """The description states the date window, the time_range check, total impact and unknown ARNs."""
    tool = await cost_anomaly_server.get_tool('cost-anomaly')
    assert tool is not None
    description = ' '.join((tool.description or '').split())

    assert 'today minus 90 days through today (UTC)' in description
    assert 'anomalies that ended earlier cannot be retrieved' in description
    assert 'With next_token, pass the same start_date and end_date' in description
    assert 'when limited_from_request is true' in description
    assert 'returns a validation_error that states the window' in description
    assert 'impact.total_impact is in dollars: actual spend minus expected spend' in description
    assert 'BETWEEN includes both bounds' in description
    assert 'Every comparison uses the unrounded value (responses round it to cents)' in description
    assert 'so EQUAL rarely matches' in description
    assert 'EQUAL is an exact match on the unrounded value' not in description
    assert 'matches no monitor returns an empty list, not an error' in description


@pytest.mark.asyncio
class TestGetAnomaliesAdditional:
    """Additional tests for get_anomalies function to improve coverage."""

    async def test_get_anomalies_with_all_parameters(self, mock_context, mock_ce_client):
        """Test get_anomalies with all optional parameters."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'
        monitor_arn = 'arn:aws:ce::123456789012:anomalymonitor/test-monitor'
        feedback = 'YES'
        max_items = 25
        total_impact_operator = 'BETWEEN'
        total_impact_start = 100.0
        total_impact_end = 500.0

        # Execute
        await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            monitor_arn,
            feedback,
            max_items,
            None,  # next_token
            total_impact_operator,
            total_impact_start,
            total_impact_end,
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert call_kwargs['MonitorArn'] == monitor_arn
        assert call_kwargs['Feedback'] == feedback
        assert call_kwargs['MaxResults'] == max_items
        assert call_kwargs['TotalImpact']['NumericOperator'] == 'BETWEEN'
        assert call_kwargs['TotalImpact']['StartValue'] == 100.0
        assert call_kwargs['TotalImpact']['EndValue'] == 500.0

    async def test_get_anomalies_formatting_with_all_fields(self, mock_context, mock_ce_client):
        """Test get_anomalies response formatting with all possible fields."""
        # Setup - create comprehensive anomaly data
        mock_ce_client.get_anomalies.return_value = {
            'Anomalies': [
                {
                    'AnomalyId': 'anomaly-complete',
                    'AnomalyStartDate': '2023-01-01',
                    'AnomalyEndDate': '2023-01-03',
                    'DimensionValue': 'Amazon EC2',
                    'MonitorArn': 'arn:aws:ce::123456789012:anomalymonitor/monitor-1',
                    'Feedback': 'YES',
                    'AnomalyScore': {
                        'CurrentScore': 95.5,
                        'MaxScore': 100.0,
                    },
                    'Impact': {
                        'TotalImpact': 250.75,
                        'TotalImpactPercentage': 35.2,
                        'MaxImpact': 100.5,
                        'TotalActualSpend': 1000.25,
                        'TotalExpectedSpend': 750.50,
                    },
                    'RootCauses': [
                        {
                            'Service': 'Amazon EC2',
                            'Region': 'us-east-1',
                            'LinkedAccount': '123456789012',
                            'LinkedAccountName': 'Development',
                            'UsageType': 'BoxUsage',
                            'Impact': {
                                'Contribution': 75.25,
                            },
                        }
                    ],
                }
            ],
            'NextPageToken': None,
        }

        # Execute
        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        # Assert comprehensive formatting
        assert result['status'] == 'success'
        anomaly = result['data']['anomalies'][0]
        assert anomaly['id'] == 'anomaly-complete'
        assert anomaly['score']['current'] == 95.5
        assert anomaly['impact']['total_impact'] == 250.75
        assert len(anomaly['root_causes']) == 1
        assert anomaly['root_causes'][0]['contribution'] == 75.25

    async def test_get_anomalies_no_optional_fields(self, mock_context, mock_ce_client):
        """Test get_anomalies with minimal anomaly data (no optional fields)."""
        # Setup - minimal anomaly data
        mock_ce_client.get_anomalies.return_value = {
            'Anomalies': [
                {
                    'AnomalyId': 'anomaly-minimal',
                    'AnomalyStartDate': '2023-01-01',
                    'AnomalyEndDate': '2023-01-02',
                    'DimensionValue': 'Amazon S3',
                    'MonitorArn': 'arn:aws:ce::123456789012:anomalymonitor/monitor-2',
                    'Feedback': None,
                    # Missing AnomalyScore, Impact, RootCauses
                }
            ],
            'NextPageToken': None,
        }

        # Execute
        result = await get_anomalies(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        # Assert minimal formatting
        assert result['status'] == 'success'
        anomaly = result['data']['anomalies'][0]
        assert anomaly['id'] == 'anomaly-minimal'
        assert 'score' not in anomaly
        assert 'impact' not in anomaly
        assert 'root_causes' not in anomaly


async def _call_cost_anomaly_capturing_request(mock_context, **kwargs):
    """Call the real cost_anomaly with a mocked CE client; return (response, client)."""
    ca_mod = _reload_cost_anomaly_with_identity_decorator()
    mock_client = MagicMock()
    mock_client.get_anomalies.return_value = {'Anomalies': []}
    with (
        patch.object(ca_mod, 'get_context_logger', return_value=AsyncMock()),
        patch.object(ca_mod, 'create_aws_client', return_value=mock_client),
        patch.object(ca_mod, '_utc_today', return_value=date(2023, 2, 1)),
    ):
        res = await ca_mod.cost_anomaly(  # type: ignore[reportCallIssue]
            mock_context, start_date='2023-01-01', end_date='2023-01-31', **kwargs
        )
    return res, mock_client


@pytest.mark.asyncio
class TestTotalImpactFilter:
    """total_impact_* arguments must reach the API or be rejected, never be dropped."""

    @pytest.mark.parametrize(
        'kwargs,expected',
        [
            (
                {'total_impact_start': 1000.0},
                {'NumericOperator': 'GREATER_THAN_OR_EQUAL', 'StartValue': 1000.0},
            ),
            (
                {'total_impact_start': 0.0},
                {'NumericOperator': 'GREATER_THAN_OR_EQUAL', 'StartValue': 0.0},
            ),
            (
                {'total_impact_start': 100.0, 'total_impact_end': 500.0},
                {'NumericOperator': 'BETWEEN', 'StartValue': 100.0, 'EndValue': 500.0},
            ),
            (
                {'total_impact_start': 0.0, 'total_impact_end': 0.0},
                {'NumericOperator': 'BETWEEN', 'StartValue': 0.0, 'EndValue': 0.0},
            ),
            (
                {'total_impact_operator': '', 'total_impact_start': 10.0},
                {'NumericOperator': 'GREATER_THAN_OR_EQUAL', 'StartValue': 10.0},
            ),
            (
                {'total_impact_operator': 'GREATER_THAN', 'total_impact_start': 200.0},
                {'NumericOperator': 'GREATER_THAN', 'StartValue': 200.0},
            ),
            (
                {
                    'total_impact_operator': 'BETWEEN',
                    'total_impact_start': 100.0,
                    'total_impact_end': 500.0,
                },
                {'NumericOperator': 'BETWEEN', 'StartValue': 100.0, 'EndValue': 500.0},
            ),
        ],
    )
    async def test_filter_sent(self, mock_context, kwargs, expected):
        """A start value without an operator defaults the operator instead of being dropped."""
        res, client = await _call_cost_anomaly_capturing_request(mock_context, **kwargs)
        assert res['status'] == 'success'
        assert client.get_anomalies.call_args.kwargs['TotalImpact'] == expected

    async def test_no_filter_sends_no_total_impact(self, mock_context):
        """No total_impact_* arguments sends no TotalImpact."""
        res, client = await _call_cost_anomaly_capturing_request(mock_context)
        assert res['status'] == 'success'
        assert 'TotalImpact' not in client.get_anomalies.call_args.kwargs

    @pytest.mark.parametrize(
        'kwargs,parameter,text',
        [
            (
                {'total_impact_operator': 'GREATER_THAN'},
                'total_impact_start',
                'total_impact_operator needs total_impact_start',
            ),
            (
                {'total_impact_operator': 'LESS_THAN', 'total_impact_end': 50.0},
                'total_impact_start',
                'total_impact_end is only used with BETWEEN',
            ),
            (
                {'total_impact_operator': 'BETWEEN', 'total_impact_end': 50.0},
                'total_impact_start',
                'total_impact_operator needs total_impact_start',
            ),
            (
                {'total_impact_end': 50.0},
                'total_impact_start',
                "total_impact_operator='LESS_THAN_OR_EQUAL' and total_impact_start=50.0",
            ),
            (
                {'total_impact_end': 0.0},
                'total_impact_start',
                'total_impact_end needs total_impact_start',
            ),
            (
                {
                    'total_impact_operator': 'GREATER_THAN',
                    'total_impact_start': 100.0,
                    'total_impact_end': 500.0,
                },
                'total_impact_end',
                'total_impact_end is only used with BETWEEN',
            ),
        ],
    )
    async def test_rejected_locally(self, mock_context, kwargs, parameter, text):
        """Incomplete or ignored total impact arguments fail before any API call."""
        res, client = await _call_cost_anomaly_capturing_request(mock_context, **kwargs)
        assert res['status'] == 'error'
        _assert_validation_error(res)
        assert res['data']['invalid_parameter'] == parameter
        assert text in res['message']
        client.get_anomalies.assert_not_called()
