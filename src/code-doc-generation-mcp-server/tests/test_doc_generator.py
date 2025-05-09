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
"""Tests for the document generation module."""

import pytest
from awslabs.code_doc_generation_mcp_server.utils.doc_generator import DocumentGenerator
from awslabs.code_doc_generation_mcp_server.utils.models import (
    DocStructure,
    DocumentationContext,
    DocumentationPlan,
    DocumentSection,
    DocumentSpec,
    ProjectAnalysis,
)
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock DocumentationContext for testing."""
    return DocumentationContext(
        project_name='test-project',
        working_dir='/path/to/repo',
        repomix_path='/path/to/repo/generated-docs',
        status='initialized',
        current_step='analysis',
        analysis_result=ProjectAnalysis(
            project_type='Web Application',
            features=['Feature 1', 'Feature 2'],
            file_structure={'root': ['/path/to/repo']},
            dependencies={'react': '^18.2.0'},
            primary_languages=['JavaScript', 'TypeScript'],
            frontend={'framework': 'React'},
            backend={'framework': 'Express', 'database': {'type': 'MongoDB'}},
            apis=None,
        ),
    )


@pytest.fixture
def mock_plan():
    """Create a mock DocumentationPlan for testing."""
    return DocumentationPlan(
        structure=DocStructure(
            root_doc='README.md', doc_tree={'root': ['README.md', 'BACKEND.md']}
        ),
        docs_outline=[
            DocumentSpec(
                name='README.md',
                type='README',
                template='README',
                sections=[
                    DocumentSection(
                        title='Overview', content='', level=1, message='Overview description'
                    ),
                    DocumentSection(
                        title='Features', content='', level=2, message='Features description'
                    ),
                ],
            ),
            DocumentSpec(
                name='BACKEND.md',
                type='BACKEND',
                template='BACKEND',
                sections=[
                    DocumentSection(
                        title='Backend Architecture',
                        content='',
                        level=1,
                        message='Backend architecture description',
                    ),
                    DocumentSection(
                        title='Data Flow', content='', level=2, message='Data flow description'
                    ),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_generate_docs(mock_context, mock_plan):
    """Test the generate_docs method properly generates documentation files."""
    # Arrange
    generator = DocumentGenerator()
    ctx = MagicMock()

    # Mock _generate_content and _write_file methods
    generator._generate_content = AsyncMock()
    generator._generate_content.side_effect = [
        '# README Content\nTest content',
        '# BACKEND Content\nTest backend content',
    ]

    generator._write_file = AsyncMock()

    # Act
    result = await generator.generate_docs(mock_plan, mock_context, ctx)

    # Assert
    assert len(result) == 2
    assert any('README.md' in path for path in result)
    assert any('BACKEND.md' in path for path in result)
    assert generator._generate_content.call_count == 2
    assert generator._write_file.call_count == 2


@pytest.mark.asyncio
async def test_write_file():
    """Test the _write_file method writes content to file correctly."""
    # Arrange
    generator = DocumentGenerator()
    path = Path('/path/to/repo/generated-docs/README.md')
    content = '# Test Content\nThis is a test'

    # Mock Path.write_text
    with (
        patch('pathlib.Path.mkdir') as mock_mkdir,
        patch('pathlib.Path.write_text') as mock_write_text,
    ):
        # Act
        await generator._write_file(path, content)

        # Assert
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write_text.assert_called_once_with(content)


@pytest.mark.asyncio
async def test_write_file_error():
    """Test the _write_file method handles errors correctly."""
    # Arrange
    generator = DocumentGenerator()
    path = Path('/path/to/repo/generated-docs/README.md')
    content = '# Test Content\nThis is a test'

    # Mock Path.write_text to raise an exception
    with (
        patch('pathlib.Path.mkdir') as mock_mkdir,
        patch('pathlib.Path.write_text') as mock_write_text,
    ):
        mock_write_text.side_effect = Exception('Write error')

        # Act & Assert
        with pytest.raises(Exception):
            await generator._write_file(path, content)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write_text.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_standard_document(mock_context):
    """Test _generate_content creates correct structure for standard documents."""
    # Arrange
    generator = DocumentGenerator()
    doc_spec = DocumentSpec(
        name='API.md',
        type='API',
        template='API',
        sections=[
            DocumentSection(
                title='API Reference', content='', level=1, message='API reference description'
            ),
            DocumentSection(
                title='Endpoints', content='', level=2, message='Endpoints description'
            ),
        ],
    )

    # Act
    content = await generator._generate_content(doc_spec, mock_context)

    # Assert
    assert '<!--' in content  # Should include a header comment
    assert '# API Reference' in content
    assert '## Endpoints' in content
    assert 'IMPORTANT: The MCP client must fill in the content' in content


@pytest.mark.asyncio
async def test_generate_content_readme_with_arch_diagram(mock_context):
    """Test _generate_content includes architecture diagram instructions for README."""
    # Arrange
    generator = DocumentGenerator()
    doc_spec = DocumentSpec(
        name='README.md',
        type='README',
        template='README',
        sections=[
            DocumentSection(title='Overview', content='', level=1, message='Overview section'),
            DocumentSection(
                title='Architecture', content='', level=2, message='Architecture section'
            ),
        ],
    )

    # Act
    content = await generator._generate_content(doc_spec, mock_context)

    # Assert
    assert '# Overview' in content
    assert '## Architecture' in content
    assert 'Generate an AWS architecture diagram using AWS Diagram MCP Server' in content
    assert 'AWS Architecture' in content  # Should include the placeholder diagram


@pytest.mark.asyncio
async def test_generate_content_backend_with_dataflow(mock_context):
    """Test _generate_content includes data flow diagram for BACKEND.md."""
    # Arrange
    generator = DocumentGenerator()
    doc_spec = DocumentSpec(
        name='BACKEND.md',
        type='BACKEND',
        template='BACKEND',
        sections=[
            DocumentSection(
                title='Backend Architecture',
                content='',
                level=1,
                message='Backend architecture section',
            ),
            DocumentSection(title='Data Flow', content='', level=2, message='Data flow section'),
        ],
    )

    # Act
    content = await generator._generate_content(doc_spec, mock_context)

    # Assert
    assert '# Backend Architecture' in content
    assert '## Data Flow' in content
    assert 'Generate a data flow diagram using AWS Diagram MCP Server' in content
    assert 'Data Flow Diagram' in content  # Should include the placeholder diagram


def test_get_component_summary():
    """Test _get_component_summary correctly summarizes project components."""
    # Arrange
    generator = DocumentGenerator()

    analysis = ProjectAnalysis(
        project_type='Web Application',
        features=['Feature 1', 'Feature 2'],
        file_structure={'root': ['/path/to/repo']},
        dependencies={'react': '^18.2.0'},
        primary_languages=['JavaScript', 'TypeScript'],
        frontend={'framework': 'React'},
        backend={'framework': 'Express', 'database': {'type': 'MongoDB'}},
        apis=None,
    )

    # Act
    summary = generator._get_component_summary(analysis)

    # Assert
    assert 'Frontend (React)' in summary
    assert 'Backend (Express)' in summary
    assert 'Database: MongoDB' in summary


def test_get_key_components():
    """Test _get_key_components correctly identifies key project components."""
    # Arrange
    generator = DocumentGenerator()

    analysis = ProjectAnalysis(
        project_type='Full Stack',
        features=[],
        file_structure={},
        dependencies={},
        primary_languages=[],
        frontend={'framework': 'React'},
        backend={'framework': 'Express'},
        apis={'type': {'name': 'REST'}},  # Fixed: apis should be Dict[str, Dict[str, Any]]
    )

    # Act
    components = generator._get_key_components(analysis)

    # Assert
    assert 'Frontend' in components
    assert 'Backend' in components
    assert 'API' in components
    assert len(components) == 3


def test_generate_diagram_placeholder():
    """Test _generate_diagram_placeholder creates correct placeholder for different diagram types."""
    # Arrange
    generator = DocumentGenerator()

    analysis = ProjectAnalysis(
        project_type='Full Stack',
        features=[],
        file_structure={},
        dependencies={},
        primary_languages=[],
        frontend={'framework': 'React'},
        backend={'framework': 'Express'},
        apis=None,
    )

    # Act
    arch_placeholder = generator._generate_diagram_placeholder('architecture', analysis)
    overview_placeholder = generator._generate_diagram_placeholder('overview', analysis)
    dataflow_placeholder = generator._generate_diagram_placeholder('dataflow', analysis)

    # Assert
    assert '## AWS Architecture' in arch_placeholder
    assert 'PLACEHOLDER' in arch_placeholder
    assert 'awslabs.aws-diagram-mcp-server' in arch_placeholder

    assert '## System Architecture' in overview_placeholder
    assert f'Project Type: {analysis.project_type}' in overview_placeholder
    assert 'Key Components: Frontend, Backend' in overview_placeholder

    assert '## Data Flow Diagram' in dataflow_placeholder
    assert 'awslabs.aws-diagram-mcp-server' in dataflow_placeholder
