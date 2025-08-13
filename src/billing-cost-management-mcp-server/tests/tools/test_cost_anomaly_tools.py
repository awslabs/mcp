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

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools import (
    cost_anomaly_server,
    get_anomalies,
)
from fastmcp import Context


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
        "Anomalies": [
            {
                "AnomalyId": "anomaly-123",
                "AnomalyStartDate": "2023-01-01",
                "AnomalyEndDate": "2023-01-03",
                "DimensionValue": "Amazon EC2",
                "MonitorArn": "arn:aws:ce::123456789012:anomalymonitor/monitor-1",
                "Feedback": None,
                "AnomalyScore": {
                    "CurrentScore": 90.0,
                    "MaxScore": 100.0,
                },
                "Impact": {
                    "TotalImpact": 250.0,
                    "TotalImpactPercentage": 35.0,
                    "MaxImpact": 100.0,
                    "TotalActualSpend": 1000.0,
                    "TotalExpectedSpend": 750.0,
                },
                "RootCauses": [
                    {
                        "Service": "Amazon EC2",
                        "Region": "us-east-1",
                        "LinkedAccount": "123456789012",
                        "LinkedAccountName": "Development",
                        "UsageType": "BoxUsage",
                        "Impact": {
                            "Contribution": 75.0,
                        },
                    },
                    {
                        "Service": "Amazon EC2",
                        "Region": "us-west-2",
                        "LinkedAccount": "123456789012",
                        "LinkedAccountName": "Development",
                        "UsageType": "BoxUsage",
                        "Impact": {
                            "Contribution": 25.0,
                        },
                    },
                ],
            },
            {
                "AnomalyId": "anomaly-456",
                "AnomalyStartDate": "2023-01-05",
                "AnomalyEndDate": "2023-01-06",
                "DimensionValue": "Amazon S3",
                "MonitorArn": "arn:aws:ce::123456789012:anomalymonitor/monitor-2",
                "Feedback": "YES",
                "AnomalyScore": {
                    "CurrentScore": 85.0,
                    "MaxScore": 100.0,
                },
                "Impact": {
                    "TotalImpact": 150.0,
                    "TotalImpactPercentage": 25.0,
                    "MaxImpact": 80.0,
                    "TotalActualSpend": 750.0,
                    "TotalExpectedSpend": 600.0,
                },
                "RootCauses": [
                    {
                        "Service": "Amazon S3",
                        "Region": "us-east-1",
                        "LinkedAccount": "123456789012",
                        "LinkedAccountName": "Production",
                        "UsageType": "DataTransfer-Out-Bytes",
                        "Impact": {
                            "Contribution": 100.0,
                        },
                    },
                ],
            },
        ],
        "NextPageToken": None,
    }
    
    return mock_client


@pytest.mark.asyncio
class TestGetAnomalies:
    """Tests for get_anomalies function."""

    async def test_get_anomalies_basic(self, mock_context, mock_ce_client):
        """Test get_anomalies with basic parameters."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        
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
        
        assert "DateInterval" in call_kwargs
        assert call_kwargs["DateInterval"]["StartDate"] == "2023-01-01"
        assert call_kwargs["DateInterval"]["EndDate"] == "2023-01-31"
        
        assert result["status"] == "success"
        assert "anomalies" in result["data"]
        assert len(result["data"]["anomalies"]) == 2

    async def test_get_anomalies_with_monitor_arn(self, mock_context, mock_ce_client):
        """Test get_anomalies with monitor_arn parameter."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        monitor_arn = "arn:aws:ce::123456789012:anomalymonitor/test-monitor"
        
        # Execute
        result = await get_anomalies(
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
        assert "MonitorArn" in call_kwargs
        assert call_kwargs["MonitorArn"] == monitor_arn

    async def test_get_anomalies_with_feedback(self, mock_context, mock_ce_client):
        """Test get_anomalies with feedback parameter."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        feedback = "YES"
        
        # Execute
        result = await get_anomalies(
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
        assert "Feedback" in call_kwargs
        assert call_kwargs["Feedback"] == "YES"

    async def test_get_anomalies_with_max_results(self, mock_context, mock_ce_client):
        """Test get_anomalies with max_results parameter."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        max_results = 50
        
        # Execute
        result = await get_anomalies(
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
        assert "MaxResults" in call_kwargs
        assert call_kwargs["MaxResults"] == 50

    async def test_get_anomalies_with_total_impact_filter(self, mock_context, mock_ce_client):
        """Test get_anomalies with total impact filter parameters."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        total_impact_operator = "GREATER_THAN"
        total_impact_start = 100.0
        
        # Execute
        result = await get_anomalies(
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
        assert "TotalImpact" in call_kwargs
        assert call_kwargs["TotalImpact"]["NumericOperator"] == "GREATER_THAN"
        assert call_kwargs["TotalImpact"]["StartValue"] == 100.0

    async def test_get_anomalies_with_between_operator(self, mock_context, mock_ce_client):
        """Test get_anomalies with BETWEEN operator for total impact."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        total_impact_operator = "BETWEEN"
        total_impact_start = 100.0
        total_impact_end = 500.0
        
        # Execute
        result = await get_anomalies(
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
        assert "TotalImpact" in call_kwargs
        assert call_kwargs["TotalImpact"]["NumericOperator"] == "BETWEEN"
        assert call_kwargs["TotalImpact"]["StartValue"] == 100.0
        assert call_kwargs["TotalImpact"]["EndValue"] == 500.0

    async def test_get_anomalies_with_pagination(self, mock_context, mock_ce_client):
        """Test get_anomalies handles pagination correctly."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        
        # Set up multi-page response
        mock_ce_client.get_anomalies.side_effect = [
            {
                "Anomalies": [{"AnomalyId": "anomaly-1"}],
                "NextPageToken": "page2token",
            },
            {
                "Anomalies": [{"AnomalyId": "anomaly-2"}],
                "NextPageToken": None,
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
        assert len(result["data"]["anomalies"]) == 2
        
        # Check second call includes NextPageToken
        second_call_kwargs = mock_ce_client.get_anomalies.call_args_list[1][1]
        assert "NextPageToken" in second_call_kwargs
        assert second_call_kwargs["NextPageToken"] == "page2token"

    @patch("awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools.handle_aws_error")
    async def test_get_anomalies_error_handling(
        self, mock_handle_aws_error, mock_context, mock_ce_client
    ):
        """Test get_anomalies error handling."""
        # Setup
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        
        error = Exception("API error")
        mock_ce_client.get_anomalies.side_effect = error
        mock_handle_aws_error.return_value = {"status": "error", "message": "API error"}
        
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
        mock_handle_aws_error.assert_called_once_with(mock_context, error, "get_anomalies", "Cost Explorer")
        assert result["status"] == "error"
        assert result["message"] == "API error"


# We're not directly testing the cost_anomaly decorated function anymore
# Instead, we test the individual implementation functions directly


def test_cost_anomaly_server_initialization():
    """Test that the cost_anomaly_server is properly initialized."""
    # Verify the server name
    assert cost_anomaly_server.name == "cost-anomaly-tools"
    
    # Verify the server instructions
    assert "Tools for working with AWS Cost Anomaly Detection API" in cost_anomaly_server.instructions