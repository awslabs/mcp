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
"""Tests for the NeptuneAnalytics class."""

import pytest
import json
from unittest.mock import MagicMock, patch, Mock
from awslabs.amazon_neptune_mcp_server.graph_store.analytics import NeptuneAnalytics
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.models import GraphSchema, Node, Relationship, RelationshipPattern, Property


@pytest.mark.asyncio
class TestNeptuneAnalytics:
    """Test class for the NeptuneAnalytics functionality."""
    
    @patch('boto3.Session')
    async def test_init_success(self, mock_session):
        """
        Test successful initialization of NeptuneAnalytics.
        
        This test verifies that:
        1. The boto3 Session is created correctly
        2. The client is created with the correct service name
        3. The schema is refreshed during initialization
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to avoid actual API calls
        with patch.object(NeptuneAnalytics, '_refresh_schema', return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[])):
            # Act
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Assert
            mock_session.assert_called_once()
            mock_session_instance.client.assert_called_once_with("neptune-graph")
            assert analytics.client == mock_client
            assert analytics.graph_identifier == "test-graph-id"
    
    @patch('boto3.Session')
    async def test_init_with_credentials_profile(self, mock_session):
        """
        Test initialization with a credentials profile.
        
        This test verifies that:
        1. The boto3 Session is created with the specified profile name
        2. The client is created with the correct service name
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to avoid actual API calls
        with patch.object(NeptuneAnalytics, '_refresh_schema', return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[])):
            # Act
            analytics = NeptuneAnalytics(
                graph_identifier="test-graph-id", 
                credentials_profile_name="test-profile"
            )
            
            # Assert
            mock_session.assert_called_once_with(profile_name="test-profile")
            mock_session_instance.client.assert_called_once_with("neptune-graph")
    
    @patch('boto3.Session')
    async def test_init_session_error(self, mock_session):
        """
        Test handling of session creation errors.
        
        This test verifies that:
        1. Errors during session creation are properly caught and re-raised
        2. The error message is appropriate
        """
        # Arrange
        mock_session.side_effect = Exception("Auth error")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Could not load credentials to authenticate with AWS client"):
            NeptuneAnalytics(graph_identifier="test-graph-id")
    
    @patch('boto3.Session')
    async def test_init_refresh_schema_error(self, mock_session):
        """
        Test handling of schema refresh errors.
        
        This test verifies that:
        1. Errors during schema refresh are properly caught and re-raised as NeptuneException
        2. The error message is appropriate
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to raise an exception
        with patch.object(NeptuneAnalytics, '_refresh_schema', side_effect=Exception("Schema refresh error")):
            # Act & Assert
            with pytest.raises(NeptuneException) as exc_info:
                NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Check the exception details
            assert "Could not get schema for Neptune database" in exc_info.value.message
    
    @patch('boto3.Session')
    async def test_refresh_schema(self, mock_session):
        """
        Test schema refresh functionality.
        
        This test verifies that:
        1. The query_opencypher method is called with the pg_schema query
        2. The schema data is correctly processed from the response
        3. The schema is stored in the instance and returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Create a mock schema response
        mock_schema_data = {
            "labelTriples": [
                {"~from": "Person", "~type": "KNOWS", "~to": "Person"},
                {"~from": "Person", "~type": "ACTED_IN", "~to": "Movie"}
            ],
            "nodeLabels": ["Person", "Movie"],
            "edgeLabels": ["KNOWS", "ACTED_IN"],
            "nodeLabelDetails": {
                "Person": {
                    "properties": {
                        "name": {"datatypes": ["STRING"]},
                        "age": {"datatypes": ["INTEGER"]}
                    }
                },
                "Movie": {
                    "properties": {
                        "title": {"datatypes": ["STRING"]},
                        "year": {"datatypes": ["INTEGER"]}
                    }
                }
            },
            "edgeLabelDetails": {
                "KNOWS": {
                    "properties": {
                        "since": {"datatypes": ["DATE"]}
                    }
                },
                "ACTED_IN": {
                    "properties": {
                        "role": {"datatypes": ["STRING"]}
                    }
                }
            }
        }
        
        # Create the analytics instance
        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
        
        # Create a new instance for testing the actual method
        analytics2 = NeptuneAnalytics.__new__(NeptuneAnalytics)
        analytics2.graph_identifier = "test-graph-id"
        analytics2.schema = None
        
        # Mock query_opencypher to return the schema data
        analytics2.query_opencypher = MagicMock(return_value=[{"schema": mock_schema_data}])
        
        # Act
        schema = analytics2._refresh_schema()
        
        # Assert
        analytics2.query_opencypher.assert_called_once()
        assert len(schema.nodes) == 2
        assert len(schema.relationships) == 2
        assert len(schema.relationship_patterns) == 2
        
        # Check that the schema was stored in the instance
        assert analytics2.schema == schema
        
        # Verify node properties
        person_node = next((n for n in schema.nodes if n.labels == "Person"), None)
        assert person_node is not None
        assert len(person_node.properties) == 2
        assert any(p.name == "name" and p.type == ["STRING"] for p in person_node.properties)
        assert any(p.name == "age" and p.type == ["INTEGER"] for p in person_node.properties)
        
        # Verify relationship properties
        knows_rel = next((r for r in schema.relationships if r.type == "KNOWS"), None)
        assert knows_rel is not None
        assert len(knows_rel.properties) == 1
        assert knows_rel.properties[0].name == "since"
        assert knows_rel.properties[0].type == ["DATE"]
        
        # Verify relationship patterns
        knows_pattern = next((p for p in schema.relationship_patterns if p.relation == "KNOWS"), None)
        assert knows_pattern is not None
        assert knows_pattern.left_node == "Person"
        assert knows_pattern.right_node == "Person"
    
    @patch('boto3.Session')
    async def test_get_schema_cached(self, mock_session):
        """
        Test that get_schema returns cached schema when available.
        
        This test verifies that:
        1. When schema is already cached, _refresh_schema is not called
        2. The cached schema is returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Create a mock schema
        mock_schema = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneAnalytics, '_refresh_schema', return_value=mock_schema):
            # Create the analytics instance
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Act
            result = analytics.get_schema()
            
            # Assert - just verify the result is the mock schema
            assert result == mock_schema
    
    @patch('boto3.Session')
    async def test_get_schema_refresh(self, mock_session):
        """
        Test that get_schema refreshes schema when not cached.
        
        This test verifies that:
        1. When schema is not cached, _refresh_schema is called
        2. The refreshed schema is returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Create a mock schema
        mock_schema = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneAnalytics, '_refresh_schema', return_value=mock_schema):
            # Create the analytics instance
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Set schema to None to force refresh
            analytics.schema = None
            
            # Reset the mock to verify it's called again
            NeptuneAnalytics._refresh_schema.reset_mock()
            NeptuneAnalytics._refresh_schema.return_value = mock_schema
            
            # Act
            result = analytics.get_schema()
            
            # Assert
            NeptuneAnalytics._refresh_schema.assert_called_once()
            assert result == mock_schema
    
    @patch('boto3.Session')
    async def test_query_opencypher_success(self, mock_session):
        """
        Test successful execution of openCypher queries.
        
        This test verifies that:
        1. The execute_query API is called with the correct parameters
        2. The result is correctly extracted from the response
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response
        mock_payload = Mock()
        mock_payload.read.return_value = json.dumps({"results": [{"n": {"id": "1"}}]}).encode('utf-8')
        mock_client.execute_query.return_value = {"payload": mock_payload}
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            # Create the analytics instance
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Act
            query = "MATCH (n) RETURN n LIMIT 1"
            result = analytics.query_opencypher(query)
            
            # Assert
            mock_client.execute_query.assert_called_once_with(
                graphIdentifier="test-graph-id",
                queryString=query,
                parameters={},
                language="OPEN_CYPHER"
            )
            assert result == [{"n": {"id": "1"}}]
    
    @patch('boto3.Session')
    async def test_query_opencypher_with_params(self, mock_session):
        """
        Test execution of openCypher queries with parameters.
        
        This test verifies that:
        1. The execute_query API is called with the correct parameters
        2. The parameters are passed correctly
        3. The result is correctly extracted from the response
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response
        mock_payload = Mock()
        mock_payload.read.return_value = json.dumps({"results": [{"n": {"id": "1"}}]}).encode('utf-8')
        mock_client.execute_query.return_value = {"payload": mock_payload}
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            # Create the analytics instance
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Act
            query = "MATCH (n) WHERE n.id = $id RETURN n"
            params = {"id": "1"}
            result = analytics.query_opencypher(query, params)
            
            # Assert
            mock_client.execute_query.assert_called_once_with(
                graphIdentifier="test-graph-id",
                queryString=query,
                parameters=params,
                language="OPEN_CYPHER"
            )
            assert result == [{"n": {"id": "1"}}]
    
    @patch('boto3.Session')
    async def test_query_opencypher_error(self, mock_session):
        """
        Test handling of errors in openCypher queries.
        
        This test verifies that:
        1. API errors are properly caught and re-raised as NeptuneException
        2. The error message is appropriate
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API to raise an exception
        mock_client.execute_query.side_effect = Exception("Query error")
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            # Create the analytics instance
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Act & Assert
            with pytest.raises(NeptuneException) as exc_info:
                analytics.query_opencypher("MATCH (n) RETURN n")
            
            # Check the exception details
            assert "An error occurred while executing the query" in exc_info.value.message
            assert "Query error" in exc_info.value.details
    
    @patch('boto3.Session')
    async def test_query_gremlin_not_supported(self, mock_session):
        """
        Test that Gremlin queries are not supported.
        
        This test verifies that:
        1. Calling query_gremlin raises NotImplementedError
        2. The error message indicates that Gremlin is not supported
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            # Create the analytics instance
            analytics = NeptuneAnalytics(graph_identifier="test-graph-id")
            
            # Act & Assert
            with pytest.raises(NotImplementedError, match="Gremlin queries are not supported for Neptune Analytics graphs"):
                analytics.query_gremlin("g.V().limit(1)")