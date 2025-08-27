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

    @pytest.mark.asyncio
    async def test_lint_cwl_bundle_success(self):
        """Test successful CWL bundle linting with imports."""
        ctx = AsyncMock()

        workflow_files = {
            'main.cwl': """cwlVersion: v1.0
class: Workflow
requirements:
  - class: SubworkflowFeatureRequirement
inputs:
  input_file: File
outputs:
  output_file:
    type: File
    outputSource: process/output
steps:
  process:
    run: process.cwl
    in:
      input: input_file
    out: [output]""",
            'process.cwl': """cwlVersion: v1.0
class: CommandLineTool
inputs:
  input: File
outputs:
  output:
    type: File
    outputBinding:
      glob: "output.txt"
baseCommand: [echo, "test"]""",
        }

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'cwl',
                'main_file': 'main.cwl',
                'files_processed': ['main.cwl', 'process.cwl'],
                'valid': True,
                'summary': {'files_count': 2},
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='cwl',
                main_workflow_file='main.cwl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'cwl'
            assert len(result['files_processed']) == 2

    @pytest.mark.asyncio
    async def test_lint_cwl_bundle_validation_errors(self):
        """Test CWL bundle linting with validation errors."""
        ctx = AsyncMock()

        workflow_files = {
            'main.cwl': """cwlVersion: v1.0
class: Workflow
# Missing required inputs/outputs""",
            'process.cwl': """cwlVersion: v1.0
class: CommandLineTool
# Invalid structure""",
        }

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'cwl',
                'message': 'CWL validation failed',
                'errors': ['Missing required field: inputs', 'Missing required field: outputs'],
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='cwl',
                main_workflow_file='main.cwl',
            )

            assert result['status'] == 'error'
            assert 'validation failed' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_lint_cwl_bundle_missing_imports(self):
        """Test CWL bundle with missing import files."""
        ctx = AsyncMock()

        workflow_files = {
            'main.cwl': """cwlVersion: v1.0
class: Workflow
steps:
  process:
    run: missing_file.cwl"""
        }

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'cwl',
                'message': 'Import resolution failed: missing_file.cwl not found',
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='cwl',
                main_workflow_file='main.cwl',
            )

            assert result['status'] == 'error'
            assert 'missing_file.cwl' in result['message']

    @pytest.mark.asyncio
    async def test_lint_wdl_syntax_error(self):
        """Test WDL linting with syntax errors."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'wdl',
                'valid': False,
                'message': 'Syntax error at line 1',
                'errors': ['Expected workflow block'],
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='invalid wdl syntax {{{',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'error'
            assert result['valid'] is False

    @pytest.mark.asyncio
    async def test_lint_cwl_syntax_error(self):
        """Test CWL linting with syntax errors."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'cwl',
                'valid': False,
                'message': 'YAML syntax error',
                'errors': ['Invalid YAML structure'],
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='invalid: yaml: syntax: [[[',
                workflow_format='cwl',
                filename='test.cwl',
            )

            assert result['status'] == 'error'
            assert result['valid'] is False

    @pytest.mark.asyncio
    async def test_lint_wdl_missing_required_fields(self):
        """Test WDL without required workflow block."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'wdl',
                'valid': False,
                'message': 'Missing workflow block',
                'errors': ['WDL must contain a workflow block'],
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\ntask OnlyTask { command { echo "test" } }',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'error'
            assert 'workflow block' in result['message']

    @pytest.mark.asyncio
    async def test_lint_cwl_missing_required_fields(self):
        """Test CWL without required class/cwlVersion."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'cwl',
                'valid': False,
                'message': 'Missing required fields',
                'errors': ['Missing cwlVersion', 'Missing class'],
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='inputs:\n  test: string',
                workflow_format='cwl',
                filename='test.cwl',
            )

            assert result['status'] == 'error'
            assert 'required fields' in result['message']

    @pytest.mark.asyncio
    async def test_lint_bundle_missing_main_file_cwl(self):
        """Test CWL bundle linting with missing main file."""
        ctx = AsyncMock()

        workflow_files = {'helper.cwl': 'cwlVersion: v1.0\nclass: CommandLineTool'}

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'cwl',
                'message': 'Main workflow file "main.cwl" not found in provided files',
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='cwl',
                main_workflow_file='main.cwl',
            )

            assert result['status'] == 'error'
            assert 'not found' in result['message']

    @pytest.mark.asyncio
    async def test_lint_bundle_invalid_file_structure(self):
        """Test bundle linting with malformed directory structure."""
        ctx = AsyncMock()

        workflow_files = {}  # Empty files dict

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'wdl',
                'message': 'No workflow files provided',
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'error'
            assert 'No workflow files' in result['message']

    @pytest.mark.asyncio
    async def test_lint_bundle_circular_imports(self):
        """Test detection of circular import dependencies."""
        ctx = AsyncMock()

        workflow_files = {
            'main.wdl': 'version 1.0\nimport "task1.wdl"',
            'task1.wdl': 'version 1.0\nimport "task2.wdl"',
            'task2.wdl': 'version 1.0\nimport "main.wdl"',
        }

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'format': 'wdl',
                'message': 'Circular import detected',
                'errors': ['Circular dependency: main.wdl -> task1.wdl -> task2.wdl -> main.wdl'],
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'error'
            assert 'Circular' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_workflow_no_inputs_warning(self):
        """Test WDL workflow without inputs generates warning."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'valid': True,
                'warnings': ['Workflow has no inputs defined'],
                'summary': {'warnings_count': 1},
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test { output { String result = "test" } }',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'
            assert 'warnings' in result
            assert any('no inputs' in w for w in result['warnings'])

    @pytest.mark.asyncio
    async def test_wdl_workflow_no_outputs_warning(self):
        """Test WDL workflow without outputs generates warning."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'valid': True,
                'warnings': ['Workflow has no outputs defined'],
                'summary': {'warnings_count': 1},
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test { input { String x } }',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'
            assert 'warnings' in result
            assert any('no outputs' in w for w in result['warnings'])

    @pytest.mark.asyncio
    async def test_cwl_workflow_no_inputs_warning(self):
        """Test CWL workflow without inputs generates warning."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'cwl',
                'valid': True,
                'warnings': ['Workflow has no inputs defined'],
                'summary': {'warnings_count': 1},
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='cwlVersion: v1.0\nclass: Workflow\noutputs:\n  result: string',
                workflow_format='cwl',
                filename='test.cwl',
            )

            assert result['status'] == 'success'
            assert 'warnings' in result
            assert any('no inputs' in w for w in result['warnings'])

    @pytest.mark.asyncio
    async def test_cwl_workflow_no_outputs_warning(self):
        """Test CWL workflow without outputs generates warning."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'cwl',
                'valid': True,
                'warnings': ['Workflow has no outputs defined'],
                'summary': {'warnings_count': 1},
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='cwlVersion: v1.0\nclass: Workflow\ninputs:\n  test: string',
                workflow_format='cwl',
                filename='test.cwl',
            )

            assert result['status'] == 'success'
            assert 'warnings' in result
            assert any('no outputs' in w for w in result['warnings'])

    @pytest.mark.asyncio
    async def test_wdl_missing_runtime_requirements(self):
        """Test WDL tasks without runtime specifications."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'valid': True,
                'warnings': ['Task "TestTask" missing runtime requirements'],
                'summary': {'warnings_count': 1},
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\ntask TestTask { command { echo "test" } }',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'
            assert 'warnings' in result
            assert any('runtime requirements' in w for w in result['warnings'])

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_unsupported_format(self):
        """Test bundle linting with unsupported format."""
        ctx = AsyncMock()

        workflow_files = {'main.nf': 'nextflow workflow'}

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'message': 'Unsupported workflow format: nextflow',
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='nextflow',
                main_workflow_file='main.nf',
            )

            assert result['status'] == 'error'
            assert 'Unsupported' in result['message']

    @pytest.mark.asyncio
    @patch('tempfile.NamedTemporaryFile')
    async def test_lint_workflow_definition_file_io_error(self, mock_temp_file):
        """Test workflow definition linting with file I/O errors."""
        ctx = AsyncMock()
        mock_temp_file.side_effect = PermissionError('Permission denied')

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.side_effect = PermissionError('Permission denied')

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            # Should handle the error gracefully
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_wdl_event_loop_conflict(self):
        """Test WDL linting with event loop conflict."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.side_effect = RuntimeError('There is already a running event loop')

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'error'
            assert 'event loop' in result.get('message', '').lower()

    @pytest.mark.asyncio
    async def test_cwl_event_loop_conflict(self):
        """Test CWL linting with event loop conflict."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.side_effect = RuntimeError('There is already a running event loop')

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='cwlVersion: v1.0\nclass: Workflow',
                workflow_format='cwl',
                filename='test.cwl',
            )

            assert result['status'] == 'error'
            assert 'event loop' in result.get('message', '').lower()
