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

"""Tests for CodePipeline tools."""

import pytest
from awslabs.aws_cicd_mcp_server.core.codepipeline.tools import (
    list_pipelines,
    get_pipeline_details,
    start_pipeline_execution,
    get_pipeline_execution_history,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
@patch('boto3.client')
async def test_list_pipelines_success(mock_boto_client):
    """Test successful pipeline listing."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    
    # Mock paginator
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {'pipelines': [
            {'name': 'test-pipeline-1'},
            {'name': 'test-pipeline-2'}
        ]}
    ]
    mock_client.get_paginator.return_value = mock_paginator
    
    result = await list_pipelines()
    
    assert result['count'] == 2
    assert 'test-pipeline-1' in result['pipelines']
    assert result['region'] == 'us-east-1'


@pytest.mark.asyncio
@patch('boto3.client')
async def test_list_pipelines_error(mock_boto_client):
    """Test pipeline listing with error."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    error = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        'ListPipelines'
    )
    
    # Mock both paginator and direct call to raise the same error
    mock_paginator = MagicMock()
    mock_paginator.paginate.side_effect = error
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.list_pipelines.side_effect = error
    
    result = await list_pipelines()
    
    assert 'error' in result


@pytest.mark.asyncio
@patch('awslabs.aws_cicd_mcp_server.core.common.config.READ_ONLY_MODE', True)
async def test_start_pipeline_execution_read_only(mock_boto_client):
    """Test pipeline execution start in read-only mode."""
    result = await start_pipeline_execution('test-pipeline')
    
    assert 'error' in result
    assert 'read-only mode' in result['error']
