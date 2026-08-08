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

"""Test cases for the check_health_checks tool."""

import importlib
import pytest
from datetime import datetime, timezone
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, call, patch


hc_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.route53.check_health_checks'
)


class TestCheckHealthChecks:
    """Test cases for check_health_checks function."""

    @pytest.fixture
    def sample_health_checks(self):
        """Sample health checks fixture."""
        return [
            {
                'Id': 'hc-http-1',
                'HealthCheckConfig': {
                    'Type': 'HTTP',
                    'IPAddress': '1.2.3.4',
                    'Port': 80,
                    'ResourcePath': '/health',
                    'RequestInterval': 30,
                    'FailureThreshold': 3,
                },
            },
            {
                'Id': 'hc-calc-1',
                'HealthCheckConfig': {
                    'Type': 'CALCULATED',
                    'RequestInterval': 30,
                    'FailureThreshold': 3,
                },
            },
        ]

    @pytest.fixture
    def sample_status_response(self):
        """Sample GetHealthCheckStatus response."""
        return {
            'HealthCheckObservations': [
                {
                    'Region': 'us-east-1',
                    'IPAddress': '10.0.0.1',
                    'StatusReport': {'Status': 'Success: HTTP Status Code 200'},
                },
                {
                    'Region': 'eu-west-1',
                    'IPAddress': '10.0.0.2',
                    'StatusReport': {'Status': 'Success: HTTP Status Code 200'},
                },
            ]
        }

    @patch.object(hc_module, 'get_aws_client')
    async def test_check_single_health_check(
        self, mock_get_client, sample_health_checks, sample_status_response
    ):
        """Test checking a single specific health check."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HealthChecks': sample_health_checks}]
        mock_r53.get_health_check_status.return_value = sample_status_response

        result = await hc_module.check_health_checks(health_check_id='hc-http-1')

        assert result['count'] == 1
        assert result['health_checks'][0]['id'] == 'hc-http-1'
        assert result['health_checks'][0]['status'] == 'healthy'
        assert len(result['health_checks'][0]['checker_results']) == 2

    @patch.object(hc_module, 'get_aws_client')
    async def test_check_all_health_checks_under_threshold(
        self, mock_get_client, sample_health_checks, sample_status_response
    ):
        """Test listing all HCs when count is under rate-limit threshold."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HealthChecks': sample_health_checks}]
        mock_r53.get_health_check_status.return_value = sample_status_response

        # CloudWatch for calculated HC
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Timestamp': datetime(2025, 1, 1, tzinfo=timezone.utc), 'Average': 1.0}
            ]
        }

        result = await hc_module.check_health_checks()

        assert result['count'] == 2
        assert result['status_retrieval_note'] is None
        # Non-calculated HC should have status from GetHealthCheckStatus
        http_hc = next(h for h in result['health_checks'] if h['id'] == 'hc-http-1')
        assert http_hc['status'] == 'healthy'
        # Calculated HC should have status from CloudWatch
        calc_hc = next(h for h in result['health_checks'] if h['id'] == 'hc-calc-1')
        assert calc_hc['status'] == 'healthy'

    @patch.object(hc_module, 'get_aws_client')
    async def test_calculated_hc_cloudwatch_fallback(self, mock_get_client):
        """Test calculated health check uses CloudWatch for status."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        calc_hc = {
            'Id': 'hc-calc-1',
            'HealthCheckConfig': {
                'Type': 'CALCULATED',
                'RequestInterval': 30,
                'FailureThreshold': 3,
            },
        }
        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HealthChecks': [calc_hc]}]

        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Timestamp': datetime(2025, 1, 1, tzinfo=timezone.utc), 'Average': 0.0}
            ]
        }

        result = await hc_module.check_health_checks(health_check_id='hc-calc-1')

        assert result['health_checks'][0]['status'] == 'unhealthy'
        # Verify CloudWatch was called with correct params
        mock_cw.get_metric_statistics.assert_called_once()
        cw_call = mock_cw.get_metric_statistics.call_args
        assert cw_call[1]['Namespace'] == 'AWS/Route53'
        assert cw_call[1]['MetricName'] == 'HealthCheckStatus'

    @patch.object(hc_module, 'get_aws_client')
    async def test_rate_limit_threshold_skips_status(self, mock_get_client):
        """Test that status retrieval is skipped when count > 20."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        # Create 21 non-calculated health checks
        many_hcs = [
            {
                'Id': f'hc-{i}',
                'HealthCheckConfig': {
                    'Type': 'HTTP',
                    'IPAddress': f'1.2.3.{i}',
                    'Port': 80,
                    'RequestInterval': 30,
                    'FailureThreshold': 3,
                },
            }
            for i in range(21)
        ]
        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HealthChecks': many_hcs}]

        result = await hc_module.check_health_checks()

        assert result['count'] == 21
        assert result['status_retrieval_note'] is not None
        assert 'exceeds threshold' in result['status_retrieval_note']
        # GetHealthCheckStatus should NOT have been called
        mock_r53.get_health_check_status.assert_not_called()
        # All should have 'unknown' status
        for hc in result['health_checks']:
            assert hc['status'] == 'unknown'

    @patch.object(hc_module, 'get_aws_client')
    async def test_status_filter_healthy(self, mock_get_client, sample_health_checks):
        """Test filtering by healthy status."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HealthChecks': sample_health_checks}]
        mock_r53.get_health_check_status.return_value = {
            'HealthCheckObservations': [
                {
                    'Region': 'us-east-1',
                    'IPAddress': '10.0.0.1',
                    'StatusReport': {'Status': 'Failure'},
                },
            ]
        }
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Timestamp': datetime(2025, 1, 1, tzinfo=timezone.utc), 'Average': 1.0}
            ]
        }

        result = await hc_module.check_health_checks(status_filter='healthy')

        # Only the calculated HC (healthy via CW) should be returned
        assert result['count'] == 1
        assert result['health_checks'][0]['id'] == 'hc-calc-1'

    async def test_check_health_checks_invalid_status_filter(self):
        """Test invalid status_filter validation."""
        with pytest.raises(ToolError, match='Invalid status_filter "bad"'):
            await hc_module.check_health_checks(status_filter='bad')

    @patch.object(hc_module, 'get_aws_client')
    async def test_cloudwatch_client_uses_us_east_1(self, mock_get_client):
        """CRITICAL: Verify CloudWatch client is created with us-east-1."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HealthChecks': []}]

        await hc_module.check_health_checks()

        # Verify the two get_aws_client calls
        calls = mock_get_client.call_args_list
        assert calls[0] == call('route53', None, None)
        assert calls[1] == call('cloudwatch', 'us-east-1', None)

    @patch.object(hc_module, 'get_aws_client')
    async def test_check_health_checks_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error checking health checks.*AccessDenied'):
            await hc_module.check_health_checks()

    @patch.object(hc_module, 'get_aws_client')
    async def test_single_hc_not_found(self, mock_get_client):
        """Test health check not found error."""
        mock_r53 = MagicMock()
        mock_cw = MagicMock()
        mock_get_client.side_effect = [mock_r53, mock_cw]

        mock_paginator = MagicMock()
        mock_r53.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HealthChecks': []}]

        with pytest.raises(ToolError, match='not found'):
            await hc_module.check_health_checks(health_check_id='hc-nonexistent')
