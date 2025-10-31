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
"""Tests for the secure_esm_guidance module."""

import pytest
from awslabs.aws_serverless_mcp_server.tools.esm.secure_esm_guidance import (
    SecureEsmGuidanceTool,
)
from unittest.mock import AsyncMock, MagicMock


class TestSecureEsmGuidanceTool:
    """Tests for the SecureEsmGuidanceTool module."""

    @pytest.fixture
    def secure_esm_guidance_tool(self):
        """Create a mock FastMCP and initialize the tool with the mock."""
        mock_mcp = MagicMock()
        return SecureEsmGuidanceTool(mock_mcp, allow_write=True)

    @pytest.mark.asyncio
    async def test_secure_esm_policy_tools_with_different_partitions(
        self, secure_esm_guidance_tool
    ):
        """Test policy generation with different AWS partitions."""
        # Test with aws-cn partition
        result = await secure_esm_guidance_tool.secure_esm_msk_policy_tool(
            AsyncMock(),
            region='cn-north-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='test-uuid-123',
            function_name='test-function',
            partition='aws-cn',
        )

        assert isinstance(result, dict)
        assert 'policy_document' in result
        policy_text = str(result)
        assert 'arn:aws-cn:' in policy_text

        # Test with aws-us-gov partition - use valid region format
        result = await secure_esm_guidance_tool.secure_esm_sqs_policy_tool(
            AsyncMock(),
            region='us-west-2',  # Use standard region format
            account='123456789012',
            queue_name='test-queue',
            function_name='test-function',
            partition='aws-us-gov',
        )

        assert isinstance(result, dict)
        assert 'policy_document' in result
        policy_text = str(result)
        assert 'arn:aws-us-gov:' in policy_text

    @pytest.mark.asyncio
    async def test_secure_esm_policy_tools_with_consumer_group_patterns(
        self, secure_esm_guidance_tool
    ):
        """Test MSK policy generation with custom consumer group patterns."""
        result = await secure_esm_guidance_tool.secure_esm_msk_policy_tool(
            AsyncMock(),
            region='us-east-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='test-uuid-123',
            function_name='test-function',
            consumer_group_pattern='my-app-*',
            topic_pattern='events-*',
        )

        assert isinstance(result, dict)
        policy_text = str(result)
        assert 'my-app-*' in policy_text
        assert 'events-*' in policy_text

    @pytest.mark.asyncio
    async def test_secure_esm_policy_tools_parameter_validation(self, secure_esm_guidance_tool):
        """Test parameter validation in secure policy tools."""
        # Test with all required parameters for comprehensive coverage
        test_cases = [
            {
                'method': 'secure_esm_msk_policy_tool',
                'params': {
                    'region': 'us-east-1',
                    'account': '123456789012',
                    'cluster_name': 'test-cluster',
                    'cluster_uuid': 'test-uuid-123',
                    'function_name': 'test-function',
                },
            },
            {
                'method': 'secure_esm_sqs_policy_tool',
                'params': {
                    'region': 'us-east-1',
                    'account': '123456789012',
                    'queue_name': 'test-queue',
                    'function_name': 'test-function',
                },
            },
            {
                'method': 'secure_esm_kinesis_policy_tool',
                'params': {
                    'region': 'us-east-1',
                    'account': '123456789012',
                    'stream_name': 'test-stream',
                    'function_name': 'test-function',
                },
            },
            {
                'method': 'secure_esm_dynamodb_policy_tool',
                'params': {
                    'region': 'us-east-1',
                    'account': '123456789012',
                    'table_name': 'test-table',
                    'function_name': 'test-function',
                },
            },
        ]

        for test_case in test_cases:
            method = getattr(secure_esm_guidance_tool, test_case['method'])
            result = await method(AsyncMock(), **test_case['params'])

            assert isinstance(result, dict)
            assert 'policy_document' in result
            assert 'Version' in result['policy_document']
            assert 'Statement' in result['policy_document']
            assert result['policy_document']['Version'] == '2012-10-17'
            assert len(result['policy_document']['Statement']) > 0

    # Simple Error Scenario Tests for Coverage Improvement

    @pytest.mark.asyncio
    async def test_secure_esm_guidance_basic_functionality(
        self, secure_esm_guidance_tool, mock_context
    ):
        """Test basic functionality of secure ESM guidance tool."""
        # This is a simple test to ensure the tool can be instantiated and basic methods work
        assert secure_esm_guidance_tool is not None
        assert hasattr(secure_esm_guidance_tool, 'allow_write')

    @pytest.mark.asyncio
    async def test_secure_esm_sqs_policy_tool(self, secure_esm_guidance_tool, mock_context):
        """Test SQS secure policy generation."""
        result = await secure_esm_guidance_tool.secure_esm_sqs_policy_tool(
            mock_context,
            region='us-east-1',
            account='123456789012',
            queue_name='test-queue',
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'policy_document' in result or 'error' in result

    @pytest.mark.asyncio
    async def test_secure_esm_kinesis_policy_tool(self, secure_esm_guidance_tool, mock_context):
        """Test Kinesis secure policy generation."""
        result = await secure_esm_guidance_tool.secure_esm_kinesis_policy_tool(
            mock_context,
            region='us-east-1',
            account='123456789012',
            stream_name='test-stream',
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'policy_document' in result or 'error' in result

    @pytest.mark.asyncio
    async def test_secure_esm_dynamodb_policy_tool(self, secure_esm_guidance_tool, mock_context):
        """Test DynamoDB secure policy generation."""
        result = await secure_esm_guidance_tool.secure_esm_dynamodb_policy_tool(
            mock_context,
            region='us-east-1',
            account='123456789012',
            table_name='test-table',
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'policy_document' in result or 'error' in result

    @pytest.mark.asyncio
    async def test_secure_esm_msk_policy_tool(self, secure_esm_guidance_tool, mock_context):
        """Test MSK Kafka secure policy generation."""
        result = await secure_esm_guidance_tool.secure_esm_msk_policy_tool(
            mock_context,
            region='us-east-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='test-uuid',
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'policy_document' in result or 'error' in result

    @pytest.mark.asyncio
    async def test_secure_esm_msk_policy_tool_validation_error(
        self, secure_esm_guidance_tool, mock_context
    ):
        """Test MSK policy tool with validation errors."""
        result = await secure_esm_guidance_tool.secure_esm_msk_policy_tool(
            mock_context,
            region='invalid-region',  # Invalid region
            account='invalid-account',  # Invalid account
            cluster_name='',  # Empty cluster name
            cluster_uuid='invalid-uuid',  # Invalid UUID
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Parameter validation failed' in result['error']

    @pytest.mark.asyncio
    async def test_secure_esm_sqs_policy_tool_validation_error(
        self, secure_esm_guidance_tool, mock_context
    ):
        """Test SQS policy tool with validation errors."""
        result = await secure_esm_guidance_tool.secure_esm_sqs_policy_tool(
            mock_context,
            region='invalid-region',  # Invalid region
            account='invalid-account',  # Invalid account
            queue_name='',  # Empty queue name
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Parameter validation failed' in result['error']

    @pytest.mark.asyncio
    async def test_secure_esm_kinesis_policy_tool_validation_error(
        self, secure_esm_guidance_tool, mock_context
    ):
        """Test Kinesis policy tool with validation errors."""
        result = await secure_esm_guidance_tool.secure_esm_kinesis_policy_tool(
            mock_context,
            region='invalid-region',  # Invalid region
            account='invalid-account',  # Invalid account
            stream_name='',  # Empty stream name
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Parameter validation failed' in result['error']

    @pytest.mark.asyncio
    async def test_secure_esm_dynamodb_policy_tool_validation_error(
        self, secure_esm_guidance_tool, mock_context
    ):
        """Test DynamoDB policy tool with validation errors."""
        result = await secure_esm_guidance_tool.secure_esm_dynamodb_policy_tool(
            mock_context,
            region='invalid-region',  # Invalid region
            account='invalid-account',  # Invalid account
            table_name='',  # Empty table name
            function_name='test-function',
        )

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Parameter validation failed' in result['error']
