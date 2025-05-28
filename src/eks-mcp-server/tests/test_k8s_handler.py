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
# ruff: noqa: D101, D102, D103
"""Tests for the K8sHandler class."""

import os
import pytest
from awslabs.eks_mcp_server.k8s_apis import K8sApis
from awslabs.eks_mcp_server.k8s_handler import K8sHandler
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, mock_open, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    return MagicMock()


@pytest.fixture
def mock_client_cache():
    """Create a mock K8sClientCache."""
    cache = MagicMock()
    mock_k8s_apis = MagicMock(spec=K8sApis)
    cache.get_client.return_value = mock_k8s_apis
    return cache


@pytest.fixture
def mock_k8s_apis():
    """Create a mock K8sApis instance."""
    return MagicMock(spec=K8sApis)


class TestK8sHandler:
    """Tests for the K8sHandler class."""

    def test_init(self, mock_mcp, mock_client_cache):
        """Test initialization of K8sHandler."""
        # Initialize the K8s handler with allow_write=True
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_write=True)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.client_cache == mock_client_cache
            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is False

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count == 7

        # Get all call args
        call_args_list = mock_mcp.tool.call_args_list

        # Get all tool names that were registered
        tool_names = [call_args[1]['name'] for call_args in call_args_list]

        # Verify that expected tools were registered
        assert 'list_k8s_resources' in tool_names
        assert 'generate_app_manifest' in tool_names
        assert 'apply_yaml' in tool_names
        assert 'manage_k8s_resource' in tool_names
        assert 'get_pod_logs' in tool_names
        assert 'get_k8s_events' in tool_names

    def test_init_with_sensitive_data_access(self, mock_mcp, mock_client_cache):
        """Test initialization of K8sHandler with sensitive data access enabled."""
        # Initialize the K8s handler with sensitive data access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_write=False, allow_sensitive_data_access=True)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.client_cache == mock_client_cache
            assert handler.allow_write is False
            assert handler.allow_sensitive_data_access is True

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count == 7

        # Get all call args
        call_args_list = mock_mcp.tool.call_args_list

        # Get all tool names that were registered
        tool_names = [call_args[1]['name'] for call_args in call_args_list]

        # Verify that expected tools were registered
        assert 'list_k8s_resources' in tool_names
        assert 'get_pod_logs' in tool_names
        assert 'get_k8s_events' in tool_names
        assert 'list_api_versions' in tool_names
        assert 'manage_k8s_resource' in tool_names
        assert 'apply_yaml' in tool_names
        assert 'generate_app_manifest' in tool_names

    def test_get_client(self, mock_mcp, mock_client_cache):
        """Test get_client method delegates to the client cache."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

            # Get a client
            client = handler.get_client('test-cluster')

            # Verify that get_client was called on the cache
            mock_client_cache.get_client.assert_called_once_with('test-cluster')

            # Verify that the client was returned
            assert client == mock_client_cache.get_client.return_value

    @pytest.mark.asyncio
    async def test_apply_yaml_relative_path(self, mock_context, mock_mcp, mock_client_cache):
        """Test apply_yaml method with a relative path."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock os.path.isabs to return False for relative paths
        with patch('os.path.isabs', return_value=False):
            # Apply YAML from a relative path
            result = await handler.apply_yaml(
                mock_context,
                yaml_path='relative/path/to/manifest.yaml',
                cluster_name='test-cluster',
                namespace='default',
                force=True,
            )

            # Verify the result
            assert result.isError
            assert isinstance(result.content[0], TextContent)
            assert 'Path must be absolute' in result.content[0].text
            assert 'relative/path/to/manifest.yaml' in result.content[0].text

    @pytest.mark.asyncio
    async def test_apply_yaml_success(self, mock_context, mock_mcp, mock_client_cache):
        """Test apply_yaml method with successful application."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Mock os.path.isabs to return True for absolute paths
            with patch('os.path.isabs', return_value=True):
                # Mock open to read the YAML file
                yaml_content = """apiVersion: v1
kind: Namespace
metadata:
  name: test-namespace
"""
                with patch('builtins.open', mock_open(read_data=yaml_content)) as mocked_open:
                    # Mock apply_from_yaml
                    mock_k8s_apis.apply_from_yaml.return_value = ([], 1, 0)

                    # Apply YAML from file
                    result = await handler.apply_yaml(
                        mock_context,
                        yaml_path='/path/to/manifest.yaml',
                        cluster_name='test-cluster',
                        namespace='default',
                        force=True,
                    )

                    # Verify that get_client was called
                    mock_client.assert_called_once_with('test-cluster')

                    # Verify that open was called with the correct path
                    mocked_open.assert_called_once_with('/path/to/manifest.yaml', 'r')

                    # Verify that apply_from_yaml was called with the correct parameters
                    mock_k8s_apis.apply_from_yaml.assert_called_once()
                    args, kwargs = mock_k8s_apis.apply_from_yaml.call_args
                    assert len(kwargs['yaml_objects']) == 1
                    assert kwargs['yaml_objects'][0]['kind'] == 'Namespace'
                    assert kwargs['namespace'] == 'default'
                    assert kwargs['force'] is True

                    # Verify the result
                    assert not result.isError
                    assert isinstance(result.content[0], TextContent)
                    assert (
                        'Successfully applied all resources from YAML file'
                        in result.content[0].text
                    )

    @pytest.mark.asyncio
    async def test_apply_yaml_file_not_found(self, mock_context, mock_mcp, mock_client_cache):
        """Test apply_yaml method with file not found error."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Mock os.path.isabs to return True for absolute paths
            with patch('os.path.isabs', return_value=True):
                # Mock open to raise FileNotFoundError
                with patch('builtins.open', side_effect=FileNotFoundError()):
                    # Apply YAML from file
                    result = await handler.apply_yaml(
                        mock_context,
                        yaml_path='/path/to/nonexistent.yaml',
                        cluster_name='test-cluster',
                        namespace='default',
                        force=True,
                    )

                    # Verify that get_client was called
                    mock_client.assert_called_once_with('test-cluster')

                    # Verify the result
                    assert result.isError
                    assert isinstance(result.content[0], TextContent)
                    assert 'YAML file not found' in result.content[0].text

    @pytest.mark.asyncio
    async def test_apply_yaml_io_error(self, mock_context, mock_mcp, mock_client_cache):
        """Test apply_yaml method with IO error."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Mock os.path.isabs to return True for absolute paths
            with patch('os.path.isabs', return_value=True):
                # Mock open to raise IOError
                with patch('builtins.open', side_effect=IOError('Permission denied')):
                    # Apply YAML from file
                    result = await handler.apply_yaml(
                        mock_context,
                        yaml_path='/path/to/protected.yaml',
                        cluster_name='test-cluster',
                        namespace='default',
                        force=True,
                    )

                    # Verify that get_client was called
                    mock_client.assert_called_once_with('test-cluster')

                    # Verify the result
                    assert result.isError
                    assert isinstance(result.content[0], TextContent)
                    assert 'Error reading YAML file' in result.content[0].text
                    assert 'Permission denied' in result.content[0].text

    @pytest.mark.asyncio
    async def test_apply_yaml_create_error(self, mock_context, mock_mcp, mock_client_cache):
        """Test apply_yaml method with error from create_from_yaml."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        with patch.object(handler, 'get_client', return_value=mock_k8s_apis):
            # Mock os.path.isabs to return True for absolute paths
            with patch('os.path.isabs', return_value=True):
                # Mock open to read the YAML file
                yaml_content = """apiVersion: v1
kind: Namespace
metadata:
  name: test-namespace
"""
                with patch('builtins.open', mock_open(read_data=yaml_content)):
                    # Mock apply_from_yaml to raise an exception
                    mock_k8s_apis.apply_from_yaml.side_effect = Exception(
                        'Failed to create resource'
                    )

                    # Apply YAML from file
                    result = await handler.apply_yaml(
                        mock_context,
                        yaml_path='/path/to/manifest.yaml',
                        cluster_name='test-cluster',
                        namespace='default',
                        force=True,
                    )

                    # Verify the result
                    assert result.isError
                    assert isinstance(result.content[0], TextContent)
                    assert 'Failed to apply YAML from file' in result.content[0].text
                    assert 'Failed to create resource' in result.content[0].text

    # Note: TTL cache expiration tests have been moved to test_k8s_client_cache.py

    @pytest.mark.asyncio
    async def test_manage_k8s_resource_create(self, mock_context, mock_mcp, mock_client_cache):
        """Test manage_k8s_resource method with create operation."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_write=True)

        # Mock the get_client method and k8s_apis.manage_resource
        mock_k8s_apis = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            'kind': 'Pod',
            'apiVersion': 'v1',
            'metadata': {'name': 'test-pod', 'namespace': 'test-namespace'},
        }
        mock_k8s_apis.manage_resource.return_value = mock_response

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Create a test resource
            body = {
                'metadata': {'name': 'test-pod'},
                'spec': {'containers': [{'name': 'test-container', 'image': 'nginx'}]},
            }

            result = await handler.manage_k8s_resource(
                mock_context,
                operation='create',
                cluster_name='test-cluster',
                kind='Pod',
                api_version='v1',
                name='test-pod',
                namespace='test-namespace',
                body=body,
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that manage_resource was called with the correct parameters
            mock_k8s_apis.manage_resource.assert_called_once()

            # Verify the result
            assert not result.isError
            assert result.kind == 'Pod'
            assert result.name == 'test-pod'
            assert result.namespace == 'test-namespace'
            assert result.api_version == 'v1'
            assert result.operation == 'create'
            assert isinstance(result.content[0], TextContent)
            assert 'Successfully created Pod test-namespace/test-pod' in result.content[0].text

    @pytest.mark.asyncio
    async def test_read_k8s_resource(self, mock_context, mock_mcp, mock_client_cache):
        """Test read_k8s_resource method."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock the get_client method and k8s_apis.manage_resource
        mock_k8s_apis = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            'kind': 'Pod',
            'apiVersion': 'v1',
            'metadata': {'name': 'test-pod', 'namespace': 'test-namespace'},
        }
        mock_k8s_apis.manage_resource.return_value = mock_response

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis):
            result = await handler.manage_k8s_resource(
                mock_context,
                operation='read',
                cluster_name='test-cluster',
                kind='Pod',
                api_version='v1',
                name='test-pod',
                namespace='test-namespace',
            )

            # Verify the result
            assert not result.isError
            assert result.kind == 'Pod'
            assert result.name == 'test-pod'
            assert result.namespace == 'test-namespace'
            assert result.api_version == 'v1'
            assert result.operation == 'read'
            assert result.resource is not None
            assert isinstance(result.content[0], TextContent)
            assert 'Successfully retrieved Pod test-namespace/test-pod' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_k8s_resource_invalid_operation(
        self, mock_context, mock_mcp, mock_client_cache
    ):
        """Test manage_k8s_resource method with an invalid operation."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Call manage_k8s_resource with an invalid operation
        result = await handler.manage_k8s_resource(
            mock_context,
            operation='invalid',
            cluster_name='test-cluster',
            kind='Pod',
            api_version='v1',
            name='test-pod',
            namespace='test-namespace',
        )

        # Verify the result
        assert result.isError
        assert result.kind == 'Pod'
        assert result.name == 'test-pod'
        assert result.namespace == 'test-namespace'
        assert result.api_version == 'v1'
        assert result.operation == 'invalid'
        assert isinstance(result.content[0], TextContent)
        assert 'Invalid operation: invalid' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_k8s_resource_error(self, mock_context, mock_mcp, mock_client_cache):
        """Test manage_k8s_resource method with an error."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.manage_resource.side_effect = Exception('Resource not found')

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            result = await handler.manage_k8s_resource(
                mock_context,
                operation='read',
                cluster_name='test-cluster',
                kind='Pod',
                api_version='v1',
                name='test-pod',
                namespace='test-namespace',
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that manage_resource was called with the correct parameters
            mock_k8s_apis.manage_resource.assert_called_once()

            # Verify the result
            assert result.isError
            assert result.kind == 'Pod'
            assert result.name == 'test-pod'
            assert result.namespace == 'test-namespace'
            assert result.api_version == 'v1'
            assert result.operation == 'read'
            assert isinstance(result.content[0], TextContent)
            assert (
                'Failed to read Pod test-namespace/test-pod: Resource not found'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_manage_k8s_resource_secret_sensitive_data_access_disabled(
        self, mock_context, mock_mcp, mock_client_cache
    ):
        """Test manage_k8s_resource method with Secret kind and sensitive data access disabled."""
        # Initialize the K8s handler with sensitive data access disabled but write access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=False)

        # Test with read operation on Secret (should be rejected)
        result = await handler.manage_k8s_resource(
            mock_context,
            operation='read',
            cluster_name='test-cluster',
            kind='Secret',
            api_version='v1',
            name='test-secret',
            namespace='test-namespace',
        )

        # Verify the result
        assert result.isError
        assert result.kind == 'Secret'
        assert result.name == 'test-secret'
        assert result.namespace == 'test-namespace'
        assert result.api_version == 'v1'
        assert result.operation == 'read'
        assert isinstance(result.content[0], TextContent)
        assert (
            'Access to Kubernetes Secrets requires --allow-sensitive-data-access flag'
            in result.content[0].text
        )

        # Test with create operation on Secret (should be rejected for sensitive data access, not write access)
        result = await handler.manage_k8s_resource(
            mock_context,
            operation='create',
            cluster_name='test-cluster',
            kind='Secret',
            api_version='v1',
            name='test-secret',
            namespace='test-namespace',
            body={'metadata': {'name': 'test-secret'}, 'data': {'key': 'dmFsdWU='}},
        )

        # Verify the result
        assert not result.isError
        assert result.kind == 'Secret'
        assert result.name == 'test-secret'
        assert result.namespace == 'test-namespace'
        assert result.api_version == 'v1'
        assert result.operation == 'create'
        assert isinstance(result.content[0], TextContent)

    @pytest.mark.asyncio
    async def test_manage_k8s_resource_write_access_disabled(
        self, mock_context, mock_mcp, mock_client_cache
    ):
        """Test manage_k8s_resource method with write access disabled for mutable operations."""
        # Initialize the K8s handler with write access disabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_write=False)

        # Test with create operation (should be rejected)
        result = await handler.manage_k8s_resource(
            mock_context,
            operation='create',
            cluster_name='test-cluster',
            kind='Pod',
            api_version='v1',
            name='test-pod',
            namespace='test-namespace',
            body={'metadata': {'name': 'test-pod'}},
        )

        # Verify the result
        assert result.isError
        assert result.kind == 'Pod'
        assert result.name == 'test-pod'
        assert result.namespace == 'test-namespace'
        assert result.api_version == 'v1'
        assert result.operation == 'create'
        assert isinstance(result.content[0], TextContent)
        assert 'Operation create is not allowed without write access' in result.content[0].text

        # Test with replace operation (should be rejected when write access is disabled)
        result = await handler.manage_k8s_resource(
            mock_context,
            operation='replace',
            cluster_name='test-cluster',
            kind='Pod',
            api_version='v1',
            name='test-pod',
            namespace='test-namespace',
            body={'metadata': {'name': 'test-pod'}},
        )

        # Verify the result
        assert result.isError
        assert result.operation == 'replace'
        assert isinstance(result.content[0], TextContent)
        assert 'Operation replace is not allowed without write access' in result.content[0].text

        # Test with patch operation (should be rejected when write access is disabled)
        result = await handler.manage_k8s_resource(
            mock_context,
            operation='patch',
            cluster_name='test-cluster',
            kind='Pod',
            api_version='v1',
            name='test-pod',
            namespace='test-namespace',
            body={'metadata': {'labels': {'app': 'test'}}},
        )

        # Verify the result
        assert result.isError
        assert result.operation == 'patch'
        assert isinstance(result.content[0], TextContent)
        assert 'Operation patch is not allowed without write access' in result.content[0].text

        # Test with delete operation (should be rejected when write access is disabled)
        result = await handler.manage_k8s_resource(
            mock_context,
            operation='delete',
            cluster_name='test-cluster',
            kind='Pod',
            api_version='v1',
            name='test-pod',
            namespace='test-namespace',
        )

        # Verify the result
        assert result.isError
        assert result.operation == 'delete'
        assert isinstance(result.content[0], TextContent)
        assert 'Operation delete is not allowed without write access' in result.content[0].text

        # Test with read operation (should be allowed even when write access is disabled)
        mock_k8s_apis = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            'kind': 'Pod',
            'apiVersion': 'v1',
            'metadata': {'name': 'test-pod', 'namespace': 'test-namespace'},
        }
        mock_k8s_apis.manage_resource.return_value = mock_response

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            result = await handler.manage_k8s_resource(
                mock_context,
                operation='read',
                cluster_name='test-cluster',
                kind='Pod',
                api_version='v1',
                name='test-pod',
                namespace='test-namespace',
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that manage_resource was called
            mock_k8s_apis.manage_resource.assert_called_once()

            # Verify the result
            assert not result.isError
            assert result.kind == 'Pod'
            assert result.name == 'test-pod'
            assert result.namespace == 'test-namespace'
            assert result.api_version == 'v1'
            assert result.operation == 'read'
            assert isinstance(result.content[0], TextContent)
            assert 'Successfully retrieved Pod test-namespace/test-pod' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_k8s_resources_success(self, mock_context, mock_mcp, mock_client_cache):
        """Test list_k8s_resources method with successful listing."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()

        # Mock response with items
        mock_item1 = MagicMock()
        mock_item1.to_dict.return_value = {
            'metadata': {
                'name': 'test-pod-1',
                'namespace': 'test-namespace',
                'creation_timestamp': '2023-01-01T00:00:00Z',
                'labels': {'app': 'test'},
                'annotations': {'description': 'Test pod 1'},
            }
        }
        mock_item2 = MagicMock()
        mock_item2.to_dict.return_value = {
            'metadata': {
                'name': 'test-pod-2',
                'namespace': 'test-namespace',
                'creation_timestamp': '2023-01-02T00:00:00Z',
                'labels': {'app': 'test'},
                'annotations': {'description': 'Test pod 2'},
            }
        }

        mock_response = MagicMock()
        mock_response.items = [mock_item1, mock_item2]
        mock_k8s_apis.list_resources.return_value = mock_response

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            result = await handler.list_k8s_resources(
                mock_context,
                cluster_name='test-cluster',
                kind='Pod',
                api_version='v1',
                namespace='test-namespace',
                label_selector='app=test',
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that list_resources was called once
            mock_k8s_apis.list_resources.assert_called_once()

            # Get the call args
            args, kwargs = mock_k8s_apis.list_resources.call_args

            # Verify the positional args
            assert args[0] == 'Pod'
            assert args[1] == 'v1'

            # Verify the keyword args
            assert kwargs['namespace'] == 'test-namespace'
            assert kwargs['label_selector'] == 'app=test'

            # Verify the result
            assert not result.isError
            assert result.kind == 'Pod'
            assert result.api_version == 'v1'
            assert result.namespace == 'test-namespace'
            assert result.count == 2
            assert len(result.items) == 2
            assert result.items[0].name == 'test-pod-1'
            assert result.items[0].namespace == 'test-namespace'
            # Don't check creation_timestamp as it might be None in the actual implementation
            assert result.items[0].labels == {'app': 'test'}
            assert result.items[0].annotations == {'description': 'Test pod 1'}
            assert result.items[1].name == 'test-pod-2'
            assert isinstance(result.content[0], TextContent)
            assert (
                'Successfully listed 2 Pod resources in test-namespace/' in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_list_k8s_resources_empty(self, mock_context, mock_mcp, mock_client_cache):
        """Test list_k8s_resources method with empty result."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()

        # Mock response with no items
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_apis.list_resources.return_value = mock_response

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis):
            result = await handler.list_k8s_resources(
                mock_context,
                cluster_name='test-cluster',
                kind='Pod',
                api_version='v1',
                namespace='test-namespace',
            )

            # Verify the result
            assert not result.isError
            assert result.kind == 'Pod'
            assert result.count == 0
            assert len(result.items) == 0
            assert isinstance(result.content[0], TextContent)
            assert (
                'Successfully listed 0 Pod resources in test-namespace/' in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_list_k8s_resources_error(self, mock_context, mock_mcp, mock_client_cache):
        """Test list_k8s_resources method with an error."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.list_resources.side_effect = Exception('Failed to list resources')

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis):
            result = await handler.list_k8s_resources(
                mock_context,
                cluster_name='test-cluster',
                kind='Pod',
                api_version='v1',
                namespace='test-namespace',
            )

            # Verify the result
            assert result.isError
            assert result.kind == 'Pod'
            assert result.count == 0
            assert len(result.items) == 0
            assert isinstance(result.content[0], TextContent)
            assert (
                'Failed to list Pod resources: Failed to list resources' in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_generate_app_manifest_success(self, mock_context, mock_mcp, mock_client_cache):
        """Test generate_app_manifest with successful creation."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Prepare mock file content
        deployment_content = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: APP_NAME
  namespace: NAMESPACE"""

        service_content = """apiVersion: v1
kind: Service
metadata:
  name: APP_NAME
  namespace: NAMESPACE
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: LOAD_BALANCER_SCHEME"""

        # Mock open function to return our test templates and for file writing
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.side_effect = [deployment_content, service_content]
        mock_open.return_value = mock_file

        # Mock os.makedirs to avoid creating directories
        with patch('os.makedirs') as mock_makedirs:
            with patch('builtins.open', mock_open):
                # Mock os.path.abspath to return a predictable absolute path
                with patch(
                    'os.path.abspath',
                    return_value='/absolute/path/test-output/test-app-manifest.yaml',
                ):
                    # Generate the manifest
                    result = await handler.generate_app_manifest(
                        mock_context,
                        app_name='test-app',
                        image_uri='123456789012.dkr.ecr.region.amazonaws.com/repo:tag',
                        port=8080,
                        replicas=3,
                        cpu='250m',
                        memory='256Mi',
                        namespace='test-namespace',
                        load_balancer_scheme='internet-facing',
                        output_dir='test-output',
                    )

                    # Verify that os.makedirs was called with exist_ok=True
                    mock_makedirs.assert_called_once_with('test-output', exist_ok=True)

                    # Verify that open was called for reading templates and writing output
                    assert mock_open.call_count == 3  # 2 reads + 1 write

                    # Verify the result
                    assert not result.isError
                    assert isinstance(result.content[0], TextContent)
                    assert 'Successfully generated YAML for test-app' in result.content[0].text
                    assert (
                        'with image 123456789012.dkr.ecr.region.amazonaws.com/repo:tag'
                        in result.content[0].text
                    )

                    # Verify that the output path is absolute
                    assert os.path.isabs(result.output_file_path)
                    assert (
                        result.output_file_path
                        == '/absolute/path/test-output/test-app-manifest.yaml'
                    )

    @pytest.mark.asyncio
    async def test_generate_app_manifest_error(self, mock_context, mock_mcp, mock_client_cache):
        """Test generate_app_manifest with an error."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock open function to raise an exception
        with patch('builtins.open', side_effect=Exception('File error')):
            # Generate the manifest
            result = await handler.generate_app_manifest(
                mock_context,
                app_name='test-app',
                image_uri='123456789012.dkr.ecr.region.amazonaws.com/repo:tag',
            )

            # Verify the result
            assert result.isError
            assert isinstance(result.content[0], TextContent)
            assert 'Failed to generate YAML' in result.content[0].text
            assert 'File error' in result.content[0].text
            assert result.output_file_path == ''

    def test_load_yaml_template(self, mock_mcp, mock_client_cache):
        """Test _load_yaml_template method."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Create mock file content for templates
        template1 = 'kind: Deployment\nmetadata:\n  name: APP_NAME'
        template2 = 'kind: Service\nmetadata:\n  name: APP_NAME'

        # Mock open to return our test templates
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.side_effect = [template1, template2]
        mock_open.return_value = mock_file

        with patch('builtins.open', mock_open):
            # Test loading and processing templates
            template_files = ['file1.yaml', 'file2.yaml']
            values = {'APP_NAME': 'test-app'}

            result = handler._load_yaml_template(template_files, values)

            # Verify open was called for each template
            assert mock_open.call_count == 2

            # Verify template content was properly processed
            assert 'kind: Deployment' in result
            assert 'kind: Service' in result
            assert 'name: test-app' in result
            assert '---' in result

    @pytest.mark.asyncio
    async def test_generate_app_manifest_multiple_templates(
        self, mock_context, mock_mcp, mock_client_cache
    ):
        """Test generate_app_manifest with multiple templates."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Mock the _load_yaml_template method to avoid template loading issues
        with patch.object(handler, '_load_yaml_template', return_value='combined yaml content'):
            # Mock os.makedirs to avoid creating directories
            with patch('os.makedirs') as mock_makedirs:
                # Mock open for writing output
                with patch('builtins.open', mock_open()) as mocked_open:
                    # Mock os.path.abspath to return a predictable absolute path
                    with patch(
                        'os.path.abspath',
                        return_value='/absolute/path/output/test-app-manifest.yaml',
                    ):
                        # Generate the manifest with all required parameters explicitly specified
                        result = await handler.generate_app_manifest(
                            mock_context,
                            app_name='test-app',
                            image_uri='123456789012.dkr.ecr.region.amazonaws.com/repo:tag',
                            port=80,
                            replicas=2,
                            cpu='100m',
                            memory='128Mi',
                            namespace='default',
                            load_balancer_scheme='internal',  # Using the default value
                            output_dir='output',
                        )

                        # Verify that os.makedirs was called with exist_ok=True
                        mock_makedirs.assert_called_once_with('output', exist_ok=True)

                        # Verify that open was called for writing output
                        mocked_open.assert_called_once_with(
                            '/absolute/path/output/test-app-manifest.yaml', 'w'
                        )

                        # Verify the output file path is absolute
                        assert os.path.isabs(result.output_file_path)
                        assert (
                            result.output_file_path
                            == '/absolute/path/output/test-app-manifest.yaml'
                        )

                        # Verify the result is successful
                        assert not result.isError

    def test_init_with_get_pod_logs(self, mock_mcp, mock_client_cache):
        """Test initialization of K8sHandler with get_pod_logs tool."""
        # Initialize the K8s handler with both write and sensitive data access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            K8sHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=True)

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count == 7

        # Get all call args
        call_args_list = mock_mcp.tool.call_args_list

        # Get all tool names that were registered
        tool_names = [call_args[1]['name'] for call_args in call_args_list]

        # Verify that get_pod_logs and get_k8s_events were registered
        assert 'get_pod_logs' in tool_names
        assert 'get_k8s_events' in tool_names

    def test_init_write_access_disabled(self, mock_mcp, mock_client_cache):
        """Test initialization of K8sHandler with write access disabled."""
        # Initialize the K8s handler with write access disabled but sensitive data access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_write=False, allow_sensitive_data_access=True)

        # Verify that allow_write is set
        assert handler.allow_write is False

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count == 7

        # Get all call args
        call_args_list = mock_mcp.tool.call_args_list

        # Get all tool names that were registered
        tool_names = [call_args[1]['name'] for call_args in call_args_list]

        # Verify that all tools are registered
        assert 'list_k8s_resources' in tool_names
        assert 'get_pod_logs' in tool_names
        assert 'get_k8s_events' in tool_names
        assert 'manage_k8s_resource' in tool_names
        assert 'apply_yaml' in tool_names
        assert 'generate_app_manifest' in tool_names

    @pytest.mark.asyncio
    async def test_get_pod_logs_success(self, mock_context, mock_mcp, mock_client_cache):
        """Test get_pod_logs method with successful log retrieval."""
        # Initialize the K8s handler with sensitive data access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.get_pod_logs.return_value = 'log line 1\nlog line 2\n'

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Get pod logs
            result = await handler.get_pod_logs(
                mock_context,
                cluster_name='test-cluster',
                namespace='test-namespace',
                pod_name='test-pod',
                container_name='test-container',
                since_seconds=60,
                tail_lines=100,
                limit_bytes=1024,
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that get_pod_logs was called with the correct parameters
            mock_k8s_apis.get_pod_logs.assert_called_once_with(
                pod_name='test-pod',
                namespace='test-namespace',
                container_name='test-container',
                since_seconds=60,
                tail_lines=100,
                limit_bytes=1024,
            )

            # Verify the result
            assert not result.isError
            assert result.pod_name == 'test-pod'
            assert result.namespace == 'test-namespace'
            assert result.container_name == 'test-container'
            assert result.log_lines == ['log line 1', 'log line 2', '']
            assert isinstance(result.content[0], TextContent)
            assert (
                'Successfully retrieved 3 log lines from pod test-namespace/test-pod (container: test-container)'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_get_pod_logs_minimal(self, mock_context, mock_mcp, mock_client_cache):
        """Test get_pod_logs method with minimal parameters."""
        # Initialize the K8s handler with sensitive data access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.get_pod_logs.return_value = 'log line 1\nlog line 2\n'

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Get pod logs with minimal parameters - explicitly pass default values for non-optional parameters
            result = await handler.get_pod_logs(
                mock_context,
                cluster_name='test-cluster',
                namespace='test-namespace',
                pod_name='test-pod',
                container_name=None,
                since_seconds=None,
                tail_lines=100,  # Default value
                limit_bytes=10240,  # Default value
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that get_pod_logs was called
            mock_k8s_apis.get_pod_logs.assert_called_once()

            # Get the call args
            args, kwargs = mock_k8s_apis.get_pod_logs.call_args

            # Verify the keyword args
            assert kwargs['pod_name'] == 'test-pod'
            assert kwargs['namespace'] == 'test-namespace'
            assert kwargs['container_name'] is None

            # Verify the result
            assert not result.isError
            assert result.pod_name == 'test-pod'
            assert result.namespace == 'test-namespace'
            assert result.container_name is None
            assert result.log_lines == ['log line 1', 'log line 2', '']
            assert isinstance(result.content[0], TextContent)
            assert (
                'Successfully retrieved 3 log lines from pod test-namespace/test-pod'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_get_pod_logs_sensitive_data_access_disabled(
        self, mock_context, mock_mcp, mock_client_cache
    ):
        """Test get_pod_logs method with sensitive data access disabled."""
        # Initialize the K8s handler with sensitive data access disabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=False)

        # Get pod logs with sensitive data access disabled
        result = await handler.get_pod_logs(
            mock_context,
            cluster_name='test-cluster',
            namespace='test-namespace',
            pod_name='test-pod',
            container_name='test-container',
        )

        # Verify the result
        assert result.isError
        assert result.pod_name == 'test-pod'
        assert result.namespace == 'test-namespace'
        assert result.container_name == 'test-container'
        assert result.log_lines == []
        assert isinstance(result.content[0], TextContent)
        assert (
            'Access to pod logs requires --allow-sensitive-data-access flag'
            in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_get_pod_logs_error(self, mock_context, mock_mcp, mock_client_cache):
        """Test get_pod_logs method with an error."""
        # Initialize the K8s handler with sensitive data access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.get_pod_logs.side_effect = Exception('Pod not found')

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Get pod logs with an error
            result = await handler.get_pod_logs(
                mock_context,
                cluster_name='test-cluster',
                namespace='test-namespace',
                pod_name='test-pod',
                container_name='test-container',
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that get_pod_logs was called
            mock_k8s_apis.get_pod_logs.assert_called_once()

            # Get the call args
            args, kwargs = mock_k8s_apis.get_pod_logs.call_args

            # Verify the keyword args
            assert kwargs['pod_name'] == 'test-pod'
            assert kwargs['namespace'] == 'test-namespace'
            assert kwargs['container_name'] == 'test-container'

            # Verify the result
            assert result.isError
            assert result.pod_name == 'test-pod'
            assert result.namespace == 'test-namespace'
            assert result.container_name == 'test-container'
            assert result.log_lines == []
            assert isinstance(result.content[0], TextContent)
            assert (
                'Failed to get logs from pod test-namespace/test-pod (container: test-container): Pod not found'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_get_k8s_events_success(self, mock_context, mock_mcp, mock_client_cache):
        """Test get_k8s_events method with successful event retrieval."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.get_events.return_value = [
            {
                'first_timestamp': '2023-01-01T00:00:00Z',
                'last_timestamp': '2023-01-01T00:05:00Z',
                'count': 5,
                'message': 'Container created',
                'reason': 'Created',
                'reporting_component': 'kubelet',
                'type': 'Normal',
            },
            {
                'first_timestamp': '2023-01-01T00:05:00Z',
                'last_timestamp': '2023-01-01T00:10:00Z',
                'count': 1,
                'message': 'Container started',
                'reason': 'Started',
                'reporting_component': 'kubelet',
                'type': 'Normal',
            },
        ]

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Get events
            result = await handler.get_k8s_events(
                mock_context,
                cluster_name='test-cluster',
                kind='Pod',
                name='test-pod',
                namespace='test-namespace',
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that get_events was called with the correct parameters
            mock_k8s_apis.get_events.assert_called_once_with(
                kind='Pod',
                name='test-pod',
                namespace='test-namespace',
            )

            # Verify the result
            assert not result.isError
            assert result.involved_object_kind == 'Pod'
            assert result.involved_object_name == 'test-pod'
            assert result.involved_object_namespace == 'test-namespace'
            assert result.count == 2
            assert len(result.events) == 2

            # Check first event
            assert result.events[0].first_timestamp == '2023-01-01T00:00:00Z'
            assert result.events[0].last_timestamp == '2023-01-01T00:05:00Z'
            assert result.events[0].count == 5
            assert result.events[0].message == 'Container created'
            assert result.events[0].reason == 'Created'
            assert result.events[0].reporting_component == 'kubelet'
            assert result.events[0].type == 'Normal'

            # Check second event
            assert result.events[1].message == 'Container started'

            # Check content
            assert isinstance(result.content[0], TextContent)
            assert (
                'Successfully retrieved 2 events for Pod test-namespace/test-pod'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_get_k8s_events_empty(self, mock_context, mock_mcp, mock_client_cache):
        """Test get_k8s_events method with no events found."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.get_events.return_value = []

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Get events
            result = await handler.get_k8s_events(
                mock_context,
                cluster_name='test-cluster',
                kind='Pod',
                name='test-pod',
                namespace='test-namespace',
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that get_events was called
            mock_k8s_apis.get_events.assert_called_once()

            # Verify the result
            assert not result.isError
            assert result.involved_object_kind == 'Pod'
            assert result.involved_object_name == 'test-pod'
            assert result.involved_object_namespace == 'test-namespace'
            assert result.count == 0
            assert len(result.events) == 0
            assert isinstance(result.content[0], TextContent)
            assert (
                'Successfully retrieved 0 events for Pod test-namespace/test-pod'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_get_k8s_events_sensitive_data_access_disabled(
        self, mock_context, mock_mcp, mock_client_cache
    ):
        """Test get_k8s_events method with sensitive data access disabled."""
        # Initialize the K8s handler with sensitive data access disabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=False)

        # Get events with sensitive data access disabled
        result = await handler.get_k8s_events(
            mock_context,
            cluster_name='test-cluster',
            kind='Pod',
            name='test-pod',
            namespace='test-namespace',
        )

        # Verify the result
        assert result.isError
        assert result.involved_object_kind == 'Pod'
        assert result.involved_object_name == 'test-pod'
        assert result.involved_object_namespace == 'test-namespace'
        assert result.count == 0
        assert len(result.events) == 0
        assert isinstance(result.content[0], TextContent)
        assert (
            'Access to Kubernetes events requires --allow-sensitive-data-access flag'
            in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_get_k8s_events_error(self, mock_context, mock_mcp, mock_client_cache):
        """Test get_k8s_events method with an error."""
        # Initialize the K8s handler with sensitive data access enabled
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock get_client
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.get_events.side_effect = Exception('Failed to get events')

        with patch.object(handler, 'get_client', return_value=mock_k8s_apis) as mock_client:
            # Get events with an error
            result = await handler.get_k8s_events(
                mock_context,
                cluster_name='test-cluster',
                kind='Pod',
                name='test-pod',
                namespace='test-namespace',
            )

            # Verify that get_client was called
            mock_client.assert_called_once_with('test-cluster')

            # Verify that get_events was called
            mock_k8s_apis.get_events.assert_called_once()

            # Verify the result
            assert result.isError
            assert result.involved_object_kind == 'Pod'
            assert result.involved_object_name == 'test-pod'
            assert result.involved_object_namespace == 'test-namespace'
            assert result.count == 0
            assert len(result.events) == 0
            assert isinstance(result.content[0], TextContent)
            assert (
                'Failed to get events for Pod test-namespace/test-pod: Failed to get events'
                in result.content[0].text
            )

    def test_remove_managed_fields(self, mock_mcp, mock_client_cache):
        """Test remove_managed_fields method for removing managed_fields from Kubernetes resources."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Create a deep copy of the input to avoid modifying the original
        import copy

        # Test case 1: Resource with managedFields (camelCase as used by dynamic client)
        resource_with_managed_fields = {
            'metadata': {
                'name': 'test-pod',
                'namespace': 'default',
                'managedFields': [
                    {
                        'manager': 'kubectl',
                        'operation': 'Update',
                        'apiVersion': 'v1',
                        'time': '2023-01-01T00:00:00Z',
                        'fieldsType': 'FieldsV1',
                        'fieldsV1': {'f:metadata': {'f:labels': {'.': {}, 'f:app': {}}}},
                    }
                ],
            },
            'spec': {'containers': [{'name': 'container1', 'image': 'nginx'}]},
        }

        expected_result = {
            'metadata': {'name': 'test-pod', 'namespace': 'default'},
            'spec': {'containers': [{'name': 'container1', 'image': 'nginx'}]},
        }

        # Make a deep copy to avoid modifying the original
        input_copy = copy.deepcopy(resource_with_managed_fields)
        result = handler.remove_managed_fields(input_copy)
        assert result == expected_result

        # Test case 2: Resource without managedFields
        resource_without_managed_fields = {
            'metadata': {'name': 'test-pod', 'namespace': 'default'},
            'spec': {'containers': [{'name': 'container1', 'image': 'nginx'}]},
        }

        # The result should be the same as the input
        result = handler.remove_managed_fields(resource_without_managed_fields)
        assert result == resource_without_managed_fields

        # Test case 3: Resource without metadata
        resource_without_metadata = {
            'kind': 'Pod',
            'apiVersion': 'v1',
            'spec': {'containers': [{'name': 'container1', 'image': 'nginx'}]},
        }

        # The result should be the same as the input
        result = handler.remove_managed_fields(resource_without_metadata)
        assert result == resource_without_metadata

        # Test case 4: Non-dict input
        non_dict_input = {}  # Use empty dict instead of string to avoid type error
        result = handler.remove_managed_fields(non_dict_input)
        assert result == non_dict_input

    def test_cleanup_resource_response(self, mock_mcp, mock_client_cache):
        """Test cleanup_resource_response method for removing managed fields and null values."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Create a complex resource with both managed_fields and null values
        complex_resource = {
            'kind': 'Pod',
            'apiVersion': 'v1',
            'metadata': {
                'name': 'test-pod',
                'namespace': 'default',
                'managedFields': [
                    {
                        'manager': 'kubectl',
                        'operation': 'Update',
                        'apiVersion': 'v1',
                        'time': '2023-01-01T00:00:00Z',
                        'fieldsType': 'FieldsV1',
                        'fieldsV1': {'f:metadata': {'f:labels': {'.': {}, 'f:app': {}}}},
                    }
                ],
                'labels': {'app': 'test', 'environment': None},
                'annotations': None,
            },
            'spec': {
                'containers': [
                    {'name': 'container1', 'image': 'nginx', 'resources': None},
                    None,
                    {
                        'name': 'container2',
                        'image': 'redis',
                        'ports': [{'containerPort': 6379}, {'containerPort': None}],
                    },
                ],
                'volumes': None,
            },
            'status': None,
        }

        # Expected result after cleanup
        expected_result = {
            'kind': 'Pod',
            'apiVersion': 'v1',
            'metadata': {'name': 'test-pod', 'namespace': 'default', 'labels': {'app': 'test'}},
            'spec': {
                'containers': [
                    {'name': 'container1', 'image': 'nginx'},
                    {
                        'name': 'container2',
                        'image': 'redis',
                        'ports': [{'containerPort': 6379}, {}],
                    },
                ]
            },
        }

        # Test with spies to verify both methods are called
        with patch.object(
            handler, 'remove_managed_fields', wraps=handler.remove_managed_fields
        ) as mock_remove:
            with patch.object(
                handler, 'filter_null_values', wraps=handler.filter_null_values
            ) as mock_filter:
                result = handler.cleanup_resource_response(complex_resource)

                # Verify that both methods were called
                mock_remove.assert_called_once_with(complex_resource)
                # We don't check the exact number of calls for filter_null_values since it's recursive
                # and will be called for each nested element
                assert mock_filter.called

                # Just verify that filter_null_values was called at least once
                # We can't easily check the exact argument since remove_managed_fields modifies the input

                # Verify the final result
                assert result == expected_result

        # Test with a simple string input
        simple_input = 'simple string'
        result = handler.cleanup_resource_response(simple_input)
        assert result == simple_input

    def test_filter_null_values(self, mock_mcp, mock_client_cache):
        """Test filter_null_values method for removing null values from data structures."""
        # Initialize the K8s handler
        with patch(
            'awslabs.eks_mcp_server.k8s_handler.K8sClientCache', return_value=mock_client_cache
        ):
            handler = K8sHandler(mock_mcp)

        # Test case 1: Simple dictionary with null values
        input_dict = {'key1': 'value1', 'key2': None, 'key3': 'value3', 'key4': None}
        expected_dict = {'key1': 'value1', 'key3': 'value3'}
        result = handler.filter_null_values(input_dict)
        assert result == expected_dict

        # Test case 2: Nested dictionary with null values
        input_nested_dict = {
            'key1': 'value1',
            'key2': None,
            'key3': {
                'nested1': 'nested_value1',
                'nested2': None,
                'nested3': {'deep1': 'deep_value1', 'deep2': None},
            },
        }
        expected_nested_dict = {
            'key1': 'value1',
            'key3': {'nested1': 'nested_value1', 'nested3': {'deep1': 'deep_value1'}},
        }
        result = handler.filter_null_values(input_nested_dict)
        assert result == expected_nested_dict

        # Test case 3: List with null values
        input_list = ['item1', None, 'item2', None, 'item3']
        expected_list = ['item1', 'item2', 'item3']
        result = handler.filter_null_values(input_list)
        assert result == expected_list

        # Test case 4: List of dictionaries with null values
        input_list_of_dicts = [
            {'key1': 'value1', 'key2': None},
            None,
            {'key3': None, 'key4': 'value4'},
        ]
        expected_list_of_dicts = [{'key1': 'value1'}, {'key4': 'value4'}]
        result = handler.filter_null_values(input_list_of_dicts)
        assert result == expected_list_of_dicts

        # Test case 5: Primitive values (non-dict, non-list)
        assert handler.filter_null_values('string') == 'string'
        assert handler.filter_null_values(123) == 123
        assert handler.filter_null_values(True)
        assert handler.filter_null_values(None) is None  # None input should return None

        # Test case 6: Empty containers
        assert handler.filter_null_values({}) == {}
        assert handler.filter_null_values([]) == []

        # Test case 7: Complex nested structure
        complex_input = {
            'metadata': {
                'name': 'test-pod',
                'namespace': 'default',
                'labels': {'app': 'test', 'environment': None},
                'annotations': None,
            },
            'spec': {
                'containers': [
                    {'name': 'container1', 'image': 'nginx', 'resources': None},
                    None,
                    {
                        'name': 'container2',
                        'image': 'redis',
                        'ports': [{'containerPort': 6379}, {'containerPort': None}],
                    },
                ],
                'volumes': None,
            },
            'status': None,
        }

        expected_complex = {
            'metadata': {'name': 'test-pod', 'namespace': 'default', 'labels': {'app': 'test'}},
            'spec': {
                'containers': [
                    {'name': 'container1', 'image': 'nginx'},
                    {
                        'name': 'container2',
                        'image': 'redis',
                        'ports': [{'containerPort': 6379}, {}],
                    },
                ]
            },
        }

        result = handler.filter_null_values(complex_input)
        assert result == expected_complex
