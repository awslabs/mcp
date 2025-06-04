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
"""Additional tests for the DocumentGenerator class to improve coverage."""

import pytest
import tempfile
from awslabs.code_doc_gen_mcp_server.utils.doc_generator import DocumentGenerator
from awslabs.code_doc_gen_mcp_server.utils.models import (
    DocStructure,
    DocumentationContext,
    DocumentationPlan,
    DocumentSection,
    DocumentSpec,
    ProjectAnalysis,
)
from pathlib import Path
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_generate_docs_error_handling():
    """Test error handling in generate_docs method."""
    # Arrange
    generator = DocumentGenerator()

    # Create plan with document specs
    plan = DocumentationPlan(
        structure=DocStructure(root_doc='README.md', doc_tree={'root': ['README.md']}),
        docs_outline=[
            DocumentSpec(
                name='README.md',
                type='README',
                template='README',
                sections=[
                    DocumentSection(title='Test Section', content='', level=1, message=None)
                ],
            ),
        ],
    )

    # Create context with project info
    context = DocumentationContext(
        project_name='test-project',
        working_dir='/invalid/path',  # Invalid path to cause error
        repomix_path='/invalid/path/generated-docs',
        status='initialized',
        current_step='analysis',
        analysis_result=None,
    )

    # Mock _write_file to simulate an error
    with patch.object(generator, '_write_file', side_effect=Exception('Test error')):
        # Act & Assert
        with pytest.raises(Exception):
            await generator.generate_docs(plan, context)


@pytest.mark.asyncio
async def test_generate_docs_with_log_messages():
    """Test generate_docs with log messages and MCP context."""
    # Arrange
    generator = DocumentGenerator()

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)

        # Create plan with document specs
        plan = DocumentationPlan(
            structure=DocStructure(root_doc='README.md', doc_tree={'root': ['README.md']}),
            docs_outline=[
                DocumentSpec(
                    name='README.md',
                    type='README',
                    template='README',
                    sections=[
                        DocumentSection(title='Test Section', content='', level=1, message=None)
                    ],
                ),
            ],
        )

        # Create ProjectAnalysis
        analysis = ProjectAnalysis(
            project_type='Web Application',
            features=['Feature 1'],
            file_structure={'root': [str(tmp_path)]},
            dependencies={},
            primary_languages=['Python'],
            apis=None,
            backend=None,
            frontend=None,
        )

        # Create context with project info
        context = DocumentationContext(
            project_name='test-project',
            working_dir=str(tmp_path),
            repomix_path=str(tmp_path / 'generated-docs'),
            status='initialized',
            current_step='analysis',
            analysis_result=analysis,
        )

        # Create MCP context mock
        ctx = AsyncMock()

        # Mock functions to avoid real file operations
        with (
            patch.object(generator, '_generate_content', return_value='README.md content'),
            patch.object(Path, 'mkdir', return_value=None),
            patch.object(Path, 'write_text', return_value=None),
        ):
            # Act
            result = await generator.generate_docs(plan, context, ctx)

            # Assert
            assert len(result) == 1
            assert result[0].endswith('README.md')
            # MCP info logging occurs in generate_docs but can be hard to verify directly


def test_get_component_summary():
    """Test _get_component_summary method with different inputs."""
    # Arrange
    generator = DocumentGenerator()

    # Test with frontend only
    analysis1 = ProjectAnalysis(
        project_type='Web Application',
        features=['Feature 1'],
        file_structure={'root': ['/path']},
        dependencies={},
        primary_languages=['JavaScript'],
        frontend={'framework': 'React'},
        apis=None,
        backend=None,
    )

    # Test with backend only
    analysis2 = ProjectAnalysis(
        project_type='API',
        features=['Feature 1'],
        file_structure={'root': ['/path']},
        dependencies={},
        primary_languages=['Python'],
        backend={'framework': 'Flask', 'database': 'PostgreSQL'},
        apis=None,
        frontend=None,
    )

    # Test with full stack - using proper nested dict for apis field
    analysis3 = ProjectAnalysis(
        project_type='Full Stack',
        features=['Feature 1'],
        file_structure={'root': ['/path']},
        dependencies={},
        primary_languages=['JavaScript', 'Python'],
        frontend={'framework': 'React'},
        backend={'framework': 'Express', 'database': {'type': 'MongoDB'}},
        apis={
            'users': {'get': {'description': 'Get users'}, 'post': {'description': 'Create user'}}
        },
    )

    # Act & Assert
    # Frontend only
    result1 = generator._get_component_summary(analysis1)
    assert '- Frontend' in result1
    assert 'React' in result1

    # Backend only
    result2 = generator._get_component_summary(analysis2)
    assert '- Backend' in result2
    assert 'Flask' in result2
    assert '- Database' in result2 or 'PostgreSQL' in result2

    # Full stack
    result3 = generator._get_component_summary(analysis3)
    assert '- Frontend' in result3
    assert '- Backend' in result3
    assert '- API Layer' in result3
    assert 'MongoDB' in result3


def test_get_key_components():
    """Test _get_key_components method with different inputs."""
    # Arrange
    generator = DocumentGenerator()

    # Test with frontend only
    analysis1 = ProjectAnalysis(
        project_type='Web Application',
        features=['Feature 1'],
        file_structure={'root': ['/path']},
        dependencies={},
        primary_languages=['JavaScript'],
        frontend={'framework': 'React'},
        apis=None,
        backend=None,
    )

    # Test with full stack - using proper nested dict for apis field
    analysis2 = ProjectAnalysis(
        project_type='Full Stack',
        features=['Feature 1'],
        file_structure={'root': ['/path']},
        dependencies={},
        primary_languages=['JavaScript', 'Python'],
        frontend={'framework': 'React'},
        backend={'framework': 'Express'},
        apis={'users': {'type': 'REST'}},
    )

    # Act
    result1 = generator._get_key_components(analysis1)
    result2 = generator._get_key_components(analysis2)

    # Assert
    assert 'Frontend' in result1
    assert len(result1) == 1

    # Check if all components are in the result
    assert 'Frontend' in result2
    assert 'Backend' in result2
    assert 'API' in result2
    assert len(result2) == 3


@pytest.mark.asyncio
async def test_generate_content():
    """Test _generate_content method with different document types."""
    # Arrange
    generator = DocumentGenerator()

    # Create document spec for README with Architecture section
    doc_spec = DocumentSpec(
        name='README.md',
        type='README',
        template='README',
        sections=[
            DocumentSection(title='Overview', content='Project overview', level=1, message=None),
            DocumentSection(
                title='Architecture', content='', level=1, message=None
            ),  # For diagram
            DocumentSection(title='Installation', content='How to install', level=1, message=None),
        ],
    )

    # Create analysis
    analysis = ProjectAnalysis(
        project_type='Web Application',
        features=['Feature 1'],
        file_structure={'root': ['/path/to/project']},
        dependencies={},
        primary_languages=['JavaScript'],
        frontend={'framework': 'React'},
        apis=None,
        backend=None,
        has_infrastructure_as_code=True,
    )

    # Create context
    context = DocumentationContext(
        project_name='test-project',
        working_dir='/path/to/project',
        repomix_path='/path/to/project/generated-docs',
        status='initialized',
        current_step='analysis',
        analysis_result=analysis,
    )

    # Act
    content = await generator._generate_content(doc_spec, context)

    # Assert
    assert '# Overview' in content
    assert 'Project overview' in content
    assert '# Architecture' in content
    assert '# Installation' in content
    assert 'How to install' in content

    # Architecture diagram placeholder should be in the content
    # The text is in the _generate_diagram_placeholder method
    assert 'AWS Architecture' in content
    assert 'placeholder' in content.lower()


def test_generate_diagram_placeholder():
    """Test _generate_diagram_placeholder method with different diagram types."""
    # Arrange
    generator = DocumentGenerator()

    # Create analysis with infrastructure as code
    analysis = ProjectAnalysis(
        project_type='Web Application',
        features=['Feature 1'],
        file_structure={'root': ['/path']},
        dependencies={},
        primary_languages=['JavaScript'],
        frontend={'framework': 'React'},
        backend={'framework': 'Express', 'database': 'MongoDB'},
        apis=None,
        has_infrastructure_as_code=True,
    )

    # Act
    arch_placeholder = generator._generate_diagram_placeholder('architecture', analysis)
    overview_placeholder = generator._generate_diagram_placeholder('overview', analysis)
    dataflow_placeholder = generator._generate_diagram_placeholder('dataflow', analysis)

    # Assert
    assert 'AWS Architecture' in arch_placeholder
    assert 'System Architecture' in overview_placeholder
    assert 'Data Flow Diagram' in dataflow_placeholder
