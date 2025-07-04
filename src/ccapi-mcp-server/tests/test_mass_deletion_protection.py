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
"""Tests for the mass deletion protection in the cfn MCP Server."""

import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.server import (
    create_template_tool as create_template,
)
from awslabs.ccapi_mcp_server.server import (
    delete_resource,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
class TestMassDeletionProtection:
    """Test mass deletion protection features."""

    @patch('awslabs.ccapi_mcp_server.server.get_aws_client')
    async def test_delete_resource_with_confirmation(self, mock_get_aws_client):
        """Test deleting a single resource with confirmation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client.delete_resource.return_value = {
            'ProgressEvent': {
                'OperationStatus': 'SUCCESS',
                'TypeName': 'AWS::S3::Bucket',
                'RequestToken': 'test-token',
            }
        }
        mock_get_aws_client.return_value = mock_client

        # Mock aws_session_info
        aws_session_info = {
            'account_id': '123456789012',
            'region': 'us-east-1',
            'readonly_mode': False,
        }

        # Call the function
        result = await delete_resource(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            confirmed=True,
            aws_session_info=aws_session_info,
        )

        # Verify results
        assert result['status'] == 'SUCCESS'
        assert result['resource_type'] == 'AWS::S3::Bucket'
        assert result['request_token'] == 'test-token'

    async def test_delete_resource_without_confirmation(self):
        """Test deleting a resource without confirmation."""
        # Call the function and expect it to fail
        with pytest.raises(ClientError, match='Please confirm the deletion'):
            await delete_resource(
                resource_type='AWS::S3::Bucket', identifier='test-bucket', confirmed=False
            )

    @patch('awslabs.ccapi_mcp_server.iac_generator.create_template')
    async def test_create_template_for_resource_cleanup(self, mock_create_template):
        """Test creating a template for resource cleanup."""
        # Setup mocks
        mock_create_template.return_value = {
            'status': 'INITIATED',
            'template_id': 'test-template-id',
            'message': 'Template generation initiated.',
        }

        # Call the function
        result = await create_template(
            template_name='cleanup-template',
            resources=[
                {
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceIdentifier': {'BucketName': 'test-bucket'},
                }
            ],
            output_format='YAML',
            deletion_policy='DELETE',
            update_replace_policy='RETAIN',
        )

        # Verify results
        assert result['status'] == 'INITIATED'
        assert result['template_id'] == 'test-template-id'
        mock_create_template.assert_called_once_with(
            template_name='cleanup-template',
            resources=[
                {
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceIdentifier': {'BucketName': 'test-bucket'},
                }
            ],
            output_format='YAML',
            deletion_policy='DELETE',
            update_replace_policy='RETAIN',
            template_id=None,
            save_to_file=None,
            region_name=None,
        )
