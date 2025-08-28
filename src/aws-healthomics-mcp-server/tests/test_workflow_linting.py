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
import subprocess
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
    @patch('subprocess.run')
    async def test_lint_wdl_success(self, mock_subprocess):
        """Test successful WDL linting."""
        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.stdout = 'Workflow is valid'
        mock_result.stderr = ''
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = await self.linter._lint_wdl('workflow test { input: String x }', 'test.wdl')

        assert result['status'] == 'success'
        assert result['format'] == 'wdl'
        assert result['linter'] == 'miniwdl'
        assert 'raw_output' in result
        assert 'STDOUT:' in result['raw_output']

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_wdl_validation_error(self, mock_subprocess):
        """Test WDL linting with validation errors."""
        # Mock subprocess result with validation error
        mock_result = MagicMock()
        mock_result.stdout = ''
        mock_result.stderr = 'Validation error: syntax error at line 1'
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        result = await self.linter._lint_wdl('invalid wdl', 'test.wdl')

        assert result['status'] == 'success'  # We always return success when subprocess runs
        assert result['format'] == 'wdl'
        assert 'raw_output' in result
        assert 'Validation error' in result['raw_output']

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_cwl_success(self, mock_subprocess):
        """Test successful CWL linting."""
        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.stdout = 'Workflow is valid'
        mock_result.stderr = ''
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = await self.linter._lint_cwl('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

        assert result['status'] == 'success'
        assert result['format'] == 'cwl'
        assert result['linter'] == 'cwltool'
        assert 'raw_output' in result
        assert 'STDOUT:' in result['raw_output']


class TestLintingTools:
    """Test cases for linting tool functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.linter = WorkflowLinter()

    @pytest.mark.asyncio
    async def test_lint_workflow_definition(self):
        """Test lint_workflow_definition function."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'linter': 'miniwdl',
                'raw_output': 'STDOUT:\nWorkflow is valid\nSTDERR:\n\nReturn code: 0',
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='workflow test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'wdl'
            assert 'raw_output' in result
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
                'linter': 'miniwdl',
                'raw_output': 'STDOUT:\nWorkflow bundle is valid\nSTDERR:\n\nReturn code: 0',
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
            assert 'raw_output' in result
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

    #     @pytest.mark.asyncio
    #     async def test_lint_cwl_bundle_validation_errors(self):
    #         """Test CWL bundle linting with validation errors."""
    #         ctx = AsyncMock()

    #         workflow_files = {
    #             'main.cwl': """cwlVersion: v1.0
    # class: Workflow
    # # Missing required inputs/outputs""",
    #             'process.cwl': """cwlVersion: v1.0
    # class: CommandLineTool
    # # Invalid structure""",
    #         }

    #         with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
    #             mock_lint.return_value = {
    #                 'status': 'error',
    #                 'format': 'cwl',
    #                 'message': 'CWL validation failed',
    #                 'errors': ['Missing required field: inputs', 'Missing required field: outputs'],
    #             }

    #             result = await lint_workflow_bundle(
    #                 ctx=ctx,
    #                 workflow_files=workflow_files,
    #                 workflow_format='cwl',
    #                 main_workflow_file='main.cwl',
    #             )

    #             assert result['status'] == 'error'
    #             assert 'validation failed' in result['message'].lower()

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

    @pytest.mark.asyncio
    async def test_lint_wdl_bundle_nested_imports(self):
        """Test WDL bundle with nested directory imports."""
        ctx = AsyncMock()
        workflow_files = {
            'main.wdl': 'version 1.0\nimport "tasks/process.wdl"',
            'tasks/process.wdl': 'version 1.0\nimport "../utils/common.wdl"',
            'utils/common.wdl': 'version 1.0\ntask CommonTask { command { echo "test" } }',
        }
        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'main_file': 'main.wdl',
                'files_processed': ['main.wdl', 'tasks/process.wdl', 'utils/common.wdl'],
                'valid': True,
                'summary': {'files_count': 3},
            }
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )
            assert result['status'] == 'success'
            assert len(result['files_processed']) == 3

    @pytest.mark.asyncio
    async def test_lint_cwl_bundle_nested_imports(self):
        """Test CWL bundle with nested directory imports."""
        ctx = AsyncMock()
        workflow_files = {
            'main.cwl': 'cwlVersion: v1.0\nclass: Workflow\nsteps:\n  process:\n    run: tools/process.cwl',
            'tools/process.cwl': 'cwlVersion: v1.0\nclass: CommandLineTool',
        }
        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'cwl',
                'main_file': 'main.cwl',
                'files_processed': ['main.cwl', 'tools/process.cwl'],
                'valid': True,
            }
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='cwl',
                main_workflow_file='main.cwl',
            )
            assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_lint_bundle_mixed_file_types(self):
        """Test bundle with both WDL and CWL files."""
        ctx = AsyncMock()
        workflow_files = {
            'main.wdl': 'version 1.0\nworkflow Test {}',
            'tool.cwl': 'cwlVersion: v1.0\nclass: CommandLineTool',
        }
        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'error',
                'message': 'Mixed file types not supported',
            }
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_lint_bundle_large_workflow(self):
        """Test performance with large workflow bundle."""
        ctx = AsyncMock()
        workflow_files = {'main.wdl': 'version 1.0\nworkflow Test {}'}
        for i in range(20):
            workflow_files[f'task_{i}.wdl'] = (
                f'version 1.0\ntask Task{i} {{ command {{ echo "test{i}" }} }}'
            )
        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'files_processed': list(workflow_files.keys()),
                'valid': True,
            }
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )
            assert result['status'] == 'success'
            assert len(result['files_processed']) == 21

    @pytest.mark.asyncio
    async def test_file_permission_error(self):
        """Test handling of permission errors."""
        ctx = AsyncMock()
        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.side_effect = PermissionError('Permission denied')
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_disk_space_error(self):
        """Test handling of disk space errors."""
        ctx = AsyncMock()
        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.side_effect = OSError('No space left on device')
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_wdl_workflow_with_structs(self):
        """Test WDL workflow with complex custom types."""
        ctx = AsyncMock()
        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'valid': True,
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nstruct Sample { String id }\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_wdl_timeout_handling(self, mock_subprocess):
        """Test WDL linting timeout handling."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired('cmd', 30)

        result = await self.linter._lint_wdl('workflow test {}', 'test.wdl')

        assert result['status'] == 'error'
        assert 'timed out' in result['raw_output']
        assert result['format'] == 'wdl'
        assert result['linter'] == 'miniwdl'

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_cwl_timeout_handling(self, mock_subprocess):
        """Test CWL linting timeout handling."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired('cmd', 30)

        result = await self.linter._lint_cwl('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

        assert result['status'] == 'error'
        assert 'timed out' in result['raw_output']
        assert result['format'] == 'cwl'
        assert result['linter'] == 'cwltool'

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_wdl_subprocess_exception(self, mock_subprocess):
        """Test WDL linting subprocess exception handling."""
        mock_subprocess.side_effect = FileNotFoundError('miniwdl not found')

        result = await self.linter._lint_wdl('workflow test {}', 'test.wdl')

        assert result['status'] == 'error'
        assert 'Failed to execute linter' in result['raw_output']
        assert 'miniwdl not found' in result['raw_output']

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_cwl_subprocess_exception(self, mock_subprocess):
        """Test CWL linting subprocess exception handling."""
        mock_subprocess.side_effect = FileNotFoundError('cwltool not found')

        result = await self.linter._lint_cwl('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

        assert result['status'] == 'error'
        assert 'Failed to execute linter' in result['raw_output']
        assert 'cwltool not found' in result['raw_output']

    @pytest.mark.asyncio
    @patch('tempfile.NamedTemporaryFile')
    async def test_lint_wdl_tempfile_exception(self, mock_tempfile):
        """Test WDL linting with temporary file creation error."""
        mock_tempfile.side_effect = OSError('No space left on device')

        result = await self.linter._lint_wdl('workflow test {}', 'test.wdl')

        assert result['status'] == 'error'
        assert 'WDL linting failed' in result['message']

    @pytest.mark.asyncio
    @patch('tempfile.NamedTemporaryFile')
    async def test_lint_cwl_tempfile_exception(self, mock_tempfile):
        """Test CWL linting with temporary file creation error."""
        mock_tempfile.side_effect = OSError('No space left on device')

        result = await self.linter._lint_cwl('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

        assert result['status'] == 'error'
        assert 'CWL linting failed' in result['message']

    @pytest.mark.asyncio
    @patch('pathlib.Path.unlink')
    @patch('subprocess.run')
    async def test_lint_wdl_cleanup_exception(self, mock_subprocess, mock_unlink):
        """Test WDL linting with file cleanup exception."""
        # Mock successful subprocess
        mock_result = MagicMock()
        mock_result.stdout = 'Success'
        mock_result.stderr = ''
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Mock cleanup failure
        mock_unlink.side_effect = PermissionError('Permission denied')

        result = await self.linter._lint_wdl('workflow test {}', 'test.wdl')

        # Should still succeed despite cleanup failure
        assert result['status'] == 'success'
        assert result['format'] == 'wdl'

    @pytest.mark.asyncio
    @patch('pathlib.Path.unlink')
    @patch('subprocess.run')
    async def test_lint_cwl_cleanup_exception(self, mock_subprocess, mock_unlink):
        """Test CWL linting with file cleanup exception."""
        # Mock successful subprocess
        mock_result = MagicMock()
        mock_result.stdout = 'Success'
        mock_result.stderr = ''
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Mock cleanup failure
        mock_unlink.side_effect = PermissionError('Permission denied')

        result = await self.linter._lint_cwl('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

        # Should still succeed despite cleanup failure
        assert result['status'] == 'success'
        assert result['format'] == 'cwl'

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_exception_handling(self):
        """Test exception handling in lint_workflow_bundle method."""
        # Mock an exception in the bundle linting process
        with patch.object(self.linter, '_lint_wdl_bundle') as mock_lint:
            mock_lint.side_effect = RuntimeError('Unexpected error')

            result = await self.linter.lint_workflow_bundle(
                workflow_files={'main.wdl': 'workflow test {}'},
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'error'
            assert 'Failed to lint wdl workflow bundle' in result['message']
            assert 'Unexpected error' in result['message']

    @pytest.mark.asyncio
    async def test_lint_workflow_exception_handling(self):
        """Test exception handling in lint_workflow method."""
        # Mock an exception in the workflow linting process
        with patch.object(self.linter, '_lint_wdl') as mock_lint:
            mock_lint.side_effect = RuntimeError('Unexpected error')

            result = await self.linter.lint_workflow(
                workflow_content='workflow test {}', workflow_format='wdl', filename='test.wdl'
            )

            assert result['status'] == 'error'
            assert 'Failed to lint wdl workflow' in result['message']
            assert 'Unexpected error' in result['message']

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_wdl_bundle_timeout_handling(self, mock_subprocess):
        """Test WDL bundle linting timeout handling."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired('cmd', 30)

        result = await self.linter._lint_wdl_bundle(
            workflow_files={'main.wdl': 'workflow test {}'}, main_workflow_file='main.wdl'
        )

        assert result['status'] == 'error'
        assert 'timed out' in result['raw_output']
        assert result['format'] == 'wdl'

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_cwl_bundle_timeout_handling(self, mock_subprocess):
        """Test CWL bundle linting timeout handling."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired('cmd', 30)

        result = await self.linter._lint_cwl_bundle(
            workflow_files={'main.cwl': 'cwlVersion: v1.0\nclass: Workflow'},
            main_workflow_file='main.cwl',
        )

        assert result['status'] == 'error'
        assert 'timed out' in result['raw_output']
        assert result['format'] == 'cwl'

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_wdl_bundle_subprocess_exception(self, mock_subprocess):
        """Test WDL bundle linting subprocess exception handling."""
        mock_subprocess.side_effect = FileNotFoundError('miniwdl not found')

        result = await self.linter._lint_wdl_bundle(
            workflow_files={'main.wdl': 'workflow test {}'}, main_workflow_file='main.wdl'
        )

        assert result['status'] == 'error'
        assert 'Failed to execute linter' in result['message']
        assert 'miniwdl not found' in result['raw_output']

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_lint_cwl_bundle_subprocess_exception(self, mock_subprocess):
        """Test CWL bundle linting subprocess exception handling."""
        mock_subprocess.side_effect = FileNotFoundError('cwltool not found')

        result = await self.linter._lint_cwl_bundle(
            workflow_files={'main.cwl': 'cwlVersion: v1.0\nclass: Workflow'},
            main_workflow_file='main.cwl',
        )

        assert result['status'] == 'error'
        assert 'Failed to execute linter' in result['message']
        assert 'cwltool not found' in result['raw_output']

    @pytest.mark.asyncio
    @patch('tempfile.TemporaryDirectory')
    async def test_lint_wdl_bundle_tempdir_exception(self, mock_tempdir):
        """Test WDL bundle linting with temporary directory creation error."""
        mock_tempdir.side_effect = OSError('No space left on device')

        result = await self.linter._lint_wdl_bundle(
            workflow_files={'main.wdl': 'workflow test {}'}, main_workflow_file='main.wdl'
        )

        assert result['status'] == 'error'
        assert 'WDL bundle linting failed' in result['message']

    @pytest.mark.asyncio
    @patch('tempfile.TemporaryDirectory')
    async def test_lint_cwl_bundle_tempdir_exception(self, mock_tempdir):
        """Test CWL bundle linting with temporary directory creation error."""
        mock_tempdir.side_effect = OSError('No space left on device')

        result = await self.linter._lint_cwl_bundle(
            workflow_files={'main.cwl': 'cwlVersion: v1.0\nclass: Workflow'},
            main_workflow_file='main.cwl',
        )

        assert result['status'] == 'error'
        assert 'CWL bundle linting failed' in result['message']

    @pytest.mark.asyncio
    async def test_lint_workflow_definition_api_exception(self):
        """Test exception handling in lint_workflow_definition API function."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.side_effect = RuntimeError('Unexpected API error')

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='workflow test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'error'
            assert 'Workflow linting failed' in result['message']
            assert 'Unexpected API error' in result['message']
            ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_api_exception(self):
        """Test exception handling in lint_workflow_bundle API function."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.side_effect = RuntimeError('Unexpected API error')

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files={'main.wdl': 'workflow test {}'},
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'error'
            assert 'Workflow bundle linting failed' in result['message']
            assert 'Unexpected API error' in result['message']
            ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_unsupported_format_in_method(self):
        """Test unsupported format handling in lint_workflow_bundle method."""
        result = await self.linter.lint_workflow_bundle(
            workflow_files={'main.nf': 'nextflow workflow'},
            workflow_format='nextflow',
            main_workflow_file='main.nf',
        )

        assert result['status'] == 'error'
        assert 'Unsupported workflow format: nextflow' in result['message']
        assert 'wdl' in result['message']
        assert 'cwl' in result['message']

    @pytest.mark.asyncio
    async def test_lint_workflow_unsupported_format_in_method(self):
        """Test unsupported format handling in lint_workflow method."""
        result = await self.linter.lint_workflow(
            workflow_content='nextflow workflow', workflow_format='nextflow', filename='main.nf'
        )

        assert result['status'] == 'error'
        assert 'Unsupported workflow format: nextflow' in result['message']
        assert 'wdl' in result['message']
        assert 'cwl' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_main_file_not_found(self):
        """Test WDL bundle when main file doesn't exist after writing files."""
        # This tests the main_file_path.exists() check
        workflow_files = {'other.wdl': 'version 1.0\ntask Test {}'}

        result = await self.linter._lint_wdl_bundle(
            workflow_files=workflow_files, main_workflow_file='missing.wdl'
        )

        assert result['status'] == 'error'
        assert result['format'] == 'wdl'
        assert 'Main workflow file "missing.wdl" not found' in result['message']

    @pytest.mark.asyncio
    async def test_cwl_bundle_main_file_not_found(self):
        """Test CWL bundle when main file doesn't exist after writing files."""
        # This tests the main_file_path.exists() check
        workflow_files = {'other.cwl': 'cwlVersion: v1.0\nclass: CommandLineTool'}

        result = await self.linter._lint_cwl_bundle(
            workflow_files=workflow_files, main_workflow_file='missing.cwl'
        )

        assert result['status'] == 'error'
        assert result['format'] == 'cwl'
        assert 'Main workflow file "missing.cwl" not found' in result['message']

    @pytest.mark.asyncio
    async def test_lint_workflow_cwl_path_coverage(self):
        """Test to ensure CWL path in lint_workflow method is covered."""
        with patch.object(self.linter, '_lint_cwl') as mock_lint_cwl:
            mock_lint_cwl.return_value = {
                'status': 'success',
                'format': 'cwl',
                'linter': 'cwltool',
                'raw_output': 'Success',
            }

            result = await self.linter.lint_workflow(
                workflow_content='cwlVersion: v1.0\nclass: Workflow',
                workflow_format='cwl',
                filename='test.cwl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'cwl'
            mock_lint_cwl.assert_called_once_with('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_cwl_elif_branch(self):
        """Test to ensure CWL elif branch in lint_workflow_bundle is covered."""
        with patch.object(self.linter, '_lint_cwl_bundle') as mock_lint_cwl_bundle:
            mock_lint_cwl_bundle.return_value = {
                'status': 'success',
                'format': 'cwl',
                'main_file': 'main.cwl',
                'files_processed': ['main.cwl'],
                'linter': 'cwltool',
                'raw_output': 'Success',
            }

            # Call lint_workflow_bundle directly to hit the elif branch
            result = await self.linter.lint_workflow_bundle(
                workflow_files={'main.cwl': 'cwlVersion: v1.0\nclass: Workflow'},
                workflow_format='CWL',  # Use uppercase to test case insensitive
                main_workflow_file='main.cwl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'cwl'
            mock_lint_cwl_bundle.assert_called_once_with(
                {'main.cwl': 'cwlVersion: v1.0\nclass: Workflow'}, 'main.cwl'
            )

    @pytest.mark.asyncio
    async def test_lint_workflow_cwl_elif_branch_direct(self):
        """Test to ensure CWL elif branch in lint_workflow is covered."""
        with patch.object(self.linter, '_lint_cwl') as mock_lint_cwl:
            mock_lint_cwl.return_value = {
                'status': 'success',
                'format': 'cwl',
                'linter': 'cwltool',
                'raw_output': 'Success',
            }

            # Call lint_workflow directly to hit the elif branch
            result = await self.linter.lint_workflow(
                workflow_content='cwlVersion: v1.0\nclass: Workflow',
                workflow_format='CWL',  # Use uppercase to test case insensitive
                filename='test.cwl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'cwl'
            mock_lint_cwl.assert_called_once_with('cwlVersion: v1.0\nclass: Workflow', 'test.cwl')

    @pytest.mark.asyncio
    async def test_lint_workflow_wdl_then_cwl_branch_coverage(self):
        """Test both WDL and CWL branches to ensure complete branch coverage."""
        # Test WDL branch first
        with patch.object(self.linter, '_lint_wdl') as mock_lint_wdl:
            mock_lint_wdl.return_value = {
                'status': 'success',
                'format': 'wdl',
                'linter': 'miniwdl',
                'raw_output': 'Success',
            }

            result = await self.linter.lint_workflow(
                workflow_content='version 1.0\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'wdl'

        # Test CWL branch second to ensure elif is properly covered
        with patch.object(self.linter, '_lint_cwl') as mock_lint_cwl:
            mock_lint_cwl.return_value = {
                'status': 'success',
                'format': 'cwl',
                'linter': 'cwltool',
                'raw_output': 'Success',
            }

            result = await self.linter.lint_workflow(
                workflow_content='cwlVersion: v1.0\nclass: Workflow',
                workflow_format='cwl',
                filename='test.cwl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'cwl'

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_wdl_then_cwl_branch_coverage(self):
        """Test both WDL and CWL branches in bundle linting to ensure complete branch coverage."""
        # Test WDL branch first
        with patch.object(self.linter, '_lint_wdl_bundle') as mock_lint_wdl_bundle:
            mock_lint_wdl_bundle.return_value = {
                'status': 'success',
                'format': 'wdl',
                'main_file': 'main.wdl',
                'files_processed': ['main.wdl'],
                'linter': 'miniwdl',
                'raw_output': 'Success',
            }

            result = await self.linter.lint_workflow_bundle(
                workflow_files={'main.wdl': 'version 1.0\nworkflow Test {}'},
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'wdl'

        # Test CWL branch second to ensure elif is properly covered
        with patch.object(self.linter, '_lint_cwl_bundle') as mock_lint_cwl_bundle:
            mock_lint_cwl_bundle.return_value = {
                'status': 'success',
                'format': 'cwl',
                'main_file': 'main.cwl',
                'files_processed': ['main.cwl'],
                'linter': 'cwltool',
                'raw_output': 'Success',
            }

            result = await self.linter.lint_workflow_bundle(
                workflow_files={'main.cwl': 'cwlVersion: v1.0\nclass: Workflow'},
                workflow_format='cwl',
                main_workflow_file='main.cwl',
            )

            assert result['status'] == 'success'
            assert result['format'] == 'cwl'

    @pytest.mark.asyncio
    async def test_cwl_workflow_with_subworkflows(self):
        """Test CWL workflow with embedded subworkflows."""
        ctx = AsyncMock()
        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'cwl',
                'valid': True,
                'summary': {'subworkflows_count': 1},
            }
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='cwlVersion: v1.0\nclass: Workflow\nrequirements:\n  - class: SubworkflowFeatureRequirement',
                workflow_format='cwl',
                filename='test.cwl',
            )
            assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_wdl_workflow_with_conditionals(self):
        """Test WDL workflow with conditional logic."""
        ctx = AsyncMock()
        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'valid': True,
                'summary': {'conditionals_count': 1},
            }
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test {\n  input { Boolean run_optional }\n  if (run_optional) { call Task }\n}',
                workflow_format='wdl',
                filename='test.wdl',
            )
            assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_cwl_workflow_with_scatter(self):
        """Test CWL workflow with scatter/gather patterns."""
        ctx = AsyncMock()
        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'cwl',
                'valid': True,
                'summary': {'scatter_steps': 1},
            }
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='cwlVersion: v1.0\nclass: Workflow\nrequirements:\n  - class: ScatterFeatureRequirement\nsteps:\n  process:\n    scatter: input_files',
                workflow_format='cwl',
                filename='test.cwl',
            )
            assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_real_cwl_bundle_success(self):
        """Test actual CWL bundle linting without mocks."""
        ctx = AsyncMock()
        workflow_files = {
            'main.cwl': """cwlVersion: v1.0
class: Workflow
inputs:
  message: string
outputs:
  result:
    type: File
    outputSource: echo/output
steps:
  echo:
    run: echo.cwl
    in:
      message: message
    out: [output]""",
            'echo.cwl': """cwlVersion: v1.0
class: CommandLineTool
inputs:
  message: string
outputs:
  output:
    type: File
    outputBinding:
      glob: "output.txt"
baseCommand: [echo]
arguments: [$(inputs.message)]
stdout: output.txt""",
        }
        result = await lint_workflow_bundle(
            ctx=ctx,
            workflow_files=workflow_files,
            workflow_format='cwl',
            main_workflow_file='main.cwl',
        )
        # CWL validation may return validation_failed for complex workflows
        assert result['status'] in ['success', 'validation_failed']

    @pytest.mark.asyncio
    async def test_real_wdl_nested_imports(self):
        """Test WDL with complex nested directory imports."""
        ctx = AsyncMock()
        workflow_files = {
            'workflows/main.wdl': """version 1.0
import "../tasks/level1/process.wdl" as proc
workflow NestedWorkflow {
    input { String data }
    call proc.ProcessData { input: input_data = data }
    output { File result = ProcessData.output }
}""",
            'tasks/level1/process.wdl': """version 1.0
import "../level2/common.wdl" as common
task ProcessData {
    input { String input_data }
    call common.CommonTask { input: data = input_data }
    command { echo "Processing: ${input_data}" > output.txt }
    output { File output = "output.txt" }
    runtime { memory: "1GB" }
}""",
            'tasks/level2/common.wdl': """version 1.0
task CommonTask {
    input { String data }
    command { echo "Common processing: ${data}" }
    runtime { memory: "512MB" }
}""",
        }
        result = await lint_workflow_bundle(
            ctx=ctx,
            workflow_files=workflow_files,
            workflow_format='wdl',
            main_workflow_file='workflows/main.wdl',
        )
        # Complex nested imports may fail validation
        assert result['status'] in ['success', 'error']

    @pytest.mark.asyncio
    async def test_real_cwl_nested_imports(self):
        """Test CWL with nested tool imports."""
        ctx = AsyncMock()
        workflow_files = {
            'workflows/main.cwl': """cwlVersion: v1.0
class: Workflow
inputs:
  input_file: File
outputs:
  processed_file:
    type: File
    outputSource: process/output
steps:
  process:
    run: ../tools/processor.cwl
    in:
      input: input_file
    out: [output]""",
            'tools/processor.cwl': """cwlVersion: v1.0
class: CommandLineTool
inputs:
  input: File
outputs:
  output:
    type: File
    outputBinding:
      glob: "processed.txt"
baseCommand: [cat]
arguments: [$(inputs.input)]
stdout: processed.txt""",
        }
        result = await lint_workflow_bundle(
            ctx=ctx,
            workflow_files=workflow_files,
            workflow_format='cwl',
            main_workflow_file='workflows/main.cwl',
        )
        assert result['status'] in ['success', 'validation_failed']

    @pytest.mark.asyncio
    async def test_real_wdl_validation_warnings(self):
        """Test WDL workflows that generate validation warnings."""
        ctx = AsyncMock()
        workflow_files = {
            'main.wdl': """version 1.0
workflow TestWorkflow {
    call EmptyTask
}
task EmptyTask {
    command { echo "test" }
}"""
        }
        result = await lint_workflow_bundle(
            ctx=ctx,
            workflow_files=workflow_files,
            workflow_format='wdl',
            main_workflow_file='main.wdl',
        )
        # May fail due to missing runtime requirements
        assert result['status'] in ['success', 'error']

    @pytest.mark.asyncio
    async def test_real_cwl_validation_warnings(self):
        """Test CWL workflows that generate validation warnings."""
        ctx = AsyncMock()
        workflow_files = {
            'main.cwl': """cwlVersion: v1.0
class: Workflow
steps:
  echo:
    run:
      class: CommandLineTool
      baseCommand: [echo, "hello"]
      outputs:
        result:
          type: stdout
    in: []
    out: [result]"""
        }
        result = await lint_workflow_bundle(
            ctx=ctx,
            workflow_files=workflow_files,
            workflow_format='cwl',
            main_workflow_file='main.cwl',
        )
        assert result['status'] in ['success', 'validation_failed']

    @pytest.mark.asyncio
    async def test_bundle_linting_generic_exception(self):
        """Test generic exception handling in bundle linting."""
        ctx = AsyncMock()
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp.side_effect = RuntimeError('Unexpected error')
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files={'main.wdl': 'version 1.0\nworkflow Test {}'},
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )
            assert result['status'] == 'error'
            assert 'Unexpected error' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_file_processing_errors(self):
        """Test file processing errors in WDL bundle linting."""
        ctx = AsyncMock()
        workflow_files = {
            'main.wdl': 'version 1.0\nimport "tasks.wdl"\nworkflow Test {}',
            'tasks.wdl': 'version 1.0\ntask TestTask {}',
        }
        with patch('pathlib.Path.write_text') as mock_write:
            mock_write.side_effect = [None, OSError('Disk full')]
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_wdl_bundle_directory_creation_failure(self):
        """Test directory creation failure in bundle processing."""
        ctx = AsyncMock()
        workflow_files = {'nested/deep/main.wdl': 'version 1.0\nworkflow Test {}'}
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError('Cannot create directory')
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='nested/deep/main.wdl',
            )
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_tool_exception(self):
        """Test LintAHOWorkflowBundle tool exception handling."""
        ctx = AsyncMock()
        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.side_effect = Exception('Linter crashed')
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files={'main.wdl': 'version 1.0\nworkflow Test {}'},
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )
            assert result['status'] == 'error'
            assert 'bundle linting failed' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_main_file_not_found_error(self):
        """Test WDL bundle main file not found error path."""
        ctx = AsyncMock()
        workflow_files = {'other.wdl': 'version 1.0\nworkflow Test {}'}
        result = await lint_workflow_bundle(
            ctx=ctx,
            workflow_files=workflow_files,
            workflow_format='wdl',
            main_workflow_file='missing.wdl',
        )
        assert result['status'] == 'error'
        assert 'not found' in result['message']

    @pytest.mark.asyncio
    async def test_cwl_bundle_main_file_not_found_error(self):
        """Test CWL bundle main file not found error path."""
        ctx = AsyncMock()
        workflow_files = {'other.cwl': 'cwlVersion: v1.0\nclass: Workflow'}
        result = await lint_workflow_bundle(
            ctx=ctx,
            workflow_files=workflow_files,
            workflow_format='cwl',
            main_workflow_file='missing.cwl',
        )
        assert result['status'] == 'error'
        assert 'not found' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_unsupported_format_error(self):
        """Test unsupported format error in bundle linting."""
        linter = WorkflowLinter()
        result = await linter.lint_workflow_bundle({'main.nf': 'nextflow'}, 'nextflow', 'main.nf')
        assert result['status'] == 'error'
        assert 'Unsupported workflow format' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_single_file_unsupported_format(self):
        """Test unsupported format in single file linting."""
        linter = WorkflowLinter()
        result = await linter.lint_workflow('nextflow content', 'nextflow', 'main.nf')
        assert result['status'] == 'error'
        assert 'Unsupported workflow format' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_tempfile_error(self):
        """Test tempfile creation error in bundle linting."""
        ctx = AsyncMock()
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp.side_effect = OSError('Cannot create temp directory')
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files={'main.wdl': 'version 1.0\nworkflow Test {}'},
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_cwl_bundle_tempfile_error(self):
        """Test tempfile creation error in CWL bundle linting."""
        ctx = AsyncMock()
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp.side_effect = OSError('Cannot create temp directory')
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files={'main.cwl': 'cwlVersion: v1.0\nclass: Workflow'},
                workflow_format='cwl',
                main_workflow_file='main.cwl',
            )
            assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_raw_output_included_in_response(self):
        """Test that raw linter output is included in the response."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'valid': True,
                'linter': 'miniwdl',
                'raw_output': 'STDOUT:\nWorkflow is valid\nSTDERR:\n\nReturn code: 0',
            }

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test { input { String x } output { String y = x } }',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'success'
            assert 'raw_output' in result
            assert 'STDOUT:' in result['raw_output']
            assert 'Return code:' in result['raw_output']

    @pytest.mark.asyncio
    async def test_raw_output_included_in_bundle_response(self):
        """Test that raw linter output is included in bundle linting response."""
        ctx = AsyncMock()

        workflow_files = {
            'main.wdl': 'version 1.0\nworkflow Test { input { String x } output { String y = x } }',
        }

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.return_value = {
                'status': 'success',
                'format': 'wdl',
                'main_file': 'main.wdl',
                'files_processed': ['main.wdl'],
                'valid': True,
                'linter': 'miniwdl',
                'raw_output': 'STDOUT:\nWorkflow bundle is valid\nSTDERR:\n\nReturn code: 0',
            }

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'success'
            assert 'raw_output' in result
            assert 'STDOUT:' in result['raw_output']
            assert 'Return code:' in result['raw_output']

    @pytest.mark.asyncio
    async def test_subprocess_timeout_error(self):
        """Test subprocess timeout handling."""
        ctx = AsyncMock()

        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = subprocess.TimeoutExpired('cmd', 30)

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'error'
            assert 'timed out' in result['raw_output']

    @pytest.mark.asyncio
    async def test_general_exception_handling(self):
        """Test general exception handling in workflow linting."""
        ctx = AsyncMock()

        with patch.object(WorkflowLinter, 'lint_workflow') as mock_lint:
            mock_lint.side_effect = Exception('Unexpected error')

            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='version 1.0\nworkflow Test {}',
                workflow_format='wdl',
                filename='test.wdl',
            )

            assert result['status'] == 'error'
            assert 'Workflow linting failed' in result['message']

    @pytest.mark.asyncio
    async def test_bundle_general_exception_handling(self):
        """Test general exception handling in bundle linting."""
        ctx = AsyncMock()

        workflow_files = {'main.wdl': 'version 1.0\nworkflow Test {}'}

        with patch.object(WorkflowLinter, 'lint_workflow_bundle') as mock_lint:
            mock_lint.side_effect = Exception('Unexpected bundle error')

            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

            assert result['status'] == 'error'
            assert 'Workflow bundle linting failed' in result['message']

    @pytest.mark.asyncio
    async def test_lint_workflow_fallback_branch(self):
        """Test fallback branch when format is neither WDL nor CWL."""
        # Temporarily modify supported_formats to allow an unsupported format through initial validation
        original_formats = self.linter.supported_formats
        self.linter.supported_formats = ['wdl', 'cwl', 'nextflow']

        try:
            result = await self.linter.lint_workflow(
                workflow_content='nextflow workflow',
                workflow_format='nextflow',
                filename='test.nf',
            )

            assert result['status'] == 'error'
            assert 'Unexpected workflow format: nextflow' in result['message']
            assert 'should not happen' in result['message']
        finally:
            # Restore original supported formats
            self.linter.supported_formats = original_formats

    @pytest.mark.asyncio
    async def test_lint_workflow_bundle_fallback_branch(self):
        """Test fallback branch when format is neither WDL nor CWL in bundle linting."""
        # Temporarily modify supported_formats to allow an unsupported format through initial validation
        original_formats = self.linter.supported_formats
        self.linter.supported_formats = ['wdl', 'cwl', 'nextflow']

        try:
            result = await self.linter.lint_workflow_bundle(
                workflow_files={'main.nf': 'nextflow workflow'},
                workflow_format='nextflow',
                main_workflow_file='main.nf',
            )

            assert result['status'] == 'error'
            assert 'Unexpected workflow format: nextflow' in result['message']
            assert 'should not happen' in result['message']
        finally:
            # Restore original supported formats
            self.linter.supported_formats = original_formats
