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
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
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
            None,  # max_results
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
            None,  # max_results
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
            None,  # max_results
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert 'Feedback' in call_kwargs
        assert call_kwargs['Feedback'] == 'YES'

    async def test_get_anomalies_with_max_results(self, mock_context, mock_ce_client):
        """Test get_anomalies with max_results parameter."""
        # Setup
        start_date = '2023-01-01'
        end_date = '2023-01-31'
        max_results = 50

        # Execute
        await get_anomalies(
            mock_context,
            mock_ce_client,
            start_date,
            end_date,
            None,  # monitor_arn
            None,  # feedback
            max_results,
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
            None,  # max_results
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
            None,  # max_results
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
            None,  # max_results
            None,  # total_impact_operator
            None,  # total_impact_start
            None,  # total_impact_end
        )

        # Assert
        assert mock_ce_client.get_anomalies.call_count == 2
        assert len(result['data']['anomalies']) == 2

        # Check second call includes NextPageToken
        second_call_kwargs = mock_ce_client.get_anomalies.call_args_list[1][1]
        assert 'NextPageToken' in second_call_kwargs
        assert second_call_kwargs['NextPageToken'] == 'page2token'

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
            None,  # max_results
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

    async def test_ca_real_future_end_date(self, mock_context):
        """Test cost_anomaly with future end_date."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with patch.object(ca_mod, 'get_context_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            from datetime import datetime, timedelta

            future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

            res = await real_fn(mock_context, start_date='2023-01-01', end_date=future_date)  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert 'Cannot request anomalies for future dates' in res['message']

    async def test_ca_real_old_start_date_warning(self, mock_context):
        """Test cost_anomaly with start_date more than 90 days old triggers warning."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch.object(ca_mod, 'create_aws_client') as mock_create_client,
            patch.object(ca_mod, 'get_anomalies', new_callable=AsyncMock) as mock_get_anomalies,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_create_client.return_value = mock_client
            mock_get_anomalies.return_value = {'status': 'success', 'data': {'anomalies': []}}

            from datetime import datetime, timedelta

            old_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
            recent_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

            res = await real_fn(mock_context, start_date=old_date, end_date=recent_date)  # type: ignore[reportCallIssue]
            assert res['status'] == 'success'
            # Check that warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert '90-day data retention' in warning_call

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

    async def test_ca_real_client_error_2024_data(self, mock_context):
        """Test cost_anomaly ClientError with 2024 data issue."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch.object(ca_mod, 'create_aws_client') as mock_create_client,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            from botocore.exceptions import ClientError

            error = ClientError(
                error_response={
                    'Error': {
                        'Code': 'ValidationException',
                        'Message': 'Invalid date range for 2024 data',
                    }
                },
                operation_name='GetAnomalies',
            )
            mock_create_client.side_effect = error

            res = await real_fn(mock_context, start_date='2024-01-01', end_date='2024-01-31')  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert '2024 data' in res['message']
            assert '24-48 hours in the past' in res['message']

    async def test_ca_real_client_error_validation(self, mock_context):
        """Test cost_anomaly ClientError with general validation exception."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch.object(ca_mod, 'create_aws_client') as mock_create_client,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger

            from botocore.exceptions import ClientError

            error = ClientError(
                error_response={
                    'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameters'}
                },
                operation_name='GetAnomalies',
            )
            mock_create_client.side_effect = error

            res = await real_fn(mock_context, start_date='2023-01-01', end_date='2023-01-31')  # type: ignore[reportCallIssue]
            assert res['status'] == 'error'
            assert 'validation error' in res['message']

    async def test_ca_real_successful_call(self, mock_context):
        """Test cost_anomaly successful call."""
        ca_mod = _reload_cost_anomaly_with_identity_decorator()
        real_fn = ca_mod.cost_anomaly

        with (
            patch.object(ca_mod, 'get_context_logger') as mock_get_logger,
            patch.object(ca_mod, 'create_aws_client') as mock_create_client,
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
                max_results=50,
                total_impact_operator='GREATER_THAN',
                total_impact_start=100.0,
            )
            assert res['status'] == 'success'
            mock_get_anomalies.assert_called_once()


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
        max_results = 25
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
            max_results,
            total_impact_operator,
            total_impact_start,
            total_impact_end,
        )

        # Assert
        call_kwargs = mock_ce_client.get_anomalies.call_args[1]
        assert call_kwargs['MonitorArn'] == monitor_arn
        assert call_kwargs['Feedback'] == feedback
        assert call_kwargs['MaxResults'] == max_results
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
        )

        # Assert minimal formatting
        assert result['status'] == 'success'
        anomaly = result['data']['anomalies'][0]
        assert anomaly['id'] == 'anomaly-minimal'
        assert 'score' not in anomaly
        assert 'impact' not in anomaly
        assert 'root_causes' not in anomaly
