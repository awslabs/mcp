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

"""Integration tests for content resolution in create_workflow and create_workflow_version.

Validates: Requirements Create Workflow with File Path or S3 URI,
Create Workflow Version with File Path or S3 URI,
Backward Compatibility,
Parameter Deprecation for definition_zip_base64.
"""

import base64
import pytest
from awslabs.aws_healthomics_mcp_server.tools.workflow_management import (
    create_workflow,
    create_workflow_version,
)
from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
    ContentInputType,
    ResolvedContent,
)
from unittest.mock import AsyncMock, MagicMock, patch


ZIP_BYTES = b'PK\x03\x04fake-zip-content'
B64_CONTENT = base64.b64encode(ZIP_BYTES).decode('utf-8')

MOCK_CREATE_RESPONSE = {
    'id': 'wfl-12345',
    'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
    'status': 'CREATING',
}

MOCK_VERSION_RESPONSE = {
    'id': 'wfl-12345',
    'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
    'status': 'CREATING',
    'name': 'test-workflow',
}


def _mock_omics_client():
    """Create a mock HealthOmics client."""
    client = MagicMock()
    client.create_workflow.return_value = MOCK_CREATE_RESPONSE
    client.create_workflow_version.return_value = MOCK_VERSION_RESPONSE
    return client


def _resolved_binary(content: bytes, source: str, input_type=None):
    """Build a ResolvedContent for binary mode."""
    return ResolvedContent(
        content=content,
        input_type=input_type or ContentInputType.INLINE_CONTENT,
        source=source,
    )


class TestCreateWorkflowResolution:
    """Integration tests for content resolution in create_workflow.

    Validates: Requirements Create Workflow with File Path or S3 URI,
    Backward Compatibility,
    Parameter Deprecation.
    """

    @pytest.mark.asyncio
    async def test_definition_source_base64(self):
        """create_workflow resolves base64 content via definition_source.

        Validates: Requirement Create Workflow with File Path or S3 URI,
        Backward Compatibility.
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_workflow(
                ctx=ctx,
                name='test-wf',
                definition_source=B64_CONTENT,
            )

        assert result['id'] == 'wfl-12345'
        call_kwargs = mock_client.create_workflow.call_args.kwargs
        assert 'definitionZip' in call_kwargs
        assert isinstance(call_kwargs['definitionZip'], bytes)

    @pytest.mark.asyncio
    async def test_definition_source_local_zip(self, tmp_path):
        """create_workflow resolves a local ZIP file path via definition_source.

        Validates: Requirement Create Workflow with File Path or S3 URI
        """
        zip_file = tmp_path / 'workflow.zip'
        zip_file.write_bytes(ZIP_BYTES)

        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_workflow(
                ctx=ctx,
                name='test-wf',
                definition_source=str(zip_file),
            )

        assert result['id'] == 'wfl-12345'
        call_kwargs = mock_client.create_workflow.call_args.kwargs
        assert call_kwargs['definitionZip'] == ZIP_BYTES

    @pytest.mark.asyncio
    async def test_definition_source_s3_uri(self):
        """create_workflow resolves an S3 URI via definition_source.

        Validates: Requirement Create Workflow with File Path or S3 URI
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'ContentLength': len(ZIP_BYTES)}
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=ZIP_BYTES))
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session',
                return_value=mock_session,
            ),
        ):
            result = await create_workflow(
                ctx=ctx,
                name='test-wf',
                definition_source='s3://my-bucket/workflow.zip',
            )

        assert result['id'] == 'wfl-12345'
        call_kwargs = mock_client.create_workflow.call_args.kwargs
        assert call_kwargs['definitionZip'] == ZIP_BYTES

    @pytest.mark.asyncio
    async def test_deprecated_alias_works_and_logs_warning(self):
        """definition_zip_base64 alias works and triggers deprecation warning.

        Validates: Requirement Parameter Deprecation
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
            ) as mock_logger,
        ):
            result = await create_workflow(
                ctx=ctx,
                name='test-wf',
                definition_zip_base64=B64_CONTENT,
            )

        assert result['id'] == 'wfl-12345'
        # Verify deprecation warning was logged
        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any('deprecated' in w.lower() for w in warning_calls)

    @pytest.mark.asyncio
    async def test_definition_source_precedence(self):
        """definition_source takes precedence when both it and alias are provided.

        Validates: Requirement Parameter Deprecation
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        other_bytes = b'PK\x03\x04other-content'
        other_b64 = base64.b64encode(other_bytes).decode('utf-8')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
            ) as mock_logger,
        ):
            result = await create_workflow(
                ctx=ctx,
                name='test-wf',
                definition_source=B64_CONTENT,
                definition_zip_base64=other_b64,
            )

        assert result['id'] == 'wfl-12345'
        call_kwargs = mock_client.create_workflow.call_args.kwargs
        # The ZIP bytes should come from definition_source, not the alias
        assert call_kwargs['definitionZip'] == ZIP_BYTES
        # Verify precedence warning was logged
        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any('both' in w.lower() for w in warning_calls)

    @pytest.mark.asyncio
    async def test_definition_uri_unchanged(self):
        """definition_uri still works and is passed directly to the API.

        Validates: Requirement Backward Compatibility
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_workflow(
                ctx=ctx,
                name='test-wf',
                definition_uri='s3://my-bucket/workflow.zip',
            )

        assert result['id'] == 'wfl-12345'
        call_kwargs = mock_client.create_workflow.call_args.kwargs
        assert call_kwargs['definitionUri'] == 's3://my-bucket/workflow.zip'
        assert 'definitionZip' not in call_kwargs

    @pytest.mark.asyncio
    async def test_resolution_error_propagation(self):
        """Error is returned when definition_source resolution fails.

        Validates: Requirement Create Workflow with File Path or S3 URI
        """
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.resolve_single_content',
            side_effect=FileNotFoundError('File not found: /no/such.zip'),
        ):
            result = await create_workflow(
                ctx=ctx,
                name='test-wf',
                definition_source='/no/such.zip',
            )

        assert 'error' in result
        assert 'resolve' in result['error'].lower() or 'File not found' in result['error']


class TestCreateWorkflowVersionResolution:
    """Integration tests for content resolution in create_workflow_version.

    Validates: Requirements Create Workflow Version with File Path or S3 URI,
    Parameter Deprecation.
    """

    @pytest.mark.asyncio
    async def test_definition_source_base64(self):
        """create_workflow_version resolves base64 content via definition_source.

        Validates: Requirement Create Workflow Version with File Path or S3 URI
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_workflow_version(
                ctx=ctx,
                workflow_id='wfl-12345',
                version_name='v2',
                definition_source=B64_CONTENT,
            )

        assert result['versionName'] == 'v2'
        call_kwargs = mock_client.create_workflow_version.call_args.kwargs
        assert 'definitionZip' in call_kwargs

    @pytest.mark.asyncio
    async def test_definition_source_local_zip(self, tmp_path):
        """create_workflow_version resolves a local ZIP file path.

        Validates: Requirement Create Workflow Version with File Path or S3 URI
        """
        zip_file = tmp_path / 'workflow.zip'
        zip_file.write_bytes(ZIP_BYTES)

        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_workflow_version(
                ctx=ctx,
                workflow_id='wfl-12345',
                version_name='v2',
                definition_source=str(zip_file),
            )

        assert result['versionName'] == 'v2'
        call_kwargs = mock_client.create_workflow_version.call_args.kwargs
        assert call_kwargs['definitionZip'] == ZIP_BYTES

    @pytest.mark.asyncio
    async def test_definition_source_s3_uri(self):
        """create_workflow_version resolves an S3 URI via definition_source.

        Validates: Requirement Create Workflow Version with File Path or S3 URI
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'ContentLength': len(ZIP_BYTES)}
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=ZIP_BYTES))
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session',
                return_value=mock_session,
            ),
        ):
            result = await create_workflow_version(
                ctx=ctx,
                workflow_id='wfl-12345',
                version_name='v2',
                definition_source='s3://my-bucket/workflow.zip',
            )

        assert result['versionName'] == 'v2'
        call_kwargs = mock_client.create_workflow_version.call_args.kwargs
        assert call_kwargs['definitionZip'] == ZIP_BYTES

    @pytest.mark.asyncio
    async def test_deprecated_alias_works(self):
        """definition_zip_base64 alias works for create_workflow_version.

        Validates: Requirement Parameter Deprecation
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_workflow_version(
                ctx=ctx,
                workflow_id='wfl-12345',
                version_name='v2',
                definition_zip_base64=B64_CONTENT,
            )

        assert result['versionName'] == 'v2'
        call_kwargs = mock_client.create_workflow_version.call_args.kwargs
        assert 'definitionZip' in call_kwargs

    @pytest.mark.asyncio
    async def test_backward_compat_base64_format(self):
        """Existing base64 format still works via definition_source.

        Validates: Requirement Backward Compatibility
        """
        ctx = AsyncMock()
        mock_client = _mock_omics_client()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_workflow_version(
                ctx=ctx,
                workflow_id='wfl-12345',
                version_name='v2',
                definition_source=B64_CONTENT,
            )

        assert result['versionName'] == 'v2'
        call_kwargs = mock_client.create_workflow_version.call_args.kwargs
        assert call_kwargs['definitionZip'] == ZIP_BYTES

    @pytest.mark.asyncio
    async def test_resolution_error_propagation(self):
        """Error is returned when definition_source resolution fails.

        Validates: Requirement Create Workflow Version with File Path or S3 URI
        """
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.resolve_single_content',
            side_effect=FileNotFoundError('File not found: /no/such.zip'),
        ):
            result = await create_workflow_version(
                ctx=ctx,
                workflow_id='wfl-12345',
                version_name='v2',
                definition_source='/no/such.zip',
            )

        assert 'error' in result
