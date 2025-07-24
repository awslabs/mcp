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

"""Comprehensive tests for the AWS FIS MCP server implementation."""

import awslabs.aws_fis_mcp_server.server as server_module
import pytest
from awslabs.aws_fis_mcp_server.server import (
    create_experiment_template,
    create_view,
    discover_relationships,
    get_experiment_details,
    get_experiment_template,
    get_stack_resources,
    list_all_fis_experiments,
    list_cfn_stacks,
    list_experiment_templates,
    list_views,
    search_resources,
    start_experiment,
    update_experiment_template,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


class TestAwsFisActions:
    """Test cases for AwsFisActions class."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients and other dependencies."""
        self.mock_aws_fis = MagicMock()
        self.mock_context = AsyncMock()

        with (
            patch.object(server_module, 'aws_fis', self.mock_aws_fis),
            patch.object(server_module, 'allow_writes', True),
        ):
            yield

    @pytest.mark.asyncio
    async def test_list_all_fis_experiments_success(self):
        """Test listing FIS experiments successfully."""
        self.mock_aws_fis.list_experiments.return_value = {
            'experiments': [
                {
                    'id': 'exp-1',
                    'arn': 'arn:aws:fis:us-east-1:123456789012:experiment/exp-1',
                    'experimentTemplateId': 'template-1',
                    'state': {'status': 'completed'},
                    'experimentOptions': {'actionsMode': 'run-all'},
                    'tags': {'Name': 'Test Experiment'},
                }
            ]
        }

        result = await list_all_fis_experiments(self.mock_context)

        assert len(result) == 1
        assert 'Test Experiment' in result
        assert result['Test Experiment']['id'] == 'exp-1'
        assert result['Test Experiment']['state'] == {'status': 'completed'}
        self.mock_aws_fis.list_experiments.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_all_fis_experiments_with_pagination(self):
        """Test listing FIS experiments with pagination."""
        self.mock_aws_fis.list_experiments.side_effect = [
            {
                'experiments': [
                    {
                        'id': 'exp-1',
                        'arn': 'arn:aws:fis:us-east-1:123456789012:experiment/exp-1',
                        'experimentTemplateId': 'template-1',
                        'state': {'status': 'completed'},
                        'tags': {'Name': 'Test Experiment 1'},
                    }
                ],
                'nextToken': 'token1',
            },
            {
                'experiments': [
                    {
                        'id': 'exp-2',
                        'arn': 'arn:aws:fis:us-east-1:123456789012:experiment/exp-2',
                        'experimentTemplateId': 'template-2',
                        'state': {'status': 'running'},
                        'tags': {'Name': 'Test Experiment 2'},
                    }
                ]
            },
        ]

        result = await list_all_fis_experiments(self.mock_context)

        assert len(result) == 2
        assert 'Test Experiment 1' in result
        assert 'Test Experiment 2' in result
        assert self.mock_aws_fis.list_experiments.call_count == 2

    @pytest.mark.asyncio
    async def test_list_all_fis_experiments_error(self):
        """Test error handling when listing FIS experiments."""
        self.mock_aws_fis.list_experiments.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}}, 'list_experiments'
        )

        with pytest.raises(ClientError):
            await list_all_fis_experiments(self.mock_context)

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_experiment_details_success(self):
        """Test getting experiment details successfully."""
        experiment_id = 'exp-1'
        self.mock_aws_fis.get_experiment.return_value = {
            'experiment': {
                'id': experiment_id,
                'arn': f'arn:aws:fis:us-east-1:123456789012:experiment/{experiment_id}',
                'state': {'status': 'completed'},
                'tags': {'Name': 'Test Experiment'},
            }
        }

        result = await get_experiment_details(self.mock_context, id=experiment_id)

        assert result['id'] == experiment_id
        assert result['state']['status'] == 'completed'
        self.mock_aws_fis.get_experiment.assert_called_once_with(id=experiment_id)

    @pytest.mark.asyncio
    async def test_get_experiment_details_error(self):
        """Test error handling when getting experiment details."""
        experiment_id = 'exp-1'
        self.mock_aws_fis.get_experiment.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Experiment not found'}},
            'get_experiment',
        )

        with pytest.raises(ClientError):
            await get_experiment_details(self.mock_context, id=experiment_id)

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_experiment_templates_success(self):
        """Test listing experiment templates successfully."""
        self.mock_aws_fis.list_experiment_templates.return_value = {
            'experimentTemplates': [
                {
                    'id': 'template-1',
                    'arn': 'arn:aws:fis:us-east-1:123456789012:experiment-template/template-1',
                    'description': 'Test Template 1',
                }
            ]
        }

        result = await list_experiment_templates(self.mock_context)

        assert len(result) == 1
        assert result[0]['id'] == 'template-1'
        assert result[0]['description'] == 'Test Template 1'
        self.mock_aws_fis.list_experiment_templates.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_experiment_template_success(self):
        """Test getting experiment template details successfully."""
        template_id = 'template-1'
        self.mock_aws_fis.get_experiment_template.return_value = {
            'experimentTemplate': {
                'id': template_id,
                'description': 'Test Template',
                'targets': {'Instances': {'resourceType': 'aws:ec2:instance'}},
                'actions': {'StopInstances': {'actionId': 'aws:ec2:stop-instances'}},
            }
        }

        result = await get_experiment_template(self.mock_context, id=template_id)

        assert 'experimentTemplate' in result
        assert result['experimentTemplate']['id'] == template_id
        self.mock_aws_fis.get_experiment_template.assert_called_once_with(id=template_id)

    @pytest.mark.asyncio
    async def test_start_experiment_success(self):
        """Test starting an experiment successfully."""
        template_id = 'template-1'
        experiment_id = 'exp-1'
        tags = {'Environment': 'Test'}

        self.mock_aws_fis.start_experiment.return_value = {
            'experiment': {
                'id': experiment_id,
                'state': {'status': 'pending'},
                'tags': tags,
            }
        }

        self.mock_aws_fis.get_experiment.side_effect = [
            {'experiment': {'id': experiment_id, 'state': {'status': 'pending'}}},
            {'experiment': {'id': experiment_id, 'state': {'status': 'completed'}}},
        ]

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await start_experiment(
                self.mock_context,
                template_id,
                'Test Experiment',
                tags,
            )

        assert result['experiment_id'] == experiment_id
        assert result['status'] == 'started'
        self.mock_aws_fis.start_experiment.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_experiment_immediate_return(self):
        """Test starting an experiment returns immediately."""
        template_id = 'template-1'
        experiment_id = 'exp-1'

        self.mock_aws_fis.start_experiment.return_value = {
            'experiment': {'id': experiment_id, 'state': {'status': 'pending'}}
        }

        result = await start_experiment(
            self.mock_context,
            template_id,
            'Test Experiment',
            None,
        )

        assert result['experiment_id'] == experiment_id
        assert result['status'] == 'started'
        assert result['name'] == 'Test Experiment'

    @pytest.mark.asyncio
    async def test_start_experiment_basic_success(self):
        """Test starting an experiment successfully."""
        template_id = 'template-1'
        experiment_id = 'exp-1'

        self.mock_aws_fis.start_experiment.return_value = {
            'experiment': {'id': experiment_id, 'state': {'status': 'pending'}}
        }

        result = await start_experiment(self.mock_context, template_id, 'Test Experiment', None)
        assert result['status'] == 'started'
        assert result['experiment_id'] == experiment_id

    @pytest.mark.asyncio
    async def test_start_experiment_error(self):
        """Test starting an experiment with AWS error."""
        template_id = 'template-1'

        self.mock_aws_fis.start_experiment.side_effect = Exception('Template not found')

        with pytest.raises(Exception, match='Template not found'):
            await start_experiment(self.mock_context, template_id, 'Test Experiment', None)

    @pytest.mark.asyncio
    async def test_list_experiment_templates_with_pagination(self):
        """Test listing experiment templates with pagination."""
        self.mock_aws_fis.list_experiment_templates.side_effect = [
            {
                'experimentTemplates': [{'id': 'template-1', 'description': 'Template 1'}],
                'nextToken': 'token1',
            },
            {'experimentTemplates': [{'id': 'template-2', 'description': 'Template 2'}]},
        ]

        result = await list_experiment_templates(self.mock_context)

        assert len(result) == 2
        assert result[0]['id'] == 'template-1'
        assert result[1]['id'] == 'template-2'
        assert self.mock_aws_fis.list_experiment_templates.call_count == 2

    @pytest.mark.asyncio
    async def test_list_experiment_templates_error(self):
        """Test error handling when listing experiment templates."""
        self.mock_aws_fis.list_experiment_templates.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'list_experiment_templates',
        )

        with pytest.raises(ClientError):
            await list_experiment_templates(self.mock_context)

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_experiment_template_error(self):
        """Test error handling when getting experiment template."""
        template_id = 'template-1'
        self.mock_aws_fis.get_experiment_template.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Template not found'}},
            'get_experiment_template',
        )

        with pytest.raises(ClientError):
            await get_experiment_template(self.mock_context, id=template_id)

        self.mock_context.error.assert_called_once()


class TestResourceDiscovery:
    """Test cases for ResourceDiscovery class."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients and other dependencies."""
        self.mock_resource_explorer = MagicMock()
        self.mock_cloudformation = MagicMock()
        self.mock_aws_config_client = MagicMock()
        self.mock_context = AsyncMock()

        with (
            patch.object(server_module, 'resource_explorer', self.mock_resource_explorer),
            patch.object(server_module, 'cloudformation', self.mock_cloudformation),
            patch.object(server_module, 'aws_config_client', self.mock_aws_config_client),
            patch.object(server_module, 'allow_writes', True),
        ):
            yield

    @pytest.mark.asyncio
    async def test_list_cfn_stacks_success(self):
        """Test listing CloudFormation stacks successfully."""
        self.mock_cloudformation.list_stacks.return_value = {
            'StackSummaries': [
                {
                    'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/12345',
                    'StackName': 'test-stack',
                    'StackStatus': 'CREATE_COMPLETE',
                }
            ]
        }

        result = await list_cfn_stacks(self.mock_context)

        assert 'stacks' in result
        assert len(result['stacks']) == 1
        assert result['stacks'][0]['StackName'] == 'test-stack'
        self.mock_cloudformation.list_stacks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stack_resources_success(self):
        """Test getting stack resources successfully."""
        stack_name = 'test-stack'
        self.mock_cloudformation.list_stack_resources.return_value = {
            'StackResourceSummaries': [
                {
                    'LogicalResourceId': 'TestInstance',
                    'PhysicalResourceId': 'i-12345678901234567',
                    'ResourceType': 'AWS::EC2::Instance',
                    'ResourceStatus': 'CREATE_COMPLETE',
                }
            ]
        }

        result = await get_stack_resources(self.mock_context, stack_name=stack_name)

        assert 'resources' in result
        assert len(result['resources']) == 1
        assert result['resources'][0]['LogicalResourceId'] == 'TestInstance'
        self.mock_cloudformation.list_stack_resources.assert_called_once_with(StackName=stack_name)

    @pytest.mark.asyncio
    async def test_list_views_success(self):
        """Test listing Resource Explorer views successfully."""
        self.mock_resource_explorer.list_views.return_value = {
            'Views': [
                {
                    'ViewArn': 'arn:aws:resource-explorer-2:us-east-1:123456789012:view/test-view',
                    'ViewName': 'test-view',
                    'Filters': {'FilterString': 'service:ec2'},
                }
            ]
        }

        result = await list_views(self.mock_context)

        assert len(result) == 1
        assert result[0]['ViewName'] == 'test-view'
        self.mock_resource_explorer.list_views.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_view_success(self):
        """Test creating a Resource Explorer view successfully."""
        query = 'service:ec2'
        view_name = 'test-view'
        tags = {'Environment': 'Test'}

        self.mock_resource_explorer.create_view.return_value = {
            'View': {
                'ViewArn': 'arn:aws:resource-explorer-2:us-east-1:123456789012:view/test-view',
                'ViewName': view_name,
                'Filters': {'FilterString': query},
            }
        }

        with patch('time.time', return_value=1234567890):
            result = await create_view(
                self.mock_context,
                query,
                view_name,
                'Test View',
                tags,
            )

        assert 'View' in result
        assert result['View']['ViewName'] == view_name
        self.mock_resource_explorer.create_view.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_cfn_stacks_with_pagination(self):
        """Test listing CloudFormation stacks with pagination."""
        self.mock_cloudformation.list_stacks.side_effect = [
            {
                'StackSummaries': [{'StackName': 'stack-1', 'StackStatus': 'CREATE_COMPLETE'}],
                'NextToken': 'token1',
            },
            {'StackSummaries': [{'StackName': 'stack-2', 'StackStatus': 'UPDATE_COMPLETE'}]},
        ]

        result = await list_cfn_stacks(self.mock_context)

        assert 'stacks' in result
        assert len(result['stacks']) == 2
        assert result['stacks'][0]['StackName'] == 'stack-1'
        assert result['stacks'][1]['StackName'] == 'stack-2'
        assert self.mock_cloudformation.list_stacks.call_count == 2

    @pytest.mark.asyncio
    async def test_list_cfn_stacks_error(self):
        """Test error handling when listing CloudFormation stacks."""
        self.mock_cloudformation.list_stacks.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'list_stacks',
        )

        with pytest.raises(ClientError):
            await list_cfn_stacks(self.mock_context)

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stack_resources_with_pagination(self):
        """Test getting stack resources with pagination."""
        stack_name = 'test-stack'
        self.mock_cloudformation.list_stack_resources.side_effect = [
            {
                'StackResourceSummaries': [
                    {
                        'LogicalResourceId': 'Resource1',
                        'ResourceType': 'AWS::EC2::Instance',
                        'ResourceStatus': 'CREATE_COMPLETE',
                    }
                ],
                'NextToken': 'token1',
            },
            {
                'StackResourceSummaries': [
                    {
                        'LogicalResourceId': 'Resource2',
                        'ResourceType': 'AWS::S3::Bucket',
                        'ResourceStatus': 'CREATE_COMPLETE',
                    }
                ]
            },
        ]

        result = await get_stack_resources(self.mock_context, stack_name=stack_name)

        assert 'resources' in result
        assert len(result['resources']) == 2
        assert result['resources'][0]['LogicalResourceId'] == 'Resource1'
        assert result['resources'][1]['LogicalResourceId'] == 'Resource2'
        assert self.mock_cloudformation.list_stack_resources.call_count == 2

    @pytest.mark.asyncio
    async def test_get_stack_resources_error(self):
        """Test error handling when getting stack resources."""
        stack_name = 'test-stack'
        self.mock_cloudformation.list_stack_resources.side_effect = ClientError(
            {'Error': {'Code': 'ValidationError', 'Message': 'Stack does not exist'}},
            'list_stack_resources',
        )

        with pytest.raises(ClientError):
            await get_stack_resources(self.mock_context, stack_name=stack_name)

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_views_with_pagination(self):
        """Test listing Resource Explorer views with pagination."""
        self.mock_resource_explorer.list_views.side_effect = [
            {
                'Views': [{'ViewName': 'view-1', 'Filters': {'FilterString': 'service:ec2'}}],
                'NextToken': 'token1',
            },
            {'Views': [{'ViewName': 'view-2', 'Filters': {'FilterString': 'service:s3'}}]},
        ]

        result = await list_views(self.mock_context)

        assert len(result) == 2
        assert result[0]['ViewName'] == 'view-1'
        assert result[1]['ViewName'] == 'view-2'
        assert self.mock_resource_explorer.list_views.call_count == 2

    @pytest.mark.asyncio
    async def test_list_views_error(self):
        """Test error handling when listing Resource Explorer views."""
        self.mock_resource_explorer.list_views.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'list_views',
        )

        with pytest.raises(ClientError):
            await list_views(self.mock_context)

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_view_without_client_token(self):
        """Test creating a Resource Explorer view without providing client token."""
        query = 'service:ec2'
        view_name = 'test-view'

        self.mock_resource_explorer.create_view.return_value = {
            'View': {
                'ViewName': view_name,
                'Filters': {'FilterString': query},
            }
        }

        with patch('time.time', return_value=1234567890):
            result = await create_view(self.mock_context, query, view_name, 'Test View', None)

        assert 'View' in result
        assert result['View']['ViewName'] == view_name
        self.mock_resource_explorer.create_view.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_view_generates_client_token(self):
        """Test that create_view generates client token when none provided."""
        query = 'service:ec2'
        view_name = 'test-view'

        self.mock_resource_explorer.create_view.return_value = {
            'View': {
                'ViewName': view_name,
                'Filters': {'FilterString': query},
            }
        }

        with patch('time.time', return_value=1234567890):
            await create_view(
                self.mock_context,
                query,
                view_name,
                'Test View',
                None,
                None,
                None,
            )

        # Verify the generated client token was used
        self.mock_resource_explorer.create_view.assert_called_once()
        call_args = self.mock_resource_explorer.create_view.call_args
        assert call_args.kwargs['ClientToken'] == 'create-view-1234567890'

    @pytest.mark.asyncio
    async def test_create_view_error(self):
        """Test error handling when creating a Resource Explorer view."""
        self.mock_resource_explorer.create_view.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid view name'}},
            'create_view',
        )

        with pytest.raises(ClientError):
            await create_view(
                self.mock_context,
                'service:ec2',
                'invalid-view',
                'Test View',
                None,
            )

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_relationships_success(self):
        """Test discovering resource relationships successfully."""
        resource_type = 'AWS::EC2::Instance'
        resource_id = 'i-02151a3c2be355f9e'

        self.mock_aws_config_client.get_resource_config_history.return_value = {
            'configurationItems': [
                {
                    'configurationItemCaptureTime': '2023-01-01T00:00:00.000Z',
                    'configurationStateId': 'ResourceStateId',
                    'awsRegion': 'us-east-1',
                    'availabilityZone': 'us-east-1a',
                    'resourceCreationTime': '2023-01-01T00:00:00.000Z',
                    'tags': {'Name': 'TestInstance'},
                    'relationships': [
                        {
                            'resourceType': 'AWS::EC2::Subnet',
                            'resourceId': 'subnet-12345',
                            'relationshipName': 'Is contained in Subnet',
                        },
                        {
                            'resourceType': 'AWS::EC2::SecurityGroup',
                            'resourceId': 'sg-12345',
                            'relationshipName': 'Is associated with SecurityGroup',
                        },
                    ],
                }
            ]
        }

        result = await discover_relationships(
            self.mock_context, resource_type=resource_type, resource_id=resource_id
        )

        assert result['resource_type'] == resource_type
        assert result['resource_id'] == resource_id
        assert len(result['relationships']) == 2
        assert result['relationships'][0]['resourceType'] == 'AWS::EC2::Subnet'
        assert result['relationships'][1]['resourceType'] == 'AWS::EC2::SecurityGroup'
        assert result['summary']['total_relationships'] == 2
        assert len(result['configuration_items']) == 1

        # Verify the method was called once
        self.mock_aws_config_client.get_resource_config_history.assert_called_once()

        # Verify the call arguments
        call_args = self.mock_aws_config_client.get_resource_config_history.call_args
        assert call_args.kwargs['resourceType'] == resource_type
        assert call_args.kwargs['resourceId'] == resource_id

    @pytest.mark.asyncio
    async def test_discover_relationships_no_config_items(self):
        """Test discovering relationships when no configuration items found."""
        resource_type = 'AWS::EC2::Instance'
        resource_id = 'i-nonexistent'

        self.mock_aws_config_client.get_resource_config_history.return_value = {
            'configurationItems': []
        }

        result = await discover_relationships(
            self.mock_context, resource_type=resource_type, resource_id=resource_id
        )

        assert result['resource_type'] == resource_type
        assert result['resource_id'] == resource_id
        assert result['message'] == 'No configuration items found for the specified resource'
        assert len(result['relationships']) == 0
        assert len(result['configuration_items']) == 0

    @pytest.mark.asyncio
    async def test_discover_relationships_with_custom_parameters(self):
        """Test discovering relationships with custom limit and chronological order."""
        resource_type = 'AWS::ElasticLoadBalancingV2::LoadBalancer'
        resource_id = 'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/1234567890abcdef'

        self.mock_aws_config_client.get_resource_config_history.return_value = {
            'configurationItems': [
                {
                    'configurationItemCaptureTime': '2023-01-01T00:00:00.000Z',
                    'configurationStateId': 'ResourceStateId',
                    'awsRegion': 'us-east-1',
                    'relationships': [
                        {
                            'resourceType': 'AWS::EC2::Subnet',
                            'resourceId': 'subnet-12345',
                            'relationshipName': 'Is contained in Subnet',
                        }
                    ],
                }
            ]
        }

        result = await discover_relationships(
            self.mock_context,
            resource_type=resource_type,
            resource_id=resource_id,
            limit=5,
            chronological_order='Forward',
        )

        assert result['resource_type'] == resource_type
        assert result['resource_id'] == resource_id
        assert len(result['relationships']) == 1
        assert result['relationships'][0]['resourceType'] == 'AWS::EC2::Subnet'

        self.mock_aws_config_client.get_resource_config_history.assert_called_once_with(
            resourceType=resource_type,
            resourceId=resource_id,
            chronologicalOrder='Forward',
            limit=5,
        )

    @pytest.mark.asyncio
    async def test_discover_relationships_error(self):
        """Test error handling when discovering resource relationships."""
        resource_type = 'AWS::EC2::Instance'
        resource_id = 'i-12345'

        self.mock_aws_config_client.get_resource_config_history.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'get_resource_config_history',
        )

        with pytest.raises(ClientError):
            await discover_relationships(
                self.mock_context, resource_type=resource_type, resource_id=resource_id
            )

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_resources_success(self):
        """Test searching resources successfully."""
        query_string = 'service:ec2 resourcetype:instance'
        view_arn = 'arn:aws:resource-explorer-2:us-east-1:123456789012:view/test-view'
        max_results = 50

        # Mock the search response
        self.mock_resource_explorer.search.return_value = {
            'Resources': [
                {
                    'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-12345',
                    'Properties': [
                        {'Name': 'resourcetype', 'Value': 'instance'},
                        {'Name': 'service', 'Value': 'ec2'},
                    ],
                    'Region': 'us-east-1',
                    'Service': 'ec2',
                },
                {
                    'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-67890',
                    'Properties': [
                        {'Name': 'resourcetype', 'Value': 'instance'},
                        {'Name': 'service', 'Value': 'ec2'},
                    ],
                    'Region': 'us-east-1',
                    'Service': 'ec2',
                },
            ],
            'NextToken': 'next-page-token',
        }

        # Call the function
        result = await search_resources(
            self.mock_context,
            query_string=query_string,
            view_arn=view_arn,
            max_results=max_results,
        )

        # Verify the results
        assert len(result['resources']) == 2
        assert result['next_token'] == 'next-page-token'
        assert result['query_string'] == query_string
        assert result['view_arn'] == view_arn
        assert result['count'] == 2

        # Verify the search was called with correct parameters
        self.mock_resource_explorer.search.assert_called_once()

        # Verify info was logged
        self.mock_context.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_resources_with_pagination(self):
        """Test searching resources with pagination."""
        query_string = 'service:ec2'
        view_arn = 'arn:aws:resource-explorer-2:us-east-1:123456789012:view/test-view'
        next_token = 'existing-token'

        # Mock the search response
        self.mock_resource_explorer.search.return_value = {
            'Resources': [
                {
                    'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-abcdef',
                    'Properties': [
                        {'Name': 'resourcetype', 'Value': 'instance'},
                        {'Name': 'service', 'Value': 'ec2'},
                    ],
                    'Region': 'us-east-1',
                    'Service': 'ec2',
                }
            ]
            # No NextToken in response
        }

        # Call the function with next_token
        result = await search_resources(
            self.mock_context, query_string=query_string, view_arn=view_arn, next_token=next_token
        )

        # Verify the results
        assert len(result['resources']) == 1
        assert 'next_token' not in result  # No more pages
        assert result['count'] == 1

        # Verify the search was called with next_token
        self.mock_resource_explorer.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_resources_empty_results(self):
        """Test searching resources with no results."""
        query_string = 'service:nonexistent'
        view_arn = 'arn:aws:resource-explorer-2:us-east-1:123456789012:view/test-view'

        # Mock empty search response
        self.mock_resource_explorer.search.return_value = {'Resources': []}

        # Import the search_resources function
        from awslabs.aws_fis_mcp_server.server import search_resources

        # Call the function
        result = await search_resources(
            self.mock_context, query_string=query_string, view_arn=view_arn
        )

        # Verify the results
        assert len(result['resources']) == 0
        assert result['count'] == 0

    @pytest.mark.asyncio
    async def test_search_resources_error(self):
        """Test error handling when searching resources."""
        query_string = 'service:ec2'
        view_arn = 'arn:aws:resource-explorer-2:us-east-1:123456789012:view/test-view'

        # Mock error response
        self.mock_resource_explorer.search.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'View not found'}}, 'search'
        )

        # Import the search_resources function
        from awslabs.aws_fis_mcp_server.server import search_resources

        # Call the function and expect exception
        with pytest.raises(ClientError):
            await search_resources(self.mock_context, query_string=query_string, view_arn=view_arn)

        # Verify error was logged
        self.mock_context.error.assert_called_once()


class TestExperimentTemplates:
    """Test cases for ExperimentTemplates class."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients and other dependencies."""
        self.mock_aws_fis = MagicMock()
        self.mock_context = AsyncMock()

        with (
            patch.object(server_module, 'aws_fis', self.mock_aws_fis),
            patch.object(server_module, 'allow_writes', True),
        ):
            yield

    @pytest.mark.asyncio
    async def test_create_experiment_template_success(self):
        """Test creating an experiment template successfully."""
        template_id = 'template-1'
        self.mock_aws_fis.create_experiment_template.return_value = {
            'experimentTemplate': {
                'id': template_id,
                'description': 'Test Template',
                'creationTime': '2023-01-01T00:00:00.000Z',
            }
        }

        client_token = 'test-token'
        description = 'Test Template'
        role_arn = 'arn:aws:iam::123456789012:role/FisRole'

        result = await create_experiment_template(
            self.mock_context,
            client_token,
            description,
            role_arn,
            'Test Template',
            None,
        )

        assert 'experimentTemplate' in result
        assert result['experimentTemplate']['id'] == template_id
        self.mock_aws_fis.create_experiment_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_experiment_template_with_all_options(self):
        """Test creating an experiment template with all options."""
        template_id = 'template-1'
        self.mock_aws_fis.create_experiment_template.return_value = {
            'experimentTemplate': {'id': template_id, 'description': 'Test Template'}
        }

        result = await create_experiment_template(
            self.mock_context,
            'test-token',
            'Test Template',
            'arn:aws:iam::123456789012:role/FisRole',
            'Test Template',
            {'Environment': 'Test'},
            [{'source': 'aws:cloudwatch:alarm', 'value': 'test-alarm'}],
            {'Instances': {'resourceType': 'aws:ec2:instance'}},
            {'StopInstances': {'actionId': 'aws:ec2:stop-instances'}},
            {'logSchemaVersion': 1},
            {'actionsMode': 'run-all'},
            {'s3Configuration': {'bucketName': 'test-bucket'}},
        )

        assert 'experimentTemplate' in result
        self.mock_aws_fis.create_experiment_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_experiment_template_error(self):
        """Test error handling when creating an experiment template."""
        self.mock_aws_fis.create_experiment_template.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid role ARN'}},
            'create_experiment_template',
        )

        with pytest.raises(ClientError):
            await create_experiment_template(
                self.mock_context,
                'test-token',
                'Test Template',
                'invalid-arn',
                'Test Template',
                None,
            )

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_experiment_template_success(self):
        """Test updating an experiment template successfully."""
        template_id = 'template-1'
        self.mock_aws_fis.update_experiment_template.return_value = {
            'experimentTemplate': {'id': template_id, 'description': 'Updated Template'}
        }

        result = await update_experiment_template(
            self.mock_context,
            id=template_id,
            description='Updated Template',
        )

        assert 'experimentTemplate' in result
        assert result['experimentTemplate']['description'] == 'Updated Template'
        self.mock_aws_fis.update_experiment_template.assert_called_once()
        self.mock_context.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_experiment_template_with_all_fields(self):
        """Test updating an experiment template with all fields."""
        template_id = 'template-1'
        self.mock_aws_fis.update_experiment_template.return_value = {
            'experimentTemplate': {'id': template_id}
        }

        result = await update_experiment_template(
            self.mock_context,
            id=template_id,
            description='Updated Description',
            stop_conditions=[{'source': 'aws:cloudwatch:alarm', 'value': 'new-alarm'}],
            targets={'NewTargets': {'resourceType': 'aws:ec2:instance'}},
            actions={'NewActions': {'actionId': 'aws:ec2:reboot-instances'}},
            role_arn='arn:aws:iam::123456789012:role/NewFisRole',
            log_configuration={'logSchemaVersion': 2},
            experiment_options={'actionsMode': 'skip-all'},
            experiment_report_configuration={'s3Configuration': {'bucketName': 'new-bucket'}},
        )

        assert 'experimentTemplate' in result
        self.mock_aws_fis.update_experiment_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_experiment_template_error(self):
        """Test error handling when updating an experiment template."""
        template_id = 'template-1'
        self.mock_aws_fis.update_experiment_template.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Template not found'}},
            'update_experiment_template',
        )

        with pytest.raises(ClientError):
            await update_experiment_template(
                self.mock_context,
                id=template_id,
                description='Updated Template',
            )

        self.mock_context.error.assert_called_once()
