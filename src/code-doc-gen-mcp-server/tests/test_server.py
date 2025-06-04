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
"""Tests for the code-doc-gen MCP Server."""

import pytest
from awslabs.code_doc_gen_mcp_server.server import (
    _analyze_project_structure,
    create_context,
    create_documentation_context,
    generate_documentation,
    plan_documentation,
    prepare_repository,
)
from awslabs.code_doc_gen_mcp_server.utils.models import (
    DocStructure,
    DocumentationContext,
    DocumentationPlan,
    GeneratedDocument,
    ProjectAnalysis,
)
from pathlib import Path
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
@patch('awslabs.code_doc_gen_mcp_server.server.RepomixManager')
async def test_prepare_repository(mock_repomix_manager):
    """Test the prepare_repository function correctly processes the repository and returns a ProjectAnalysis."""
    # Arrange
    mock_instance = mock_repomix_manager.return_value
    # Create an async mock that can be awaited
    mock_prepare = AsyncMock()
    mock_prepare.return_value = {
        'project_info': {'name': 'test-project', 'path': '/path/to/repo'},
        'directory_structure': 'bin/\n  app.ts\nlib/\n  stack.ts',
    }
    mock_instance.prepare_repository = mock_prepare

    mock_analyze = AsyncMock()
    mock_analyze.return_value = {
        'project_info': {'name': 'test-project', 'path': '/path/to/repo'},
        'metadata': {'key': 'value'},
        'output_dir': '/path/to/repo/generated-docs',
        'directory_structure': 'bin/\n  app.ts\nlib/\n  stack.ts',
    }

    with patch('awslabs.code_doc_gen_mcp_server.server._analyze_project_structure', mock_analyze):
        # Act
        test_project_path = '/path/to/repo'
        ctx = AsyncMock()
        result = await prepare_repository(test_project_path, ctx)

        # Assert
        assert result.project_type == ''  # Should be empty for Cline to fill
        assert result.features == []  # Should be empty for Cline to fill
        assert result.file_structure['root'] == [test_project_path]
        assert result.file_structure['directory_structure'] == 'bin/\n  app.ts\nlib/\n  stack.ts'
        # Fix warning by using assert_called_once_with instead of called_once_with
        mock_instance.prepare_repository.assert_called_once_with(
            test_project_path, Path(test_project_path) / 'generated-docs', ctx
        )


@pytest.mark.asyncio
async def test_analyze_project_structure():
    """Test the _analyze_project_structure function correctly processes raw analysis data."""
    # Arrange
    raw_analysis = {
        'project_info': {'name': 'test-project', 'path': '/path/to/repo'},
        'directory_structure': 'bin/\n  app.ts\nlib/\n  stack.ts',
        'metadata': {'key': 'value'},
    }
    docs_dir = Path('/path/to/repo/generated-docs')
    ctx = AsyncMock()

    # Act
    result = await _analyze_project_structure(raw_analysis, docs_dir, ctx)

    # Assert
    assert result['project_info'] == {'name': 'test-project', 'path': '/path/to/repo'}
    assert result['metadata'] == {'key': 'value'}
    assert result['output_dir'] == str(docs_dir)
    assert result['directory_structure'] == 'bin/\n  app.ts\nlib/\n  stack.ts'


def test_create_documentation_context():
    """Test the create_documentation_context function creates a proper context object."""
    # Arrange
    project_root = '/path/to/repo'
    analysis = ProjectAnalysis(
        project_type='Web Application',
        features=['Feature 1', 'Feature 2'],
        file_structure={'root': ['/path/to/repo']},
        dependencies={'react': '^18.2.0'},
        primary_languages=['JavaScript', 'TypeScript'],
        apis=None,
        backend=None,
        frontend=None,
    )

    # Act
    result = create_documentation_context(project_root, analysis)

    # Assert
    assert isinstance(result, DocumentationContext)
    assert result.project_name == Path(project_root).name
    assert result.working_dir == project_root
    assert result.repomix_path == f'{project_root}/generated-docs'
    assert result.analysis_result == analysis


@pytest.mark.asyncio
async def test_create_context():
    """Test the create_context function properly wraps create_documentation_context."""
    # Arrange
    project_root = '/path/to/repo'
    analysis = ProjectAnalysis(
        project_type='Web Application',
        features=['Feature 1', 'Feature 2'],
        file_structure={'root': ['/path/to/repo']},
        dependencies={'react': '^18.2.0'},
        primary_languages=['JavaScript', 'TypeScript'],
        apis=None,
        backend=None,
        frontend=None,
    )
    ctx = AsyncMock()

    # Act
    with patch(
        'awslabs.code_doc_gen_mcp_server.server.create_documentation_context'
    ) as mock_create:
        mock_create.return_value = DocumentationContext(
            project_name='test-project',
            working_dir=project_root,
            repomix_path=f'{project_root}/generated-docs',
            status='initialized',
            current_step='analysis',
            analysis_result=analysis,
        )
        result = await create_context(project_root, analysis, ctx)

    # Assert
    assert isinstance(result, DocumentationContext)
    assert result.analysis_result == analysis


@pytest.mark.asyncio
@patch('awslabs.code_doc_gen_mcp_server.server.get_template_for_file')
@patch('awslabs.code_doc_gen_mcp_server.server.create_doc_from_template')
async def test_plan_documentation(mock_create_doc, mock_get_template):
    """Test the plan_documentation function creates the right plan based on analysis."""
    # Arrange
    from awslabs.code_doc_gen_mcp_server.utils.models import DocumentSection, DocumentSpec

    # Create proper DocumentSpec objects instead of MagicMock
    mock_get_template.side_effect = lambda name: name.upper().replace('.MD', '')
    mock_create_doc.side_effect = lambda template, name: DocumentSpec(
        name=name,
        type=template,
        template=template,
        sections=[
            DocumentSection(
                title=f'{template} Section', content='', level=1, message=f'{template} message'
            )
        ],
    )

    ctx = AsyncMock()
    doc_context = DocumentationContext(
        project_name='test-project',
        working_dir='/path/to/repo',
        repomix_path='/path/to/repo/generated-docs',
        status='initialized',
        current_step='analysis',
        analysis_result=ProjectAnalysis(
            project_type='Web Application',
            features=['Feature 1', 'Feature 2'],
            file_structure={'root': ['/path/to/repo'], 'backend': ['src/api']},
            dependencies={'react': '^18.2.0'},
            primary_languages=['JavaScript', 'TypeScript'],
            backend={'framework': 'Express'},
            frontend={'framework': 'React'},
            apis={
                'endpoints': {'paths': ['/api/users']}
            },  # Fixed: apis should be Dict[str, Dict[str, Any]]
        ),
    )

    # Act
    result = await plan_documentation(doc_context, ctx)

    # Assert
    assert isinstance(result, DocumentationPlan)
    assert result.structure.root_doc == 'README.md'
    assert 'README.md' in result.structure.doc_tree['root']
    assert 'BACKEND.md' in result.structure.doc_tree['root']
    assert 'API.md' in result.structure.doc_tree['root']
    assert len(result.docs_outline) >= 3  # At minimum README, BACKEND, and API docs


@pytest.mark.asyncio
@patch('awslabs.code_doc_gen_mcp_server.server.DocumentGenerator')
async def test_generate_documentation(mock_doc_generator_class):
    """Test the generate_documentation function properly delegates to DocumentGenerator."""
    # Arrange
    mock_doc_generator = mock_doc_generator_class.return_value
    mock_generator_docs = AsyncMock()
    mock_generator_docs.return_value = [
        '/path/to/repo/generated-docs/README.md',
        '/path/to/repo/generated-docs/BACKEND.md',
    ]
    mock_doc_generator.generate_docs = mock_generator_docs

    # Create proper DocumentSpec objects instead of MagicMock
    from awslabs.code_doc_gen_mcp_server.utils.models import DocumentSection, DocumentSpec

    plan = DocumentationPlan(
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
                        title='Overview', content='', level=1, message='Overview section'
                    )
                ],
            ),
            DocumentSpec(
                name='BACKEND.md',
                type='BACKEND',
                template='BACKEND',
                sections=[
                    DocumentSection(
                        title='Backend', content='', level=1, message='Backend section'
                    )
                ],
            ),
        ],
    )

    doc_context = DocumentationContext(
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
            apis=None,
            backend=None,
            frontend=None,
        ),
    )

    ctx = AsyncMock()

    # Act
    result = await generate_documentation(plan, doc_context, ctx)

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], GeneratedDocument)
    assert result[0].path == '/path/to/repo/generated-docs/README.md'
    assert result[0].type == 'readme'
    assert result[1].path == '/path/to/repo/generated-docs/BACKEND.md'
    assert result[1].type == 'docs'
    # Fix warning by using assert_called_once_with instead of called_once_with
    mock_doc_generator.generate_docs.assert_called_once_with(plan, doc_context)
