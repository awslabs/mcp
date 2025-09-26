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


class URIItem(BaseModel):
    """Represents an item with a URI and local name.

    Attributes:
        uri (str): The full URI of the item
        local (str): The local name/identifier of the item
    """

    uri: str
    local: str


class OntologyItem(BaseModel):
    """Represents an ontology with its metadata.

    Attributes:
        uri (str): The full URI of the ontology
        label (str | None): The human-readable label of the ontology
        comment (str | None): A description or comment about the ontology
    """

    uri: str
    label: str | None = None
    comment: str | None = None


class ClassItem(BaseModel):
    """Represents a class definition in an RDF schema.

    Attributes:
        uri (str): The full URI of the class
        local (str): The local name/identifier of the class
        parent_uri (str | None): The URI of the parent class if it exists
        label (str | None): The human-readable label of the class
        comment (str | None): A description or comment about the class
    """

    uri: str
    local: str
    parent_uri: str | None = None
    label: str | None = None
    comment: str | None = None


class PropertyItem(BaseModel):
    """Base class for RDF properties.

    Attributes:
        uri (str): The full URI of the property
        local (str): The local name/identifier of the property
        parent_uri (str | None): The URI of the parent property if it exists
        domain_uri (str | None): The URI of the domain class
        range_uri (str | None): The URI of the range class or datatype
        label (str | None): The human-readable label of the property
        comment (str | None): A description or comment about the property
    """

    uri: str
    local: str
    parent_uri: str | None = None
    domain_uri: str | None = None
    range_uri: str | None = None
    label: str | None = None
    comment: str | None = None


class DatatypePropertyItem(PropertyItem):
    """Represents a datatype property in an RDF schema."""

    pass


class ObjectPropertyItem(PropertyItem):
    """Represents an object property in an RDF schema."""

    pass


class RDFGraphSchema(BaseModel):
    """Represents a complete RDF schema definition.

    Attributes:
        distinct_prefixes (Dict[str, str]): Mapping of URI prefixes to their aliases
        ontologies (List[OntologyItem]): List of ontology definitions with metadata
        classes (List[ClassItem]): List of class definitions with hierarchies and metadata
        rels (List[URIItem]): List of relationship definitions with URIs and local names
        dtprops (List[DatatypePropertyItem]): List of datatype properties with domains, ranges, and metadata
        oprops (List[ObjectPropertyItem]): List of object properties with domains, ranges, and metadata
        rdfclasses (List[str]): List of classes in the graph.
        predicates (List[str]): List of predicates in the graph
    """

    distinct_prefixes: dict[str, str]
    ontologies: List[OntologyItem] = []
    classes: List[ClassItem] = []
    rels: List[URIItem] = []
    dtprops: List[DatatypePropertyItem] = []
    oprops: List[ObjectPropertyItem] = []
    rdfclasses: List[str] = []
    predicates: List[str] = []
