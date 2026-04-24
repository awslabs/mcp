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

"""Integration tests for content resolution in package_workflow.

Validates: Requirements Package Workflow with File Path or S3 URI,
Backward Compatibility.
"""

import base64
import pytest
import zipfile
from awslabs.aws_healthomics_mcp_server.tools.helper_tools import package_workflow
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch


SAMPLE_WDL = 'version 1.0\nworkflow Test { }'


def _unzip_base64(b64: str) -> dict[str, str]:
    """Decode a base64 ZIP and return {filename: text_content}."""
    data = base64.b64decode(b64)
    with zipfile.ZipFile(BytesIO(data)) as zf:
        return {name: zf.read(name).decode('utf-8') for name in zf.namelist()}


class TestPackageWorkflowResolution:
    """Integration tests for content resolution in package_workflow.

    Validates: Requirements Package Workflow with File Path or S3 URI,
    Backward Compatibility.
    """

    @pytest.mark.asyncio
    async def test_local_file_path(self, tmp_path):
        """Package resolves a local file path for main_file_content.

        Validates: Requirement Package Workflow with File Path or S3 URI
        """
        wdl_file = tmp_path / 'workflow.wdl'
        wdl_file.write_text(SAMPLE_WDL)

        ctx = AsyncMock()
        result = await package_workflow(
            ctx=ctx,
            main_file_content=str(wdl_file),
            main_file_name='main.wdl',
            additional_files=None,
            output_path=None,
        )

        assert isinstance(result, str)
        files = _unzip_base64(result)
        assert files['main.wdl'] == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_s3_uri(self):
        """Package resolves an S3 URI for main_file_content.

        Validates: Requirement Package Workflow with File Path or S3 URI
        """
        ctx = AsyncMock()

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'ContentLength': len(SAMPLE_WDL)}
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=SAMPLE_WDL.encode('utf-8')))
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session',
            return_value=mock_session,
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content='s3://my-bucket/workflow.wdl',
                main_file_name='main.wdl',
                additional_files=None,
                output_path=None,
            )

        assert isinstance(result, str)
        files = _unzip_base64(result)
        assert files['main.wdl'] == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_inline_content(self):
        """Package passes inline content through unchanged (backward compat).

        Validates: Requirement Package Workflow with File Path or S3 URI,
        Backward Compatibility.
        """
        ctx = AsyncMock()
        result = await package_workflow(
            ctx=ctx,
            main_file_content=SAMPLE_WDL,
            main_file_name='main.wdl',
            additional_files=None,
            output_path=None,
        )

        assert isinstance(result, str)
        files = _unzip_base64(result)
        assert files['main.wdl'] == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_additional_files_resolved_individually(self, tmp_path):
        """Each additional_files value is resolved individually.

        Validates: Requirement Package Workflow with File Path or S3 URI
        """
        tasks_file = tmp_path / 'tasks.wdl'
        tasks_content = 'version 1.0\ntask T { }'
        tasks_file.write_text(tasks_content)

        ctx = AsyncMock()
        result = await package_workflow(
            ctx=ctx,
            main_file_content=SAMPLE_WDL,
            main_file_name='main.wdl',
            additional_files={
                'tasks.wdl': str(tasks_file),
                'inline.wdl': 'version 1.0\ntask I { }',
            },
            output_path=None,
        )

        assert isinstance(result, str)
        files = _unzip_base64(result)
        assert files['main.wdl'] == SAMPLE_WDL
        assert files['tasks.wdl'] == tasks_content
        assert files['inline.wdl'] == 'version 1.0\ntask I { }'

    @pytest.mark.asyncio
    async def test_error_propagation_main_file(self):
        """Error is returned when main file resolution fails.

        Validates: Requirement Package Workflow with File Path or S3 URI
        """
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.resolve_single_content',
            side_effect=FileNotFoundError('File not found: /no/such/file.wdl'),
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content='/no/such/file.wdl',
                main_file_name='main.wdl',
                additional_files=None,
                output_path=None,
            )

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'File not found' in result['error']

    @pytest.mark.asyncio
    async def test_error_propagation_additional_file(self):
        """Error is returned when an additional file resolution fails.

        Validates: Requirement Package Workflow with File Path or S3 URI
        """
        ctx = AsyncMock()

        # First call succeeds (main file), second call fails (additional file)
        call_count = 0

        async def _side_effect(value, mode='text'):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
                    ContentInputType,
                    ResolvedContent,
                )

                return ResolvedContent(
                    content=SAMPLE_WDL,
                    input_type=ContentInputType.INLINE_CONTENT,
                    source=value,
                )
            raise FileNotFoundError('File not found: /missing.wdl')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.resolve_single_content',
            side_effect=_side_effect,
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files={'extra.wdl': '/missing.wdl'},
                output_path=None,
            )

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'File not found' in result['error']

    @pytest.mark.asyncio
    async def test_unexpected_exception_in_package_workflow(self):
        """Lines 84-85: outer except catches unexpected exceptions in package_workflow."""
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.resolve_single_content',
        ) as mock_resolve:
            from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
                ContentInputType,
                ResolvedContent,
            )

            mock_resolve.return_value = ResolvedContent(
                content=SAMPLE_WDL,
                input_type=ContentInputType.INLINE_CONTENT,
                source='inline',
            )

            with patch(
                'awslabs.aws_healthomics_mcp_server.tools.helper_tools.create_zip_file',
                side_effect=RuntimeError('Unexpected ZIP error'),
            ):
                result = await package_workflow(
                    ctx=ctx,
                    main_file_content=SAMPLE_WDL,
                    main_file_name='main.wdl',
                    additional_files=None,
                    output_path=None,
                )

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Unexpected ZIP error' in result['error']
