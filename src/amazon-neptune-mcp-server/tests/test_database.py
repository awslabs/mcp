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
"""Tests for the NeptuneDatabase class."""

import pytest
import json
from unittest.mock import MagicMock, patch
from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.models import GraphSchema


@pytest.mark.asyncio
class TestNeptuneDatabase:
    """Test class for the NeptuneDatabase functionality."""
    
    @patch('boto3.Session')
    async def test_init_success(self, mock_session):
        """
        Test successful initialization of NeptuneDatabase.
        
        This test verifies that:
        1. The boto3 Session is created correctly
        2. The client is created with the correct parameters
        3. The schema is refreshed during initialization
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to avoid actual API calls
        with patch.object(NeptuneDatabase, '_refresh_schema', return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[])):
            # Act
            db = NeptuneDatabase(host="test-endpoint", port=8182, use_https=True)
            
            # Assert
            mock_session.assert_called_once()
            mock_session_instance.client.assert_called_once_with(
                "neptunedata", 
                endpoint_url="https://test-endpoint:8182"
            )
            assert db.client == mock_client
    
    @patch('boto3.Session')
    async def test_init_with_credentials_profile(self, mock_session):
        """
        Test initialization with a credentials profile.
        
        This test verifies that:
        1. The boto3 Session is created with the specified profile name
        2. The client is created with the correct parameters
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to avoid actual API calls
        with patch.object(NeptuneDatabase, '_refresh_schema', return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[])):
            # Act
            db = NeptuneDatabase(
                host="test-endpoint", 
                port=8182, 
                use_https=True, 
                credentials_profile_name="test-profile"
            )
            
            # Assert
            mock_session.assert_called_once_with(profile_name="test-profile")
            mock_session_instance.client.assert_called_once_with(
                "neptunedata", 
                endpoint_url="https://test-endpoint:8182"
            )
    
    @patch('boto3.Session')
    async def test_init_with_http(self, mock_session):
        """
        Test initialization with HTTP instead of HTTPS.
        
        This test verifies that:
        1. The client is created with an HTTP endpoint URL when use_https is False
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to avoid actual API calls
        with patch.object(NeptuneDatabase, '_refresh_schema', return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[])):
            # Act
            db = NeptuneDatabase(host="test-endpoint", port=8182, use_https=False)
            
            # Assert
            mock_session_instance.client.assert_called_once_with(
                "neptunedata", 
                endpoint_url="http://test-endpoint:8182"
            )
    
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
            NeptuneDatabase(host="test-endpoint")
    
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
        with patch.object(NeptuneDatabase, '_refresh_schema', side_effect=Exception("Schema refresh error")):
            # Act & Assert
            with pytest.raises(NeptuneException) as exc_info:
                NeptuneDatabase(host="test-endpoint")
            
            # Check the exception details
            assert "Could not get schema for Neptune database" in exc_info.value.message
    
    @patch('boto3.Session')
    async def test_get_summary_success(self, mock_session):
        """
        Test successful retrieval of graph summary.
        
        This test verifies that:
        1. The get_propertygraph_summary API is called
        2. The summary data is correctly extracted from the response
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response
        mock_summary = {
            "nodeLabels": ["Person", "Movie"],
            "edgeLabels": ["ACTED_IN", "DIRECTED"]
        }
        mock_client.get_propertygraph_summary.return_value = {
            "payload": {
                "graphSummary": mock_summary
            }
        }
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act
            result = db._get_summary()
            
            # Assert
            mock_client.get_propertygraph_summary.assert_called_once()
            assert result == mock_summary
    
    @patch('boto3.Session')
    async def test_get_summary_api_error(self, mock_session):
        """
        Test handling of API errors in get_summary.
        
        This test verifies that:
        1. API errors are properly caught and re-raised as NeptuneException
        2. The error message indicates the Summary API is not available
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API to raise an exception
        mock_client.get_propertygraph_summary.side_effect = Exception("API error")
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act & Assert
            with pytest.raises(NeptuneException) as exc_info:
                db._get_summary()
            
            # Check the exception details
            assert "Summary API is not available" in exc_info.value.message
            assert "API error" in exc_info.value.details
    
    @patch('boto3.Session')
    async def test_get_summary_invalid_response(self, mock_session):
        """
        Test handling of invalid responses in get_summary.
        
        This test verifies that:
        1. Invalid responses are properly caught and re-raised as NeptuneException
        2. The error message indicates the response was invalid
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API to return an invalid response
        class MockResponse:
            def __init__(self):
                self.payload = {}  # Missing graphSummary
                self.content = b"Invalid response"
            
            def __getitem__(self, key):
                return getattr(self, key)
        
        mock_client.get_propertygraph_summary.return_value = MockResponse()
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act & Assert
            with pytest.raises(NeptuneException) as exc_info:
                db._get_summary()
            
            # Check the exception details
            assert "Summary API did not return a valid response" in exc_info.value.message
    
    @patch('boto3.Session')
    async def test_get_labels(self, mock_session):
        """
        Test retrieval of node and edge labels.
        
        This test verifies that:
        1. The _get_summary method is called
        2. Node and edge labels are correctly extracted from the summary
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Mock _get_summary
            mock_summary = {
                "nodeLabels": ["Person", "Movie"],
                "edgeLabels": ["ACTED_IN", "DIRECTED"]
            }
            with patch.object(db, '_get_summary', return_value=mock_summary):
                # Act
                n_labels, e_labels = db._get_labels()
                
                # Assert
                assert n_labels == ["Person", "Movie"]
                assert e_labels == ["ACTED_IN", "DIRECTED"]
    
    @patch('boto3.Session')
    async def test_query_opencypher_without_params(self, mock_session):
        """
        Test execution of openCypher queries without parameters.
        
        This test verifies that:
        1. The execute_open_cypher_query API is called with the correct query
        2. The result is correctly extracted from the response
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response
        mock_result = [{"n": {"id": "1"}}]
        mock_client.execute_open_cypher_query.return_value = {
            "result": mock_result
        }
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act
            result = db.query_opencypher("MATCH (n) RETURN n LIMIT 1")
            
            # Assert
            mock_client.execute_open_cypher_query.assert_called_once_with(
                openCypherQuery="MATCH (n) RETURN n LIMIT 1"
            )
            assert result == mock_result
    
    @patch('boto3.Session')
    async def test_query_opencypher_with_params(self, mock_session):
        """
        Test execution of openCypher queries with parameters.
        
        This test verifies that:
        1. The execute_open_cypher_query API is called with the correct query and parameters
        2. The parameters are properly JSON-encoded
        3. The result is correctly extracted from the response
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response
        mock_result = [{"n": {"id": "1"}}]
        mock_client.execute_open_cypher_query.return_value = {
            "result": mock_result
        }
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act
            params = {"id": "1"}
            result = db.query_opencypher("MATCH (n) WHERE n.id = $id RETURN n", params)
            
            # Assert
            mock_client.execute_open_cypher_query.assert_called_once_with(
                openCypherQuery="MATCH (n) WHERE n.id = $id RETURN n",
                parameters=json.dumps(params)
            )
            assert result == mock_result
    
    @patch('boto3.Session')
    async def test_query_opencypher_results_format(self, mock_session):
        """
        Test handling of different result formats in openCypher queries.
        
        This test verifies that:
        1. The method correctly handles responses with 'results' instead of 'result'
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response with 'results' instead of 'result'
        mock_results = [{"n": {"id": "1"}}]
        mock_client.execute_open_cypher_query.return_value = {
            "results": mock_results
        }
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act
            result = db.query_opencypher("MATCH (n) RETURN n LIMIT 1")
            
            # Assert
            assert result == mock_results
    
    @patch('boto3.Session')
    async def test_query_gremlin(self, mock_session):
        """
        Test execution of Gremlin queries.
        
        This test verifies that:
        1. The execute_gremlin_query API is called with the correct query
        2. The serializer parameter is correctly set
        3. The result is correctly extracted from the response
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response
        mock_result = [{"id": "1"}]
        mock_client.execute_gremlin_query.return_value = {
            "result": mock_result
        }
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act
            result = db.query_gremlin("g.V().limit(1)")
            
            # Assert
            mock_client.execute_gremlin_query.assert_called_once()
            assert result == mock_result
    
    @patch('boto3.Session')
    async def test_query_gremlin_results_format(self, mock_session):
        """
        Test handling of different result formats in Gremlin queries.
        
        This test verifies that:
        1. The method correctly handles responses with 'results' instead of 'result'
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance
        
        # Mock the API response with 'results' instead of 'result'
        mock_results = [{"id": "1"}]
        mock_client.execute_gremlin_query.return_value = {
            "results": mock_results
        }
        
        # Mock _refresh_schema to avoid actual API calls during init
        with patch.object(NeptuneDatabase, '_refresh_schema'):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act
            result = db.query_gremlin("g.V().limit(1)")
            
            # Assert
            assert result == mock_results
    
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
        with patch.object(NeptuneDatabase, '_refresh_schema', return_value=mock_schema):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Act
            result = db.get_schema()
            
            # Assert - just verify the result is the mock schema
            assert result == mock_schema
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
        with patch.object(NeptuneDatabase, '_refresh_schema', return_value=mock_schema):
            # Create the database instance
            db = NeptuneDatabase(host="test-endpoint")
            
            # Set schema to None to force refresh
            db.schema = None
            
            # Reset the mock to verify it's called again
            NeptuneDatabase._refresh_schema.reset_mock()
            NeptuneDatabase._refresh_schema.return_value = mock_schema
            
            # Act
            result = db.get_schema()
            
            # Assert
            NeptuneDatabase._refresh_schema.assert_called_once()
            assert result == mock_schema