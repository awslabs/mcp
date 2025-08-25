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

"""Tests for improvements to AWS CI/CD MCP Server."""

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from awslabs.aws_cicd_mcp_server.core.common.utils import paginate_results, validate_iam_role, validate_s3_bucket
from awslabs.aws_cicd_mcp_server.core.codepipeline import tools as pipeline_tools


@pytest.mark.asyncio
async def test_pagination_support():
    """Test that pagination is properly implemented."""
    with patch('boto3.client') as mock_client:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'pipelines': [{'name': 'pipeline1'}, {'name': 'pipeline2'}]},
            {'pipelines': [{'name': 'pipeline3'}]}
        ]
        mock_client.return_value.get_paginator.return_value = mock_paginator
        
        result = await pipeline_tools.list_pipelines(max_items=50)
        
        assert 'pipelines' in result
        assert result['count'] == 3
        mock_client.return_value.get_paginator.assert_called_with('list_pipelines')


@pytest.mark.asyncio
async def test_resource_validation():
    """Test that resource validation works."""
    with patch('boto3.client') as mock_client:
        # Test successful validation
        mock_client.return_value.get_role.return_value = {'Role': {'RoleName': 'test-role'}}
        result = await validate_iam_role('arn:aws:iam::123456789012:role/test-role')
        assert result is True
        
        # Test failed validation
        mock_client.return_value.get_role.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchEntity', 'Message': 'Role not found'}},
            'GetRole'
        )
        result = await validate_iam_role('arn:aws:iam::123456789012:role/missing-role')
        assert result is False


@pytest.mark.asyncio
async def test_error_handling_decorator():
    """Test that error handling decorator provides helpful messages."""
    with patch('boto3.client') as mock_client:
        from botocore.exceptions import ClientError
        
        # Simulate AccessDenied error
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'User is not authorized'
            }
        }
        error = ClientError(error_response, 'ListPipelines')
        
        # Mock both paginator and direct call to raise the same error
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = error
        mock_client.return_value.get_paginator.return_value = mock_paginator
        mock_client.return_value.list_pipelines.side_effect = error
        
        result = await pipeline_tools.list_pipelines()
        
        assert 'error' in result
        assert 'IAM permissions' in result['error']
        assert 'CodePipeline' in result['error']


@pytest.mark.asyncio
async def test_create_pipeline_with_validation():
    """Test pipeline creation with resource validation."""
    from unittest.mock import AsyncMock
    
    with patch('boto3.client') as mock_client, \
         patch('awslabs.aws_cicd_mcp_server.core.codepipeline.tools.validate_iam_role') as mock_validate_role, \
         patch('awslabs.aws_cicd_mcp_server.core.codepipeline.tools.validate_s3_bucket') as mock_validate_bucket, \
         patch('awslabs.aws_cicd_mcp_server.core.codepipeline.tools.READ_ONLY_MODE', False):
        
        # Test validation failure
        mock_validate_role.return_value = False
        
        result = await pipeline_tools.create_pipeline(
            'test-pipeline', 
            'arn:aws:iam::123456789012:role/invalid-role',
            'test-bucket',
            'test-repo'
        )
        
        assert 'error' in result
        assert 'not found or not accessible' in result['error']
