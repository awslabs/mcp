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
"""Tests for the cfn MCP Server."""

import pytest
from awslabs.cfn_mcp_server.context import Context
from awslabs.cfn_mcp_server.errors import ClientError
from awslabs.cfn_mcp_server.server import (
    analyze_stack,
    create_resource,
    create_template,
    delete_resource,
    get_resource,
    get_resource_request_status,
    get_resource_schema_information,
    list_related_resources,
    list_resources,
    list_resources_by_filter,
    propose_new_stacks,
    start_resource_scan,
    update_resource,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestReadonly:
    """Test tools for server in readonly."""

    Context.initialize(True)

    async def test_update_resource(self):
        """Testing testing update."""
        with pytest.raises(ClientError):
            await update_resource(
                resource_type='AWS::CodeStarConnections::Connection',
                identifier='identifier',
                patch_document=[],
            )

    async def test_create_resource(self):
        """Testing testing create."""
        with pytest.raises(ClientError):
            await create_resource(
                resource_type='AWS::CodeStarConnections::Connection', properties={}
            )

    async def test_delete_resource(self):
        """Testing testing delete."""
        with pytest.raises(ClientError):
            await delete_resource(
                resource_type='AWS::CodeStarConnections::Connection', identifier='identifier'
            )


@pytest.mark.asyncio
class TestTools:
    """Test tools for server."""

    Context.initialize(False)

    async def test_get_resource_schema_no_type(self):
        """Testing no type provided."""
        with pytest.raises(ClientError):
            await get_resource_schema_information(resource_type=None)

    @patch('awslabs.cfn_mcp_server.server.schema_manager')
    async def test_get_resource_schema(self, mock_schema_manager):
        """Testing getting the schema."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(return_value={'properties': []})
        mock_schema_manager.return_value = mock_instance

        # Call the function
        result = await get_resource_schema_information(
            resource_type='AWS::CodeStarConnections::Connection'
        )

        # Check the result
        assert result == {
            'properties': [],
        }

    async def test_list_resources_no_type(self):
        """Testing no type provided."""
        with pytest.raises(ClientError):
            await list_resources(resource_type=None)

    @patch('awslabs.cfn_mcp_server.server.get_aws_client')
    async def test_list_resources(self, mock_get_aws_client):
        """Testing testing simple list."""
        # Setup the mock
        page = {'ResourceDescriptions': [{'Identifier': 'Identifier'}]}

        # Create a proper mock iterator
        mock_paginator = MagicMock()
        mock_paginator.paginate = MagicMock(
            return_value=[page]
        )  # This returns an iterable with the page

        # Set up the client chain
        mock_client = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_aws_client.return_value = mock_client

        # Call the function
        result = await list_resources(resource_type='AWS::CodeStarConnections::Connection')

        # Check the result
        assert result == ['Identifier']

    async def test_get_resource_no_type(self):
        """Testing no type provided."""
        with pytest.raises(ClientError):
            await get_resource(resource_type=None, identifier='identifier')

    async def test_get_resource_no_identifier(self):
        """Testing no identifier provided."""
        with pytest.raises(ClientError):
            await get_resource(
                resource_type='AWS::CodeStarConnections::Connection', identifier=None
            )

    @patch('awslabs.cfn_mcp_server.server.get_aws_client')
    async def test_get_resource(self, mock_get_aws_client):
        """Testing simple get."""
        # Setup the mock
        mock_get_resource_return_value = MagicMock(
            return_value={
                'ResourceDescription': {'Identifier': 'Identifier', 'Properties': 'Properties'}
            }
        )
        mock_cloudcontrol_client = MagicMock(get_resource=mock_get_resource_return_value)
        mock_get_aws_client.return_value = mock_cloudcontrol_client

        # Call the function
        result = await get_resource(
            resource_type='AWS::CodeStarConnections::Connection', identifier='identifier'
        )

        # Check the result
        assert result == {
            'properties': 'Properties',
            'identifier': 'Identifier',
        }

    async def test_update_resource_no_type(self):
        """Testing testing update with no type."""
        with pytest.raises(ClientError):
            await update_resource(resource_type=None, identifier='identifier', patch_document=[])

    async def test_update_resource_no_identifier(self):
        """Testing no identifier provided."""
        with pytest.raises(ClientError):
            await update_resource(
                resource_type='AWS::CodeStarConnections::Connection',
                identifier=None,
                patch_document=[],
            )

    async def test_update_resource_no_patch(self):
        """Testing no patch provided."""
        with pytest.raises(ClientError):
            await update_resource(
                identifier='identifier',
                resource_type='AWS::CodeStarConnections::Connection',
                patch_document=None,
            )

    @patch('awslabs.cfn_mcp_server.server.get_aws_client')
    async def test_update_resource(self, mock_get_aws_client):
        """Testing simple update."""
        # Setup the mock
        response = {
            'ProgressEvent': {
                'OperationStatus': 'SUCCESS',
                'TypeName': 'AWS::CodeStarConnections::Connection',
                'RequestToken': 'RequestToken',
            }
        }
        mock_update_resource_return_value = MagicMock(return_value=response)
        mock_cloudcontrol_client = MagicMock(update_resource=mock_update_resource_return_value)
        mock_get_aws_client.return_value = mock_cloudcontrol_client

        # Call the function
        result = await update_resource(
            resource_type='AWS::CodeStarConnections::Connection',
            identifier='identifier',
            patch_document=[{'op': 'remove', 'path': '/item'}],
        )

        # Check the result
        assert result == {
            'status': 'SUCCESS',
            'resource_type': 'AWS::CodeStarConnections::Connection',
            'is_complete': True,
            'request_token': 'RequestToken',
        }

    async def test_create_resource_no_type(self):
        """Testing no type provided."""
        with pytest.raises(ClientError):
            await create_resource(resource_type=None, properties={})

    async def test_create_resource_no_properties(self):
        """Testing no properties provided."""
        with pytest.raises(ClientError):
            await create_resource(
                resource_type='AWS::CodeStarConnections::Connection', properties=None
            )

    @patch('awslabs.cfn_mcp_server.server.get_aws_client')
    async def test_create_resource(self, mock_get_aws_client):
        """Testing simple create."""
        # Setup the mock
        response = {
            'ProgressEvent': {
                'OperationStatus': 'SUCCESS',
                'TypeName': 'AWS::CodeStarConnections::Connection',
                'RequestToken': 'RequestToken',
            }
        }
        mock_create_resource_return_value = MagicMock(return_value=response)
        mock_cloudcontrol_client = MagicMock(create_resource=mock_create_resource_return_value)
        mock_get_aws_client.return_value = mock_cloudcontrol_client

        # Call the function
        result = await create_resource(
            resource_type='AWS::CodeStarConnections::Connection',
            properties={'ConnectionName': 'Name'},
        )

        # Check the result
        assert result == {
            'status': 'SUCCESS',
            'resource_type': 'AWS::CodeStarConnections::Connection',
            'is_complete': True,
            'request_token': 'RequestToken',
        }

    async def test_delete_resource_no_type(self):
        """Testing simple delete."""
        with pytest.raises(ClientError):
            await delete_resource(resource_type=None, identifier='Identifier')

    async def test_delete_resource_no_identifier(self):
        """Testing no identifier on delete."""
        with pytest.raises(ClientError):
            await delete_resource(
                resource_type='AWS::CodeStarConnections::Connection', identifier=None
            )

    @patch('awslabs.cfn_mcp_server.server.get_aws_client')
    async def test_delete_resource(self, mock_get_aws_client):
        """Testing simple delete."""
        # Setup the mock
        response = {
            'ProgressEvent': {
                'OperationStatus': 'SUCCESS',
                'TypeName': 'AWS::CodeStarConnections::Connection',
                'RequestToken': 'RequestToken',
            }
        }
        mock_delete_resource_return_value = MagicMock(return_value=response)
        mock_cloudcontrol_client = MagicMock(delete_resource=mock_delete_resource_return_value)
        mock_get_aws_client.return_value = mock_cloudcontrol_client

        # Call the function
        result = await delete_resource(
            resource_type='AWS::CodeStarConnections::Connection', identifier='Identifier'
        )

        # Check the result
        assert result == {
            'status': 'SUCCESS',
            'resource_type': 'AWS::CodeStarConnections::Connection',
            'is_complete': True,
            'request_token': 'RequestToken',
        }

    async def test_get_request_status_no_token(self):
        """Testing no token."""
        with pytest.raises(ClientError):
            await get_resource_request_status(request_token=None)

    @patch('awslabs.cfn_mcp_server.server.get_aws_client')
    async def test_get_resource_request_status(self, mock_get_aws_client):
        """Testing get resource request status."""
        # Setup the mock
        response = {
            'ProgressEvent': {
                'OperationStatus': 'SUCCESS',
                'TypeName': 'AWS::CodeStarConnections::Connection',
                'RequestToken': 'RequestToken',
            }
        }
        mock_get_status_return_value = MagicMock(return_value=response)
        mock_cloudcontrol_client = MagicMock(
            get_resource_request_status=mock_get_status_return_value
        )
        mock_get_aws_client.return_value = mock_cloudcontrol_client

        # Call the function
        result = await get_resource_request_status(request_token='RequestToken')

        # Check the result
        assert result == {
            'status': 'SUCCESS',
            'resource_type': 'AWS::CodeStarConnections::Connection',
            'is_complete': True,
            'request_token': 'RequestToken',
        }

    @patch('awslabs.cfn_mcp_server.server.create_template_impl')
    async def test_create_template(self, mock_create_template_impl):
        """Testing create_template function."""
        # Setup the mock
        mock_create_template_impl.return_value = {
            'status': 'INITIATED',
            'template_id': 'test-template-id',
            'message': 'Template generation initiated.',
        }

        # Call the function
        result = await create_template(
            template_name='test-template',
            resources=[{'ResourceType': 'AWS::S3::Bucket', 'ResourceIdentifier': 'test-bucket'}],
            output_format='YAML',
            deletion_policy='RETAIN',
            update_replace_policy='RETAIN',
        )

        # Check the result
        assert result == {
            'status': 'INITIATED',
            'template_id': 'test-template-id',
            'message': 'Template generation initiated.',
        }

        # Verify the implementation was called with the correct parameters
        mock_create_template_impl.assert_called_once()

    @patch('awslabs.cfn_mcp_server.server.list_resources_by_filter_impl')
    async def test_list_resources_by_filter(self, mock_list_resources_by_filter_impl):
        """Testing list_resources_by_filter function."""
        # Setup the mock
        mock_list_resources_by_filter_impl.return_value = {
            'resources': [
                {
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceIdentifier': {'BucketName': 'test-bucket'},
                }
            ],
            'next_token': None,
        }

        # Call the function
        result = await list_resources_by_filter(
            resource_type_prefix='AWS::S3::',
            tag_key='Environment',
            tag_value='Test',
            limit=10,
        )

        # Check the result
        assert result['resources'][0]['ResourceType'] == 'AWS::S3::Bucket'
        assert result['resources'][0]['ResourceIdentifier']['BucketName'] == 'test-bucket'
        assert result['next_token'] is None

        # Verify the implementation was called with the correct parameters
        mock_list_resources_by_filter_impl.assert_called_once()

    @patch('awslabs.cfn_mcp_server.server.list_related_resources_impl')
    async def test_list_related_resources(self, mock_list_related_resources_impl):
        """Testing list_related_resources function."""
        # Setup the mock
        mock_list_related_resources_impl.return_value = {
            'related_resources': [
                {
                    'ResourceType': 'AWS::IAM::Role',
                    'ResourceIdentifier': {'RoleName': 'test-role'},
                    'ManagedByStack': False,
                }
            ],
            'next_token': None,
        }

        # Call the function
        resources = [
            {
                'resource_type': 'AWS::S3::Bucket',
                'resource_identifier': {'BucketName': 'test-bucket'},
            }
        ]
        result = await list_related_resources(resources=resources, max_results=10)

        # Check the result
        assert result['related_resources'][0]['ResourceType'] == 'AWS::IAM::Role'
        assert result['related_resources'][0]['ResourceIdentifier']['RoleName'] == 'test-role'
        assert result['next_token'] is None

        # Verify the implementation was called
        assert mock_list_related_resources_impl.called
        call_args = mock_list_related_resources_impl.call_args[1]
        assert call_args['resources'] == resources
        assert call_args['max_results'] == 10

    @patch('awslabs.cfn_mcp_server.server.handle_start_resource_scan')
    async def test_start_resource_scan(self, mock_handle_start_resource_scan):
        """Testing start_resource_scan function."""
        # Setup the mock
        mock_handle_start_resource_scan.return_value = {
            'scan_id': 'test-scan-id',
        }

        # Call the function
        result = await start_resource_scan(resource_types=['AWS::S3::Bucket'])

        # Check the result
        assert result['scan_id'] == 'test-scan-id'

        # Verify the implementation was called
        assert mock_handle_start_resource_scan.called
        call_args = mock_handle_start_resource_scan.call_args[1]
        assert call_args['resource_types'] == ['AWS::S3::Bucket']

    @patch('awslabs.cfn_mcp_server.server.StackAnalyzer')
    async def test_analyze_stack_success(self, mock_stack_analyzer_class):
        """Test analyze_stack with successful stack analysis."""
        # Mock the StackAnalyzer instance
        mock_analyzer = MagicMock()
        mock_stack_analyzer_class.return_value = mock_analyzer

        # Mock the get_best_cfn_practices method
        mock_stack_analyzer_class.get_best_cfn_practices.return_value = {
            'resource_management': 'Manage all stack resources through CloudFormation.',
            'stack_policies': 'Use stack policies to prevent unintentional updates.',
        }

        # Mock the analyze_stack method with the new structure
        mock_analyzer.analyze_stack.return_value = {
            'stack_info': {
                'StackName': 'test-stack',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': '2023-01-01T00:00:00Z',
                'LastUpdatedTime': '2023-01-02T00:00:00Z',
            },
            'stack_status': 'CREATE_COMPLETE',
            'creation_time': '2023-01-01T00:00:00Z',
            'last_updated_time': '2023-01-02T00:00:00Z',
            'outputs': [{'OutputKey': 'BucketName', 'OutputValue': 'test-bucket'}],
            'parameters': [{'ParameterKey': 'Environment', 'ParameterValue': 'test'}],
            'resource_summary': {
                'total_resources': 10,
                'managed_resources': 10,
                'unmanaged_resources': 0,
            },
            'related_resources_summary': {
                'total_resources': 5,
                'managed_resources': 3,
                'unmanaged_resources': 2,
                'by_product_type': [],
            },
            'account_summary': {
                'overall_summary': {
                    'total_resources': 100,
                    'managed_resources': 80,
                    'unmanaged_resources': 20,
                    'managed_percentage': 80.0,
                    'unmanaged_percentage': 20.0,
                },
                'scan_metadata': {
                    'scan_id': 'test-scan-id',
                    'scan_time': '2023-01-01T00:00:00Z',
                },
            },
            'augment_recommendation': 'template-id-123',
            'related_unmanaged_count': 2,
        }

        # Call the function
        result = await analyze_stack(stack_name='test-stack', region='us-east-1')

        # Verify the StackAnalyzer was created with the correct region
        mock_stack_analyzer_class.assert_called_once_with('us-east-1')

        # Verify analyze_stack was called with the correct stack name
        mock_analyzer.analyze_stack.assert_called_once_with('test-stack')

        # Verify the result structure matches the new implementation
        assert 'message' in result
        assert 'stack_info' in result
        assert 'stack_status' in result
        assert 'creation_time' in result
        assert 'last_updated_time' in result
        assert 'outputs' in result
        assert 'parameters' in result
        assert 'resource_summary' in result
        assert 'related_resources_summary' in result
        assert 'account_summary' in result
        assert 'template_generation_info' in result
        assert 'augment_recommendation' in result
        assert 'related_unmanaged_count' in result
        assert 'best_practices' in result

    @patch('awslabs.cfn_mcp_server.server.RecommendationGenerator')
    async def test_propose_new_stacks(self, mock_recommendation_generator_class):
        """Test propose_new_stacks function."""
        # Mock the RecommendationGenerator instance
        mock_generator = MagicMock()
        mock_recommendation_generator_class.return_value = mock_generator

        # Mock the propose_new_stacks_by_product_type method
        mock_generator.propose_new_stacks_by_product_type.return_value = {
            'summary': {
                'total_unmanaged_resources': 100,
                'resources_in_proposals': 100,
                'stack_proposals': 2,
                'successful_templates': 2,
            },
            'grouped_proposals': {
                'Compute': [
                    {
                        'stack_name': 'ComputeStack1',
                        'resource_count': 50,
                        'template_status': 'COMPLETE',
                    }
                ],
                'Storage': [
                    {
                        'stack_name': 'StorageStack1',
                        'resource_count': 50,
                        'template_status': 'COMPLETE',
                    }
                ],
            },
        }

        # Call the function
        result = await propose_new_stacks(
            product_type='Compute', create_templates=True, region='us-east-1'
        )

        # Verify the RecommendationGenerator was created with the correct region
        mock_recommendation_generator_class.assert_called_once_with(region='us-east-1')

        # Verify propose_new_stacks_by_product_type was called with the correct parameters
        mock_generator.propose_new_stacks_by_product_type.assert_called_once_with(
            product_type='Compute', create_templates=True
        )

        # Verify the result structure
        assert 'summary' in result
        assert 'grouped_proposals' in result
        assert 'template_generation_info' in result
        assert result['template_generation_info']['successful_templates'] == 2
