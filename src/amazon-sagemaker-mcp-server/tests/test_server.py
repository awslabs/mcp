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

"""Tests for Amazon SageMaker MCP Server."""

import argparse
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from awslabs.amazon_sagemaker_mcp_server.server import (
    mcp,
    parse_args,
    main,
    list_sm_nb_instances,
    describe_sm_nb_instance,
    start_sm_nb_instance,
    stop_sm_nb_instance,
    list_sm_domains,
    describe_sm_domain,
    list_sm_endpoints,
    describe_sm_endpoint,
    invoke_sm_endpoint,
    list_sm_space_apps,
    create_sm_space_app,
    delete_sm_space_app,
)


class TestServerBasics:
    """Test basic server functionality."""

    def test_server_exists(self):
        """Test that the server exists."""
        assert mcp is not None
        assert mcp.name == 'amazon-sagemaker-mcp-server'

    def test_server_has_tools(self):
        """Test that the server has tools registered."""
        # Check that we have some expected tools
        # FastMCP stores tools in the tool manager
        assert hasattr(mcp, '_tool_manager')
        assert hasattr(mcp._tool_manager, '_tools')
        
        tool_names = list(mcp._tool_manager._tools.keys())
        expected_tools = [
            'list_sm_nb_instances',
            'describe_sm_nb_instance',
            'start_sm_nb_instance',
            'stop_sm_nb_instance',
            'list_sm_domains',
            'describe_sm_domain',
            'list_sm_endpoints',
            'describe_sm_endpoint',
            'invoke_sm_endpoint',
        ]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_server_has_resources(self):
        """Test that the server has resources registered."""
        # FastMCP stores resources in the resource manager
        assert hasattr(mcp, '_resource_manager')


class TestArgumentParsing:
    """Test command line argument parsing."""

    def test_parse_args_default(self):
        """Test parsing default arguments."""
        with patch('sys.argv', ['server.py']):
            args = parse_args()
            assert not args.allow_write
            assert not args.allow_sensitive_data_access

    def test_parse_args_with_flags(self):
        """Test parsing arguments with flags."""
        with patch('sys.argv', ['server.py', '--allow-write', '--allow-sensitive-data-access']):
            args = parse_args()
            assert args.allow_write
            assert args.allow_sensitive_data_access

    def test_parse_args_version(self):
        """Test version argument."""
        with patch('sys.argv', ['server.py', '--version']):
            with pytest.raises(SystemExit):
                parse_args()


class TestNotebookInstanceTools:
    """Test notebook instance related tools."""

    @pytest.mark.asyncio
    async def test_list_notebook_instances_success(self):
        """Test successful listing of notebook instances."""
        mock_response = {
            'NotebookInstances': [
                {
                    'NotebookInstanceName': 'test-instance',
                    'NotebookInstanceStatus': 'InService',
                    'CreationTime': '2023-01-01T00:00:00Z'
                }
            ]
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_notebook_instances.return_value = mock_response
            
            result = await list_sm_nb_instances()
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert len(result_dict['instances']) == 1
            assert result_dict['instances'][0]['NotebookInstanceName'] == 'test-instance'

    @pytest.mark.asyncio
    async def test_list_notebook_instances_with_filters(self):
        """Test listing notebook instances with filters."""
        mock_response = {'NotebookInstances': []}
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_notebook_instances.return_value = mock_response
            
            result = await list_sm_nb_instances(
                name_contains='test',
                status_equals='InService',
                max_results=5
            )
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            # Check that the function was called with the right parameters
            call_args = mock_client.return_value.list_notebook_instances.call_args
            assert call_args[1]['MaxResults'] == 5
            assert call_args[1]['NameContains'] == 'test'
            assert call_args[1]['StatusEquals'] == 'InService'

    @pytest.mark.asyncio
    async def test_list_notebook_instances_error(self):
        """Test error handling in list notebook instances."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_notebook_instances.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'ListNotebookInstances'
            )
            
            result = await list_sm_nb_instances()
            result_dict = json.loads(result)
            
            assert result_dict['success'] is False
            assert 'Access denied' in result_dict['error']

    @pytest.mark.asyncio
    async def test_describe_notebook_instance_success(self):
        """Test successful describe notebook instance."""
        mock_response = {
            'NotebookInstanceName': 'test-instance',
            'NotebookInstanceStatus': 'InService',
            'InstanceType': 'ml.t3.medium'
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.describe_notebook_instance.return_value = mock_response
            
            result = await describe_sm_nb_instance('test-instance')
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert result_dict['instance_name'] == 'test-instance'
            assert result_dict['instance_details']['NotebookInstanceName'] == 'test-instance'

    @pytest.mark.asyncio
    async def test_start_notebook_instance_success(self):
        """Test successful start notebook instance."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.start_notebook_instance.return_value = {}
            
            result = await start_sm_nb_instance('test-instance')
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert result_dict['instance_name'] == 'test-instance'
            mock_client.return_value.start_notebook_instance.assert_called_once_with(
                NotebookInstanceName='test-instance'
            )

    @pytest.mark.asyncio
    async def test_stop_notebook_instance_success(self):
        """Test successful stop notebook instance."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.stop_notebook_instance.return_value = {}
            
            result = await stop_sm_nb_instance('test-instance')
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert result_dict['instance_name'] == 'test-instance'
            mock_client.return_value.stop_notebook_instance.assert_called_once_with(
                NotebookInstanceName='test-instance'
            )


class TestDomainTools:
    """Test domain related tools."""

    @pytest.mark.asyncio
    async def test_list_domains_success(self):
        """Test successful listing of domains."""
        mock_response = {
            'Domains': [
                {
                    'DomainId': 'd-123456789',
                    'DomainName': 'test-domain',
                    'Status': 'InService'
                }
            ]
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_domains.return_value = mock_response
            
            result = await list_sm_domains()
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert len(result_dict['domains']) == 1

    @pytest.mark.asyncio
    async def test_describe_domain_success(self):
        """Test successful describe domain."""
        mock_response = {
            'DomainId': 'd-123456789',
            'DomainName': 'test-domain',
            'Status': 'InService'
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.describe_domain.return_value = mock_response
            
            result = await describe_sm_domain('d-123456789')
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert result_dict['domain_id'] == 'd-123456789'


class TestSpaceAppTools:
    """Test Space App related tools."""

    @pytest.mark.asyncio
    async def test_list_space_apps_success(self):
        """Test successful listing of space apps."""
        mock_response = {
            'Apps': [
                {
                    'DomainId': 'd-123456789',
                    'SpaceName': 'test-space',
                    'AppType': 'JupyterLab',
                    'AppName': 'default',
                    'Status': 'InService',
                    'CreationTime': '2023-01-01T00:00:00Z'
                }
            ]
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_apps.return_value = mock_response
            
            result = await list_sm_space_apps()
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert len(result_dict['apps']) == 1
            assert result_dict['apps'][0]['DomainId'] == 'd-123456789'

    @pytest.mark.asyncio
    async def test_list_space_apps_with_filters(self):
        """Test listing space apps with filters."""
        mock_response = {
            'Apps': [
                {
                    'DomainId': 'd-123456789',
                    'SpaceName': 'test-space',
                    'AppType': 'JupyterLab',
                    'AppName': 'default',
                    'Status': 'InService',
                    'CreationTime': '2023-01-01T00:00:00Z'
                }
            ]
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_apps.return_value = mock_response
            
            result = await list_sm_space_apps(
                domain_id_contains='d-123456789',
                space_name_contains='test-space'
            )
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert len(result_dict['apps']) == 1

    @pytest.mark.asyncio
    async def test_create_space_app_success(self):
        """Test successful creation of space app."""
        mock_response = {
            'AppArn': 'arn:aws:sagemaker:us-east-1:123456789012:app/d-123456789/test-space/JupyterLab/default'
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.create_app.return_value = mock_response
            
            result = await create_sm_space_app(
                domain_id='d-123456789',
                space_name='test-space',
                app_type='JupyterLab',
                app_name='default'
            )
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert 'app_details' in result_dict
            assert result_dict['message'] == 'Successfully created SageMaker Space App: default'

    @pytest.mark.asyncio
    async def test_delete_space_app_success(self):
        """Test successful deletion of space app."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.delete_app.return_value = {}
            
            result = await delete_sm_space_app(
                domain_id='d-123456789',
                space_name='test-space',
                app_type='JupyterLab',
                app_name='default'
            )
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert result_dict['message'] == 'Successfully deleted SageMaker Space App: default'

    @pytest.mark.asyncio
    async def test_list_space_apps_error(self):
        """Test error handling in list space apps."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_apps.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'ListApps'
            )
            
            result = await list_sm_space_apps()
            result_dict = json.loads(result)
            
            assert result_dict['success'] is False
            assert 'error' in result_dict

    @pytest.mark.asyncio
    async def test_create_space_app_error(self):
        """Test error handling in create space app."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.create_app.side_effect = ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameters'}},
                'CreateApp'
            )
            
            result = await create_sm_space_app(
                domain_id='d-123456789',
                space_name='test-space',
                app_type='JupyterLab',
                app_name='default'
            )
            result_dict = json.loads(result)
            
            assert result_dict['success'] is False
            assert 'error' in result_dict

    @pytest.mark.asyncio
    async def test_delete_space_app_error(self):
        """Test error handling in delete space app."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.delete_app.side_effect = ClientError(
                {'Error': {'Code': 'ResourceNotFound', 'Message': 'App not found'}},
                'DeleteApp'
            )
            
            result = await delete_sm_space_app(
                domain_id='d-123456789',
                space_name='test-space',
                app_type='JupyterLab',
                app_name='default'
            )
            result_dict = json.loads(result)
            
            assert result_dict['success'] is False
            assert 'error' in result_dict


class TestEndpointTools:
    """Test endpoint related tools."""

    @pytest.mark.asyncio
    async def test_list_endpoints_success(self):
        """Test successful listing of endpoints."""
        mock_response = {
            'Endpoints': [
                {
                    'EndpointName': 'test-endpoint',
                    'EndpointStatus': 'InService',
                    'CreationTime': '2023-01-01T00:00:00Z'
                }
            ]
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_endpoints.return_value = mock_response
            
            result = await list_sm_endpoints()
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert len(result_dict['endpoints']) == 1
            assert result_dict['endpoints'][0]['EndpointName'] == 'test-endpoint'

    @pytest.mark.asyncio
    async def test_describe_endpoint_success(self):
        """Test successful describe endpoint."""
        mock_response = {
            'EndpointName': 'test-endpoint',
            'EndpointStatus': 'InService',
            'EndpointConfigName': 'test-config'
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.describe_endpoint.return_value = mock_response
            
            result = await describe_sm_endpoint('test-endpoint')
            result_dict = json.loads(result)
            
            assert result_dict['success'] is True
            assert result_dict['endpoint_name'] == 'test-endpoint'
            assert result_dict['endpoint_details']['EndpointName'] == 'test-endpoint'

    @pytest.mark.asyncio
    async def test_invoke_endpoint_success(self):
        """Test successful endpoint invocation."""
        mock_body = MagicMock()
        mock_body.read.return_value = b'{"prediction": "success"}'
        
        mock_response = {
            'Body': mock_body,
            'ContentType': 'application/json',
            'InvokedProductionVariant': 'variant-1'
        }
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_runtime_client') as mock_client:
            with patch('awslabs.amazon_sagemaker_mcp_server.server.require_sensitive_data_access'):
                mock_client.return_value.invoke_endpoint.return_value = mock_response
                
                result = await invoke_sm_endpoint(
                    'test-endpoint',
                    '{"input": "data"}',
                    'application/json',
                    'application/json'
                )
                result_dict = json.loads(result)
                
                assert result_dict['success'] is True
                assert result_dict['endpoint_name'] == 'test-endpoint'
                assert '{"prediction": "success"}' in result_dict['response_body']

    @pytest.mark.asyncio
    async def test_invoke_endpoint_permission_error(self):
        """Test endpoint invocation without sensitive data access."""
        # Don't set the permission environment variable, so it should fail
        if 'ALLOW_SENSITIVE_DATA_ACCESS' in os.environ:
            del os.environ['ALLOW_SENSITIVE_DATA_ACCESS']
        
        result = await invoke_sm_endpoint('test-endpoint', '{}')
        result_dict = json.loads(result)
        
        assert result_dict['success'] is False
        assert 'Sensitive data access is required' in result_dict['error']


class TestMainFunction:
    """Test main function and entry point."""

    def test_main_with_valid_credentials(self):
        """Test main function with valid AWS credentials."""
        test_args = ['server.py', '--allow-write']
        
        with patch('sys.argv', test_args):
            with patch('awslabs.amazon_sagemaker_mcp_server.server.validate_aws_credentials', return_value=True):
                with patch('awslabs.amazon_sagemaker_mcp_server.server.mcp.run') as mock_run:
                    main()
                    mock_run.assert_called_once()
                    assert os.environ.get('ALLOW_WRITE') == 'true'

    def test_main_with_invalid_credentials(self):
        """Test main function with invalid AWS credentials."""
        test_args = ['server.py']
        
        with patch('sys.argv', test_args):
            with patch('awslabs.amazon_sagemaker_mcp_server.server.validate_aws_credentials', return_value=False):
                with patch('sys.exit') as mock_exit:
                    with patch('awslabs.amazon_sagemaker_mcp_server.server.logger.error'):
                        # Prevent the actual server from running
                        with patch('awslabs.amazon_sagemaker_mcp_server.server.mcp.run'):
                            main()
                            mock_exit.assert_called_once_with(1)

    def test_main_sets_default_region(self):
        """Test that main sets default AWS region."""
        test_args = ['server.py']
        
        # Clear AWS_REGION if set
        original_region = os.environ.get('AWS_REGION')
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']
        
        try:
            with patch('sys.argv', test_args):
                with patch('awslabs.amazon_sagemaker_mcp_server.server.validate_aws_credentials', return_value=True):
                    with patch('awslabs.amazon_sagemaker_mcp_server.server.mcp.run'):
                        main()
                        assert os.environ.get('AWS_REGION') == 'us-east-1'
        finally:
            # Restore original region
            if original_region:
                os.environ['AWS_REGION'] = original_region
            elif 'AWS_REGION' in os.environ:
                del os.environ['AWS_REGION']


class TestErrorHandling:
    """Test error handling across different tools."""

    @pytest.mark.asyncio
    async def test_client_error_handling(self):
        """Test handling of AWS client errors."""
        error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}},
            'DescribeEndpoint'
        )
        
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.describe_endpoint.side_effect = error
            
            result = await describe_sm_endpoint('invalid-endpoint')
            result_dict = json.loads(result)
            
            assert result_dict['success'] is False
            assert 'Invalid parameter' in result_dict['error']

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self):
        """Test handling of generic exceptions."""
        with patch('awslabs.amazon_sagemaker_mcp_server.server.get_sagemaker_client') as mock_client:
            mock_client.return_value.list_endpoints.side_effect = Exception('Unexpected error')
            
            result = await list_sm_endpoints()
            result_dict = json.loads(result)
            
            assert result_dict['success'] is False
            assert 'Unexpected error' in result_dict['error']
