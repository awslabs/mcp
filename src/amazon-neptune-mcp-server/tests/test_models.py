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
"""Tests for the data models."""

import pytest
from awslabs.amazon_neptune_mcp_server.models import (
    Property,
    Node,
    Relationship,
    RelationshipPattern,
    GraphSchema
)


class TestModels:
    def test_property_model(self):
        # Create a property
        prop = Property(name="age", type=["INTEGER"])
        
        # Verify attributes
        assert prop.name == "age"
        assert prop.type == ["INTEGER"]
        
        # Test serialization
        prop_dict = prop.model_dump()
        assert prop_dict == {"name": "age", "type": ["INTEGER"]}
    
    def test_node_model(self):
        # Create properties
        name_prop = Property(name="name", type=["STRING"])
        age_prop = Property(name="age", type=["INTEGER"])
        
        # Create a node with properties
        node = Node(labels="Person", properties=[name_prop, age_prop])
        
        # Verify attributes
        assert node.labels == "Person"
        assert len(node.properties) == 2
        assert node.properties[0].name == "name"
        assert node.properties[1].name == "age"
        
        # Test serialization
        node_dict = node.model_dump()
        assert node_dict["labels"] == "Person"
        assert len(node_dict["properties"]) == 2
    
    def test_node_model_without_properties(self):
        # Create a node without properties
        node = Node(labels="EmptyNode")
        
        # Verify attributes
        assert node.labels == "EmptyNode"
        assert node.properties == []
        
        # Test serialization
        node_dict = node.model_dump()
        assert node_dict["labels"] == "EmptyNode"
        assert node_dict["properties"] == []
    
    def test_relationship_model(self):
        # Create properties
        since_prop = Property(name="since", type=["DATE"])
        
        # Create a relationship with properties
        rel = Relationship(type="KNOWS", properties=[since_prop])
        
        # Verify attributes
        assert rel.type == "KNOWS"
        assert len(rel.properties) == 1
        assert rel.properties[0].name == "since"
        
        # Test serialization
        rel_dict = rel.model_dump()
        assert rel_dict["type"] == "KNOWS"
        assert len(rel_dict["properties"]) == 1
    
    def test_relationship_model_without_properties(self):
        # Create a relationship without properties
        rel = Relationship(type="FOLLOWS")
        
        # Verify attributes
        assert rel.type == "FOLLOWS"
        assert rel.properties == []
        
        # Test serialization
        rel_dict = rel.model_dump()
        assert rel_dict["type"] == "FOLLOWS"
        assert rel_dict["properties"] == []
    
    def test_relationship_pattern_model(self):
        # Create a relationship pattern
        pattern = RelationshipPattern(
            left_node="Person",
            right_node="Person",
            relation="KNOWS"
        )
        
        # Verify attributes
        assert pattern.left_node == "Person"
        assert pattern.right_node == "Person"
        assert pattern.relation == "KNOWS"
        
        # Test serialization
        pattern_dict = pattern.model_dump()
        assert pattern_dict["left_node"] == "Person"
        assert pattern_dict["right_node"] == "Person"
        assert pattern_dict["relation"] == "KNOWS"
    
    def test_graph_schema_model(self):
        # Create nodes
        person_node = Node(
            labels="Person",
            properties=[
                Property(name="name", type=["STRING"]),
                Property(name="age", type=["INTEGER"])
            ]
        )
        
        city_node = Node(
            labels="City",
            properties=[
                Property(name="name", type=["STRING"]),
                Property(name="population", type=["INTEGER"])
            ]
        )
        
        # Create relationships
        knows_rel = Relationship(
            type="KNOWS",
            properties=[Property(name="since", type=["DATE"])]
        )
        
        lives_in_rel = Relationship(type="LIVES_IN")
        
        # Create relationship patterns
        person_knows_person = RelationshipPattern(
            left_node="Person",
            right_node="Person",
            relation="KNOWS"
        )
        
        person_lives_in_city = RelationshipPattern(
            left_node="Person",
            right_node="City",
            relation="LIVES_IN"
        )
        
        # Create graph schema
        schema = GraphSchema(
            nodes=[person_node, city_node],
            relationships=[knows_rel, lives_in_rel],
            relationship_patterns=[person_knows_person, person_lives_in_city]
        )
        
        # Verify attributes
        assert len(schema.nodes) == 2
        assert len(schema.relationships) == 2
        assert len(schema.relationship_patterns) == 2
        
        # Test serialization
        schema_dict = schema.model_dump()
        assert len(schema_dict["nodes"]) == 2
        assert len(schema_dict["relationships"]) == 2
        assert len(schema_dict["relationship_patterns"]) == 2