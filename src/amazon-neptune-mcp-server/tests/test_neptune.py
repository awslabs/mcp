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
"""Tests for the NeptuneServer class."""

import pytest
from unittest.mock import patch, MagicMock
from awslabs.amazon_neptune_mcp_server.neptune import NeptuneServer
from awslabs.amazon_neptune_mcp_server.models import GraphSchema


@pytest.mark.asyncio
class TestNeptuneServer:
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneDatabase')
    async def test_init_neptune_db(self, mock_neptune_db):
        # Arrange
        mock_db_instance = MagicMock()
        mock_neptune_db.return_value = mock_db_instance
        endpoint = "neptune-db://test-endpoint"
        
        # Act
        server = NeptuneServer(endpoint, use_https=True, port=8182)
        
        # Assert
        assert server.graph == mock_db_instance
        mock_neptune_db.assert_called_once_with("test-endpoint", 8182, use_https=True)
    
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneAnalytics')
    async def test_init_neptune_analytics(self, mock_neptune_analytics):
        # Arrange
        mock_analytics_instance = MagicMock()
        mock_neptune_analytics.return_value = mock_analytics_instance
        endpoint = "neptune-graph://test-graph-id"
        
        # Act
        server = NeptuneServer(endpoint)
        
        # Assert
        assert server.graph == mock_analytics_instance
        mock_neptune_analytics.assert_called_once_with("test-graph-id")
    
    async def test_init_invalid_endpoint_format(self):
        # Act & Assert
        with pytest.raises(ValueError, match="You must provide an endpoint to create a NeptuneServer as either neptune-db"):
            NeptuneServer("invalid-endpoint")
    
    async def test_init_empty_endpoint(self):
        # Act & Assert
        with pytest.raises(ValueError, match="You must provide an endpoint to create a NeptuneServer"):
            NeptuneServer("")
    
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneDatabase')
    async def test_status_available(self, mock_neptune_db):
        # Arrange
        mock_db_instance = MagicMock()
        mock_db_instance.query_opencypher.return_value = {"result": 1}
        mock_neptune_db.return_value = mock_db_instance
        
        server = NeptuneServer("neptune-db://test-endpoint")
        
        # Act
        status = server.status()
        
        # Assert
        assert status == "Available"
        mock_db_instance.query_opencypher.assert_called_once_with("RETURN 1", None)
    
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneDatabase')
    async def test_status_unavailable(self, mock_neptune_db):
        # Arrange
        mock_db_instance = MagicMock()
        mock_db_instance.query_opencypher.side_effect = Exception("Connection error")
        mock_neptune_db.return_value = mock_db_instance
        
        server = NeptuneServer("neptune-db://test-endpoint")
        
        # Act
        status = server.status()
        
        # Assert
        assert status == "Unavailable"
        mock_db_instance.query_opencypher.assert_called_once_with("RETURN 1", None)
    
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneDatabase')
    async def test_schema(self, mock_neptune_db):
        # Arrange
        mock_db_instance = MagicMock()
        mock_schema = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
        mock_db_instance.get_schema.return_value = mock_schema
        mock_neptune_db.return_value = mock_db_instance
        
        server = NeptuneServer("neptune-db://test-endpoint")
        
        # Act
        schema = server.schema()
        
        # Assert
        assert schema == mock_schema
        mock_db_instance.get_schema.assert_called_once()
    
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneDatabase')
    async def test_query_opencypher(self, mock_neptune_db):
        # Arrange
        mock_db_instance = MagicMock()
        mock_result = {"results": [{"n": {"id": "1"}}]}
        mock_db_instance.query_opencypher.return_value = mock_result
        mock_neptune_db.return_value = mock_db_instance
        
        server = NeptuneServer("neptune-db://test-endpoint")
        
        # Act
        result = server.query_opencypher("MATCH (n) RETURN n LIMIT 1")
        
        # Assert
        assert result == mock_result
        mock_db_instance.query_opencypher.assert_called_once_with("MATCH (n) RETURN n LIMIT 1", None)
    
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneDatabase')
    async def test_query_opencypher_with_parameters(self, mock_neptune_db):
        # Arrange
        mock_db_instance = MagicMock()
        mock_result = {"results": [{"n": {"id": "1"}}]}
        mock_db_instance.query_opencypher.return_value = mock_result
        mock_neptune_db.return_value = mock_db_instance
        
        server = NeptuneServer("neptune-db://test-endpoint")
        parameters = {"id": "1"}
        
        # Act
        result = server.query_opencypher("MATCH (n) WHERE n.id = $id RETURN n", parameters)
        
        # Assert
        assert result == mock_result
        mock_db_instance.query_opencypher.assert_called_once_with("MATCH (n) WHERE n.id = $id RETURN n", parameters)
    
    @patch('awslabs.amazon_neptune_mcp_server.neptune.NeptuneDatabase')
    async def test_query_gremlin(self, mock_neptune_db):
        # Arrange
        mock_db_instance = MagicMock()
        mock_result = {"results": [{"id": "1"}]}
        mock_db_instance.query_gremlin.return_value = mock_result
        mock_neptune_db.return_value = mock_db_instance
        
        server = NeptuneServer("neptune-db://test-endpoint")
        
        # Act
        result = server.query_gremlin("g.V().limit(1)")
        
        # Assert
        assert result == mock_result
        mock_db_instance.query_gremlin.assert_called_once_with("g.V().limit(1)")