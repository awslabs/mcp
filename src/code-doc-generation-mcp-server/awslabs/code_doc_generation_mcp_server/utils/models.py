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

"""Shared data models for document generation."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class DocumentSection(BaseModel):
    """Section of a document with content and metadata."""

    title: str = Field(..., description='Section title')
    content: str = Field(..., description='Section content')
    level: int = Field(default=2, description='Heading level (1-6)')
    subsections: Optional[List['DocumentSection']] = Field(
        default=None, description='Nested sections'
    )
    message: Optional[str] = Field(
        None, description='Message for the MCP client about this section'
    )


DocumentSection.model_rebuild()  # Required for recursive type definition


class DocumentTemplate(BaseModel):
    """Template for common document types."""

    type: str = Field(..., description='Template type (e.g., README, API, Setup)')
    sections: List[DocumentSection] = Field(..., description='Default sections for this type')


class DocumentSpec(BaseModel):
    """Specification for a document to generate."""

    name: str = Field(..., description='Document filename (e.g. README.md)')
    type: str = Field(..., description='Document type (README, API, etc)')
    template: Optional[str] = Field(None, description='Template to use (if any)')
    sections: List[DocumentSection] = Field(..., description='Document sections')


class ProjectAnalysis(BaseModel):
    """Analysis results that the MCP client must determine from reading repository structure."""

    project_type: str = Field(
        ...,
        description='Type of project - to be analyzed from code. Example: "Web Application", "CLI Tool", "AWS CDK Application"',
    )
    features: List[str] = Field(
        ...,
        description='Key features of the project. Example: ["Authentication", "Data Processing", "API Integration"]',
    )
    file_structure: Dict[str, Any] = Field(
        ...,
        description='Project organization with categories of files. Example: {"root": ["/path/to/project"], "frontend": ["src/components", "src/pages"], "backend": ["api/", "server.js"]}',
    )
    dependencies: Dict[str, str] = Field(
        ...,
        description='Project dependencies with versions. Example: {"react": "^18.2.0", "express": "^4.18.2"}',
    )
    primary_languages: List[str] = Field(
        ...,
        description='Programming languages used in the project. Example: ["JavaScript", "TypeScript", "Python"]',
    )
    apis: Optional[Dict[str, Dict[str, Any]]] = Field(
        None,
        description='API details with endpoints and methods. Example: {"users": {"get": {"description": "Get all users"}, "post": {"description": "Create a user"}}}',
    )
    backend: Optional[Dict[str, Any]] = Field(
        None,
        description='Backend implementation details. Example: {"framework": "Express", "database": "MongoDB", "authentication": "JWT"}',
    )
    frontend: Optional[Dict[str, Any]] = Field(
        None,
        description='Frontend implementation details. Example: {"framework": "React", "state_management": "Redux", "styling": "Tailwind CSS"}',
    )
    has_infrastructure_as_code: bool = Field(
        default=False,
        description='Whether the project contains infrastructure as code (CDK, Terraform, CloudFormation, etc.). Set to True if detected.',
    )


class DocStructure(BaseModel):
    """Core documentation structure.

    This class represents the overall structure of the documentation,
    including the root document and the document tree.
    """

    root_doc: str = Field(..., description='Main entry point document (e.g. README.md)')
    doc_tree: Dict[str, List[str]] = Field(
        ..., description='Maps sections to their document files'
    )


class McpServerContext(BaseModel):
    """Configuration for an MCP server integration."""

    server_name: str = Field(..., description='Name of the MCP server')
    tool_name: str = Field(..., description='Name of the tool to use')


class DocumentationContext(BaseModel):
    """Documentation process state and file locations.

    This class maintains the state of the documentation generation process.
    """

    project_name: str = Field(..., description='Name of the project')
    working_dir: str = Field(..., description='Working directory for doc generation')
    repomix_path: str = Field(..., description='Path to Repomix output')
    status: str = Field('initialized', description='Current status of documentation process')
    current_step: str = Field('analysis', description='Current step in the documentation process')
    analysis_result: Optional[ProjectAnalysis] = Field(
        None,
        description='Analysis results from the MCP client - will be populated during planning',
    )


class DocumentationPlan(BaseModel):
    """Documentation plan based on repository analysis.

    This class represents a plan for generating documentation based on
    repository analysis. It includes the overall structure and individual
    document specifications.
    """

    structure: DocStructure = Field(
        ..., description='Overall documentation structure - The MCP client will determine this'
    )
    docs_outline: List[DocumentSpec] = Field(
        ..., description='Individual document sections - The MCP client will determine this'
    )


class GeneratedDocument(BaseModel):
    """Generated document structure that the MCP client must fill with content.

    When you (the MCP client) receive a GeneratedDocument:
    1. The content field will be empty - YOU must fill it
    2. Write comprehensive content for each section
    3. Include code examples and explanations
    4. Do not leave sections empty
    5. Use your analysis to create accurate content
    """

    path: str = Field(..., description='Full path to generated file')
    content: str = Field(..., description='Document content - The MCP client must fill this')
    type: str = Field(..., description='Document type')
    message: str = Field('', description='Message for the MCP client with instructions')
