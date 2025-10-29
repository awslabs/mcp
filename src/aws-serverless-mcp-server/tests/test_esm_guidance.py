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
import os
import pytest
import tempfile
from awslabs.aws_serverless_mcp_server.tools.poller.esm_guidance import (
    EsmGuidanceTool,
)
from unittest.mock import AsyncMock, MagicMock


class TestEsmGuidanceTool:
    """Tests for the EsmGuidanceTool module."""

    @pytest.fixture
    def esm_guidance_tool(self):
        """Create a mock FastMCP and initialize the tool with the mock."""
        mock_mcp = MagicMock()
        return EsmGuidanceTool(mock_mcp)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'prompt_id, event_source',
        [
            (1, 'dynamodb'),
            (2, 'kinesis'),
            (3, 'kafka'),
            (4, 'unspecified'),
            (5, None),  # Test with None to see default behavior
        ],
    )
    async def test_esm_guidance_tool(self, esm_guidance_tool, prompt_id, event_source):
        """Test requesting an ESM guidance."""
        result = await esm_guidance_tool.esm_guidance_tool(
            AsyncMock(),
            event_source=event_source,
        )

        # Print the prompt ID and result for inspection
        print(f'\nPrompt {prompt_id} with event_source={event_source}:')
        print(json.dumps(result, indent=2, default=str))

        # Basic assertions
        assert isinstance(result, dict)
        assert 'steps' in result
        assert 'next_actions' in result

        # Verify the response contains appropriate guidance based on the event source
        steps_text = ' '.join(result['steps'])
        if event_source == 'dynamodb':
            assert 'DynamoDB' in steps_text
        elif event_source == 'kinesis':
            assert 'Kinesis' in steps_text
        elif event_source == 'kafka':
            assert 'MSK' in steps_text
        elif event_source == 'unspecified' or event_source is None:
            assert 'solicit prompt to user' in steps_text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'region, account, cluster_name, cluster_uuid, partition, expected_cluster_arn',
        [
            (
                'us-east-1',
                '123456789012',
                'test-cluster',
                'abc123',
                'aws',
                'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abc123',
            ),
            (
                'cn-north-1',
                '111122223333',
                'china-cluster',
                'def456',
                'aws-cn',
                'arn:aws-cn:kafka:cn-north-1:111122223333:cluster/china-cluster/def456',
            ),
        ],
    )
    async def test_esm_msk_policy_tool(
        self,
        esm_guidance_tool,
        region,
        account,
        cluster_name,
        cluster_uuid,
        partition,
        expected_cluster_arn,
    ):
        """Test MSK policy generation with various parameters."""
        result = await esm_guidance_tool.esm_msk_policy_tool(
            AsyncMock(),
            region=region,
            account=account,
            cluster_name=cluster_name,
            cluster_uuid=cluster_uuid,
            partition=partition,
        )

        # Verify policy structure
        assert isinstance(result, dict)
        assert result['Version'] == '2012-10-17'
        assert 'Statement' in result
        assert len(result['Statement']) == 5

        # Verify cluster access statement
        cluster_statement = result['Statement'][0]
        assert cluster_statement['Effect'] == 'Allow'
        assert 'kafka-cluster:Connect' in cluster_statement['Action']
        assert 'kafka-cluster:DescribeCluster' in cluster_statement['Action']
        assert cluster_statement['Resource'] == expected_cluster_arn

        # Verify topic access statement
        topic_statement = result['Statement'][1]
        assert topic_statement['Effect'] == 'Allow'
        assert 'kafka-cluster:DescribeTopic' in topic_statement['Action']
        assert 'kafka-cluster:ReadData' in topic_statement['Action']
        assert (
            topic_statement['Resource']
            == f'arn:{partition}:kafka:{region}:{account}:topic/{cluster_name}/*'
        )

        # Verify group access statement
        group_statement = result['Statement'][2]
        assert group_statement['Effect'] == 'Allow'
        assert 'kafka-cluster:AlterGroup' in group_statement['Action']
        assert 'kafka-cluster:DescribeGroup' in group_statement['Action']
        assert (
            group_statement['Resource']
            == f'arn:{partition}:kafka:{region}:{account}:group/{cluster_name}/*'
        )

        # Verify Kafka API statement
        kafka_api_statement = result['Statement'][3]
        assert kafka_api_statement['Effect'] == 'Allow'
        assert 'kafka:DescribeClusterV2' in kafka_api_statement['Action']
        assert 'kafka:GetBootstrapBrokers' in kafka_api_statement['Action']
        assert len(kafka_api_statement['Resource']) == 3

        # Verify EC2 permissions statement
        ec2_statement = result['Statement'][4]
        assert ec2_statement['Effect'] == 'Allow'
        assert 'ec2:CreateNetworkInterface' in ec2_statement['Action']
        assert ec2_statement['Resource'] == '*'

    @pytest.mark.asyncio
    async def test_esm_msk_policy_tool_validation_error(self, esm_guidance_tool):
        """Test MSK policy tool with invalid parameters."""
        result = await esm_guidance_tool.esm_msk_policy_tool(
            AsyncMock(),
            region='invalid-region',
            account='123',
            cluster_name='test-cluster',
            cluster_uuid='abc123',
            partition='aws',
        )

        # Verify error response structure
        assert 'error' in result
        assert 'details' in result
        assert result['error'] == 'Invalid parameters'
        assert 'region' in result['details']
        assert 'account' in result['details']

    @pytest.mark.asyncio
    async def test_esm_msk_security_group_tool(self, esm_guidance_tool):
        """Test MSK security group SAM template generation."""
        security_group_id = 'sg-12345678'

        result = await esm_guidance_tool.esm_msk_security_group_tool(
            AsyncMock(), security_group_id=security_group_id
        )

        # Verify sg-id is correct
        assert 'SecurityGroupId' in result['Parameters']
        assert result['Parameters']['SecurityGroupId']['Default'] == security_group_id

        # Verify resources/outputs
        resources = result['Resources']
        assert 'MSKIngressHTTPS' in resources
        assert 'MSKIngressKafka' in resources
        assert 'MSKEgressAll' in resources
        assert 'SecurityGroupId' in result['Outputs']

        # Verify SecurityGroupId in every rules
        assert resources['MSKIngressHTTPS']['Properties']['GroupId']['Ref'] == 'SecurityGroupId'
        assert (
            resources['MSKIngressHTTPS']['Properties']['SourceSecurityGroupId']['Ref']
            == 'SecurityGroupId'
        )

        assert resources['MSKIngressKafka']['Properties']['GroupId']['Ref'] == 'SecurityGroupId'
        assert (
            resources['MSKIngressKafka']['Properties']['SourceSecurityGroupId']['Ref']
            == 'SecurityGroupId'
        )

        assert resources['MSKEgressAll']['Properties']['GroupId']['Ref'] == 'SecurityGroupId'
        assert (
            resources['MSKEgressAll']['Properties']['DestinationSecurityGroupId']['Ref']
            == 'SecurityGroupId'
        )

        assert result['Outputs']['SecurityGroupId']['Value']['Ref'] == 'SecurityGroupId'

    @pytest.mark.asyncio
    async def test_esm_msk_security_group_tool_validation_error(self, esm_guidance_tool):
        """Test MSK security group tool with invalid security group ID."""
        result = await esm_guidance_tool.esm_msk_security_group_tool(
            AsyncMock(), security_group_id='invalid-sg-id'
        )

        # Verify error response structure
        assert 'error' in result
        assert 'expected_format' in result
        assert 'Invalid security group ID format' in result['error']
        assert 'sg-xxxxxxxx' in result['expected_format']

    def test_validate_aws_parameters(self, esm_guidance_tool):
        """Test AWS parameter validation."""
        # Valid parameters - should return empty dict
        errors = esm_guidance_tool._validate_aws_parameters(
            'us-east-1', '123456789012', 'test-cluster', 'abc123', 'aws'
        )
        assert errors == {}

        # Invalid region
        errors = esm_guidance_tool._validate_aws_parameters(
            'invalid-region', '123456789012', 'test-cluster', 'abc123', 'aws'
        )
        assert 'region' in errors

        # Invalid account ID (not 12 digits)
        errors = esm_guidance_tool._validate_aws_parameters(
            'us-east-1', '12345', 'test-cluster', 'abc123', 'aws'
        )
        assert 'account' in errors

        # Invalid cluster name (too long)
        errors = esm_guidance_tool._validate_aws_parameters(
            'us-east-1', '123456789012', 'a' * 65, 'abc123', 'aws'
        )
        assert 'cluster_name' in errors

        # Invalid cluster UUID (special chars)
        errors = esm_guidance_tool._validate_aws_parameters(
            'us-east-1', '123456789012', 'test-cluster', 'abc@123', 'aws'
        )
        assert 'cluster_uuid' in errors

        # Invalid partition
        errors = esm_guidance_tool._validate_aws_parameters(
            'us-east-1', '123456789012', 'test-cluster', 'abc123', 'invalid'
        )
        assert 'partition' in errors

        # Wildcard cluster UUID should be valid
        errors = esm_guidance_tool._validate_aws_parameters(
            'us-east-1', '123456789012', 'test-cluster', '*', 'aws'
        )
        assert errors == {}

    @pytest.mark.asyncio
    async def test_esm_deployment_precheck_tool_no_deploy_intent(self, esm_guidance_tool):
        """Test precheck tool with no deploy intent."""
        result = await esm_guidance_tool.esm_deployment_precheck_tool(
            AsyncMock(),
            prompt='Just checking the configuration',
            project_directory=tempfile.mkdtemp(),
        )

        assert result['deploy_intent_detected'] is False
        assert 'No deploy intent detected' in result['message']

    @pytest.mark.asyncio
    async def test_esm_deployment_precheck_tool_deploy_intent_no_template(self, esm_guidance_tool):
        """Test precheck tool with deploy intent but no template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await esm_guidance_tool.esm_deployment_precheck_tool(
                AsyncMock(), prompt='Please deploy this application', project_directory=temp_dir
            )

            assert result['deploy_intent_detected'] is True
            assert 'error' in result
            assert 'No SAM template found' in result['error']

    @pytest.mark.asyncio
    async def test_esm_deployment_precheck_tool_deploy_intent_with_template(
        self, esm_guidance_tool
    ):
        """Test precheck tool with deploy intent and template found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a template file
            template_path = os.path.join(temp_dir, 'template.yaml')
            with open(template_path, 'w') as f:
                f.write('AWSTemplateFormatVersion: "2010-09-09"')

            result = await esm_guidance_tool.esm_deployment_precheck_tool(
                AsyncMock(), prompt='Ready to deploy the stack', project_directory=temp_dir
            )

            assert result['deploy_intent_detected'] is True
            assert result['template_found'] is True
            assert 'Deploy intent confirmed' in result['message']
