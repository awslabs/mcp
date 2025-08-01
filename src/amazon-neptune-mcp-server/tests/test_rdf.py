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
"""Tests for the RDF functionality in the Neptune database."""

import pytest
from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase
from awslabs.amazon_neptune_mcp_server.models import (
    RDFGraphSchema,
)
from unittest.mock import MagicMock, patch


class TestRDFFunctionality:
    """Test class for the RDF functionality in the NeptuneDatabase class."""

    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.NeptuneDatabase._query_sparql')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.boto3.Session')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.requests.request')
    def test_get_local_name(self, mock_request, mock_session, mock_query_sparql):
        """Test the _get_local_name method for extracting local names from IRIs.

        This test verifies that:
        1. IRIs with '#' are correctly split into prefix and local name
        2. IRIs with '/' are correctly split into prefix and local name
        3. Invalid IRIs raise a ValueError
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client

        # Mock the get_lpg_schema and get_rdf_schema methods to avoid actual API calls
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': {'nodeLabels': [], 'edgeLabels': []}}
        }
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
        }

        # Mock the _query_sparql method to avoid SigV4Auth issues
        mock_query_sparql.return_value = {'results': {'bindings': []}}

        # Create a NeptuneDatabase instance
        db = NeptuneDatabase('test-host')

        # Act & Assert - Test with '#'
        prefix, local = db._get_local_name('http://example.org/ontology#Person')
        assert prefix == 'http://example.org/ontology#'
        assert local == 'Person'

        # Act & Assert - Test with '/'
        prefix, local = db._get_local_name('http://example.org/ontology/Person')
        assert prefix == 'http://example.org/ontology/'
        assert local == 'Person'

        # Act & Assert - Test with invalid IRI
        with pytest.raises(
            ValueError, match="Unexpected IRI 'invalid-iri', contains neither '#' nor '/'"
        ):
            db._get_local_name('invalid-iri')

    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.NeptuneDatabase._query_sparql')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.boto3.Session')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.requests.request')
    def test_query_sparql(self, mock_request, mock_session, mock_query_sparql):
        """Test the query_sparql method for executing SPARQL queries.

        This test verifies that:
        1. The _query_sparql method is called with the correct query
        2. The result from the _query_sparql method is returned unchanged
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client

        # Mock the get_lpg_schema and get_rdf_schema methods to avoid actual API calls
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': {'nodeLabels': [], 'edgeLabels': []}}
        }
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
        }

        # Mock the _query_sparql method to avoid SigV4Auth issues
        mock_query_sparql.return_value = {'results': {'bindings': []}}

        # Create a NeptuneDatabase instance
        db = NeptuneDatabase('test-host')

        # Reset the mock to track new calls
        mock_query_sparql.reset_mock()

        # Act
        query = 'SELECT * WHERE { ?s ?p ?o } LIMIT 10'
        result = db.query_sparql(query)

        # Assert
        mock_query_sparql.assert_called_once_with(query)
        assert result == {'results': {'bindings': []}}

    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.NeptuneDatabase._query_sparql')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.boto3.Session')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.requests.request')
    def test_get_rdf_schema(self, mock_request, mock_session, mock_query_sparql):
        """Test the get_rdf_schema method for retrieving the RDF schema.

        This test verifies that:
        1. The get_rdf_graph_summary API is called to get the RDF schema
        2. The _query_sparql method is called with the correct SPARQL query
        3. The RDF schema is correctly constructed from the API and query results
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client

        # Mock the get_lpg_schema method to avoid actual API calls
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': {'nodeLabels': [], 'edgeLabels': []}}
        }

        # Mock the get_rdf_graph_summary API response
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': ['http://example.org/Person', 'http://example.org/Organization'],
                    'predicates': [
                        {'http://example.org/name': {}},
                        {'http://example.org/worksFor': {}},
                    ],
                }
            }
        }

        # Mock the SPARQL query response
        mock_query_sparql.return_value = {
            'results': {
                'bindings': [
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Ontology'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Example Ontology'},
                    },
                    {
                        's': {'value': 'http://example.org/Person'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Class'},
                    },
                    {
                        's': {'value': 'http://example.org/Person'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Person'},
                    },
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#DatatypeProperty'},
                    },
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#domain'},
                        'o': {'value': 'http://example.org/Person'},
                    },
                    {
                        's': {'value': 'http://example.org/worksFor'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#ObjectProperty'},
                    },
                    {
                        's': {'value': 'http://example.org/worksFor'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#domain'},
                        'o': {'value': 'http://example.org/Person'},
                    },
                    {
                        's': {'value': 'http://example.org/worksFor'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#range'},
                        'o': {'value': 'http://example.org/Organization'},
                    },
                ]
            }
        }

        # Create a NeptuneDatabase instance
        db = NeptuneDatabase('test-host')

        # Reset the rdf_schema to None to force a refresh
        db.rdf_schema = None

        # Reset the mock to track new calls
        mock_query_sparql.reset_mock()

        # Act
        schema = db.get_rdf_schema()

        # Assert
        assert isinstance(schema, RDFGraphSchema)
        assert len(schema.rdfclasses) == 2
        assert 'http://example.org/Person' in schema.rdfclasses
        assert 'http://example.org/Organization' in schema.rdfclasses

        assert len(schema.predicates) == 2
        assert 'http://example.org/name' in schema.predicates
        assert 'http://example.org/worksFor' in schema.predicates

        assert len(schema.ontologies) == 1
        assert schema.ontologies[0].uri == 'http://example.org/ontology'
        assert schema.ontologies[0].label == 'Example Ontology'

        assert len(schema.classes) == 1
        assert schema.classes[0].uri == 'http://example.org/Person'
        assert schema.classes[0].local == 'Person'

        assert len(schema.dtprops) == 1
        assert schema.dtprops[0].uri == 'http://example.org/name'
        assert schema.dtprops[0].domain_uri == 'http://example.org/Person'

        assert len(schema.oprops) == 1
        assert schema.oprops[0].uri == 'http://example.org/worksFor'
        assert schema.oprops[0].domain_uri == 'http://example.org/Person'
        assert schema.oprops[0].range_uri == 'http://example.org/Organization'

        assert len(schema.rels) == 1
        assert schema.rels[0].uri == 'http://example.org/worksFor'
        assert schema.rels[0].local == 'worksFor'

        # Verify that _query_sparql was called
        mock_query_sparql.assert_called_once()

    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.NeptuneDatabase._query_sparql')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.boto3.Session')
    @patch('awslabs.amazon_neptune_mcp_server.graph_store.database.requests.request')
    def test_get_rdf_schema_cached(self, mock_request, mock_session, mock_query_sparql):
        """Test that get_rdf_schema returns the cached schema if available.

        This test verifies that:
        1. When rdf_schema is already set, it is returned without making API calls
        2. The cached schema is returned unchanged
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client

        # Mock the get_lpg_schema and get_rdf_schema methods to avoid actual API calls
        mock_client.get_propertygraph_summary.return_value = {
            'payload': {'graphSummary': {'nodeLabels': [], 'edgeLabels': []}}
        }
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
        }

        # Mock the _query_sparql method to avoid SigV4Auth issues
        mock_query_sparql.return_value = {'results': {'bindings': []}}

        # Create a NeptuneDatabase instance
        db = NeptuneDatabase('test-host')

        # Create a mock schema
        mock_schema = RDFGraphSchema(
            distinct_prefixes={'http://example.org/': 'ex'},
            rdfclasses=['http://example.org/Person'],
            predicates=['http://example.org/name'],
        )

        # Set the cached schema
        db.rdf_schema = mock_schema

        # Reset the mocks to track new calls
        mock_client.get_rdf_graph_summary.reset_mock()
        mock_query_sparql.reset_mock()

        # Act
        schema = db.get_rdf_schema()

        # Assert
        assert schema == mock_schema
        mock_client.get_rdf_graph_summary.assert_not_called()  # Should not be called again
        mock_query_sparql.assert_not_called()  # Should not be called again

    @patch('boto3.Session')
    async def test_get_rdf_schema_processing(self, mock_session):
        """Test processing of RDF schema data.

        This test verifies that:
        1. The get_rdf_graph_summary API is called
        2. The SPARQL query is executed to get ontology, classes, and properties
        3. The schema elements are correctly processed from the query results
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': ['http://example.org/Person', 'http://example.org/Movie'],
                    'predicates': [
                        {'http://example.org/name': {}},
                        {'http://example.org/age': {}},
                    ],
                }
            }
        }

        # Mock SPARQL query response with ontology, class, and property data
        mock_sparql_response = {
            'results': {
                'bindings': [
                    # Ontology
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Ontology'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Example Ontology'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'An example ontology for testing'},
                    },
                    # Class
                    {
                        's': {'value': 'http://example.org/Person'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Class'},
                    },
                    {
                        's': {'value': 'http://example.org/Person'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#subClassOf'},
                        'o': {'value': 'http://example.org/Agent'},
                    },
                    {
                        's': {'value': 'http://example.org/Person'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Person'},
                    },
                    {
                        's': {'value': 'http://example.org/Person'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'A person'},
                    },
                    # Datatype Property
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#DatatypeProperty'},
                    },
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#domain'},
                        'o': {'value': 'http://example.org/Person'},
                    },
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#range'},
                        'o': {'value': 'http://www.w3.org/2001/XMLSchema#string'},
                    },
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'name'},
                    },
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'The name of a person'},
                    },
                    # Object Property
                    {
                        's': {'value': 'http://example.org/knows'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#ObjectProperty'},
                    },
                    {
                        's': {'value': 'http://example.org/knows'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#subPropertyOf'},
                        'o': {'value': 'http://example.org/related'},
                    },
                    {
                        's': {'value': 'http://example.org/knows'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#domain'},
                        'o': {'value': 'http://example.org/Person'},
                    },
                    {
                        's': {'value': 'http://example.org/knows'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#range'},
                        'o': {'value': 'http://example.org/Person'},
                    },
                    {
                        's': {'value': 'http://example.org/knows'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'knows'},
                    },
                    {
                        's': {'value': 'http://example.org/knows'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'A person knows another person'},
                    },
                ]
            }
        }

        # Mock _refresh_lpg_schema and _query_sparql to avoid actual API calls during init
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(
                NeptuneDatabase, '_query_sparql', return_value={'results': {'bindings': []}}
            ),
        ):
            # Create the database instance
            db = NeptuneDatabase(host='test-endpoint')

            # Reset the rdf_schema to None to force refresh
            db.rdf_schema = None

            # Mock _query_sparql to return the test data
            db._query_sparql = MagicMock(return_value=mock_sparql_response)

            # Act
            schema = db.get_rdf_schema()

            # Assert
            mock_client.get_rdf_graph_summary.assert_called()
            db._query_sparql.assert_called_once()

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

            # Check the schema elements
            assert len(schema.rdfclasses) == 2
            assert len(schema.predicates) == 2
            assert len(schema.ontologies) == 1
            assert len(schema.classes) == 1
            assert len(schema.dtprops) == 1
            assert len(schema.oprops) == 1
            assert len(schema.rels) == 1

            # Check ontology details
            ontology = schema.ontologies[0]
            assert ontology.uri == 'http://example.org/ontology'
            assert ontology.label == 'Example Ontology'
            assert ontology.comment == 'An example ontology for testing'

            # Check class details
            cls = schema.classes[0]
            assert cls.uri == 'http://example.org/Person'
            assert cls.local == 'Person'
            assert cls.parent_uri == 'http://example.org/Agent'
            assert cls.label == 'Person'
            assert cls.comment == 'A person'

            # Check datatype property details
            dt_prop = schema.dtprops[0]
            assert dt_prop.uri == 'http://example.org/name'
            assert dt_prop.local == 'name'
            assert dt_prop.domain_uri == 'http://example.org/Person'
            assert dt_prop.range_uri == 'http://www.w3.org/2001/XMLSchema#string'
            assert dt_prop.label == 'name'
            assert dt_prop.comment == 'The name of a person'

            # Check object property details
            obj_prop = schema.oprops[0]
            assert obj_prop.uri == 'http://example.org/knows'
            assert obj_prop.local == 'knows'
            assert obj_prop.parent_uri == 'http://example.org/related'
            assert obj_prop.domain_uri == 'http://example.org/Person'
            assert obj_prop.range_uri == 'http://example.org/Person'
            assert obj_prop.label == 'knows'
            assert obj_prop.comment == 'A person knows another person'

            # Check relationship details
            rel = schema.rels[0]
            assert rel.uri == 'http://example.org/knows'
            assert rel.local == 'knows'

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_ontology(self, mock_session):
        """Test retrieval of RDF schema with ontology information.

        This test verifies that:
        1. The get_rdf_schema method correctly processes ontology information
        2. The ontology items are correctly added to the schema
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': ['http://example.org/ontology#Person'],
                    'predicates': [{'http://example.org/ontology#name': 100}],
                }
            }
        }

        # Mock _query_sparql to return ontology information
        sparql_result = {
            'results': {
                'bindings': [
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Ontology'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Example Ontology'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'An example ontology for testing'},
                    },
                ]
            }
        }

        # Create the database instance with mocked methods
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(NeptuneDatabase, '_query_sparql', return_value=sparql_result),
        ):
            db = NeptuneDatabase(host='test-endpoint')

            # Ensure rdf_schema is None
            db.rdf_schema = None

            # Act
            result = db.get_rdf_schema()

            # Assert
            assert isinstance(result, RDFGraphSchema)
            assert len(result.ontologies) == 1
            assert result.ontologies[0].uri == 'http://example.org/ontology'
            assert result.ontologies[0].label == 'Example Ontology'
            assert result.ontologies[0].comment == 'An example ontology for testing'
            assert result.rdfclasses == ['http://example.org/ontology#Person']
            assert result.predicates == ['http://example.org/ontology#name']

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_classes(self, mock_session):
        """Test retrieval of RDF schema with class information.

        This test verifies that:
        1. The get_rdf_schema method correctly processes class information
        2. The class items are correctly added to the schema
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': ['http://example.org/ontology#Person'],
                    'predicates': [{'http://example.org/ontology#name': 100}],
                }
            }
        }

        # Mock _query_sparql to return class information
        sparql_result = {
            'results': {
                'bindings': [
                    {
                        's': {'value': 'http://example.org/ontology#Person'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Class'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#Person'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#subClassOf'},
                        'o': {'value': 'http://example.org/ontology#Agent'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#Person'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Person'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#Person'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'A person in the system'},
                    },
                ]
            }
        }

        # Create the database instance with mocked methods
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(NeptuneDatabase, '_query_sparql', return_value=sparql_result),
        ):
            db = NeptuneDatabase(host='test-endpoint')

            # Ensure rdf_schema is None
            db.rdf_schema = None

            # Act
            result = db.get_rdf_schema()

            # Assert
            assert isinstance(result, RDFGraphSchema)
            assert len(result.classes) == 1
            assert result.classes[0].uri == 'http://example.org/ontology#Person'
            assert result.classes[0].local == 'Person'
            assert result.classes[0].parent_uri == 'http://example.org/ontology#Agent'
            assert result.classes[0].label == 'Person'
            assert result.classes[0].comment == 'A person in the system'
            assert result.rdfclasses == ['http://example.org/ontology#Person']
            assert result.predicates == ['http://example.org/ontology#name']

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_datatype_properties(self, mock_session):
        """Test retrieval of RDF schema with datatype property information.

        This test verifies that:
        1. The get_rdf_schema method correctly processes datatype property information
        2. The datatype property items are correctly added to the schema
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': ['http://example.org/ontology#Person'],
                    'predicates': [{'http://example.org/ontology#name': 100}],
                }
            }
        }

        # Mock _query_sparql to return datatype property information
        sparql_result = {
            'results': {
                'bindings': [
                    {
                        's': {'value': 'http://example.org/ontology#name'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#DatatypeProperty'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#subPropertyOf'},
                        'o': {'value': 'http://example.org/ontology#label'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#domain'},
                        'o': {'value': 'http://example.org/ontology#Person'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#range'},
                        'o': {'value': 'http://www.w3.org/2001/XMLSchema#string'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Name'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'The name of a person'},
                    },
                ]
            }
        }

        # Create the database instance with mocked methods
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(NeptuneDatabase, '_query_sparql', return_value=sparql_result),
        ):
            db = NeptuneDatabase(host='test-endpoint')

            # Ensure rdf_schema is None
            db.rdf_schema = None

            # Act
            result = db.get_rdf_schema()

            # Assert
            assert isinstance(result, RDFGraphSchema)
            assert len(result.dtprops) == 1
            assert result.dtprops[0].uri == 'http://example.org/ontology#name'
            assert result.dtprops[0].local == 'name'
            assert result.dtprops[0].parent_uri == 'http://example.org/ontology#label'
            assert result.dtprops[0].domain_uri == 'http://example.org/ontology#Person'
            assert result.dtprops[0].range_uri == 'http://www.w3.org/2001/XMLSchema#string'
            assert result.dtprops[0].label == 'Name'
            assert result.dtprops[0].comment == 'The name of a person'
            assert result.rdfclasses == ['http://example.org/ontology#Person']
            assert result.predicates == ['http://example.org/ontology#name']

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_object_properties(self, mock_session):
        """Test retrieval of RDF schema with object property information.

        This test verifies that:
        1. The get_rdf_schema method correctly processes object property information
        2. The object property items are correctly added to the schema
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': [
                        'http://example.org/ontology#Person',
                        'http://example.org/ontology#Organization',
                    ],
                    'predicates': [{'http://example.org/ontology#worksFor': 100}],
                }
            }
        }

        # Mock _query_sparql to return object property information
        sparql_result = {
            'results': {
                'bindings': [
                    {
                        's': {'value': 'http://example.org/ontology#worksFor'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#ObjectProperty'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#worksFor'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#subPropertyOf'},
                        'o': {'value': 'http://example.org/ontology#affiliatedWith'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#worksFor'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#domain'},
                        'o': {'value': 'http://example.org/ontology#Person'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#worksFor'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#range'},
                        'o': {'value': 'http://example.org/ontology#Organization'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#worksFor'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'Works For'},
                    },
                    {
                        's': {'value': 'http://example.org/ontology#worksFor'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#comment'},
                        'o': {'value': 'Indicates that a person works for an organization'},
                    },
                ]
            }
        }

        # Create the database instance with mocked methods
        with (
            patch.object(NeptuneDatabase, '_refresh_lpg_schema'),
            patch.object(NeptuneDatabase, '_query_sparql', return_value=sparql_result),
        ):
            db = NeptuneDatabase(host='test-endpoint')

            # Ensure rdf_schema is None
            db.rdf_schema = None

            # Act
            result = db.get_rdf_schema()

            # Assert
            assert isinstance(result, RDFGraphSchema)
            assert len(result.oprops) == 1
            assert result.oprops[0].uri == 'http://example.org/ontology#worksFor'
            assert result.oprops[0].local == 'worksFor'
            assert result.oprops[0].parent_uri == 'http://example.org/ontology#affiliatedWith'
            assert result.oprops[0].domain_uri == 'http://example.org/ontology#Person'
            assert result.oprops[0].range_uri == 'http://example.org/ontology#Organization'
            assert result.oprops[0].label == 'Works For'
            assert result.oprops[0].comment == 'Indicates that a person works for an organization'
            assert len(result.rels) == 1
            assert result.rels[0].uri == 'http://example.org/ontology#worksFor'
            assert result.rels[0].local == 'worksFor'
            assert result.rdfclasses == [
                'http://example.org/ontology#Person',
                'http://example.org/ontology#Organization',
            ]
            assert result.predicates == ['http://example.org/ontology#worksFor']
