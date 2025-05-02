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
    """Analysis results that YOU (Cline) must determine from reading repomix output."""

    project_type: str = Field(
        ...,
        description='Type of project - Cline will analyze from code. Example: "Web Application", "CLI Tool", "AWS CDK Application"',
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
        None, description='Analysis results from Cline - will be populated during planning'
    )


class DocumentationPlan(BaseModel):
    """Documentation plan based on repository analysis.

    This class represents a plan for generating documentation based on
    repository analysis. It includes the overall structure and individual
    document specifications.
    """

    structure: DocStructure = Field(
        ..., description='Overall documentation structure - Cline will determine this'
    )
    docs_outline: List[DocumentSpec] = Field(
        ..., description='Individual document sections - Cline will determine this'
    )


class GeneratedDocument(BaseModel):
    """Generated document structure that Cline must fill with content.

    When you (Cline) receive a GeneratedDocument:
    1. The content field will be empty - YOU must fill it
    2. Write comprehensive content for each section
    3. Include code examples and explanations
    4. Do not leave sections empty
    5. Use your analysis to create accurate content
    """

    path: str = Field(..., description='Full path to generated file')
    content: str = Field(..., description='Document content - YOU (Cline) must fill this')
    type: str = Field(..., description='Document type')
