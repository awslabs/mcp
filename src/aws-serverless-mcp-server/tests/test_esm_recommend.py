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
"""Tests for the esm_recommend module."""

import pytest
from awslabs.aws_serverless_mcp_server.tools.poller.esm_recommend import EsmRecommendTool
from unittest.mock import AsyncMock, Mock, patch


class TestEsmRecommendTool:
    """Tests for the TestEsmRecommendTool module."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP and initialize the tool with the mock."""
        mcp = Mock()
        mcp.tool = Mock(return_value=lambda func: func)
        return mcp

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        ctx = Mock()
        ctx.info = AsyncMock()
        return ctx

    @pytest.fixture
    def esm_tool(self, mock_mcp):
        """Create EsmRecommendTool instance with mocked boto3 client."""
        with patch('boto3.client') as mock_boto_client:
            # Create mock lambda client
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            # Mock the methods that will be called
            mock_lambda_client.get_event_source_mapping = Mock()
            mock_lambda_client.list_event_source_mappings = Mock()

        return EsmRecommendTool(mock_mcp)

    def test_initialize_lambda_client_exception(self):
        """Test _initialize_lambda_client with boto3 exception."""
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.poller.esm_recommend.boto3_client',
            side_effect=Exception('AWS Error'),
        ):
            tool = EsmRecommendTool.__new__(EsmRecommendTool)
            with pytest.raises(RuntimeError, match='AWS client initialization failed'):
                tool._initialize_lambda_client()

    @pytest.mark.parametrize(
        'params,expected_method,expected_args',
        [
            ({'uuid': 'test-uuid'}, 'get_event_source_mapping', {'UUID': 'test-uuid'}),
            (
                {'event_source_arn': 'test-arn'},
                'list_event_source_mappings',
                {'EventSourceArn': 'test-arn'},
            ),
            (
                {'function_name': 'test-function'},
                'list_event_source_mappings',
                {'FunctionName': 'test-function'},
            ),
            ({}, 'list_event_source_mappings', {}),
        ],
    )
    def test_get_esm_configs_all_inputs(self, esm_tool, params, expected_method, expected_args):
        """Test that _get_esm_configs returns expected configs."""
        # Setup mock responses and mock the specific method being tested
        with patch.object(esm_tool.lambda_client, expected_method) as mock_method:
            if expected_method == 'get_event_source_mapping':
                mock_method.return_value = {'UUID': 'test-uuid'}
                expected_result = [{'UUID': 'test-uuid'}]
            else:
                mock_method.return_value = {'EventSourceMappings': [{'UUID': 'test-uuid'}]}
                expected_result = [{'UUID': 'test-uuid'}]

            result = esm_tool._get_esm_configs(**params)

            assert result == expected_result
            mock_method.assert_called_once_with(**expected_args)

    def test_get_esm_configs_exception(self, esm_tool):
        """Test _get_esm_configs returns an empty list on exception."""
        with patch.object(esm_tool.lambda_client, 'get_event_source_mapping') as mock_method:
            mock_method.side_effect = Exception()

            with patch('logging.warning') as mock_log:
                result = esm_tool._get_esm_configs(uuid='test-uuid')

                assert result == []
                mock_log.assert_called_once_with('Error getting ESM configurations')

    @patch('requests.get')
    def test_get_esm_limits_from_aws(self, mock_requests, esm_tool):
        """Test _get_esm_limits_from_aws returns correct limits."""
        mock_requests.return_value.json.return_value = {
            'ResourceTypes': {
                'AWS::Lambda::EventSourceMapping': {
                    'Properties': {'BatchSize': {'Minimum': 1, 'Maximum': 1000}}
                }
            }
        }

        mock_operation = Mock()
        mock_shape = Mock()
        mock_shape.members = {'BatchSize': Mock()}
        mock_shape.members['BatchSize'].metadata = {'min': 1, 'max': 1000}
        mock_operation.input_shape = mock_shape

        with patch.object(
            esm_tool.lambda_client._service_model, 'operation_model', return_value=mock_operation
        ):
            result = esm_tool._get_esm_limits_from_aws()

        assert 'BatchSize' in result
        assert result['BatchSize']['min'] == 1
        assert result['BatchSize']['max'] == 1000

    def test_get_esm_limits_from_aws_exception(self, esm_tool):
        """Test that _get_esm_limits_from_aws returns empty dict on exception."""
        with patch.object(
            esm_tool.lambda_client._service_model,
            'operation_model',
            side_effect=Exception('API Error'),
        ):
            result = esm_tool._get_esm_limits_from_aws()

        assert result == {}

    def test_get_esm_limits_from_aws_cached(self, esm_tool):
        """Test _get_esm_limits_from_aws returns cached limits."""
        cached_limits = {'BatchSize': {'min': 1, 'max': 100}}
        esm_tool._cached_limits = cached_limits

        result = esm_tool._get_esm_limits_from_aws()

        assert result == cached_limits

    def test_get_esm_limits_no_metadata(self, esm_tool):
        """Test _get_esm_limits_from_aws with param_shape without metadata."""
        mock_operation = Mock()
        mock_shape = Mock()
        mock_param_without_metadata = Mock()
        del mock_param_without_metadata.metadata  # Remove metadata attribute
        mock_shape.members = {'ParamWithoutMetadata': mock_param_without_metadata}
        mock_operation.input_shape = mock_shape

        with patch.object(
            esm_tool.lambda_client._service_model, 'operation_model', return_value=mock_operation
        ):
            result = esm_tool._get_esm_limits_from_aws()

        assert result == {}

    @patch('requests.get')
    def test_get_esm_limits_metadata_no_min_max(self, mock_requests, esm_tool):
        """Test _get_esm_limits_from_aws with metadata but no min/max."""
        mock_operation = Mock()
        mock_shape = Mock()
        mock_param = Mock()
        mock_param.metadata = {'other_field': 'value'}  # No min/max
        mock_shape.members = {'SomeParam': mock_param}
        mock_operation.input_shape = mock_shape

        with patch.object(
            esm_tool.lambda_client._service_model, 'operation_model', return_value=mock_operation
        ):
            result = esm_tool._get_esm_limits_from_aws()

        assert result == {}

    @pytest.mark.parametrize(
        'optimization_targets',
        [
            ['failure_rate', 'latency'],
            ['cost'],
            ['failure_rate', 'latency', 'cost'],
            ['throughput', 'cost'],
            ['latency', 'cost', 'aaa'],
            [],
        ],
    )
    @pytest.mark.asyncio
    async def test_esm_get_config_tradeoff_tool(
        self, esm_tool, mock_context, optimization_targets
    ):
        """Test esm_get_config_tradeoff_tool returns tradeoffs for various optimization targets."""
        esm_tool._get_esm_limits_from_aws = Mock(
            return_value={'BatchSize': {'min': 1, 'max': 1000}}
        )
        esm_tool._get_esm_configs = Mock(return_value=[])

        result = await esm_tool.esm_get_config_tradeoff_tool(mock_context, optimization_targets)

        assert 'limits' in result
        assert 'current_configs' in result
        assert 'tradeoffs' in result
        assert 'next_actions' in result
        assert all(target in result['tradeoffs'] for target in optimization_targets)

    @pytest.mark.asyncio
    async def test_esm_validate_configs_tool(self, esm_tool, mock_context):
        """Test ESM configuration validation with new input format."""
        # Mock the limits method
        esm_tool._get_esm_limits_from_aws = Mock(
            return_value={
                'BatchSize': {'min': 1, 'max': 1000},
                'ParallelizationFactor': {'min': 1, 'max': 10},
            }
        )

        # Test case 1: Valid Kinesis configuration
        valid_kinesis_config = {
            'BatchSize': 100,
            'ParallelizationFactor': 5,
            'MaximumRetryAttempts': 3,
        }

        result = await esm_tool.esm_validate_configs_tool(
            mock_context, event_source='kinesis', configs=valid_kinesis_config
        )

        assert result['validation_result'] == 'passed'
        assert len(result['failed_causes']) == 0

        # Test case 2: Invalid configuration - value out of range
        invalid_config = {
            'BatchSize': 2000,  # Above max limit of 1000
            'ParallelizationFactor': 15,  # Above max limit of 10
        }

        result = await esm_tool.esm_validate_configs_tool(
            mock_context, event_source='kinesis', configs=invalid_config
        )

        assert result['validation_result'] == 'failed'
        assert len(result['failed_causes']) == 2
        assert any('BatchSize' in failure['property'] for failure in result['failed_causes'])
        assert any(
            'ParallelizationFactor' in failure['property'] for failure in result['failed_causes']
        )

        # Test case 3: Kafka with restricted property
        kafka_config_with_restricted = {
            'BatchSize': 500,
            'BisectBatchOnFunctionError': True,  # Not allowed for Kafka
        }

        result = await esm_tool.esm_validate_configs_tool(
            mock_context, event_source='kafka', configs=kafka_config_with_restricted
        )

        assert result['validation_result'] == 'failed'
        assert len(result['failed_causes']) == 1
        assert result['failed_causes'][0]['property'] == 'BisectBatchOnFunctionError'
        assert 'not allowed for kafka' in result['failed_causes'][0]['error']

        # Test case 4: Empty configuration
        empty_config = {}

        result = await esm_tool.esm_validate_configs_tool(
            mock_context, event_source='dynamodb', configs=empty_config
        )

        assert result['validation_result'] == 'failed'
        assert len(result['failed_causes']) == 1
        assert result['failed_causes'][0]['error'] == 'Empty configuration'

        # Test case 5: Unsupported event source
        result = await esm_tool.esm_validate_configs_tool(
            mock_context, event_source='unsupported_source', configs={'BatchSize': 100}
        )

        assert result['validation_result'] == 'failed'
        assert len(result['failed_causes']) == 1
        assert (
            result['failed_causes'][0]['error'] == 'Unsupported event source: unsupported_source'
        )
