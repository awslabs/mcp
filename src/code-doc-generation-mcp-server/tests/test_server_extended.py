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
"""Additional tests for the code-doc-generation MCP Server to improve coverage."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

from awslabs.code_doc_generation_mcp_server.server import (
    _analyze_project_structure,
    create_context,
    plan_documentation,
    generate_documentation,
    main,
)
from awslabs.code_doc_generation_mcp_server.utils.models import (
    DocStructure,
    DocumentationContext,
    DocumentationPlan,
    DocumentSection,
    DocumentSpec,
    ProjectAnalysis,
)


@pytest.mark.asyncio
async def test_analyze_project_structure_with_fallbacks():
    """Test _analyze_project_structure with fallbacks when directory_structure is not found."""
    # Arrange
    # Case 1: directory_structure in file_structure
    raw_analysis = {
        'project_info': {'name': 'test-project', 'path': '/path/to/repo'},
        'directory_structure': None,  # Not found
        'file_structure': {
            'directory_structure': 'bin/\n  app.ts\nlib/\n  stack.ts'
        },
        'metadata': {'key': 'value'},
    }
    docs_dir = Path('/path/to/repo/generated-docs')
    ctx = AsyncMock()

    # Act
    result = await _analyze_project_structure(raw_analysis, docs_dir, ctx)

    # Assert
    assert result['directory_structure'] == 'bin/\n  app.ts\nlib/\n  stack.ts'
    assert result['metadata'] == {'key': 'value'}
    assert result['output_dir'] == str(docs_dir)

    # Case 2: No directory_structure found anywhere
    raw_analysis = {
        'project_info': {'name': 'test-project', 'path': '/path/to/repo'},
        'metadata': {'key': 'value'},
    }

    # Act
    result = await _analyze_project_structure(raw_analysis, docs_dir, ctx)

    # Assert
    assert result['directory_structure'] is None
    assert result['metadata'] == {'key': 'value'}
    assert result['output_dir'] == str(docs_dir)


@pytest.mark.asyncio
@patch('awslabs.code_doc_generation_mcp_server.server.create_documentation_context')
async def test_create_context_with_error_logging(mock_create_doc_ctx):
    """Test create_context error handling and logging."""
    # Arrange
    mock_create_doc_ctx.side_effect = Exception("Test exception")
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

    # Act & Assert
    with pytest.raises(Exception):
        await create_context(project_root, analysis, ctx)
    ctx.error.assert_called_once()  # Error should be logged


@pytest.mark.asyncio
@patch('awslabs.code_doc_generation_mcp_server.server.get_template_for_file')
@patch('awslabs.code_doc_generation_mcp_server.server.create_doc_from_template')
async def test_plan_documentation_with_infrastructure(mock_create_doc, mock_get_template):
    """Test plan_documentation adds DEPLOYMENT_GUIDE.md for projects with infrastructure as code."""
    # Arrange
    from awslabs.code_doc_generation_mcp_server.utils.models import DocumentSection, DocumentSpec

    # Setup template mocking
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
    
    # Create a context with infrastructure as code flag set to True
    doc_context = DocumentationContext(
        project_name='test-project',
        working_dir='/path/to/repo',
        repomix_path='/path/to/repo/generated-docs',
        status='initialized',
        current_step='analysis',
        analysis_result=ProjectAnalysis(
            project_type='Infrastructure',
            features=['Feature 1', 'Feature 2'],
            file_structure={'root': ['/path/to/repo']},
            dependencies={'aws-cdk-lib': '^2.0.0'},
            primary_languages=['TypeScript'],
            has_infrastructure_as_code=True,  # This should trigger DEPLOYMENT_GUIDE.md
            apis=None,
            backend=None,
            frontend=None,
        ),
    )

    # Act
    result = await plan_documentation(doc_context, ctx)

    # Assert
    assert isinstance(result, DocumentationPlan)
    assert 'DEPLOYMENT_GUIDE.md' in result.structure.doc_tree['root']
    
    # Verify info logging occurred
    ctx.info.assert_called()


@pytest.mark.asyncio
async def test_plan_documentation_error_handling():
    """Test plan_documentation error handling."""
    # Arrange
    # Create a doc context that will raise an error during processing
    doc_context = DocumentationContext(
        project_name='test-project',
        working_dir='/path/to/repo',
        repomix_path='/path/to/repo/generated-docs',
        status='initialized',
        current_step='analysis',
        # Set analysis_result to None but reference it in a way that will raise an exception
        analysis_result=None,
    )
    
    ctx = AsyncMock()
    
    # Mock the needed_docs retrieval to force an error
    with patch('awslabs.code_doc_generation_mcp_server.server.get_template_for_file', 
               side_effect=Exception('Test error')):
        # Act & Assert
        with pytest.raises(Exception):
            await plan_documentation(doc_context, ctx)
        # Should have logged an error
        ctx.error.assert_called_once()


@pytest.mark.asyncio
@patch('awslabs.code_doc_generation_mcp_server.server.DocumentGenerator')
async def test_generate_documentation_with_all_doc_types(mock_doc_generator_class):
    """Test generate_documentation with all document types."""
    # Arrange
    mock_doc_generator = mock_doc_generator_class.return_value
    mock_generator_docs = AsyncMock()
    mock_generator_docs.return_value = [
        '/path/to/repo/generated-docs/README.md',
        '/path/to/repo/generated-docs/API.md',
        '/path/to/repo/generated-docs/BACKEND.md',
        '/path/to/repo/generated-docs/FRONTEND.md',
        '/path/to/repo/generated-docs/DEPLOYMENT_GUIDE.md',
    ]
    mock_doc_generator.generate_docs = mock_generator_docs

    # Create proper document specs with sections
    test_section = DocumentSection(title='Test Section', content='', level=1, message=None)
    
    # Create plan with proper document specs
    plan = DocumentationPlan(
        structure=DocStructure(
            root_doc='README.md',
            doc_tree={'root': [
                'README.md', 
                'API.md',
                'BACKEND.md', 
                'FRONTEND.md', 
                'DEPLOYMENT_GUIDE.md'
            ]}
        ),
        docs_outline=[
            DocumentSpec(name='README.md', type='README', template='README', sections=[test_section]),
            DocumentSpec(name='API.md', type='API', template='API', sections=[test_section]),
            DocumentSpec(name='BACKEND.md', type='BACKEND', template='BACKEND', sections=[test_section]),
            DocumentSpec(name='FRONTEND.md', type='FRONTEND', template='FRONTEND', sections=[test_section]),
            DocumentSpec(name='DEPLOYMENT_GUIDE.md', type='DEPLOYMENT', template='DEPLOYMENT', sections=[test_section]),
        ],
    )

    # Create context with all component types - fix apis format
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
            apis={'users': {'get': {'description': 'Get all users'}}},
            backend={'framework': 'Express'},
            frontend={'framework': 'React'},
            has_infrastructure_as_code=True,
        ),
    )

    ctx = AsyncMock()

    # Act
    result = await generate_documentation(plan, doc_context, ctx)

    # Assert
    assert len(result) == 5
    
    # Find API.md and check its message
    api_doc = next((doc for doc in result if doc.path.endswith('API.md')), None)
    assert api_doc is not None
    assert 'Document all API endpoints' in api_doc.message
    
    # Find FRONTEND.md and check its message
    frontend_doc = next((doc for doc in result if doc.path.endswith('FRONTEND.md')), None)
    assert frontend_doc is not None
    assert 'Document the frontend structure' in frontend_doc.message
    
    # Verify info messages were logged
    ctx.info.assert_called()


@pytest.mark.asyncio
@patch('awslabs.code_doc_generation_mcp_server.server.DocumentGenerator')
async def test_generate_documentation_error_handling(mock_doc_generator_class):
    """Test generate_documentation error handling."""
    # Arrange
    mock_doc_generator = mock_doc_generator_class.return_value
    mock_generator_docs = AsyncMock()
    mock_generator_docs.side_effect = Exception("Test exception")
    mock_doc_generator.generate_docs = mock_generator_docs

    # Create a simple plan
    test_section = DocumentSection(title='Test Section', content='', level=1, message=None)
    plan = DocumentationPlan(
        structure=DocStructure(root_doc='README.md', doc_tree={'root': ['README.md']}),
        docs_outline=[
            DocumentSpec(name='README.md', type='README', template='README', sections=[test_section]),
        ],
    )
    
    # Create a simple context
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
    
    # Create a mock context with reset_mock() to clear previous calls
    ctx = AsyncMock()
    ctx.error.reset_mock()  # Ensure no previous calls are counted

    # Act & Assert
    with pytest.raises(Exception):
        await generate_documentation(plan, doc_context, ctx)
    
    # Check that error was called with the exception message
    assert any(call_args[0][0] == 'Error in generate_documentation: Test exception' 
               for call_args in ctx.error.call_args_list)


@patch('awslabs.code_doc_generation_mcp_server.server.mcp')
def test_main_with_sse(mock_mcp):
    """Test main function with SSE transport."""
    # Arrange
    with patch('sys.argv', ['server.py', '--sse', '--port', '9999']):
        # Act
        main()

    # Assert
    assert mock_mcp.settings.port == 9999
    mock_mcp.run.assert_called_once_with(transport='sse')


@patch('awslabs.code_doc_generation_mcp_server.server.mcp')
def test_main_without_sse(mock_mcp):
    """Test main function without SSE transport."""
    # Arrange
    with patch('sys.argv', ['server.py']):
        # Act
        main()

    # Assert
    mock_mcp.run.assert_called_once_with()
