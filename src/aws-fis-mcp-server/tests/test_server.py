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
from awslabs.aws_fis_mcp_server.server import AwsFisActions, ExperimentTemplates, ResourceDiscovery
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


class TestAwsFisActions:
    """Test cases for AwsFisActions class."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients and other dependencies."""
        self.mock_aws_fis = MagicMock()
        self.mock_context = AsyncMock()
        self.fis_actions = AwsFisActions()

        with patch.object(server_module, 'aws_fis', self.mock_aws_fis):
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

        result = await self.fis_actions.list_all_fis_experiments.fn(self.mock_context)

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

        result = await self.fis_actions.list_all_fis_experiments.fn(self.mock_context)

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
            await self.fis_actions.list_all_fis_experiments.fn(self.mock_context)

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

        result = await self.fis_actions.get_experiment_details.fn(
            self.mock_context, id=experiment_id
        )

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
            await self.fis_actions.get_experiment_details.fn(self.mock_context, id=experiment_id)

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

        result = await self.fis_actions.list_experiment_templates.fn(self.mock_context)

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

        result = await self.fis_actions.get_experiment_template.fn(
            self.mock_context, id=template_id
        )

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
            result = await self.fis_actions.start_experiment.fn(
                self.mock_context,
                id=template_id,
                tags=tags,
                max_timeout_seconds=10,
            )

        assert result['id'] == experiment_id
        assert result['state']['status'] == 'completed'
        self.mock_aws_fis.start_experiment.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_experiment_timeout(self):
        """Test starting an experiment that times out."""
        template_id = 'template-1'
        experiment_id = 'exp-1'

        self.mock_aws_fis.start_experiment.return_value = {
            'experiment': {'id': experiment_id, 'state': {'status': 'pending'}}
        }

        self.mock_aws_fis.get_experiment.return_value = {
            'experiment': {'id': experiment_id, 'state': {'status': 'pending'}}
        }

        with patch('asyncio.sleep', new_callable=AsyncMock), patch('time.time') as mock_time:
            mock_time.side_effect = [0, 0, 11]  # Simulate timeout

            with pytest.raises(TimeoutError):
                await self.fis_actions.start_experiment.fn(
                    self.mock_context,
                    id=template_id,
                    max_timeout_seconds=10,
                    initial_poll_interval=1,
                )

    @pytest.mark.asyncio
    async def test_start_experiment_stopped_state(self):
        """Test starting an experiment that gets stopped."""
        template_id = 'template-1'
        experiment_id = 'exp-1'

        self.mock_aws_fis.start_experiment.return_value = {
            'experiment': {'id': experiment_id, 'state': {'status': 'pending'}}
        }

        self.mock_aws_fis.get_experiment.return_value = {
            'experiment': {
                'id': experiment_id,
                'state': {'status': 'stopped'},
            }
        }

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await self.fis_actions.start_experiment.fn(
                self.mock_context, id=template_id, max_timeout_seconds=10
            )
            assert result['state']['status'] == 'stopped'

    @pytest.mark.asyncio
    async def test_start_experiment_not_found_error(self):
        """Test starting an experiment with 'experiment not found' error."""
        template_id = 'template-1'
        experiment_id = 'exp-1'

        self.mock_aws_fis.start_experiment.return_value = {
            'experiment': {'id': experiment_id, 'state': {'status': 'pending'}}
        }

        self.mock_aws_fis.get_experiment.side_effect = Exception('Experiment not found')

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(Exception, match='Experiment not found'):
                await self.fis_actions.start_experiment.fn(
                    self.mock_context, id=template_id, max_timeout_seconds=10
                )

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

        result = await self.fis_actions.list_experiment_templates.fn(self.mock_context)

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
            await self.fis_actions.list_experiment_templates.fn(self.mock_context)

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
            await self.fis_actions.get_experiment_template.fn(self.mock_context, id=template_id)

        self.mock_context.error.assert_called_once()


class TestResourceDiscovery:
    """Test cases for ResourceDiscovery class."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients and other dependencies."""
        self.mock_resource_explorer = MagicMock()
        self.mock_cloudformation = MagicMock()
        self.mock_context = AsyncMock()
        self.resource_discovery = ResourceDiscovery()

        with (
            patch.object(server_module, 'resource_explorer', self.mock_resource_explorer),
            patch.object(server_module, 'cloudformation', self.mock_cloudformation),
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

        result = await self.resource_discovery.list_cfn_stacks(self.mock_context)

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

        result = await self.resource_discovery.get_stack_resources(
            self.mock_context, stack_name=stack_name
        )

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

        result = await self.resource_discovery.list_views(self.mock_context)

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
            result = await self.resource_discovery.create_view.fn(
                self.mock_context,
                query=query,
                view_name=view_name,
                tags=tags,
            )

        assert 'View' in result
        assert result['View']['ViewName'] == view_name
        self.mock_resource_explorer.create_view.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_resources_resource_explorer_only(self):
        """Test discovering resources from Resource Explorer only."""
        query = 'service:ec2'
        self.mock_resource_explorer.search.return_value = {
            'Resources': [
                {
                    'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-12345',
                    'Region': 'us-east-1',
                    'ResourceType': 'AWS::EC2::Instance',
                    'Service': 'ec2',
                }
            ]
        }

        result = await self.resource_discovery.discover_resources.fn(
            self.mock_context, source='resource-explorer', query=query
        )

        assert 'resources' in result
        assert len(result['resources']) == 1
        assert result['resources'][0]['source'] == 'resource-explorer'
        assert result['resources'][0]['service'] == 'ec2'

    @pytest.mark.asyncio
    async def test_discover_resources_cloudformation_missing_stack_name(self):
        """Test error when CloudFormation source is specified without stack name."""
        with pytest.raises(ValueError, match='stack_name is required'):
            await self.resource_discovery.discover_resources.fn(
                self.mock_context,
                source='cloudformation',
                stack_name=None,
            )

    @pytest.mark.asyncio
    async def test_discover_resources_resource_explorer_error(self):
        """Test discover_resources with Resource Explorer error handling."""
        # Mock Resource Explorer search to fail
        self.mock_resource_explorer.search.side_effect = Exception('Access denied')

        result = await self.resource_discovery.discover_resources.fn(
            self.mock_context, source='resource-explorer'
        )

        # Should return empty resources list
        assert 'resources' in result
        assert len(result['resources']) == 0
        # Should have called warning for the error
        self.mock_context.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_resources_cloudformation_with_stack_name(self):
        """Test discover_resources with cloudformation source and stack name."""
        stack_name = 'test-stack'

        # Mock get_stack_resources to return some resources
        mock_resources = {
            'resources': [
                {
                    'ResourceType': 'AWS::EC2::Instance',
                    'LogicalResourceId': 'MyInstance',
                    'PhysicalResourceId': 'i-12345',
                    'ResourceStatus': 'CREATE_COMPLETE',
                }
            ]
        }

        # Mock the static method using patch
        with patch.object(
            ResourceDiscovery, 'get_stack_resources', new_callable=AsyncMock
        ) as mock_get_stack:
            mock_get_stack.return_value = mock_resources

            result = await self.resource_discovery.discover_resources.fn(
                self.mock_context,
                source='cloudformation',
                stack_name=stack_name,
            )

            # Should have resources from the stack
            assert 'resources' in result
            assert len(result['resources']) == 1
            assert result['resources'][0]['source'] == 'cloudformation'
            assert result['resources'][0]['stack_name'] == stack_name

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

        result = await self.resource_discovery.list_cfn_stacks(self.mock_context)

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
            await self.resource_discovery.list_cfn_stacks(self.mock_context)

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

        result = await self.resource_discovery.get_stack_resources(
            self.mock_context, stack_name=stack_name
        )

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
            await self.resource_discovery.get_stack_resources(
                self.mock_context, stack_name=stack_name
            )

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

        result = await self.resource_discovery.list_views(self.mock_context)

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
            await self.resource_discovery.list_views(self.mock_context)

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
            result = await self.resource_discovery.create_view.fn(
                self.mock_context, query=query, view_name=view_name
            )

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
            await self.resource_discovery.create_view.fn(
                self.mock_context,
                query=query,
                view_name=view_name,
                client_token=None,
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
            await self.resource_discovery.create_view.fn(
                self.mock_context,
                query='service:ec2',
                view_name='invalid-view',
            )

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_resources_with_pagination(self):
        """Test discovering resources with pagination from Resource Explorer."""
        query = 'service:ec2'
        self.mock_resource_explorer.search.side_effect = [
            {
                'Resources': [
                    {
                        'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-12345',
                        'Service': 'ec2',
                        'ResourceType': 'AWS::EC2::Instance',
                    }
                ],
                'NextToken': 'token1',
            },
            {
                'Resources': [
                    {
                        'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-67890',
                        'Service': 'ec2',
                        'ResourceType': 'AWS::EC2::Instance',
                    }
                ]
            },
        ]

        result = await self.resource_discovery.discover_resources.fn(
            self.mock_context,
            source='resource-explorer',
            query=query,
            max_results=10,
        )

        assert 'resources' in result
        assert len(result['resources']) == 2
        assert (
            result['resources'][0]['arn'] == 'arn:aws:ec2:us-east-1:123456789012:instance/i-12345'
        )
        assert (
            result['resources'][1]['arn'] == 'arn:aws:ec2:us-east-1:123456789012:instance/i-67890'
        )

    @pytest.mark.asyncio
    async def test_discover_resources_max_results_with_pagination(self):
        """Test resource discovery hitting max_results limit during pagination."""
        query = 'service:ec2'

        # Mock paginated response - first call returns 1 resource with NextToken, second call returns 2 more
        self.mock_resource_explorer.search.side_effect = [
            {
                'Resources': [
                    {
                        'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-1',
                        'ResourceType': 'ec2:instance',
                    }
                ],
                'NextToken': 'token1',
            },
            {
                'Resources': [
                    {
                        'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-2',
                        'ResourceType': 'ec2:instance',
                    },
                    {
                        'Arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-3',
                        'ResourceType': 'ec2:instance',
                    },
                ]
            },
        ]

        result = await self.resource_discovery.discover_resources.fn(
            self.mock_context,
            source='resource-explorer',
            query=query,
            max_results=2,
        )

        assert 'resources' in result
        assert (
            len(result['resources']) == 2
        )  # Should break when hitting max_results during pagination


class TestExperimentTemplates:
    """Test cases for ExperimentTemplates class."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients and other dependencies."""
        self.mock_aws_fis = MagicMock()
        self.mock_context = AsyncMock()
        self.experiment_templates = ExperimentTemplates()

        with patch.object(server_module, 'aws_fis', self.mock_aws_fis):
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

        result = await self.experiment_templates.create_experiment_template.fn(
            self.mock_context,
            clientToken=client_token,
            description=description,
            role_arn=role_arn,
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

        result = await self.experiment_templates.create_experiment_template.fn(
            self.mock_context,
            clientToken='test-token',
            description='Test Template',
            role_arn='arn:aws:iam::123456789012:role/FisRole',
            tags={'Environment': 'Test'},
            stop_conditions=[{'source': 'aws:cloudwatch:alarm', 'value': 'test-alarm'}],
            targets={'Instances': {'resourceType': 'aws:ec2:instance'}},
            actions={'StopInstances': {'actionId': 'aws:ec2:stop-instances'}},
            log_configuration={'logSchemaVersion': 1},
            experiment_options={'actionsMode': 'run-all'},
            report_configuration={'s3Configuration': {'bucketName': 'test-bucket'}},
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
            await self.experiment_templates.create_experiment_template.fn(
                self.mock_context,
                clientToken='test-token',
                description='Test Template',
                role_arn='invalid-arn',
            )

        self.mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_experiment_template_success(self):
        """Test updating an experiment template successfully."""
        template_id = 'template-1'
        self.mock_aws_fis.update_experiment_template.return_value = {
            'experimentTemplate': {'id': template_id, 'description': 'Updated Template'}
        }

        result = await self.experiment_templates.update_experiment_template.fn(
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

        result = await self.experiment_templates.update_experiment_template.fn(
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
            await self.experiment_templates.update_experiment_template.fn(
                self.mock_context,
                id=template_id,
                description='Updated Template',
            )

        self.mock_context.error.assert_called_once()
