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
"""Tests for the data models."""

from awslabs.amazon_neptune_mcp_server.models import (
    ClassItem,
    DatatypePropertyItem,
    GraphSchema,
    Node,
    ObjectPropertyItem,
    OntologyItem,
    Property,
    RDFGraphSchema,
    Relationship,
    RelationshipPattern,
    URIItem,
)


class TestModels:
    """Test class for the data model classes."""

    def test_property_model(self):
        """Test the Property model creation and serialization.

        This test verifies that:
        1. A Property can be created with name and type attributes
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create a property
        prop = Property(name='age', type=['INTEGER'])

        # Verify attributes
        assert prop.name == 'age'
        assert prop.type == ['INTEGER']

        # Test serialization
        prop_dict = prop.model_dump()
        assert prop_dict == {'name': 'age', 'type': ['INTEGER']}

    def test_node_model(self):
        """Test the Node model creation and serialization with properties.

        This test verifies that:
        1. A Node can be created with labels and properties
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create properties
        name_prop = Property(name='name', type=['STRING'])
        age_prop = Property(name='age', type=['INTEGER'])

        # Create a node with properties
        node = Node(labels='Person', properties=[name_prop, age_prop])

        # Verify attributes
        assert node.labels == 'Person'
        assert len(node.properties) == 2
        assert node.properties[0].name == 'name'
        assert node.properties[1].name == 'age'

        # Test serialization
        node_dict = node.model_dump()
        assert node_dict['labels'] == 'Person'
        assert len(node_dict['properties']) == 2

    def test_node_model_without_properties(self):
        """Test the Node model creation and serialization without properties.

        This test verifies that:
        1. A Node can be created with only labels
        2. The properties attribute defaults to an empty list
        3. The model serializes correctly to a dictionary
        """
        # Create a node without properties
        node = Node(labels='EmptyNode')

        # Verify attributes
        assert node.labels == 'EmptyNode'
        assert node.properties == []

        # Test serialization
        node_dict = node.model_dump()
        assert node_dict['labels'] == 'EmptyNode'
        assert node_dict['properties'] == []

    def test_relationship_model(self):
        """Test the Relationship model creation and serialization with properties.

        This test verifies that:
        1. A Relationship can be created with type and properties
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create properties
        since_prop = Property(name='since', type=['DATE'])

        # Create a relationship with properties
        rel = Relationship(type='KNOWS', properties=[since_prop])

        # Verify attributes
        assert rel.type == 'KNOWS'
        assert len(rel.properties) == 1
        assert rel.properties[0].name == 'since'

        # Test serialization
        rel_dict = rel.model_dump()
        assert rel_dict['type'] == 'KNOWS'
        assert len(rel_dict['properties']) == 1

    def test_relationship_model_without_properties(self):
        """Test the Relationship model creation and serialization without properties.

        This test verifies that:
        1. A Relationship can be created with only type
        2. The properties attribute defaults to an empty list
        3. The model serializes correctly to a dictionary
        """
        # Create a relationship without properties
        rel = Relationship(type='FOLLOWS')

        # Verify attributes
        assert rel.type == 'FOLLOWS'
        assert rel.properties == []

        # Test serialization
        rel_dict = rel.model_dump()
        assert rel_dict['type'] == 'FOLLOWS'
        assert rel_dict['properties'] == []

    def test_relationship_pattern_model(self):
        """Test the RelationshipPattern model creation and serialization.

        This test verifies that:
        1. A RelationshipPattern can be created with left_node, right_node, and relation
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create a relationship pattern
        pattern = RelationshipPattern(left_node='Person', right_node='Person', relation='KNOWS')

        # Verify attributes
        assert pattern.left_node == 'Person'
        assert pattern.right_node == 'Person'
        assert pattern.relation == 'KNOWS'

        # Test serialization
        pattern_dict = pattern.model_dump()
        assert pattern_dict['left_node'] == 'Person'
        assert pattern_dict['right_node'] == 'Person'
        assert pattern_dict['relation'] == 'KNOWS'

    def test_graph_schema_model(self):
        """Test the GraphSchema model creation and serialization.

        This test verifies that:
        1. A GraphSchema can be created with nodes, relationships, and relationship_patterns
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create nodes
        person_node = Node(
            labels='Person',
            properties=[
                Property(name='name', type=['STRING']),
                Property(name='age', type=['INTEGER']),
            ],
        )

        city_node = Node(
            labels='City',
            properties=[
                Property(name='name', type=['STRING']),
                Property(name='population', type=['INTEGER']),
            ],
        )

        # Create relationships
        knows_rel = Relationship(type='KNOWS', properties=[Property(name='since', type=['DATE'])])

        lives_in_rel = Relationship(type='LIVES_IN')

        # Create relationship patterns
        person_knows_person = RelationshipPattern(
            left_node='Person', right_node='Person', relation='KNOWS'
        )

        person_lives_in_city = RelationshipPattern(
            left_node='Person', right_node='City', relation='LIVES_IN'
        )

        # Create graph schema
        schema = GraphSchema(
            nodes=[person_node, city_node],
            relationships=[knows_rel, lives_in_rel],
            relationship_patterns=[person_knows_person, person_lives_in_city],
        )

        # Verify attributes
        assert len(schema.nodes) == 2
        assert len(schema.relationships) == 2
        assert len(schema.relationship_patterns) == 2

        # Test serialization
        schema_dict = schema.model_dump()
        assert len(schema_dict['nodes']) == 2
        assert len(schema_dict['relationships']) == 2
        assert len(schema_dict['relationship_patterns']) == 2

    def test_uri_item_model(self):
        """Test the URIItem model creation and serialization.

        This test verifies that:
        1. A URIItem can be created with uri and local attributes
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create a URIItem
        uri_item = URIItem(uri='http://example.org/person', local='person')

        # Verify attributes
        assert uri_item.uri == 'http://example.org/person'
        assert uri_item.local == 'person'

        # Test serialization
        uri_item_dict = uri_item.model_dump()
        assert uri_item_dict == {'uri': 'http://example.org/person', 'local': 'person'}

    def test_ontology_item_model(self):
        """Test the OntologyItem model creation and serialization.

        This test verifies that:
        1. An OntologyItem can be created with uri, label, and comment attributes
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create an OntologyItem
        ontology = OntologyItem(
            uri='http://example.org/ontology',
            label='Example Ontology',
            comment='An example ontology for testing',
        )

        # Verify attributes
        assert ontology.uri == 'http://example.org/ontology'
        assert ontology.label == 'Example Ontology'
        assert ontology.comment == 'An example ontology for testing'

        # Test serialization
        ontology_dict = ontology.model_dump()
        assert ontology_dict == {
            'uri': 'http://example.org/ontology',
            'label': 'Example Ontology',
            'comment': 'An example ontology for testing',
        }

    def test_class_item_model(self):
        """Test the ClassItem model creation and serialization.

        This test verifies that:
        1. A ClassItem can be created with all attributes
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create a ClassItem
        class_item = ClassItem(
            uri='http://example.org/Person',
            local='Person',
            parent_uri='http://example.org/Agent',
            label='Person Class',
            comment='Represents a person',
        )

        # Verify attributes
        assert class_item.uri == 'http://example.org/Person'
        assert class_item.local == 'Person'
        assert class_item.parent_uri == 'http://example.org/Agent'
        assert class_item.label == 'Person Class'
        assert class_item.comment == 'Represents a person'

        # Test serialization
        class_item_dict = class_item.model_dump()
        assert class_item_dict == {
            'uri': 'http://example.org/Person',
            'local': 'Person',
            'parent_uri': 'http://example.org/Agent',
            'label': 'Person Class',
            'comment': 'Represents a person',
        }

    def test_datatype_property_item_model(self):
        """Test the DatatypePropertyItem model creation and serialization.

        This test verifies that:
        1. A DatatypePropertyItem can be created with all attributes
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create a DatatypePropertyItem
        dt_prop = DatatypePropertyItem(
            uri='http://example.org/age',
            local='age',
            domain_uri='http://example.org/Person',
            range_uri='http://www.w3.org/2001/XMLSchema#integer',
            label='Age',
            comment='The age of a person',
        )

        # Verify attributes
        assert dt_prop.uri == 'http://example.org/age'
        assert dt_prop.local == 'age'
        assert dt_prop.domain_uri == 'http://example.org/Person'
        assert dt_prop.range_uri == 'http://www.w3.org/2001/XMLSchema#integer'
        assert dt_prop.label == 'Age'
        assert dt_prop.comment == 'The age of a person'

        # Test serialization
        dt_prop_dict = dt_prop.model_dump()
        assert dt_prop_dict == {
            'uri': 'http://example.org/age',
            'local': 'age',
            'parent_uri': None,
            'domain_uri': 'http://example.org/Person',
            'range_uri': 'http://www.w3.org/2001/XMLSchema#integer',
            'label': 'Age',
            'comment': 'The age of a person',
        }

    def test_object_property_item_model(self):
        """Test the ObjectPropertyItem model creation and serialization.

        This test verifies that:
        1. An ObjectPropertyItem can be created with all attributes
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create an ObjectPropertyItem
        obj_prop = ObjectPropertyItem(
            uri='http://example.org/knows',
            local='knows',
            domain_uri='http://example.org/Person',
            range_uri='http://example.org/Person',
            label='Knows',
            comment='Indicates that a person knows another person',
        )

        # Verify attributes
        assert obj_prop.uri == 'http://example.org/knows'
        assert obj_prop.local == 'knows'
        assert obj_prop.domain_uri == 'http://example.org/Person'
        assert obj_prop.range_uri == 'http://example.org/Person'
        assert obj_prop.label == 'Knows'
        assert obj_prop.comment == 'Indicates that a person knows another person'

        # Test serialization
        obj_prop_dict = obj_prop.model_dump()
        assert obj_prop_dict == {
            'uri': 'http://example.org/knows',
            'local': 'knows',
            'parent_uri': None,
            'domain_uri': 'http://example.org/Person',
            'range_uri': 'http://example.org/Person',
            'label': 'Knows',
            'comment': 'Indicates that a person knows another person',
        }

    def test_rdf_graph_schema_model(self):
        """Test the RDFGraphSchema model creation and serialization.

        This test verifies that:
        1. An RDFGraphSchema can be created with all attributes
        2. The attributes are correctly accessible
        3. The model serializes correctly to a dictionary
        """
        # Create prefixes
        prefixes = {'ex': 'http://example.org/'}

        # Create ontologies
        ontology = OntologyItem(uri='http://example.org/ontology', label='Example Ontology')

        # Create classes
        person_class = ClassItem(uri='http://example.org/Person', local='Person')

        # Create relationships
        knows_rel = URIItem(uri='http://example.org/knows', local='knows')

        # Create datatype properties
        age_prop = DatatypePropertyItem(uri='http://example.org/age', local='age')

        # Create object properties
        knows_prop = ObjectPropertyItem(uri='http://example.org/knows', local='knows')

        # Create RDF classes and predicates
        rdfclasses = ['http://example.org/Person']
        predicates = ['http://example.org/knows', 'http://example.org/age']

        # Create RDF graph schema
        schema = RDFGraphSchema(
            distinct_prefixes=prefixes,
            ontologies=[ontology],
            classes=[person_class],
            rels=[knows_rel],
            dtprops=[age_prop],
            oprops=[knows_prop],
            rdfclasses=rdfclasses,
            predicates=predicates,
        )

        # Verify attributes
        assert schema.distinct_prefixes == prefixes
        assert len(schema.ontologies) == 1
        assert len(schema.classes) == 1
        assert len(schema.rels) == 1
        assert len(schema.dtprops) == 1
        assert len(schema.oprops) == 1
        assert len(schema.rdfclasses) == 1
        assert len(schema.predicates) == 2

        # Test serialization
        schema_dict = schema.model_dump()
        assert schema_dict['distinct_prefixes'] == prefixes
        assert len(schema_dict['ontologies']) == 1
        assert len(schema_dict['classes']) == 1
        assert len(schema_dict['rels']) == 1
        assert len(schema_dict['dtprops']) == 1
        assert len(schema_dict['oprops']) == 1
        assert len(schema_dict['rdfclasses']) == 1
        assert len(schema_dict['predicates']) == 2
