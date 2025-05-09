#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
"""Data Models Module for Neptune Graph Database.

This module defines the core data structures and types used throughout the Neptune
graph database interface. It includes models for query languages, graph schema
definitions, and knowledge graph components.

The models use Python's dataclass decorator for clean, type-safe data structures
that represent both the graph structure and its contents.
"""

from pydantic import BaseModel
from typing import List


class Property(BaseModel):
    """Represents a property definition for nodes and relationships in the graph.

    Properties are key-value pairs that can be attached to both nodes and
    relationships, storing additional metadata about these graph elements.

    Attributes:
        name (str): The name/key of the property
        type (str): The data type of the property value
    """

    name: str
    type: List[str]


class Node(BaseModel):
    """Defines a node type in the graph schema.

    Nodes represent entities in the graph database and can have labels
    and properties that describe their characteristics.

    Attributes:
        labels (str): The label(s) that categorize this node type
        properties (List[Property]): List of properties that can be assigned to this node type
    """

    labels: str
    properties: List[Property] = []


class Relationship(BaseModel):
    """Defines a relationship type in the graph schema.

    Relationships represent connections between nodes in the graph and can
    have their own properties to describe the nature of the connection.

    Attributes:
        type (str): The type/category of the relationship
        properties (List[Property]): List of properties that can be assigned to this relationship type
    """

    type: str
    properties: List[Property] = []


class RelationshipPattern(BaseModel):
    """Defines a valid relationship pattern between nodes in the graph.

    Relationship patterns describe the allowed connections between different
    types of nodes in the graph schema.

    Attributes:
        left_node (str): The label of the source/starting node
        right_node (str): The label of the target/ending node
        relation (str): The type of relationship connecting the nodes
    """

    left_node: str
    right_node: str
    relation: str


class GraphSchema(BaseModel):
    """Represents the complete schema definition for the graph database.

    The graph schema defines all possible node types, relationship types,
    and valid patterns of connections between nodes.

    Attributes:
        nodes (List[Node]): List of all node types defined in the schema
        relationships (List[Relationship]): List of all relationship types defined in the schema
        relationship_patterns (List[RelationshipPattern]): List of valid relationship patterns
    """

    nodes: List[Node]
    relationships: List[Relationship]
    relationship_patterns: List[RelationshipPattern]
