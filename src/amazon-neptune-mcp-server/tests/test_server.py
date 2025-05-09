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
from unittest.mock import patch, MagicMock
from awslabs.amazon_neptune_mcp_server.server import (
    get_graph,
    get_status,
    get_schema,
    run_opencypher_query,
    run_gremlin_query,
    get_status_resource,
    get_schema_resource,
    main
)


@pytest.mark.asyncio
class TestServerTools:
    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_status(self, mock_get_graph):
        # Arrange
        mock_graph = MagicMock()
        mock_graph.status.return_value = "Connected"
        mock_get_graph.return_value = mock_graph
        
        # Act
        result = get_status()
        
        # Assert
        assert result == "Connected"
        mock_graph.status.assert_called_once()
    
    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_schema(self, mock_get_graph):
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
        # Arrange
        mock_graph = MagicMock()
        mock_result = {"results": [{"n": {"id": "1"}}]}
        mock_graph.query_opencypher.return_value = mock_result
        mock_get_graph.return_value = mock_graph
        
        # Act
        result = run_opencypher_query("MATCH (n) RETURN n LIMIT 1")
        
        # Assert
        assert result == mock_result
        mock_graph.query_opencypher.assert_called_once_with("MATCH (n) RETURN n LIMIT 1", None)
    
    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_run_opencypher_query_with_parameters(self, mock_get_graph):
        # Arrange
        mock_graph = MagicMock()
        mock_result = {"results": [{"n": {"id": "1"}}]}
        mock_graph.query_opencypher.return_value = mock_result
        mock_get_graph.return_value = mock_graph
        parameters = {"id": "1"}
        
        # Act
        result = run_opencypher_query("MATCH (n) WHERE n.id = $id RETURN n", parameters)
        
        # Assert
        assert result == mock_result
        mock_graph.query_opencypher.assert_called_once_with(
            "MATCH (n) WHERE n.id = $id RETURN n", 
            parameters
        )
    
    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_run_gremlin_query(self, mock_get_graph):
        # Arrange
        mock_graph = MagicMock()
        mock_result = {"results": [{"id": "1"}]}
        mock_graph.query_gremlin.return_value = mock_result
        mock_get_graph.return_value = mock_graph
        
        # Act
        result = run_gremlin_query("g.V().limit(1)")
        
        # Assert
        assert result == mock_result
        mock_graph.query_gremlin.assert_called_once_with("g.V().limit(1)")
    
    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_status_resource(self, mock_get_graph):
        # Arrange
        mock_graph = MagicMock()
        mock_graph.status.return_value = "AVAILABLE"
        mock_get_graph.return_value = mock_graph
        
        # Act
        result = get_status_resource()
        
        # Assert
        assert result == "AVAILABLE"
        mock_graph.status.assert_called_once()
    
    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_get_schema_resource(self, mock_get_graph):
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
    @patch('os.environ.get')
    @patch('awslabs.amazon_neptune_mcp_server.server.NeptuneServer')
    async def test_get_graph_initialization(self, mock_neptune_server, mock_environ_get):
        # Arrange
        mock_environ_get.side_effect = lambda key, default=None: {
            "NEPTUNE_ENDPOINT": "neptune-db://test-endpoint",
            "NEPTUNE_USE_HTTPS": "True"
        }.get(key, default)
        
        mock_server = MagicMock()
        mock_neptune_server.return_value = mock_server
        
        # Act
        graph = get_graph()
        
        # Assert
        assert graph == mock_server
        mock_neptune_server.assert_called_once_with("neptune-db://test-endpoint", use_https=True)
        
        # Call again to verify singleton behavior
        graph2 = get_graph()
        assert graph2 == graph
        mock_neptune_server.assert_called_once()  # Should not be called again
    
    @patch('os.environ.get')
    async def test_get_graph_missing_endpoint(self, mock_environ_get):
        # Arrange
        mock_environ_get.side_effect = lambda key, default=None: {
            "NEPTUNE_ENDPOINT": None,
            "NEPTUNE_USE_HTTPS": "True"
        }.get(key, default)
        
        # Reset the global _graph variable
        import awslabs.amazon_neptune_mcp_server.server
        awslabs.amazon_neptune_mcp_server.server._graph = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="NEPTUNE_ENDPOINT environment variable is not set"):
            get_graph()
    
    @patch('os.environ.get')
    @patch('awslabs.amazon_neptune_mcp_server.server.NeptuneServer')
    async def test_get_graph_with_https_false(self, mock_neptune_server, mock_environ_get):
        # Arrange
        mock_environ_get.side_effect = lambda key, default=None: {
            "NEPTUNE_ENDPOINT": "neptune-db://test-endpoint",
            "NEPTUNE_USE_HTTPS": "false"
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
        mock_neptune_server.assert_called_once_with("neptune-db://test-endpoint", use_https=False)


@pytest.mark.asyncio
class TestMainFunction:
    @patch('awslabs.amazon_neptune_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_main_default(self, mock_parse_args, mock_mcp):
        # Arrange
        mock_args = MagicMock()
        mock_args.sse = False
        mock_parse_args.return_value = mock_args
        
        # Act
        main()
        
        # Assert
        mock_mcp.run.assert_called_once_with()
        assert not mock_mcp.settings.port.called
    
    @patch('awslabs.amazon_neptune_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_main_with_sse(self, mock_parse_args, mock_mcp):
        # Arrange
        mock_args = MagicMock()
        mock_args.sse = True
        mock_args.port = 9999
        mock_parse_args.return_value = mock_args
        
        # Act
        main()
        
        # Assert
        mock_mcp.run.assert_called_once_with(transport='sse')
        assert mock_mcp.settings.port == 9999
    
    @patch('awslabs.amazon_neptune_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_main_with_custom_port(self, mock_parse_args, mock_mcp):
        # Arrange
        mock_args = MagicMock()
        mock_args.sse = True
        mock_args.port = 7777
        mock_parse_args.return_value = mock_args
        
        # Act
        main()
        
        # Assert
        mock_mcp.run.assert_called_once_with(transport='sse')
        assert mock_mcp.settings.port == 7777