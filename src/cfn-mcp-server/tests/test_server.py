# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the cfn MCP Server."""

import pytest
from awslabs.cfn_mcp_server.context import Context
from awslabs.cfn_mcp_server.errors import ClientError
from awslabs.cfn_mcp_server.server import (
    create_resource,
    delete_resource,
    get_resource_request_status,
    get_resource,
    get_resource_schema_information,
    list_resources,
    update_resource,
    create_template,
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

    async def test_get_request_type_no_token(self):
        """Testing no token."""
        with pytest.raises(ClientError):
            await get_resource_request_status(request_token='Token')

    @patch('awslabs.cfn_mcp_server.server.create_template_impl')
    async def test_create_template(self, mock_create_template_impl):
        """Testing create_template function."""
        # Setup the mock
        mock_create_template_impl.return_value = {
            "status": "INITIATED",
            "template_id": "test-template-id",
            "message": "Template generation initiated."
        }

        # Call the function
        result = await create_template(
            template_name="test-template",
            resources=[{"ResourceType": "AWS::S3::Bucket", "ResourceIdentifier": "test-bucket"}],
            output_format="YAML",
            deletion_policy="RETAIN",
            update_replace_policy="RETAIN"
        )

        # Check the result
        assert result == {
            "status": "INITIATED",
            "template_id": "test-template-id",
            "message": "Template generation initiated."
        }
        
        # Verify the implementation was called with the correct parameters
        mock_create_template_impl.assert_called_once()
