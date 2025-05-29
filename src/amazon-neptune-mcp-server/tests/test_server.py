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
"""Tests for the amazon-neptune MCP Server."""

import pytest
from awslabs.amazon_neptune_mcp_server.server import (
    get_graph,
    get_schema,
    get_schema_resource,
    get_status,
    get_status_resource,
    main,
    run_gremlin_query,
    run_opencypher_query,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
class TestServerTools:
    """Test class for server tool functions that interact with the Neptune graph."""

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_status(self, mock_get_graph):
        """Test that get_status correctly returns the status from the graph.
        This test verifies that:
        1. The get_graph function is called to obtain the graph instance
        2. The status method is called on the graph instance
        3. The result from the graph's status method is returned unchanged.
        """
        # Arrange
        mock_graph = MagicMock()
        mock_graph.status.return_value = 'Connected'
        mock_get_graph.return_value = mock_graph

        # Act
        result = get_status()

        # Assert
        assert result == 'Connected'
        mock_graph.status.assert_called_once()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_schema(self, mock_get_graph):
        """Test that get_schema correctly returns the schema from the graph.
        This test verifies that:
        1. The get_graph function is called to obtain the graph instance
        2. The schema method is called on the graph instance
        3. The result from the graph's schema method is returned unchanged.
        """
        # Arrange
        mock_graph = MagicMock()
        mock_schema = MagicMock()
        mock_graph.schema.return_value = mock_schema
        mock_get_graph.return_value = mock_graph

        # Act
        result = get_schema()

        # Assert
        assert result == mock_schema
        mock_graph.schema.assert_called_once()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_run_opencypher_query(self, mock_get_graph):
        """Test that run_opencypher_query correctly executes a query without parameters.
        This test verifies that:
        1. The get_graph function is called to obtain the graph instance
        2. The query_opencypher method is called with the correct query and None parameters
        3. The result from the graph's query_opencypher method is returned unchanged.
        """
        # Arrange
        mock_graph = MagicMock()
        mock_result = {'results': [{'n': {'id': '1'}}]}
        mock_graph.query_opencypher.return_value = mock_result
        mock_get_graph.return_value = mock_graph

        # Act
        result = run_opencypher_query('MATCH (n) RETURN n LIMIT 1')

        # Assert
        assert result == mock_result
        mock_graph.query_opencypher.assert_called_once_with('MATCH (n) RETURN n LIMIT 1', None)

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_run_opencypher_query_with_parameters(self, mock_get_graph):
        """Test that run_opencypher_query correctly executes a query with parameters.
        This test verifies that:
        1. The get_graph function is called to obtain the graph instance
        2. The query_opencypher method is called with the correct query and parameters
        3. The result from the graph's query_opencypher method is returned unchanged.
        """
        # Arrange
        mock_graph = MagicMock()
        mock_result = {'results': [{'n': {'id': '1'}}]}
        mock_graph.query_opencypher.return_value = mock_result
        mock_get_graph.return_value = mock_graph
        parameters = {'id': '1'}

        # Act
        result = run_opencypher_query('MATCH (n) WHERE n.id = $id RETURN n', parameters)

        # Assert
        assert result == mock_result
        mock_graph.query_opencypher.assert_called_once_with(
            'MATCH (n) WHERE n.id = $id RETURN n', parameters
        )

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_run_gremlin_query(self, mock_get_graph):
        """Test that run_gremlin_query correctly executes a Gremlin query.
        This test verifies that:
        1. The get_graph function is called to obtain the graph instance
        2. The query_gremlin method is called with the correct query
        3. The result from the graph's query_gremlin method is returned unchanged.
        """
        # Arrange
        mock_graph = MagicMock()
        mock_result = {'results': [{'id': '1'}]}
        mock_graph.query_gremlin.return_value = mock_result
        mock_get_graph.return_value = mock_graph

        # Act
        result = run_gremlin_query('g.V().limit(1)')

        # Assert
        assert result == mock_result
        mock_graph.query_gremlin.assert_called_once_with('g.V().limit(1)')

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_status_resource(self, mock_get_graph):
        """Test that get_status_resource correctly returns the status from the graph.
        This test verifies that:
        1. The get_graph function is called to obtain the graph instance
        2. The status method is called on the graph instance
        3. The result from the graph's status method is returned unchanged.
        """
        # Arrange
        mock_graph = MagicMock()
        mock_graph.status.return_value = 'AVAILABLE'
        mock_get_graph.return_value = mock_graph

        # Act
        result = get_status_resource()

        # Assert
        assert result == 'AVAILABLE'
        mock_graph.status.assert_called_once()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_schema_resource(self, mock_get_graph):
        """Test that get_schema_resource correctly returns the schema from the graph.
        This test verifies that:
        1. The get_graph function is called to obtain the graph instance
        2. The schema method is called on the graph instance
        3. The result from the graph's schema method is returned unchanged.
        """
        # Arrange
        mock_graph = MagicMock()
        mock_schema = MagicMock()
        mock_graph.schema.return_value = mock_schema
        mock_get_graph.return_value = mock_graph

        # Act
        result = get_schema_resource()

        # Assert
        assert result == mock_schema
        mock_graph.schema.assert_called_once()


@pytest.mark.asyncio
class TestGraphInitialization:
    """Test class for the graph initialization functionality."""

    @patch('os.environ.get')
    @patch('awslabs.amazon_neptune_mcp_server.server.NeptuneServer')
    async def test_get_graph_initialization(self, mock_neptune_server, mock_environ_get):
        """Test that get_graph correctly initializes a NeptuneServer instance.
        This test verifies that:
        1. Environment variables are correctly read
        2. NeptuneServer is initialized with the correct parameters
        3. The same instance is returned on subsequent calls (singleton pattern).
        """
        # Arrange
        mock_environ_get.side_effect = lambda key, default=None: {
            'NEPTUNE_ENDPOINT': 'neptune-db://test-endpoint',
            'NEPTUNE_USE_HTTPS': 'True',
        }.get(key, default)

        mock_server = MagicMock()
        mock_neptune_server.return_value = mock_server

        # Act
        graph = get_graph()

        # Assert
        assert graph == mock_server
        mock_neptune_server.assert_called_once_with('neptune-db://test-endpoint', use_https=True)

        # Call again to verify singleton behavior
        graph2 = get_graph()
        assert graph2 == graph
        mock_neptune_server.assert_called_once()  # Should not be called again

    @patch('os.environ.get')
    async def test_get_graph_missing_endpoint(self, mock_environ_get):
        """Test that get_graph raises an error when the NEPTUNE_ENDPOINT environment variable is missing.
        This test verifies that:
        1. When NEPTUNE_ENDPOINT is None, a ValueError is raised
        2. The error message correctly indicates the missing environment variable.
        """
        # Arrange
        mock_environ_get.side_effect = lambda key, default=None: {
            'NEPTUNE_ENDPOINT': None,
            'NEPTUNE_USE_HTTPS': 'True',
        }.get(key, default)

        # Reset the global _graph variable
        import awslabs.amazon_neptune_mcp_server.server

        awslabs.amazon_neptune_mcp_server.server._graph = None

        # Act & Assert
        with pytest.raises(ValueError, match='NEPTUNE_ENDPOINT environment variable is not set'):
            get_graph()

    @patch('os.environ.get')
    @patch('awslabs.amazon_neptune_mcp_server.server.NeptuneServer')
    async def test_get_graph_with_https_false(self, mock_neptune_server, mock_environ_get):
        """Test that get_graph correctly handles HTTPS settings from environment variables.
        This test verifies that:
        1. When NEPTUNE_USE_HTTPS is set to "false", use_https is set to False
        2. NeptuneServer is initialized with the correct parameters.
        """
        # Arrange
        mock_environ_get.side_effect = lambda key, default=None: {
            'NEPTUNE_ENDPOINT': 'neptune-db://test-endpoint',
            'NEPTUNE_USE_HTTPS': 'false',
        }.get(key, default)

        # Reset the global _graph variable
        import awslabs.amazon_neptune_mcp_server.server

        awslabs.amazon_neptune_mcp_server.server._graph = None

        mock_server = MagicMock()
        mock_neptune_server.return_value = mock_server

        # Act
        graph = get_graph()

        # Assert
        assert graph == mock_server
        mock_neptune_server.assert_called_once_with('neptune-db://test-endpoint', use_https=False)


@pytest.mark.asyncio
class TestMainFunction:
    """Test class for the main function that runs the MCP server."""

    @patch('awslabs.amazon_neptune_mcp_server.server.mcp')
    async def test_main_default(self, mock_mcp):
        """Test that main correctly runs the server with default settings."""
        # Arrange

        # Act
        main()

        # Assert
        assert mock_mcp.run.call_count == 1
