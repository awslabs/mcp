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

"""Tests for cross-account CloudWatch tools."""

import pytest
from awslabs.cross_account_cloudwatch_mcp_server.config import (
    CloudWatchConfig,
    ConfigNotProvidedError,
)
from awslabs.cross_account_cloudwatch_mcp_server.tools import CrossAccountCloudWatchTools
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def tools():
    """Create tools instance."""
    return CrossAccountCloudWatchTools()


@pytest.fixture
def mock_ctx():
    """Create mock MCP context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    ctx.warning = AsyncMock()
    return ctx


class TestQueryLogs:
    """Tests for query_logs tool."""

    @pytest.fixture
    def query_window(self):
        """Create a stable UTC query window for tests."""
        return (
            datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 16, 11, 0, tzinfo=timezone.utc),
        )

    @pytest.fixture
    def sample_config(self):
        """Create a valid allowlisted CloudWatch target config."""
        return CloudWatchConfig.model_validate(
            {
                'accounts': [
                    {
                        'accountId': '123456789012',
                        'region': 'us-west-2',
                        'roleName': 'DevAccessReadOnly',
                        'logGroups': [
                            {
                                'name': '/aws/lambda/my-fn',
                                'description': 'Primary function logs',
                            },
                            {
                                'name': '/test',
                                'description': 'General test logs',
                            },
                        ],
                    },
                    {
                        'accountId': '999888777666',
                        'region': 'eu-west-1',
                        'roleName': 'CustomRole',
                        'logGroups': [{'name': '/test', 'description': 'EU test logs'}],
                    },
                ]
            }
        )

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.get_cross_account_client')
    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_success(
        self, mock_load_config, mock_get_client, tools, mock_ctx, sample_config, query_window
    ):
        """Test successful log query."""
        mock_load_config.return_value = (sample_config, Path('/tmp/cw_config.yaml'))
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs
        mock_logs.start_query.return_value = {'queryId': 'q-123'}
        mock_logs.get_query_results.return_value = {
            'status': 'Complete',
            'statistics': {'bytesScanned': 1000},
            'results': [[{'field': '@message', 'value': 'test log'}]],
        }

        result = await tools.query_logs(
            ctx=mock_ctx,
            account_id='123456789012',
            log_group='/aws/lambda/my-fn',
            query_string='fields @message | limit 10',
            start_time=query_window[0],
            end_time=query_window[1],
        )

        assert result['status'] == 'Complete'
        assert result['queryIds'] == ['q-123']
        assert len(result['results']) == 1
        assert result['results'][0]['@message'] == 'test log'
        assert result['statistics']['bytesScanned'] == 1000
        assert result['target']['description'] == 'Primary function logs'
        mock_get_client.assert_called_once_with(
            'logs', '123456789012', 'DevAccessReadOnly', 'us-west-2'
        )
        mock_logs.start_query.assert_called_once_with(
            logGroupName='/aws/lambda/my-fn',
            startTime=int(query_window[0].timestamp()),
            endTime=int(query_window[1].timestamp()),
            queryString='fields @message | limit 10',
        )

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_missing_config(self, mock_load_config, tools, mock_ctx, query_window):
        """Test query rejection when no cw_config is available."""
        mock_load_config.side_effect = ConfigNotProvidedError(
            'CloudWatch config file not found at /tmp/cw_config.yaml.'
        )

        result = await tools.query_logs(
            ctx=mock_ctx,
            account_id='123456789012',
            log_group='/aws/lambda/my-fn',
            query_string='fields @message',
            start_time=query_window[0],
            end_time=query_window[1],
        )

        assert result['status'] == 'Error'
        assert 'CloudWatch config file not found' in result['message']

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.get_cross_account_client')
    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_timeout(
        self, mock_load_config, mock_get_client, tools, mock_ctx, sample_config, query_window
    ):
        """Test query polling timeout."""
        mock_load_config.return_value = (sample_config, Path('/tmp/cw_config.yaml'))
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs
        mock_logs.start_query.return_value = {'queryId': 'q-timeout'}
        mock_logs.get_query_results.return_value = {'status': 'Running', 'results': []}

        result = await tools.query_logs(
            ctx=mock_ctx,
            account_id='123456789012',
            log_group='/test',
            query_string='fields @message',
            start_time=query_window[0],
            end_time=query_window[1],
            max_timeout=1,
        )

        assert result['status'] == 'Polling Timeout'
        assert 'did not complete' in result['message']

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.get_cross_account_client')
    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_custom_role_and_region(
        self, mock_load_config, mock_get_client, tools, mock_ctx, sample_config, query_window
    ):
        """Test custom role name and region."""
        mock_load_config.return_value = (sample_config, Path('/tmp/cw_config.yaml'))
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs
        mock_logs.start_query.return_value = {'queryId': 'q-1'}
        mock_logs.get_query_results.return_value = {
            'status': 'Complete',
            'results': [],
        }

        await tools.query_logs(
            ctx=mock_ctx,
            account_id='999888777666',
            log_group='/test',
            query_string='fields @message',
            role_name='CustomRole',
            region='eu-west-1',
            start_time=query_window[0],
            end_time=query_window[1],
        )

        mock_get_client.assert_called_once_with('logs', '999888777666', 'CustomRole', 'eu-west-1')

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.get_cross_account_client')
    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_partitions_only_on_limit(
        self, mock_load_config, mock_get_client, tools, mock_ctx, sample_config, query_window
    ):
        """Test query execution partitions only after reaching the CloudWatch row ceiling."""
        mock_load_config.return_value = (sample_config, Path('/tmp/cw_config.yaml'))
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs
        mock_logs.start_query.side_effect = [
            {'queryId': 'q-root'},
            {'queryId': 'q-left'},
            {'queryId': 'q-right'},
        ]
        limit_result = [[{'field': '@message', 'value': f'row-{i}'}] for i in range(10_000)]

        def get_query_results_side_effect(*, queryId):
            if queryId == 'q-root':
                return {
                    'status': 'Complete',
                    'statistics': {'bytesScanned': 1000},
                    'results': limit_result,
                }
            if queryId == 'q-left':
                return {
                    'status': 'Complete',
                    'statistics': {'bytesScanned': 200},
                    'results': [[{'field': '@message', 'value': 'left'}]],
                }
            if queryId == 'q-right':
                return {
                    'status': 'Complete',
                    'statistics': {'bytesScanned': 300},
                    'results': [[{'field': '@message', 'value': 'right'}]],
                }
            raise AssertionError(f'Unexpected query id: {queryId}')

        mock_logs.get_query_results.side_effect = get_query_results_side_effect

        result = await tools.query_logs(
            ctx=mock_ctx,
            account_id='123456789012',
            log_group='/test',
            query_string='fields @message | limit 10',
            start_time=query_window[0],
            end_time=query_window[1],
        )

        assert result['status'] == 'Complete'
        assert result['queryIds'] == ['q-left', 'q-right']
        assert len(result['partitions']) == 2
        assert [row['@message'] for row in result['results']] == ['left', 'right']
        assert result['statistics']['bytesScanned'] == 500

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_rejects_unconfigured_target(
        self, mock_load_config, tools, mock_ctx, sample_config, query_window
    ):
        """Test query rejection when the requested target is not in the allowlist."""
        mock_load_config.return_value = (sample_config, Path('/tmp/cw_config.yaml'))

        result = await tools.query_logs(
            ctx=mock_ctx,
            account_id='123456789012',
            log_group='/aws/lambda/not-allowed',
            query_string='fields @message',
            start_time=query_window[0],
            end_time=query_window[1],
        )

        assert result['status'] == 'Error'
        assert 'not present in cw_config' in result['message']

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_rejects_invalid_time_window(
        self, mock_load_config, tools, mock_ctx, sample_config, query_window
    ):
        """Test query rejection when end_time is not after start_time."""
        mock_load_config.return_value = (sample_config, Path('/tmp/cw_config.yaml'))

        result = await tools.query_logs(
            ctx=mock_ctx,
            account_id='123456789012',
            log_group='/test',
            query_string='fields @message',
            start_time=query_window[1],
            end_time=query_window[0],
        )

        assert result['status'] == 'Error'
        assert 'end_time must be later than start_time' in result['message']

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.get_cross_account_client')
    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_query_logs_returns_assume_role_remediation(
        self, mock_load_config, mock_get_client, tools, mock_ctx, sample_config, query_window
    ):
        """Test customer-facing remediation guidance for AssumeRole access denied errors."""
        mock_load_config.return_value = (sample_config, Path('/tmp/cw_config.yaml'))
        mock_get_client.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'User is not authorized to perform: sts:AssumeRole',
                }
            },
            'AssumeRole',
        )

        result = await tools.query_logs(
            ctx=mock_ctx,
            account_id='123456789012',
            log_group='/test',
            query_string='fields @message',
            start_time=query_window[0],
            end_time=query_window[1],
        )

        assert result['status'] == 'Error'
        assert 'trust relationship' in result['message']
        assert '"Action": "sts:AssumeRole"' in result['message']
        assert 'arn:aws:iam::123456789012:role/DevAccessReadOnly' in result['message']


class TestConfigTools:
    """Tests for config-backed target discovery tools."""

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_list_cw_targets_success(self, mock_load_config, tools, mock_ctx):
        """Test successful CloudWatch config loading."""
        mock_load_config.return_value = (
            CloudWatchConfig.model_validate(
                {
                    'accounts': [
                        {
                            'accountId': '123456789012',
                            'region': 'us-west-2',
                            'roleName': 'CloudWatchReadOnly',
                            'logGroups': [
                                {
                                    'name': '/aws/lambda/payments-prod',
                                    'description': 'Primary payment handler',
                                }
                            ],
                        }
                    ]
                }
            ),
            Path('/tmp/cw_config.yaml'),
        )

        result = await tools.list_cw_targets(ctx=mock_ctx)

        assert result['found'] is True
        assert result['configPath'] == '/tmp/cw_config.yaml'
        assert result['accounts'][0]['accountId'] == '123456789012'
        assert result['accounts'][0]['logGroups'][0]['name'] == '/aws/lambda/payments-prod'

    @patch('awslabs.cross_account_cloudwatch_mcp_server.tools.load_cloudwatch_config')
    async def test_list_cw_targets_missing_config(self, mock_load_config, tools, mock_ctx):
        """Test missing CloudWatch config file handling."""
        mock_load_config.side_effect = ConfigNotProvidedError(
            'CloudWatch config file not found at /tmp/cw_config.yaml.'
        )

        result = await tools.list_cw_targets(ctx=mock_ctx)

        assert result['found'] is False
        assert result['accounts'] == []
        assert 'CloudWatch config file not found' in result['message']
