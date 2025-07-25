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
"""Tests for the NeptuneDatabase class."""

import json
import pytest
import requests
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase
from awslabs.amazon_neptune_mcp_server.models import (
    GraphSchema,
    Node,
    Property,
    RDFGraphSchema,
    Relationship,
    RelationshipPattern,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
class TestNeptuneDatabase:
    """Test class for the NeptuneDatabase functionality."""

    @patch('boto3.Session')
    async def test_init_success(self, mock_session):
        """Test successful initialization of NeptuneDatabase.
        This test verifies that:
        1. The boto3 Session is created correctly
        2. The client is created with the correct parameters
        3. The schema is refreshed during initialization.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock API responses
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': {'nodeLabels': [], 'edgeLabels': []}}
        }
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
        }

        # Mock _refresh_lpg_schema to avoid actual API calls
        with (
            patch.object(
                NeptuneDatabase,
                '_refresh_lpg_schema',
                return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[]),
            ),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Act
            db = NeptuneDatabase(host='test-endpoint', port=8182, use_https=True)

            # Assert
            mock_session.assert_called_once()
            mock_session_instance.client.assert_called_once_with(
                'neptunedata', endpoint_url='https://test-endpoint:8182'
            )
            assert db.client == mock_client

    @patch('boto3.Session')
    async def test_init_with_credentials_profile(self, mock_session):
        """Test initialization with a credentials profile.
        This test verifies that:
        1. The boto3 Session is created with the specified profile name
        2. The client is created with the correct parameters.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock API responses
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': {'nodeLabels': [], 'edgeLabels': []}}
        }
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
        }

        # Mock _refresh_lpg_schema to avoid actual API calls
        with (
            patch.object(
                NeptuneDatabase,
                '_refresh_lpg_schema',
                return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[]),
            ),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Act
            NeptuneDatabase(
                host='test-endpoint',
                port=8182,
                use_https=True,
                credentials_profile_name='test-profile',
            )

            # Assert
            mock_session.assert_called_once_with(profile_name='test-profile')
            mock_session_instance.client.assert_called_once_with(
                'neptunedata', endpoint_url='https://test-endpoint:8182'
            )

    @patch('boto3.Session')
    async def test_init_with_http(self, mock_session):
        """Test initialization with HTTP instead of HTTPS.
        This test verifies that:
        1. The client is created with an HTTP endpoint URL when use_https is False.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock API responses
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': {'nodeLabels': [], 'edgeLabels': []}}
        }
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
        }

        # Mock _refresh_lpg_schema to avoid actual API calls
        with (
            patch.object(
                NeptuneDatabase,
                '_refresh_lpg_schema',
                return_value=GraphSchema(nodes=[], relationships=[], relationship_patterns=[]),
            ),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Act
            NeptuneDatabase(host='test-endpoint', port=8182, use_https=False)

            # Assert
            mock_session_instance.client.assert_called_once_with(
                'neptunedata', endpoint_url='http://test-endpoint:8182'
            )

    @patch('boto3.Session')
    async def test_init_session_error(self, mock_session):
        """Test handling of session creation errors.
        This test verifies that:
        1. Errors during session creation are properly caught and re-raised
        2. The error message is appropriate.
        """
        # Arrange
        mock_session.side_effect = Exception('Auth error')

        # Act & Assert
        with pytest.raises(
            ValueError, match='Could not load credentials to authenticate with AWS client'
        ):
            NeptuneDatabase(host='test-endpoint')

    @patch('boto3.Session')
    async def test_get_summary_success(self, mock_session):
        """Test successful retrieval of graph summary.
        This test verifies that:
        1. The get_propertygraph_summary API is called
        2. The summary data is correctly extracted from the response.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API response
        mock_summary = {'nodeLabels': ['Person', 'Movie'], 'edgeLabels': ['ACTED_IN', 'DIRECTED']}
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': mock_summary}
        }

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            result = db._get_summary()

            # Assert
            mock_client.get_propertygraph_summary.assert_called_once()
            assert result == mock_summary

    @patch('boto3.Session')
    async def test_get_summary_api_error(self, mock_session):
        """Test handling of API errors in get_summary.
        This test verifies that:
        1. API errors are properly caught and re-raised as NeptuneException
        2. The error message indicates the Summary API is not available.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API to raise an exception
        mock_client.get_propertygraph_summary.side_effect = Exception('API error')

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act & Assert
            with pytest.raises(NeptuneException) as exc_info:
                db._get_summary()

            # Check the exception details
            assert 'Summary API is not available' in exc_info.value.message
            assert 'API error' in exc_info.value.details

    @patch('boto3.Session')
    async def test_get_summary_invalid_response(self, mock_session):
        """Test handling of invalid responses in get_summary.
        This test verifies that:
        1. Invalid responses are properly caught and re-raised as NeptuneException
        2. The error message indicates the response was invalid.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API to return an invalid response
        class MockResponse:
            def __init__(self):
                self.payload = {}  # Missing graphSummary
                self.content = b'Invalid response'

            def __getitem__(self, key):
                return getattr(self, key)

        mock_client.get_propertygraph_summary.return_value = MockResponse()

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act & Assert
            with pytest.raises(NeptuneException) as exc_info:
                db._get_summary()

            # Check the exception details
            assert 'Summary API did not return a valid response' in exc_info.value.message

    @patch('boto3.Session')
    async def test_get_labels(self, mock_session):
        """Test retrieval of node and edge labels.
        This test verifies that:
        1. The _get_summary method is called
        2. Node and edge labels are correctly extracted from the summary.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock _get_summary
            mock_summary = {
                'nodeLabels': ['Person', 'Movie'],
                'edgeLabels': ['ACTED_IN', 'DIRECTED'],
            }
            with patch.object(db, '_get_summary', return_value=mock_summary):
                # Act
                n_labels, e_labels = db._get_labels()

                # Assert
                assert n_labels == ['Person', 'Movie']
                assert e_labels == ['ACTED_IN', 'DIRECTED']

    @patch('boto3.Session')
    async def test_query_opencypher_without_params(self, mock_session):
        """Test execution of openCypher queries without parameters.
        This test verifies that:
        1. The execute_open_cypher_query API is called with the correct query
        2. The result is correctly extracted from the response.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API response
        mock_result = [{'n': {'id': '1'}}]
        mock_client.execute_open_cypher_query.return_value = {'result': mock_result}

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            result = db.query_opencypher('MATCH (n) RETURN n LIMIT 1')

            # Assert
            mock_client.execute_open_cypher_query.assert_called_once_with(
                openCypherQuery='MATCH (n) RETURN n LIMIT 1'
            )
            assert result == mock_result

    @patch('boto3.Session')
    async def test_query_opencypher_with_params(self, mock_session):
        """Test execution of openCypher queries with parameters.
        This test verifies that:
        1. The execute_open_cypher_query API is called with the correct query and parameters
        2. The parameters are properly JSON-encoded
        3. The result is correctly extracted from the response.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API response
        mock_result = [{'n': {'id': '1'}}]
        mock_client.execute_open_cypher_query.return_value = {'result': mock_result}

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            params = {'id': '1'}
            result = db.query_opencypher('MATCH (n) WHERE n.id = $id RETURN n', params)

            # Assert
            mock_client.execute_open_cypher_query.assert_called_once_with(
                openCypherQuery='MATCH (n) WHERE n.id = $id RETURN n',
                parameters=json.dumps(params),
            )
            assert result == mock_result

    @patch('boto3.Session')
    async def test_query_opencypher_results_format(self, mock_session):
        """Test handling of different result formats in openCypher queries.
        This test verifies that:
        1. The method correctly handles responses with 'results' instead of 'result'.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API response with 'results' instead of 'result'
        mock_results = [{'n': {'id': '1'}}]
        mock_client.execute_open_cypher_query.return_value = {'results': mock_results}

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            result = db.query_opencypher('MATCH (n) RETURN n LIMIT 1')

            # Assert
            assert result == mock_results

    @patch('boto3.Session')
    async def test_query_gremlin(self, mock_session):
        """Test execution of Gremlin queries.
        This test verifies that:
        1. The execute_gremlin_query API is called with the correct query
        2. The serializer parameter is correctly set
        3. The result is correctly extracted from the response.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API response
        mock_result = [{'id': '1'}]
        mock_client.execute_gremlin_query.return_value = {'result': mock_result}

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            result = db.query_gremlin('g.V().limit(1)')

            # Assert
            mock_client.execute_gremlin_query.assert_called_once()
            assert result == mock_result

    @patch('boto3.Session')
    async def test_query_gremlin_results_format(self, mock_session):
        """Test handling of different result formats in Gremlin queries.
        This test verifies that:
        1. The method correctly handles responses with 'results' instead of 'result'.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API response with 'results' instead of 'result'
        mock_results = [{'id': '1'}]
        mock_client.execute_gremlin_query.return_value = {'results': mock_results}

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            result = db.query_gremlin('g.V().limit(1)')

            # Assert
            assert result == mock_results

    @patch('boto3.Session')
    async def test_get_schema_cached(self, mock_session):
        """Test that get_schema returns cached schema when available.
        This test verifies that:
        1. When schema is already cached, _refresh_lpg_schema is not called
        2. The cached schema is returned.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Create a mock schema
        mock_schema = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema', return_value=mock_schema),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            result = db.get_lpg_schema()

            # Assert - just verify the result is the mock schema
            assert result == mock_schema
            assert result == mock_schema

    @patch('boto3.Session')
    async def test_get_schema_refresh(self, mock_session):
        """Test that get_schema refreshes schema when not cached.
        This test verifies that:
        1. When schema is not cached, _refresh_lpg_schema is called
        2. The refreshed schema is returned.
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'  # Add region_name attribute
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Create a mock schema
        mock_schema = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema', return_value=mock_schema),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Set schema to None to force refresh
            db.schema = None

            # Reset the mock to verify it's called again
            NeptuneDatabase._refresh_lpg_schema.reset_mock()
            NeptuneDatabase._refresh_lpg_schema.return_value = mock_schema

            # Act
            result = db.get_lpg_schema()

            # Assert
            NeptuneDatabase._refresh_lpg_schema.assert_called_once()
            assert result == mock_schema

    @patch('boto3.Session')
    async def test_get_triples(self, mock_session):
        """Test retrieval of relationship patterns (triples).

        This test verifies that:
        1. The query_opencypher method is called for each edge label
        2. The relationship patterns are correctly created from the query results
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return test data
            db.query_opencypher = MagicMock()
            db.query_opencypher.side_effect = [
                [
                    {'from': ['Person'], 'edge': 'KNOWS', 'to': ['Person']},
                    {'from': ['Person'], 'edge': 'KNOWS', 'to': ['Person']},
                ],
                [
                    {'from': ['Person'], 'edge': 'ACTED_IN', 'to': ['Movie']},
                    {'from': ['Director'], 'edge': 'ACTED_IN', 'to': ['Movie']},
                ],
            ]

            # Act
            result = db._get_triples(['KNOWS', 'ACTED_IN'])

            # Assert
            assert len(result) == 4
            assert db.query_opencypher.call_count == 2

            # Check the first relationship pattern
            assert result[0].left_node == 'Person'
            assert result[0].relation == 'KNOWS'
            assert result[0].right_node == 'Person'

            # Check the third relationship pattern
            assert result[2].left_node == 'Person'
            assert result[2].relation == 'ACTED_IN'
            assert result[2].right_node == 'Movie'

    @patch('boto3.Session')
    async def test_get_node_properties(self, mock_session):
        """Test retrieval of node properties.

        This test verifies that:
        1. The query_opencypher method is called for each node label
        2. The node properties are correctly extracted from the query results
        3. The property types are correctly mapped
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return test data
            db.query_opencypher = MagicMock()
            db.query_opencypher.side_effect = [
                [
                    {'props': {'name': 'John', 'age': 30, 'active': True}},
                    {'props': {'name': 'Jane', 'age': 25, 'score': 4.5}},
                ],
                [
                    {'props': {'title': 'The Matrix', 'year': 1999}},
                    {'props': {'title': 'Inception', 'year': 2010}},
                ],
            ]

            # Define type mapping
            types = {'str': 'STRING', 'int': 'INTEGER', 'float': 'DOUBLE', 'bool': 'BOOLEAN'}

            # Act
            result = db._get_node_properties(['Person', 'Movie'], types)

            # Assert
            assert len(result) == 2
            assert db.query_opencypher.call_count == 2

            # Check the Person node
            person_node = result[0]
            assert person_node.labels == 'Person'
            assert len(person_node.properties) == 4

            # Check property types
            prop_types = {p.name: p.type for p in person_node.properties}
            assert 'STRING' in prop_types['name']
            assert 'INTEGER' in prop_types['age']
            assert 'BOOLEAN' in prop_types['active']
            assert 'DOUBLE' in prop_types['score']

            # Check the Movie node
            movie_node = result[1]
            assert movie_node.labels == 'Movie'
            assert len(movie_node.properties) == 2

            # Check property types
            prop_types = {p.name: p.type for p in movie_node.properties}
            assert 'STRING' in prop_types['title']
            assert 'INTEGER' in prop_types['year']

    @patch('boto3.Session')
    async def test_get_edge_properties(self, mock_session):
        """Test retrieval of edge properties.

        This test verifies that:
        1. The query_opencypher method is called for each edge label
        2. The edge properties are correctly extracted from the query results
        3. The property types are correctly mapped
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return test data
            db.query_opencypher = MagicMock()
            db.query_opencypher.side_effect = [
                [
                    {'props': {'since': '2020-01-01', 'strength': 0.8}},
                    {'props': {'since': '2019-05-15', 'strength': 0.6}},
                ],
                [
                    {'props': {'role': 'Neo', 'screenTime': 120}},
                    {'props': {'role': 'Trinity', 'screenTime': 90}},
                ],
            ]

            # Define type mapping
            types = {'str': 'STRING', 'int': 'INTEGER', 'float': 'DOUBLE'}

            # Act
            result = db._get_edge_properties(['KNOWS', 'ACTED_IN'], types)

            # Assert
            assert len(result) == 2
            assert db.query_opencypher.call_count == 2

            # Check the KNOWS relationship
            knows_rel = result[0]
            assert knows_rel.type == 'KNOWS'
            assert len(knows_rel.properties) == 2

            # Check property types
            prop_types = {p.name: p.type for p in knows_rel.properties}
            assert 'STRING' in prop_types['since']
            assert 'DOUBLE' in prop_types['strength']

            # Check the ACTED_IN relationship
            acted_in_rel = result[1]
            assert acted_in_rel.type == 'ACTED_IN'
            assert len(acted_in_rel.properties) == 2

            # Check property types
            prop_types = {p.name: p.type for p in acted_in_rel.properties}
            assert 'STRING' in prop_types['role']
            assert 'INTEGER' in prop_types['screenTime']

    @patch('boto3.Session')
    async def test_propertygraph_schema(self, mock_session):
        """Test that propertygraph_schema calls get_lpg_schema.

        This test verifies that:
        1. The propertygraph_schema method calls get_lpg_schema
        2. The result from get_lpg_schema is returned unchanged
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Create a mock schema
            mock_schema = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

            # Mock get_lpg_schema
            db.get_lpg_schema = MagicMock(return_value=mock_schema)

            # Act
            result = db.propertygraph_schema()

            # Assert
            db.get_lpg_schema.assert_called_once()
            assert result == mock_schema

    @patch('boto3.Session')
    async def test_query_sparql(self, mock_session):
        """Test execution of SPARQL queries.

        This test verifies that:
        1. The _query_sparql method is called with the correct query
        2. The result is returned unchanged
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock _query_sparql
            mock_result = {
                'results': {'bindings': [{'s': {'value': 'http://example.org/subject'}}]}
            }
            db._query_sparql = MagicMock(return_value=mock_result)

            # Act
            query = 'SELECT * WHERE { ?s ?p ?o } LIMIT 1'
            result = db.query_sparql(query)

            # Assert
            db._query_sparql.assert_called_once_with(query)
            assert result == mock_result

    @patch('boto3.Session')
    async def test_get_local_name_with_hash(self, mock_session):
        """Test extraction of local name from IRI with hash.

        This test verifies that:
        1. The _get_local_name method correctly splits IRIs with hash
        2. The prefix and local name are correctly returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            iri = 'http://example.org/ontology#Person'
            prefix, local = db._get_local_name(iri)

            # Assert
            assert prefix == 'http://example.org/ontology#'
            assert local == 'Person'

    @patch('boto3.Session')
    async def test_get_local_name_with_slash(self, mock_session):
        """Test extraction of local name from IRI with slash.

        This test verifies that:
        1. The _get_local_name method correctly splits IRIs with slash
        2. The prefix and local name are correctly returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            iri = 'http://example.org/ontology/Person'
            prefix, local = db._get_local_name(iri)

            # Assert
            assert prefix == 'http://example.org/ontology/'
            assert local == 'Person'

    @patch('boto3.Session')
    async def test_get_local_name_invalid(self, mock_session):
        """Test extraction of local name from invalid IRI.

        This test verifies that:
        1. The _get_local_name method raises ValueError for IRIs without hash or slash
        2. The error message correctly indicates the issue
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act & Assert
            with pytest.raises(
                ValueError, match="Unexpected IRI 'invalid-iri', contains neither '#' nor '/'"
            ):
                db._get_local_name('invalid-iri')

    @patch('boto3.Session')
    async def test_get_rdf_schema_cached(self, mock_session):
        """Test that get_rdf_schema returns cached schema when available.

        This test verifies that:
        1. When rdf_schema is already cached, it is returned without making API calls
        2. The cached schema is returned unchanged
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Create a mock RDF schema
            mock_rdf_schema = RDFGraphSchema(distinct_prefixes={})

            # Set the cached schema
            db.rdf_schema = mock_rdf_schema

            # Reset the mocks to verify they're not called
            mock_client.get_rdf_graph_summary.reset_mock()

            # Act
            result = db.get_rdf_schema()

            # Assert
            assert result == mock_rdf_schema
            mock_client.get_rdf_graph_summary.assert_not_called()

    @patch('boto3.Session')
    @patch('requests.request')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.AWSRequest')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.SigV4Auth')
    async def test_query_sparql_construct(
        self, mock_sigv4auth, mock_aws_request, mock_request, mock_session
    ):
        """Test execution of SPARQL CONSTRUCT queries.

        This test verifies that:
        1. The correct headers and data are set for CONSTRUCT queries
        2. SigV4Auth is used to sign the request
        3. The request is made with the correct parameters
        4. The response is correctly parsed and returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_session_instance.get_credentials.return_value = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the request response
        mock_response = MagicMock()
        mock_response.text = (
            '{"results": {"bindings": [{"s": {"value": "http://example.org/subject"}}]}}'
        )
        mock_request.return_value = mock_response

        # Mock AWS request
        mock_aws_request_instance = MagicMock()
        mock_aws_request_instance.headers = {'Authorization': 'AWS4-HMAC-SHA256...'}
        mock_aws_request.return_value = mock_aws_request_instance

        # Mock SPARQLWrapper to identify query type
        with patch(
            'awslabs.amazon_neptune_mcp_server.graph_store.database.SPARQLWrapper'
        ) as mock_sparql_wrapper:
            mock_wrapper_instance = MagicMock()
            mock_wrapper_instance.queryType = 'CONSTRUCT'
            mock_sparql_wrapper.return_value = mock_wrapper_instance

            # Mock _refresh_lpg_schema to avoid actual API calls during init
            with (
                patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
                patch.object(
                    NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
                ),
            ):
                # Create the database instance
                db = NeptuneDatabase(host='test-endpoint')
                db.endpoint_url = 'https://test-endpoint:8182'
                db.session = mock_session_instance

                # Reset the mock to test the actual method
                NeptuneDatabase._query_sparql = NeptuneDatabase._query_sparql

                # Act
                query = 'CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 1'
                db._query_sparql(query)

    @patch('boto3.Session')
    @patch('requests.request')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.AWSRequest')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.SigV4Auth')
    async def test_query_sparql_select(
        self, mock_sigv4auth, mock_aws_request, mock_request, mock_session
    ):
        """Test execution of SPARQL SELECT queries.

        This test verifies that:
        1. The correct headers and data are set for SELECT queries
        2. SigV4Auth is used to sign the request
        3. The request is made with the correct parameters
        4. The response is correctly parsed and returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_session_instance.get_credentials.return_value = MagicMock()
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the request response
        mock_response = MagicMock()
        mock_response.text = (
            '{"results": {"bindings": [{"s": {"value": "http://example.org/subject"}}]}}'
        )
        mock_request.return_value = mock_response

        # Mock AWS request
        mock_aws_request_instance = MagicMock()
        mock_aws_request_instance.headers = {'Authorization': 'AWS4-HMAC-SHA256...'}
        mock_aws_request.return_value = mock_aws_request_instance

        # Mock SPARQLWrapper to identify query type
        with patch(
            'awslabs.amazon_neptune_mcp_server.graph_store.database.SPARQLWrapper'
        ) as mock_sparql_wrapper:
            mock_wrapper_instance = MagicMock()
            mock_wrapper_instance.queryType = 'SELECT'
            mock_sparql_wrapper.return_value = mock_wrapper_instance

            # Mock _refresh_lpg_schema to avoid actual API calls during init
            with (
                patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
                patch.object(
                    NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
                ),
            ):
                # Create the database instance
                db = NeptuneDatabase(host='test-endpoint')
                db.endpoint_url = 'https://test-endpoint:8182'
                db.session = mock_session_instance

                # Reset the mock to test the actual method
                NeptuneDatabase._query_sparql = NeptuneDatabase._query_sparql

                # Act
                query = 'SELECT * WHERE { ?s ?p ?o } LIMIT 1'
                db._query_sparql(query)

    @patch('boto3.Session')
    @patch('requests.request')
    async def test_query_sparql_request_error(self, mock_request, mock_session):
        """Test handling of request errors in _query_sparql.

        This test verifies that:
        1. When the request raises an exception, the exception is propagated
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the request to raise an exception
        mock_request.side_effect = requests.RequestException('Connection error')

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
            patch('awslabs.amazon_neptune_mcp_server.graph_store.database.AWSRequest'),
            patch('awslabs.amazon_neptune_mcp_server.graph_store.database.SigV4Auth'),
            patch(
                'awslabs.amazon_neptune_mcp_server.graph_store.database.SPARQLWrapper'
            ) as mock_sparql_wrapper,
        ):
            mock_wrapper_instance = MagicMock()
            mock_wrapper_instance.queryType = 'SELECT'
            mock_sparql_wrapper.return_value = mock_wrapper_instance

            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')
            db.endpoint_url = 'https://test-endpoint:8182'
            db.session = mock_session_instance

            # Reset the mock to test the actual method
            NeptuneDatabase._query_sparql = NeptuneDatabase._query_sparql

    @patch('boto3.Session')
    async def test_query_opencypher_error(self, mock_session):
        """Test handling of errors in query_opencypher.

        This test verifies that:
        1. When the API call fails, the error is properly logged
        2. The error is propagated to the caller
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API to raise an exception
        mock_client.execute_open_cypher_query.side_effect = Exception('Query error')

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
            patch('awslabs.amazon_neptune_mcp_server.graph_store.database.logger') as mock_logger,
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act & Assert
            with pytest.raises(Exception, match='Query error'):
                db.query_opencypher('MATCH (n) RETURN n')

            # Verify logging
            mock_logger.debug.assert_any_call(
                'Querying Neptune with OpenCypher: MATCH (n) RETURN n'
            )

    @patch('boto3.Session')
    async def test_query_gremlin_error(self, mock_session):
        """Test handling of errors in query_gremlin.

        This test verifies that:
        1. When the API call fails, the error is properly logged
        2. The error is propagated to the caller
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the API to raise an exception
        mock_client.execute_gremlin_query.side_effect = Exception('Query error')

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
            patch('awslabs.amazon_neptune_mcp_server.graph_store.database.logger') as mock_logger,
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act & Assert
            with pytest.raises(Exception, match='Query error'):
                db.query_gremlin('g.V().limit(1)')

            # Verify logging
            mock_logger.debug.assert_any_call('Querying Neptune with Gremlin: g.V().limit(1)')

    @patch('boto3.Session')
    async def test_get_local_name_with_multiple_slashes(self, mock_session):
        """Test extraction of local name from IRI with multiple slashes.

        This test verifies that:
        1. The _get_local_name method correctly handles IRIs with multiple slashes
        2. The prefix includes all parts before the last slash
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            iri = 'http://example.org/ontology/with/multiple/slashes'
            prefix, local = db._get_local_name(iri)

            # Assert
            assert prefix == 'http://example.org/ontology/with/multiple/'
            assert local == 'slashes'

    @patch('boto3.Session')
    async def test_get_local_name_with_empty_local(self, mock_session):
        """Test extraction of local name from IRI with empty local part.

        This test verifies that:
        1. The _get_local_name method correctly handles IRIs with empty local part
        2. The local part is an empty string
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            iri = 'http://example.org/'
            prefix, local = db._get_local_name(iri)

            # Assert
            assert prefix == 'http://example.org/'
            assert local == ''

    @patch('boto3.Session')
    async def test_init_refresh_schema_error(self, mock_session):
        """Test handling of schema refresh errors during initialization.

        This test verifies that:
        1. Errors during schema refresh are properly caught and re-raised
        2. The error message is appropriate
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

    @patch('boto3.Session')
    async def test_get_lpg_schema_empty_schema(self, mock_session):
        """Test that get_lpg_schema returns empty schema when schema is None.

        This test verifies that:
        1. When schema is None and _refresh_lpg_schema returns None, an empty schema is returned
        2. The empty schema has the expected structure
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to return None
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema', return_value=None),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Set schema to None to force refresh
            db.schema = None

            # Reset the mock to verify it's called again
            NeptuneDatabase._refresh_lpg_schema.reset_mock()

            # Act
            result = db.get_lpg_schema()

            # Assert
            NeptuneDatabase._refresh_lpg_schema.assert_called_once()
            assert isinstance(result, GraphSchema)
            assert result.nodes == []
            assert result.relationships == []
            assert result.relationship_patterns == []

    @patch('boto3.Session')
    async def test_get_labels_empty_summary(self, mock_session):
        """Test retrieval of node and edge labels with empty summary.

        This test verifies that:
        1. When the summary has no labels, empty lists are returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock _get_summary to return empty summary
            empty_summary = {'nodeLabels': [], 'edgeLabels': []}
            with patch.object(db, '_get_summary', return_value=empty_summary):
                # Act
                n_labels, e_labels = db._get_labels()

                # Assert
                assert n_labels == []
                assert e_labels == []
                db._get_summary.assert_called_once()

    @patch('boto3.Session')
    async def test_get_triples_empty_result(self, mock_session):
        """Test retrieval of relationship patterns with empty query results.

        This test verifies that:
        1. When the query returns no results, an empty list is returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return empty results
            db.query_opencypher = MagicMock(return_value=[])

            # Act
            result = db._get_triples(['KNOWS'])

            # Assert
            assert result == []
            db.query_opencypher.assert_called_once()

    @patch('boto3.Session')
    async def test_get_node_properties_empty_result(self, mock_session):
        """Test retrieval of node properties with empty query results.

        This test verifies that:
        1. When the query returns no results, nodes with empty properties are returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return empty results
            db.query_opencypher = MagicMock(return_value=[])

            # Define type mapping
            types = {'str': 'STRING', 'int': 'INTEGER'}

            # Act
            result = db._get_node_properties(['Person'], types)

            # Assert
            assert len(result) == 1
            assert result[0].labels == 'Person'
            assert result[0].properties == []
            db.query_opencypher.assert_called_once()

    @patch('boto3.Session')
    async def test_get_edge_properties_empty_result(self, mock_session):
        """Test retrieval of edge properties with empty query results.

        This test verifies that:
        1. When the query returns no results, edges with empty properties are returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return empty results
            db.query_opencypher = MagicMock(return_value=[])

            # Define type mapping
            types = {'str': 'STRING', 'int': 'INTEGER'}

            # Act
            result = db._get_edge_properties(['KNOWS'], types)

            # Assert
            assert len(result) == 1
            assert result[0].type == 'KNOWS'
            assert result[0].properties == []
            db.query_opencypher.assert_called_once()

    @patch('boto3.Session')
    async def test_refresh_lpg_schema(self, mock_session):
        """Test the _refresh_lpg_schema method.

        This test verifies that:
        1. The _get_labels method is called to get node and edge labels
        2. The _get_triples method is called with the edge labels
        3. The _get_node_properties method is called with the node labels
        4. The _get_edge_properties method is called with the edge labels
        5. A GraphSchema is created with the correct components
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Create the database instance with mocked methods
        with patch.object(
            NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
        ):
            db = NeptuneDatabase(host='test-endpoint')

            # Mock the methods called by _refresh_lpg_schema
            n_labels = ['Person', 'Movie']
            e_labels = ['ACTED_IN', 'DIRECTED']

            triple_schema = [
                RelationshipPattern(left_node='Person', right_node='Movie', relation='ACTED_IN'),
                RelationshipPattern(left_node='Person', right_node='Movie', relation='DIRECTED'),
            ]

            nodes = [
                Node(
                    labels='Person',
                    properties=[
                        Property(name='name', type=['STRING']),
                        Property(name='age', type=['INTEGER']),
                    ],
                ),
                Node(
                    labels='Movie',
                    properties=[
                        Property(name='title', type=['STRING']),
                        Property(name='year', type=['INTEGER']),
                    ],
                ),
            ]

            edges = [
                Relationship(type='ACTED_IN', properties=[Property(name='role', type=['STRING'])]),
                Relationship(type='DIRECTED', properties=[]),
            ]

            # Mock the methods that _refresh_lpg_schema calls
            db._get_labels = MagicMock(return_value=(n_labels, e_labels))
            db._get_triples = MagicMock(return_value=triple_schema)
            db._get_node_properties = MagicMock(return_value=nodes)
            db._get_edge_properties = MagicMock(return_value=edges)

            # Act
            result = db._refresh_lpg_schema()

            # Assert
            db._get_labels.assert_called_once()
            db._get_triples.assert_called_once_with(e_labels)
            db._get_node_properties.assert_called_once()
            db._get_edge_properties.assert_called_once()

            assert result.nodes == nodes
            assert result.relationships == edges
            assert result.relationship_patterns == triple_schema
            assert db.schema == result

    @patch('boto3.Session')
    async def test_get_local_name_with_multiple_hashes(self, mock_session):
        """Test extraction of local name from IRI with multiple hashes.

        This test verifies that:
        1. The _get_local_name method correctly handles IRIs with multiple hashes
        2. The prefix includes everything up to the first hash
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            iri = 'http://example.org/ontology#Person#Detail'
            prefix, local = db._get_local_name(iri)

            # Assert
            assert prefix == 'http://example.org/ontology#'
            assert local == 'Person'  # The method splits on the first hash

    @patch('boto3.Session')
    async def test_get_local_name_with_hash_and_slash(self, mock_session):
        """Test extraction of local name from IRI with both hash and slash.

        This test verifies that:
        1. The _get_local_name method prioritizes hash over slash when both are present
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Act
            iri = 'http://example.org/ontology/path#Person'
            prefix, local = db._get_local_name(iri)

            # Assert
            assert prefix == 'http://example.org/ontology/path#'
            assert local == 'Person'

    @patch('boto3.Session')
    async def test_get_rdf_schema_empty(self, mock_session):
        """Test that get_rdf_schema returns an empty schema when not cached.

        This test verifies that:
        1. When rdf_schema is not cached, a new empty schema is returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Ensure rdf_schema is None
            db.rdf_schema = None

            # Act
            result = db.get_rdf_schema()

            # Assert
            assert isinstance(result, RDFGraphSchema)
            assert result.distinct_prefixes == {}
            assert result.classes == []
            assert result.rels == []
            assert result.dtprops == []
            assert result.oprops == []
            assert result.rdfclasses == []
            assert result.predicates == []

    @patch('boto3.Session')
    async def test_get_triples_empty(self, mock_session):
        """Test retrieval of relationship patterns with empty query results.

        This test verifies that:
        1. When the query returns no results, an empty list is returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return empty results
            db.query_opencypher = MagicMock(return_value=[])

            # Act
            result = db._get_triples(['KNOWS'])

            # Assert
            assert result == []
            db.query_opencypher.assert_called_once()

    @patch('boto3.Session')
    async def test_get_node_properties_empty(self, mock_session):
        """Test retrieval of node properties with empty query results.

        This test verifies that:
        1. When the query returns no results, nodes with empty properties are returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return empty results
            db.query_opencypher = MagicMock(return_value=[])

            # Define type mapping
            types = {'str': 'STRING', 'int': 'INTEGER'}

            # Act
            result = db._get_node_properties(['Person'], types)

            # Assert
            assert len(result) == 1
            assert result[0].labels == 'Person'
            assert result[0].properties == []
            db.query_opencypher.assert_called_once()

    @patch('boto3.Session')
    async def test_get_edge_properties_empty(self, mock_session):
        """Test retrieval of edge properties with empty query results.

        This test verifies that:
        1. When the query returns no results, edges with empty properties are returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return empty results
            db.query_opencypher = MagicMock(return_value=[])

            # Define type mapping
            types = {'str': 'STRING', 'int': 'INTEGER'}

            # Act
            result = db._get_edge_properties(['KNOWS'], types)

            # Assert
            assert len(result) == 1
            assert result[0].type == 'KNOWS'
            assert result[0].properties == []
            db.query_opencypher.assert_called_once()

    @patch('boto3.Session')
    async def test_get_node_properties_with_mixed_types(self, mock_session):
        """Test retrieval of node properties with mixed property types.

        This test verifies that:
        1. When a property has multiple types across different nodes, all types are captured
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return results with mixed types
            db.query_opencypher = MagicMock(
                return_value=[
                    {'props': {'age': 30}},  # Integer
                    {'props': {'age': 25.5}},  # Float
                ]
            )

            # Define type mapping
            types = {'str': 'STRING', 'int': 'INTEGER', 'float': 'DOUBLE'}

            # Act
            result = db._get_node_properties(['Person'], types)

            # Assert
            assert len(result) == 1
            assert result[0].labels == 'Person'
            assert len(result[0].properties) == 1

            # Check that both INTEGER and DOUBLE types are captured for the 'age' property
            age_prop = result[0].properties[0]
            assert age_prop.name == 'age'
            assert set(age_prop.type) == {'INTEGER', 'DOUBLE'}

    @patch('boto3.Session')
    async def test_get_edge_properties_with_mixed_types(self, mock_session):
        """Test retrieval of edge properties with mixed property types.

        This test verifies that:
        1. When a property has multiple types across different edges, all types are captured
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock _refresh_lpg_schema to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Mock query_opencypher to return results with mixed types
            db.query_opencypher = MagicMock(
                return_value=[
                    {'props': {'weight': 0.5}},  # Float
                    {'props': {'weight': True}},  # Boolean
                ]
            )

            # Define type mapping
            types = {'float': 'DOUBLE', 'bool': 'BOOLEAN'}

            # Act
            result = db._get_edge_properties(['KNOWS'], types)

            # Assert
            assert len(result) == 1
            assert result[0].type == 'KNOWS'
            assert len(result[0].properties) == 1

            # Check that both DOUBLE and BOOLEAN types are captured for the 'weight' property
            weight_prop = result[0].properties[0]
            assert weight_prop.name == 'weight'
            assert set(weight_prop.type) == {'DOUBLE', 'BOOLEAN'}
