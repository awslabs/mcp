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
"""Tests for the esm_guidance module."""

import json
import pytest
from awslabs.aws_serverless_mcp_server.tools.esm.esm_guidance import (
    EsmGuidanceTool,
)
from unittest.mock import AsyncMock, MagicMock


class TestEsmGuidanceTool:
    """Tests for the EsmGuidanceTool module."""

    @pytest.fixture
    def esm_guidance_tool(self):
        """Create a mock FastMCP and initialize the tool with the mock."""
        mock_mcp = MagicMock()
        return EsmGuidanceTool(mock_mcp, allow_write=True)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'prompt_id, event_source, guidance_type',
        [
            (1, 'dynamodb', 'setup'),
            (2, 'kinesis', 'setup'),
            (3, 'kafka', 'setup'),
            (4, 'sqs', 'setup'),
            (5, 'unspecified', 'setup'),
            (6, 'kafka', 'networking'),
            (7, 'kinesis', 'troubleshooting'),
            (8, None, 'setup'),  # Test with None to see default behavior
        ],
    )
    async def test_esm_guidance_tool(
        self, esm_guidance_tool, prompt_id, event_source, guidance_type
    ):
        """Test requesting an ESM guidance."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source=event_source,
            guidance_type=guidance_type,
        )

        # Print the prompt ID and result for inspection
        print(
            f'\nPrompt {prompt_id} with event_source={event_source}, guidance_type={guidance_type}:'
        )
        print(json.dumps(result, indent=2, default=str))

        # Basic assertions
        assert isinstance(result, dict)

        # For setup guidance, expect steps and next_actions
        if guidance_type == 'setup':
            assert 'steps' in result
            assert 'next_actions' in result
            assert 'deployment_warning' in result
            assert 'sam_deploy_integration' in result

            # Verify deployment warning is present
            assert 'CRITICAL' in result['deployment_warning']
            assert 'confirmation' in str(result['deployment_warning']).lower()

            # Verify SAM integration information is present
            assert 'sam_deploy' in str(result['sam_deploy_integration']).lower()

            # Verify the response contains appropriate guidance based on the event source
            steps_text = ' '.join(result['steps'])
            if event_source == 'dynamodb':
                assert 'DynamoDB' in steps_text or 'stream' in steps_text.lower()
            elif event_source == 'kinesis':
                assert 'Kinesis' in steps_text or 'stream' in steps_text.lower()
            elif event_source == 'kafka':
                assert 'Kafka' in steps_text or 'MSK' in steps_text
            elif event_source == 'sqs':
                assert 'SQS' in steps_text or 'queue' in steps_text.lower()
            elif event_source == 'unspecified' or event_source is None:
                assert 'specify' in steps_text.lower() or 'event source' in steps_text.lower()

        # For networking guidance, expect networking-specific content
        elif guidance_type == 'networking':
            # Should contain networking guidance
            result_text = str(result).lower()
            assert (
                'vpc' in result_text or 'network' in result_text or 'security group' in result_text
            )

        # For troubleshooting guidance, expect troubleshooting content
        elif guidance_type == 'troubleshooting':
            result_text = str(result).lower()
            if event_source == 'kafka':
                assert 'esm_kafka_troubleshoot' in result_text
            else:
                assert 'troubleshoot' in result_text or 'cloudwatch' in result_text

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_networking_question(self, esm_guidance_tool):
        """Test ESM guidance tool with networking-specific questions."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source='kafka',
            guidance_type='networking',
            networking_question='VPC configuration for MSK',
        )

        # Basic assertions
        assert isinstance(result, dict)

        # Verify networking-specific content
        result_text = str(result).lower()
        assert 'vpc' in result_text or 'network' in result_text or 'security group' in result_text

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_sqs_networking(self, esm_guidance_tool):
        """Test ESM guidance tool with SQS networking guidance."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(), event_source='sqs', guidance_type='networking'
        )

        # Basic assertions
        assert isinstance(result, dict)

        # Verify SQS-specific networking content
        result_text = str(result).lower()
        assert 'sqs' in result_text
        assert 'managed service' in result_text or 'no vpc' in result_text

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_policy_generation(self, esm_guidance_tool):
        """Test that ESM guidance tool can generate policies."""
        # Test MSK policy generation
        result = await esm_guidance_tool.esm_msk_policy_tool(
            AsyncMock(),
            region='us-east-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='test-uuid',
        )

        # Verify policy structure
        assert isinstance(result, dict)
        assert 'Version' in result
        assert 'Statement' in result
        assert result['Version'] == '2012-10-17'
        assert len(result['Statement']) > 0

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_sqs_policy_generation(self, esm_guidance_tool):
        """Test SQS policy generation."""
        result = await esm_guidance_tool.esm_sqs_policy_tool(
            AsyncMock(), region='us-east-1', account='123456789012', queue_name='test-queue'
        )

        # Verify policy structure
        assert isinstance(result, dict)
        assert 'Version' in result
        assert 'Statement' in result
        assert result['Version'] == '2012-10-17'

        # Verify SQS-specific permissions
        policy_text = str(result)
        assert 'sqs:ReceiveMessage' in policy_text
        assert 'sqs:DeleteMessage' in policy_text

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_security_group_generation(self, esm_guidance_tool):
        """Test security group template generation."""
        result = await esm_guidance_tool.esm_msk_security_group_tool(
            AsyncMock(), security_group_id='sg-12345678'
        )

        # Verify SAM template structure
        assert isinstance(result, dict)
        assert 'AWSTemplateFormatVersion' in result
        assert 'Resources' in result
        assert 'MSKIngressHTTPS' in result['Resources']
        assert 'MSKIngressKafka' in result['Resources']

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_invalid_parameters(self, esm_guidance_tool):
        """Test error handling for invalid parameters."""
        # Test invalid region
        result = await esm_guidance_tool.esm_msk_policy_tool(
            AsyncMock(),
            region='invalid-region',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='test-uuid',
        )

        assert 'error' in result
        assert 'Invalid parameters' in result['error']

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_sqs_concurrency_guidance(self, esm_guidance_tool):
        """Test SQS concurrency guidance."""
        result = await esm_guidance_tool.esm_sqs_concurrency_guidance_tool(
            AsyncMock(), target_throughput='high', message_processing_time=2, queue_type='standard'
        )

        # Verify concurrency guidance structure
        assert isinstance(result, dict)
        assert 'base_recommendations' in result
        assert 'MaximumConcurrency' in result['base_recommendations']
        assert 'BatchSize' in result['base_recommendations']
        assert 'monitoring_setup' in result
        assert 'performance_tuning' in result

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_invalid_event_source(self, esm_guidance_tool):
        """Test with invalid event source to cover line 264."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source='invalid-source',
            guidance_type='networking',
        )

        # Should handle invalid event source gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_self_managed_kafka_policy(self, esm_guidance_tool):
        """Test self-managed Kafka policy generation."""
        result = await esm_guidance_tool.esm_self_managed_kafka_policy_tool(
            AsyncMock(), region='us-east-1', account='123456789012'
        )

        # Verify policy structure
        assert isinstance(result, dict)
        assert 'Version' in result
        assert 'Statement' in result

        # Verify VPC-specific permissions for self-managed Kafka
        policy_text = str(result)
        assert 'ec2:CreateNetworkInterface' in policy_text
        assert 'ec2:DescribeNetworkInterfaces' in policy_text

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_deployment_precheck(self, esm_guidance_tool):
        """Test deployment precheck tool."""
        result = await esm_guidance_tool.esm_deployment_precheck_tool(
            AsyncMock(),
            prompt='deploy my kafka application',
            project_directory='/tmp/test-project',
        )

        # Verify precheck structure
        assert isinstance(result, dict)
        assert 'deploy_intent_detected' in result
        # Should detect deployment intent and provide error about missing SAM template
        assert result['deploy_intent_detected'] is True
        assert 'error' in result
        assert 'SAM template' in result['error']

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_all_networking_event_sources(self, esm_guidance_tool):
        """Test networking guidance for all event sources."""
        event_sources = ['kafka', 'kinesis', 'dynamodb', 'sqs', 'general']

        for event_source in event_sources:
            result = await esm_guidance_tool.esm_guidance_tool(
                AsyncMock(),
                event_source=event_source,
                guidance_type='networking',
            )

            assert isinstance(result, dict)
            result_text = str(result).lower()

            if event_source == 'sqs':
                assert 'managed service' in result_text or 'no vpc' in result_text
            else:
                assert 'vpc' in result_text or 'network' in result_text

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_troubleshooting_all_sources(self, esm_guidance_tool):
        """Test troubleshooting guidance for all event sources."""
        event_sources = ['kafka', 'kinesis', 'dynamodb', 'sqs']

        for event_source in event_sources:
            result = await esm_guidance_tool.esm_guidance_tool(
                AsyncMock(),
                event_source=event_source,
                guidance_type='troubleshooting',
            )

            assert isinstance(result, dict)
            result_text = str(result).lower()

            if event_source == 'kafka':
                assert 'esm_kafka_troubleshoot' in result_text
            else:
                assert 'cloudwatch' in result_text or 'troubleshoot' in result_text

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_policy_validation_errors(self, esm_guidance_tool):
        """Test policy generation with validation errors."""
        # Test invalid account ID
        result = await esm_guidance_tool.esm_msk_policy_tool(
            AsyncMock(),
            region='us-east-1',
            account='invalid-account',
            cluster_name='test-cluster',
            cluster_uuid='test-uuid',
        )

        assert 'error' in result
        assert 'Invalid parameters' in result['error']

        # Test invalid region
        result = await esm_guidance_tool.esm_sqs_policy_tool(
            AsyncMock(),
            region='invalid-region',
            account='123456789012',
            queue_name='test-queue',
        )

        assert 'error' in result
        assert 'Invalid parameters' in result['error']

        # Test invalid queue name for SQS policy
        result = await esm_guidance_tool.esm_sqs_policy_tool(
            AsyncMock(),
            region='us-east-1',
            account='123456789012',
            queue_name='invalid-queue-name-that-is-way-too-long-and-exceeds-the-80-character-limit-for-sqs-queue-names',
        )

        assert 'error' in result
        assert 'Invalid parameters' in result['error']

        # Test invalid partition for self-managed Kafka policy
        result = await esm_guidance_tool.esm_self_managed_kafka_policy_tool(
            AsyncMock(), region='us-east-1', account='123456789012', partition='invalid-partition'
        )

        assert 'error' in result
        assert 'Invalid parameters' in result['error']

    # Error Scenario Tests for Coverage Improvement

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_troubleshooting_type(self, esm_guidance_tool):
        """Test ESM guidance tool with troubleshooting guidance type."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(), event_source='sqs', guidance_type='troubleshooting'
        )

        assert isinstance(result, dict)
        assert 'guidance' in result or 'troubleshooting_guide' in result

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_networking_type(self, esm_guidance_tool):
        """Test ESM guidance tool with networking guidance type."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source='kafka',
            guidance_type='networking',
            networking_question='vpc_configuration',
        )

        assert isinstance(result, dict)
        assert 'networking_guidance' in result or 'guidance' in result

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_unspecified_event_source(self, esm_guidance_tool):
        """Test ESM guidance tool with unspecified event source."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(), event_source='unspecified', guidance_type='setup'
        )

        assert isinstance(result, dict)
        # Should provide general guidance for unspecified event source

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_kafka_setup_guidance(self, esm_guidance_tool):
        """Test Kafka setup guidance."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source='kafka',
            guidance_type='setup',
        )

        assert isinstance(result, dict)
        assert 'steps' in result or 'deployment_warning' in result

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_networking_guidance(self, esm_guidance_tool):
        """Test networking guidance."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source='kafka',
            guidance_type='networking',
            networking_question='vpc_connectivity',
        )

        assert isinstance(result, dict)
        assert 'networking_guidance' in result

    @pytest.mark.asyncio
    async def test_esm_guidance_tool_troubleshooting_guidance(self, esm_guidance_tool):
        """Test troubleshooting guidance."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source='kafka',
            guidance_type='troubleshooting',
        )

        assert isinstance(result, dict)
        assert 'guidance' in result
        assert 'next_action' in result
