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

"""Integration tests for content resolution in workflow linting tools.

Validates: Requirements Lint Workflow Definition with File Path or S3 URI,
Lint Workflow Bundle with File Path or S3 URI,
Backward Compatibility.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.workflow_linting import (
    lint_workflow_bundle,
    lint_workflow_definition,
)
from unittest.mock import AsyncMock, MagicMock, patch


SAMPLE_WDL = 'version 1.0\nworkflow Test { }'


def _mock_linter():
    """Create a mock linter that returns a success response."""
    linter = AsyncMock()
    linter.lint_workflow.return_value = {
        'status': 'success',
        'format': 'wdl',
        'linter': 'miniwdl',
        'raw_output': 'STDOUT:\nvalid\nSTDERR:\n\nReturn code: 0',
    }
    linter.lint_workflow_bundle.return_value = {
        'status': 'success',
        'format': 'wdl',
        'linter': 'miniwdl',
        'main_file': 'main.wdl',
        'files_processed': ['main.wdl'],
        'raw_output': 'STDOUT:\nvalid\nSTDERR:\n\nReturn code: 0',
    }
    return linter


class TestLintWorkflowDefinitionResolution:
    """Integration tests for content resolution in lint_workflow_definition.

    Validates: Requirements Lint Workflow Definition with File Path or S3 URI,
    Backward Compatibility.
    """

    @pytest.mark.asyncio
    async def test_local_file_path(self, tmp_path):
        """Lint resolves a local file path to its content before linting.

        Validates: Requirement Lint Workflow Definition with File Path or S3 URI
        """
        wdl_file = tmp_path / 'workflow.wdl'
        wdl_file.write_text(SAMPLE_WDL)

        ctx = AsyncMock()
        mock_lint = _mock_linter()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.get_linter',
            return_value=mock_lint,
        ):
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content=str(wdl_file),
                workflow_format='wdl',
            )

        assert result['status'] == 'success'
        mock_lint.lint_workflow.assert_called_once()
        call_kwargs = mock_lint.lint_workflow.call_args
        assert call_kwargs.kwargs.get('workflow_content') == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_s3_uri(self):
        """Lint resolves an S3 URI to its content before linting.

        Validates: Requirement Lint Workflow Definition with File Path or S3 URI
        """
        ctx = AsyncMock()
        mock_lint = _mock_linter()

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'ContentLength': len(SAMPLE_WDL)}
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=SAMPLE_WDL.encode('utf-8')))
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.get_linter',
                return_value=mock_lint,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session',
                return_value=mock_session,
            ),
        ):
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='s3://my-bucket/workflow.wdl',
                workflow_format='wdl',
            )

        assert result['status'] == 'success'
        mock_lint.lint_workflow.assert_called_once()
        call_kwargs = mock_lint.lint_workflow.call_args
        assert call_kwargs.kwargs.get('workflow_content') == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_inline_content(self):
        """Lint passes inline content through unchanged.

        Validates: Requirement Lint Workflow Definition with File Path or S3 URI,
        Backward Compatibility.
        """
        ctx = AsyncMock()
        mock_lint = _mock_linter()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.get_linter',
            return_value=mock_lint,
        ):
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content=SAMPLE_WDL,
                workflow_format='wdl',
            )

        assert result['status'] == 'success'
        mock_lint.lint_workflow.assert_called_once()
        call_kwargs = mock_lint.lint_workflow.call_args
        assert call_kwargs.kwargs.get('workflow_content') == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_resolution_error_file_not_found(self):
        """Error is returned when the local file does not exist.

        Validates: Requirement Lint Workflow Definition with File Path or S3 URI
        """
        ctx = AsyncMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.get_linter',
            ) as mock_get_linter,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.resolve_single_content',
                side_effect=FileNotFoundError('File not found: /no/such/file.wdl'),
            ),
        ):
            result = await lint_workflow_definition(
                ctx=ctx,
                workflow_content='/no/such/file.wdl',
                workflow_format='wdl',
            )

        assert 'error' in result
        assert 'File not found' in result['error']
        mock_get_linter.return_value.lint_workflow.assert_not_called()


class TestLintWorkflowBundleResolution:
    """Integration tests for content resolution in lint_workflow_bundle.

    Validates: Requirements Lint Workflow Bundle with File Path or S3 URI.
    """

    @pytest.mark.asyncio
    async def test_local_directory(self, tmp_path):
        """Bundle resolves a local directory path to a file dictionary.

        Validates: Requirement Lint Workflow Bundle with File Path or S3 URI
        """
        (tmp_path / 'main.wdl').write_text(SAMPLE_WDL)
        (tmp_path / 'tasks.wdl').write_text('version 1.0\ntask T { }')

        ctx = AsyncMock()
        mock_lint = _mock_linter()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.get_linter',
            return_value=mock_lint,
        ):
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=str(tmp_path),
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

        assert result['status'] == 'success'
        mock_lint.lint_workflow_bundle.assert_called_once()
        call_kwargs = mock_lint.lint_workflow_bundle.call_args
        files = call_kwargs.kwargs.get('workflow_files')
        assert 'main.wdl' in files
        assert files['main.wdl'] == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_dict_passthrough(self):
        """Bundle passes a dict through directly (backward compatibility).

        Validates: Requirement Lint Workflow Bundle with File Path or S3 URI
        """
        workflow_files = {
            'main.wdl': SAMPLE_WDL,
            'tasks.wdl': 'version 1.0\ntask T { }',
        }

        ctx = AsyncMock()
        mock_lint = _mock_linter()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.get_linter',
            return_value=mock_lint,
        ):
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files=workflow_files,
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

        assert result['status'] == 'success'
        mock_lint.lint_workflow_bundle.assert_called_once()
        call_kwargs = mock_lint.lint_workflow_bundle.call_args
        assert call_kwargs.kwargs.get('workflow_files') == workflow_files

    @pytest.mark.asyncio
    async def test_resolution_error_propagation(self):
        """Error is returned when bundle resolution fails.

        Validates: Requirement Lint Workflow Bundle with File Path or S3 URI
        """
        ctx = AsyncMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.get_linter',
            ) as mock_get_linter,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_linting.resolve_bundle_content',
                side_effect=ValueError('Path contains traversal sequences'),
            ),
        ):
            result = await lint_workflow_bundle(
                ctx=ctx,
                workflow_files='../../etc/passwd',
                workflow_format='wdl',
                main_workflow_file='main.wdl',
            )

        assert 'error' in result
        assert 'traversal' in result['error']
        mock_get_linter.return_value.lint_workflow_bundle.assert_not_called()
