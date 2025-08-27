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

"""Tests for workflow linting functionality."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.workflow_linting import (
    WorkflowLinter,
    check_linting_dependencies,
    lint_workflow_bundle,
    lint_workflow_definition,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestWorkflowLinter:
    """Test cases for WorkflowLinter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.linter = WorkflowLinter()

    def test_init(self):
        """Test WorkflowLinter initialization."""
        assert self.linter.supported_formats == ['wdl', 'cwl']

    @pytest.mark.asyncio
    async def test_lint_workflow_unsupported_format(self):
        """Test linting with unsupported workflow format."""
        result = await self.linter.lint_workflow(
            workflow_content='test content', workflow_format='nextflow'
        )

        assert result['status'] == 'error'
        assert 'Unsupported workflow format' in result['message']

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_linting.WDL')
    async def test_lint_wdl_success(self, mock_wdl):
        """Test successful WDL linting."""
        # Mock WDL document
        mock_doc = MagicMock()
        mock_workflow = MagicMock()
        mock_workflow.available_inputs = ['input1']
        mock_workflow.outputs = ['output1']
        mock_doc.workflow = mock_workflow
        mock_doc.tasks = []

        mock_wdl.load.return_value = mock_doc

        result = await self.linter._lint_wdl('workflow test { input: String x }', 'test.wdl')

        assert result['status'] == 'success'
        assert result['format'] == 'wdl'
        assert result['valid'] is True
        assert result['linter'] == 'miniwdl'
        assert 'summary' in result

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_linting.WDL')
    async def test_lint_wdl_validation_error(self, mock_wdl):
        """Test WDL linting with validation errors."""
        from unittest.mock import MagicMock

        # Create a mock validation error
        mock_error = MagicMock()
        mock_error.__str__ = lambda: 'Validation error'
        mock_error.pos = {'filename': 'test.wdl', 'line': 1, 'column': 5}

        validation_error = Exception('Validation failed')
        validation_error.errors = [mock_error]

        mock_wdl.load.side_effect = validation_error
        mock_wdl.Error.ValidationError = Exception

        result = await self.linter._lint_wdl('invalid wdl', 'test.wdl')

        assert result['status'] == 'error'
        assert result['format'] == 'wdl'

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_linting.LoadingContext')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_linting.cwltool')
    async def test_lint_cwl_success(self, mock_cwltool, mock_loading_context):
        """Test successful CWL linting."""
        # Mock CWL tool
        mock_tool = MagicMock()
        mock_tool.tool = {
            'class': 'Workflow',
            'inputs': ['input1'],
            'outputs': ['output1'],
            'steps': {'step1': {'run': 'tool.cwl'}},
        }

        mock_cwltool.load_tool.load_tool.return_value = mock_tool
        mock_loading_context.return_value = MagicMock()

        result = await self.linter._lint_cwl('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

        assert result['status'] == 'success'
        assert result['format'] == 'cwl'
        assert result['valid'] is True
        assert result['linter'] == 'cwltool'
        assert 'summary' in result


class TestLintingTools:
    """Test cases for linting tool functions."""

    @pytest.mark.asyncio
    async def test_lint_workflow_definition(self):
        """Test lint_workflow_definition function."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {'status': 'success', 'format': 'wdl', 'valid': True}

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='workflow test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'wdl'
            mock_lint.assert_called_once_with(
                workflow_content='workflow test {}', workflow_format='wdl', filename='test.wdl'
            )

    @pytest.mark.asyncio
    async def test_check_linting_dependencies(self):
        """Test dependency check returns version information."""
        ctx = AsyncMock()

        with (
            patch('awslabs.aws_healthomics_mcp_server.tools.workflow_linting.WDL') as mock_wdl,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.cwltool'
            ) as mock_cwltool,
        ):
            mock_wdl.__version__ = '1.0.0'
            mock_cwltool.__version__ = '3.0.0'

            result = await check_linting_dependencies(ctx)

            assert result['status'] == 'success'
            assert result['dependencies']['miniwdl']['available'] is True
            assert result['dependencies']['cwltool']['available'] is True
            assert result['summary']['all_available'] is True
            assert result['summary']['missing'] == 0

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_wdl(self):
        """Test WDL bundle linting functionality."""
        ctx = AsyncMock()

        workflow_files = {
            'main.wdl': """version 1.0
import "tasks.wdl" as tasks
workflow Test { call tasks.TestTask }""",
            'tasks.wdl': """version 1.0
task TestTask { command { echo "test" } output { String result = stdout() } }""",
        }

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'main_file': 'main.wdl',
                'files_processed': ['main.wdl', 'tasks.wdl'],
                'valid': True,
                'summary': {'files_count': 2},
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'wdl'
            assert result['main_file'] == 'main.wdl'
            assert len(result['files_processed']) == 2
            mock_lint.assert_called_once_with(
                workflow_files=workflow_files, workflow_format='wdl', main_workflow_file='main.wdl'
            )

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_missing_main_file(self):
        """Test bundle linting with missing main file."""
        ctx = AsyncMock()

        workflow_files = {'tasks.wdl': 'version 1.0\ntask Test {}'}

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'wdl',
                'message': 'Main workflow file "main.wdl" not found in provided files',
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'error'
            assert 'not found' in result['message']
