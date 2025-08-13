# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for AWS CI/CD MCP Server fixes."""

import pytest
from unittest.mock import patch, MagicMock
from awslabs.aws_cicd_mcp_server.core.codepipeline import tools as pipeline_tools
from awslabs.aws_cicd_mcp_server.core.codebuild import tools as build_tools
from awslabs.aws_cicd_mcp_server.core.codedeploy import tools as deploy_tools


@pytest.mark.asyncio
async def test_list_pipelines_pagination():
    """Test pagination works for list_pipelines."""
    with patch('boto3.client') as mock_client:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'pipelines': [{'name': 'pipeline1'}, {'name': 'pipeline2'}]}
        ]
        mock_client.return_value.get_paginator.return_value = mock_paginator
        
        result = await pipeline_tools.list_pipelines(max_items=50)
        
        assert 'pipelines' in result
        assert result['count'] == 2
        assert 'pipeline1' in result['pipelines']


@pytest.mark.asyncio
async def test_list_projects_pagination():
    """Test pagination works for list_projects."""
    with patch('boto3.client') as mock_client:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'projects': ['project1', 'project2']}
        ]
        mock_client.return_value.get_paginator.return_value = mock_paginator
        
        result = await build_tools.list_projects(max_items=50)
        
        assert 'projects' in result
        assert result['count'] == 2
        assert 'project1' in result['projects']


@pytest.mark.asyncio
async def test_list_applications_pagination():
    """Test pagination works for list_applications."""
    with patch('boto3.client') as mock_client:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'applications': ['app1', 'app2']}
        ]
        mock_client.return_value.get_paginator.return_value = mock_paginator
        
        result = await deploy_tools.list_applications(max_items=50)
        
        assert 'applications' in result
        assert result['count'] == 2
        assert 'app1' in result['applications']


@pytest.mark.asyncio
async def test_error_handling_decorator():
    """Test error handling decorator provides helpful messages."""
    with patch('boto3.client') as mock_client:
        from botocore.exceptions import ClientError
        
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'User is not authorized'
            }
        }
        mock_client.return_value.get_pipeline.side_effect = ClientError(error_response, 'GetPipeline')
        
        result = await pipeline_tools.get_pipeline_details('test-pipeline')
        
        assert 'error' in result
        assert 'IAM permissions' in result['error']


@pytest.mark.asyncio
async def test_resource_validation():
    """Test resource validation works."""
    with patch('awslabs.aws_cicd_mcp_server.core.common.utils.boto3.client') as mock_client:
        # Test successful validation
        mock_client.return_value.get_role.return_value = {'Role': {'RoleName': 'test-role'}}
        
        from awslabs.aws_cicd_mcp_server.core.common.utils import validate_iam_role
        result = await validate_iam_role('arn:aws:iam::123456789012:role/test-role')
        assert result is True
        
        # Test failed validation
        from botocore.exceptions import ClientError
        mock_client.return_value.get_role.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetRole'
        )
        result = await validate_iam_role('arn:aws:iam::123456789012:role/missing-role')
        assert result is False


@pytest.mark.asyncio
async def test_build_logs_with_content():
    """Test build logs fetch actual content."""
    with patch('boto3.client') as mock_client:
        # Mock CodeBuild response
        mock_client.return_value.batch_get_builds.return_value = {
            'builds': [{
                'id': 'build-123',
                'buildStatus': 'SUCCEEDED',
                'logs': {
                    'groupName': '/aws/codebuild/test-project',
                    'streamName': 'stream-123'
                }
            }]
        }
        
        # Mock CloudWatch Logs response
        logs_client = MagicMock()
        logs_client.get_log_events.return_value = {
            'events': [
                {'message': 'Build started'},
                {'message': 'Build completed'}
            ]
        }
        
        def client_side_effect(service, **kwargs):
            if service == 'codebuild':
                return mock_client.return_value
            elif service == 'logs':
                return logs_client
        
        with patch('boto3.client', side_effect=client_side_effect):
            result = await build_tools.get_build_logs('build-123')
            
            assert 'log_content' in result
            assert len(result['log_content']) == 2
            assert 'Build started' in result['log_content']


@pytest.mark.asyncio
async def test_create_pipeline_validation():
    """Test pipeline creation with resource validation."""
    with patch('awslabs.aws_cicd_mcp_server.core.codepipeline.tools.READ_ONLY_MODE', False), \
         patch('awslabs.aws_cicd_mcp_server.core.common.utils.validate_iam_role') as mock_validate_role, \
         patch('awslabs.aws_cicd_mcp_server.core.common.utils.validate_s3_bucket') as mock_validate_bucket:
        
        # Test validation failure
        mock_validate_role.return_value = False
        mock_validate_bucket.return_value = True
        
        result = await pipeline_tools.create_pipeline(
            'test-pipeline', 
            'arn:aws:iam::123456789012:role/invalid-role',
            'test-bucket',
            'test-repo'
        )
        
        assert 'error' in result
        assert 'not found or not accessible' in result['error']


if __name__ == '__main__':
    pytest.main([__file__])
