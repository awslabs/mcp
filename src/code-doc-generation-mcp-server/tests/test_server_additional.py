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
"""Additional tests for server.py to improve test coverage."""

import pytest
import os
import tempfile
from pathlib import Path
from awslabs.code_doc_generation_mcp_server.server import (
    generate_documentation,
    plan_documentation,
    prepare_repository,
)
from awslabs.code_doc_generation_mcp_server.utils.models import (
    DocStructure,
    DocumentationContext,
    DocumentationPlan,
    DocumentSection,
    DocumentSpec,
    GeneratedDocument,
    ProjectAnalysis,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_plan_documentation_with_minimal_info():
    """Test the plan_documentation function with minimal project information."""
    # Arrange
    ctx = MagicMock()
    doc_context = DocumentationContext(
        project_name="minimal-project",
        working_dir="/path/to/repo",
        repomix_path="/path/to/repo/generated-docs",
        analysis_result=ProjectAnalysis(
            project_type="CLI Tool",
            features=["Feature 1"],
            file_structure={"root": ["/path/to/repo"]},
            dependencies={"package": "1.0.0"},
            primary_languages=["Python"],
        ),
    )

    # Act
    result = await plan_documentation(doc_context, ctx)

    # Assert
    assert isinstance(result, DocumentationPlan)
    assert "README.md" in result.structure.doc_tree["root"]
    assert len(result.docs_outline) >= 1  # At minimum README doc
    ctx.info.assert_called()


@pytest.mark.asyncio
async def test_plan_documentation_with_infrastructure():
    """Test the plan_documentation function with infrastructure components."""
    # Arrange
    ctx = MagicMock()
    doc_context = DocumentationContext(
        project_name="infra-project",
        working_dir="/path/to/repo",
        repomix_path="/path/to/repo/generated-docs",
        analysis_result=ProjectAnalysis(
            project_type="Infrastructure",
            features=["Feature 1"],
            file_structure={
                "root": ["/path/to/repo"],
                "infrastructure": ["src/cdk"],
                "deploy": ["scripts/deploy.sh"],
            },
            dependencies={"aws-cdk-lib": "^2.0.0"},
            primary_languages=["TypeScript"],
            has_infrastructure_as_code=True,
        ),
    )

    # Act
    result = await plan_documentation(doc_context, ctx)

    # Assert
    assert isinstance(result, DocumentationPlan)
    assert "README.md" in result.structure.doc_tree["root"]
    assert "DEPLOYMENT_GUIDE.md" in result.structure.doc_tree["root"]
    assert len(result.docs_outline) >= 2
    ctx.info.assert_called()


@pytest.mark.asyncio
@patch("awslabs.code_doc_generation_mcp_server.server.DocumentGenerator")
async def test_generate_documentation_with_error(mock_doc_generator_class):
    """Test generate_documentation handles errors gracefully."""
    # Arrange
    mock_doc_generator = mock_doc_generator_class.return_value
    mock_generator_docs = AsyncMock()
    mock_generator_docs.side_effect = Exception("Test exception")
    mock_doc_generator.generate_docs = mock_generator_docs

    plan = DocumentationPlan(
        structure=DocStructure(root_doc="README.md", doc_tree={"root": ["README.md"]}),
        docs_outline=[
            DocumentSpec(
                name="README.md",
                type="README",
                template="README",
                sections=[DocumentSection(title="Overview", content="", level=1)],
            )
        ],
    )

    doc_context = DocumentationContext(
        project_name="test-project",
        working_dir="/path/to/repo",
        repomix_path="/path/to/repo/generated-docs",
        analysis_result=ProjectAnalysis(
            project_type="Web Application",
            features=["Feature 1"],
            file_structure={"root": ["/path/to/repo"]},
            dependencies={"react": "^18.2.0"},
            primary_languages=["JavaScript"],
        ),
    )

    ctx = MagicMock()

    # Act & Assert
    with pytest.raises(RuntimeError):
        await generate_documentation(plan, doc_context, ctx)
    
    # Verify error was logged
    ctx.error.assert_called()


@pytest.mark.asyncio
@patch("awslabs.code_doc_generation_mcp_server.utils.models.DocStructure")
async def test_plan_documentation_edge_cases(mock_doc_structure):
    """Test plan_documentation with edge case inputs."""
    # Arrange
    ctx = MagicMock()
    
    # Test with empty features list
    doc_context1 = DocumentationContext(
        project_name="empty-features",
        working_dir="/path/to/repo",
        repomix_path="/path/to/repo/generated-docs",
        analysis_result=ProjectAnalysis(
            project_type="CLI Tool",
            features=[],  # Empty features list
            file_structure={"root": ["/path/to/repo"]},
            dependencies={},  # Empty dependencies
            primary_languages=["Python"],
        ),
    )
    
    # Act
    result1 = await plan_documentation(doc_context1, ctx)
    
    # Assert
    assert isinstance(result1, DocumentationPlan)
    assert "README.md" in result1.structure.doc_tree["root"]
    
    # Test with all optional components
    doc_context2 = DocumentationContext(
        project_name="full-project",
        working_dir="/path/to/repo",
        repomix_path="/path/to/repo/generated-docs",
        analysis_result=ProjectAnalysis(
            project_type="Full Stack Application",
            features=["Authentication", "Data Processing"],
            file_structure={"root": ["/path/to/repo"]},
            dependencies={"react": "^18.2.0", "express": "^4.18.2"},
            primary_languages=["JavaScript", "TypeScript"],
            backend={"framework": "Express", "database": "MongoDB"},
            frontend={"framework": "React", "state_management": "Redux"},
            apis={"endpoints": {"paths": ["/api/users", "/api/posts"]}},
        ),
    )
    
    # Act
    result2 = await plan_documentation(doc_context2, ctx)
    
    # Assert
    assert "README.md" in result2.structure.doc_tree["root"]
    assert "API.md" in result2.structure.doc_tree["root"]
    assert "FRONTEND.md" in result2.structure.doc_tree["root"]
    assert "BACKEND.md" in result2.structure.doc_tree["root"]
    assert len(result2.docs_outline) >= 4


@pytest.mark.asyncio
@patch("awslabs.code_doc_generation_mcp_server.server.RepomixManager")
async def test_prepare_repository_with_empty_structure(mock_repomix_manager):
    """Test prepare_repository handles empty directory structure."""
    # Arrange
    mock_instance = mock_repomix_manager.return_value
    mock_prepare = AsyncMock()
    mock_prepare.return_value = {
        "project_info": {"name": "test-project", "path": "/path/to/repo"},
        # Empty directory_structure
        "directory_structure": "",
    }
    mock_instance.prepare_repository = mock_prepare

    mock_analyze = AsyncMock()
    mock_analyze.return_value = {
        "project_info": {"name": "test-project", "path": "/path/to/repo"},
        "metadata": {"key": "value"},
        "output_dir": "/path/to/repo/generated-docs",
        # Empty directory_structure
        "directory_structure": "",
    }

    with patch(
        "awslabs.code_doc_generation_mcp_server.server._analyze_project_structure", mock_analyze
    ):
        # Act
        test_project_path = "/path/to/repo"
        ctx = MagicMock()
        result = await prepare_repository(test_project_path, ctx)

        # Assert
        assert result.project_type == ""
        assert result.features == []
        assert result.file_structure["root"] == [test_project_path]
        assert result.file_structure["directory_structure"] == ""
