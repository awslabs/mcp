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
"""Tests for the RDF schema functionality in NeptuneDatabase."""

import pytest
from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
class TestRDFSchema:
    """Test class for the RDF schema functionality."""

    @patch('boto3.Session')
    async def test_get_rdf_schema_empty_response(self, mock_session):
        """Test get_rdf_schema with empty response.

        This test verifies that:
        1. When the API returns an empty response, a valid empty schema is created
        2. The schema is stored in the instance and returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response with empty data
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
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

            # Act
            schema = db.get_rdf_schema()

            # Assert
            mock_client.get_rdf_graph_summary.assert_called_once()
            assert schema.rdfclasses == []
            assert schema.predicates == []
            assert schema.ontologies == []
            assert schema.classes == []
            assert schema.dtprops == []
            assert schema.oprops == []
            assert schema.rels == []

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_classes_only(self, mock_session):
        """Test get_rdf_schema with classes but no properties.

        This test verifies that:
        1. When the API returns classes but no properties, they are correctly processed
        2. The schema is stored in the instance and returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response with classes only
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': ['http://example.org/Person', 'http://example.org/Movie'],
                    'predicates': [],
                }
            }
        }

        # Mock SPARQL query response with class data only
        mock_sparql_response = {
            'results': {
                'bindings': [
                    # Class
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
                ]
            }
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

            # Reset the rdf_schema to None to force refresh
            db.rdf_schema = None

            # Mock _query_sparql to return the test data
            db._query_sparql = MagicMock(return_value=mock_sparql_response)

            # Act
            schema = db.get_rdf_schema()

            # Assert
            mock_client.get_rdf_graph_summary.assert_called_once()
            db._query_sparql.assert_called_once()

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

            # Check the schema elements
            assert len(schema.rdfclasses) == 2
            assert schema.rdfclasses == ['http://example.org/Person', 'http://example.org/Movie']
            assert len(schema.predicates) == 0
            assert len(schema.classes) == 1

            # Check class details
            cls = schema.classes[0]
            assert cls.uri == 'http://example.org/Person'
            assert cls.local == 'Person'
            assert cls.label == 'Person'

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_predicates_only(self, mock_session):
        """Test get_rdf_schema with predicates but no classes.

        This test verifies that:
        1. When the API returns predicates but no classes, they are correctly processed
        2. The schema is stored in the instance and returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response with predicates only
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {
                'graphSummary': {
                    'classes': [],
                    'predicates': [
                        {'http://example.org/name': {}},
                        {'http://example.org/age': {}},
                    ],
                }
            }
        }

        # Mock SPARQL query response with property data only
        mock_sparql_response = {
            'results': {
                'bindings': [
                    # Datatype Property
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#DatatypeProperty'},
                    },
                    {
                        's': {'value': 'http://example.org/name'},
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'o': {'value': 'name'},
                    },
                ]
            }
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

            # Reset the rdf_schema to None to force refresh
            db.rdf_schema = None

            # Mock _query_sparql to return the test data
            db._query_sparql = MagicMock(return_value=mock_sparql_response)

            # Act
            schema = db.get_rdf_schema()

            # Assert
            mock_client.get_rdf_graph_summary.assert_called_once()
            db._query_sparql.assert_called_once()

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

            # Check the schema elements
            assert len(schema.rdfclasses) == 0
            assert len(schema.predicates) == 2
            assert schema.predicates == ['http://example.org/name', 'http://example.org/age']
            assert len(schema.dtprops) == 1

            # Check property details
            dt_prop = schema.dtprops[0]
            assert dt_prop.uri == 'http://example.org/name'
            assert dt_prop.local == 'name'
            assert dt_prop.label == 'name'

    @patch('boto3.Session')
    async def test_get_rdf_schema_invalid_iri(self, mock_session):
        """Test get_rdf_schema with invalid IRI.

        This test verifies that:
        1. When an invalid IRI is encountered, it's skipped without causing the entire process to fail
        2. Valid IRIs are still processed correctly
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
                    'classes': ['http://example.org/Person', 'invalid-iri'],
                    'predicates': [],
                }
            }
        }

        # Mock SPARQL query response with class data including invalid IRI
        mock_sparql_response = {
            'results': {
                'bindings': [
                    # Valid class
                    {
                        's': {'value': 'http://example.org/Person'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Class'},
                    },
                    # Invalid IRI
                    {
                        's': {'value': 'invalid-iri'},
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'o': {'value': 'http://www.w3.org/2002/07/owl#Class'},
                    },
                ]
            }
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

            # Reset the rdf_schema to None to force refresh
            db.rdf_schema = None

            # Mock _query_sparql to return the test data
            db._query_sparql = MagicMock(return_value=mock_sparql_response)

            # Act
            schema = db.get_rdf_schema()

            # Assert
            mock_client.get_rdf_graph_summary.assert_called_once()
            db._query_sparql.assert_called_once()

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

            # Check the schema elements - should only have the valid class
            assert len(schema.rdfclasses) == 2  # Both are in rdfclasses from the summary
            assert len(schema.classes) == 1  # Only the valid one is processed into classes

            # Check class details
            cls = schema.classes[0]
            assert cls.uri == 'http://example.org/Person'

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_ontology(self, mock_session):
        """Test get_rdf_schema with ontology data.

        This test verifies that:
        1. Ontology data is correctly processed
        2. The schema is stored in the instance and returned
        """
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock the RDF graph summary response
        mock_client.get_rdf_graph_summary.return_value = {
            'payload': {'graphSummary': {'classes': [], 'predicates': []}}
        }

        # Mock SPARQL query response with ontology data
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
                ]
            }
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

            # Reset the rdf_schema to None to force refresh
            db.rdf_schema = None

            # Mock _query_sparql to return the test data
            db._query_sparql = MagicMock(return_value=mock_sparql_response)

            # Act
            schema = db.get_rdf_schema()

            # Assert
            mock_client.get_rdf_graph_summary.assert_called_once()
            db._query_sparql.assert_called_once()

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

            # Check the schema elements
            assert len(schema.ontologies) == 1

            # Check ontology details
            ontology = schema.ontologies[0]
            assert ontology.uri == 'http://example.org/ontology'
            assert ontology.label == 'Example Ontology'
            assert ontology.comment == 'An example ontology for testing'

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_object_property(self, mock_session):
        """Test get_rdf_schema with object property data.

        This test verifies that:
        1. Object property data is correctly processed
        2. The schema is stored in the instance and returned
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
                'graphSummary': {'classes': [], 'predicates': [{'http://example.org/knows': {}}]}
            }
        }

        # Mock SPARQL query response with object property data
        mock_sparql_response = {
            'results': {
                'bindings': [
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
                ]
            }
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

            # Reset the rdf_schema to None to force refresh
            db.rdf_schema = None

            # Mock _query_sparql to return the test data
            db._query_sparql = MagicMock(return_value=mock_sparql_response)

            # Act
            schema = db.get_rdf_schema()

            # Assert
            mock_client.get_rdf_graph_summary.assert_called_once()
            db._query_sparql.assert_called_once()

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

            # Check the schema elements
            assert len(schema.predicates) == 1
            assert len(schema.oprops) == 1
            assert len(schema.rels) == 1

            # Check object property details
            obj_prop = schema.oprops[0]
            assert obj_prop.uri == 'http://example.org/knows'
            assert obj_prop.local == 'knows'
            assert obj_prop.parent_uri == 'http://example.org/related'
            assert obj_prop.domain_uri == 'http://example.org/Person'
            assert obj_prop.range_uri == 'http://example.org/Person'

            # Check relationship details
            rel = schema.rels[0]
            assert rel.uri == 'http://example.org/knows'
            assert rel.local == 'knows'

    @patch('boto3.Session')
    async def test_get_rdf_schema_with_no_results(self, mock_session):
        """Test get_rdf_schema when SPARQL query returns no results.

        This test verifies that:
        1. When the SPARQL query returns no results, the schema is still created with summary data
        2. The schema is stored in the instance and returned
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
                    'classes': ['http://example.org/Person'],
                    'predicates': [{'http://example.org/name': {}}],
                }
            }
        }

        # Mock SPARQL query response with no results key
        mock_sparql_response = {}

        # Mock _refresh_lpg_schema to avoid actual API calls during init
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
            mock_client.get_rdf_graph_summary.assert_called_once()
            db._query_sparql.assert_called_once()

            # Check that the schema was stored in the instance
            assert db.rdf_schema == schema

            # Check the schema elements - should still have the summary data
            assert len(schema.rdfclasses) == 1
            assert schema.rdfclasses == ['http://example.org/Person']
            assert len(schema.predicates) == 1
            assert schema.predicates == ['http://example.org/name']

            # But no processed data
            assert len(schema.classes) == 0
            assert len(schema.dtprops) == 0
            assert len(schema.oprops) == 0
