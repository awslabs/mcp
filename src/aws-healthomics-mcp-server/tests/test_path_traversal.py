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

"""Comprehensive path traversal prevention tests across all path-handling components.

Tests cover:
- Workflow linting bundle file paths (WDL and CWL)
- ZIP extraction (Zip Slip prevention)
- S3 prefix key traversal
- Content resolver path validation
- Path utility validation functions
"""

import io
import os
import pytest
import zipfile
from awslabs.aws_healthomics_mcp_server.tools.workflow_linting import (
    CWLWorkflowLinter,
    WDLWorkflowLinter,
)
from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
    _extract_zip_contents,
    resolve_bundle_content,
)
from awslabs.aws_healthomics_mcp_server.utils.path_utils import (
    sanitize_local_path,
    validate_local_path,
)
from unittest.mock import MagicMock, patch


class TestValidateLocalPath:
    """Tests for validate_local_path traversal detection."""

    def test_rejects_leading_dotdot_slash(self):
        """Property: Paths starting with ../ are rejected."""
        with pytest.raises(ValueError, match='traversal'):
            validate_local_path('../etc/passwd')

    def test_rejects_embedded_dotdot(self):
        """Property: Paths with /../ in the middle are rejected."""
        with pytest.raises(ValueError, match='traversal'):
            validate_local_path('foo/../../../etc/passwd')

    def test_rejects_trailing_dotdot(self):
        """Property: Paths ending with /.. are rejected."""
        with pytest.raises(ValueError, match='traversal'):
            validate_local_path('foo/bar/..')

    def test_rejects_bare_dotdot(self):
        """Property: Bare '..' is rejected."""
        with pytest.raises(ValueError, match='traversal'):
            validate_local_path('..')

    def test_rejects_os_native_separator_traversal(self):
        """Property: Traversal using OS-native separators is rejected."""
        with pytest.raises(ValueError, match='traversal'):
            validate_local_path(os.sep.join(['foo', '..', '..', 'etc', 'passwd']))

    def test_allows_valid_relative_path(self):
        """Property: Valid relative paths without traversal are accepted."""
        # Should not raise
        validate_local_path('workflows/main.wdl')
        validate_local_path('tasks/align.wdl')
        validate_local_path('deeply/nested/path/file.txt')

    def test_allows_dotdot_in_filename(self):
        """Property: Filenames containing '..' as substring (not component) are accepted."""
        # 'file..name' does not contain '..' as a path component
        validate_local_path('file..name.txt')

    def test_rejects_multiple_traversal_levels(self):
        """Property: Multiple levels of ../ traversal are rejected."""
        with pytest.raises(ValueError, match='traversal'):
            validate_local_path('a/b/c/../../../../etc/shadow')


class TestSanitizeLocalPath:
    """Tests for sanitize_local_path defense-in-depth."""

    def test_rejects_null_bytes(self):
        """Property: Paths with null bytes are rejected."""
        with pytest.raises(ValueError, match='null bytes'):
            sanitize_local_path('/tmp/file\x00.txt')

    def test_rejects_traversal(self):
        """Property: Paths with traversal sequences are rejected."""
        with pytest.raises(ValueError, match='traversal'):
            sanitize_local_path('../../../etc/passwd')

    def test_resolves_valid_path(self):
        """Property: Valid paths are resolved to absolute form."""
        result = sanitize_local_path('/tmp/test.svg')
        assert os.path.isabs(result)


class TestZipSlipPrevention:
    """Tests for path traversal prevention in ZIP extraction."""

    def _make_zip_with_entry(self, filename: str, content: str = 'test') -> bytes:
        """Helper to create a ZIP with a specific filename entry."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr(filename, content)
        return buf.getvalue()

    def test_rejects_dotdot_in_zip_entry(self):
        """Property: ZIP entries with ../ traversal are rejected."""
        data = self._make_zip_with_entry('../../../etc/passwd', 'malicious')
        with pytest.raises(ValueError, match='Path traversal detected in ZIP entry'):
            _extract_zip_contents(data)

    def test_rejects_nested_traversal_in_zip_entry(self):
        """Property: ZIP entries with nested ../ traversal are rejected."""
        data = self._make_zip_with_entry('subdir/../../outside.txt', 'malicious')
        with pytest.raises(ValueError, match='Path traversal detected in ZIP entry'):
            _extract_zip_contents(data)

    def test_rejects_absolute_path_in_zip_entry(self):
        """Property: ZIP entries with absolute paths are rejected."""
        data = self._make_zip_with_entry('/etc/passwd', 'malicious')
        with pytest.raises(ValueError, match='Absolute path detected in ZIP entry'):
            _extract_zip_contents(data)

    def test_rejects_home_dir_traversal_in_zip(self):
        """Property: ZIP entries targeting home directory are rejected."""
        data = self._make_zip_with_entry(
            '../../../home/user/.ssh/authorized_keys', 'ssh-rsa AAAA...'
        )
        with pytest.raises(ValueError, match='Path traversal detected in ZIP entry'):
            _extract_zip_contents(data)

    def test_rejects_python_module_overwrite_in_zip(self):
        """Property: ZIP entries targeting Python site-packages are rejected."""
        data = self._make_zip_with_entry(
            '../../../../lib/python3.10/site-packages/WDL/__init__.py',
            'import os; os.system("echo pwned")',
        )
        with pytest.raises(ValueError, match='Path traversal detected in ZIP entry'):
            _extract_zip_contents(data)

    def test_allows_valid_nested_paths_in_zip(self):
        """Property: ZIP entries with valid nested paths are accepted."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('workflows/main.wdl', 'workflow main {}')
            zf.writestr('tasks/align.wdl', 'task align {}')
            zf.writestr('deeply/nested/path/file.wdl', 'task deep {}')
        result = _extract_zip_contents(buf.getvalue())
        assert 'workflows/main.wdl' in result
        assert 'tasks/align.wdl' in result
        assert 'deeply/nested/path/file.wdl' in result

    def test_rejects_traversal_mixed_with_valid_entries(self):
        """Property: A single malicious entry causes rejection even with valid entries."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('valid/file.wdl', 'workflow valid {}')
            zf.writestr('../../../etc/crontab', '* * * * * evil')
        with pytest.raises(ValueError, match='Path traversal detected in ZIP entry'):
            _extract_zip_contents(buf.getvalue())

    def test_rejects_backslash_traversal_in_zip(self):
        """Property: ZIP entries with backslash traversal are rejected on all platforms.

        Note: On macOS/Linux, backslash is a valid filename character, not a separator.
        The normpath check only catches this on Windows. On Unix, the forward-slash
        variant is the relevant attack vector.
        """
        data = self._make_zip_with_entry('..\\..\\..\\etc\\passwd', 'malicious')
        if os.sep == '\\':
            # Windows: backslash is a path separator, so normpath catches it
            with pytest.raises(ValueError, match='traversal'):
                _extract_zip_contents(data)
        else:
            # Unix: backslash is a valid filename char, not a traversal vector
            # The forward-slash tests above cover the real attack on Unix
            result = _extract_zip_contents(data)
            assert '..\\..\\..\\etc\\passwd' in result


class TestS3PrefixTraversalPrevention:
    """Tests for path traversal prevention in S3 prefix listing."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.content_resolver.validate_s3_uri_format',
        return_value=('my-bucket', 'prefix/'),
    )
    async def test_rejects_traversal_in_s3_object_key(self, mock_validate, mock_get_session):
        """Property: S3 object keys that produce traversal relative paths are rejected."""
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_session.client.return_value = mock_s3
        mock_get_session.return_value = mock_session

        # Simulate S3 returning an object with a traversal key
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'prefix/../../../etc/passwd', 'Size': 10},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator
        mock_body = MagicMock()
        mock_body.read.return_value = b'malicious content'
        mock_s3.get_object.return_value = {'Body': mock_body}

        with pytest.raises(ValueError, match='Path traversal detected in S3 object key'):
            await resolve_bundle_content('s3://my-bucket/prefix/')

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.content_resolver.validate_s3_uri_format',
        return_value=('my-bucket', 'workflows/'),
    )
    async def test_allows_valid_s3_object_keys(self, mock_validate, mock_get_session):
        """Property: S3 object keys with valid relative paths are accepted."""
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_session.client.return_value = mock_s3
        mock_get_session.return_value = mock_session

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'workflows/main.wdl', 'Size': 20},
                    {'Key': 'workflows/tasks/align.wdl', 'Size': 15},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        def mock_get_object(Bucket, Key):
            body = MagicMock()
            body.read.return_value = b'workflow content'
            return {'Body': body}

        mock_s3.get_object.side_effect = mock_get_object

        result = await resolve_bundle_content('s3://my-bucket/workflows/')
        assert 'main.wdl' in result.files
        assert 'tasks/align.wdl' in result.files


class TestBundleLintingEndToEnd:
    """End-to-end tests verifying path traversal is blocked through the full linting pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.wdl_linter = WDLWorkflowLinter()
        self.cwl_linter = CWLWorkflowLinter()

    @pytest.mark.asyncio
    async def test_wdl_bundle_rejects_dotdot_in_file_path(self):
        """Property: WDL bundle linting rejects file paths with ../ traversal."""
        workflow_files = {
            '../../../etc/malicious.wdl': 'version 1.0\nworkflow evil {}',
            'main.wdl': 'version 1.0\nworkflow main {}',
        }

        result = await self.wdl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.wdl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_cwl_bundle_rejects_dotdot_in_file_path(self):
        """Property: CWL bundle linting rejects file paths with ../ traversal."""
        workflow_files = {
            '../../../etc/malicious.cwl': 'class: Workflow\ncwlVersion: v1.0',
            'main.cwl': 'class: Workflow\ncwlVersion: v1.0',
        }

        result = await self.cwl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.cwl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_rejects_absolute_path(self):
        """Property: WDL bundle linting rejects absolute file paths."""
        workflow_files = {
            '/tmp/malicious.wdl': 'version 1.0\nworkflow evil {}',
            'main.wdl': 'version 1.0\nworkflow main {}',
        }

        result = await self.wdl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.wdl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_cwl_bundle_rejects_absolute_path(self):
        """Property: CWL bundle linting rejects absolute file paths."""
        workflow_files = {
            '/tmp/malicious.cwl': 'class: Workflow\ncwlVersion: v1.0',
            'main.cwl': 'class: Workflow\ncwlVersion: v1.0',
        }

        result = await self.cwl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.cwl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_rejects_nested_traversal(self):
        """Property: WDL bundle linting rejects deeply nested ../ traversal."""
        workflow_files = {
            'subdir/../../outside.wdl': 'version 1.0\nworkflow evil {}',
            'main.wdl': 'version 1.0\nworkflow main {}',
        }

        result = await self.wdl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.wdl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_cwl_bundle_rejects_nested_traversal(self):
        """Property: CWL bundle linting rejects deeply nested ../ traversal."""
        workflow_files = {
            'subdir/../../outside.cwl': 'class: Workflow\ncwlVersion: v1.0',
            'main.cwl': 'class: Workflow\ncwlVersion: v1.0',
        }

        result = await self.cwl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.cwl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_rejects_traversal_in_main_workflow_file(self):
        """Property: WDL bundle linting rejects ../ traversal in main_workflow_file."""
        workflow_files = {
            'main.wdl': 'version 1.0\nworkflow main {}',
        }

        result = await self.wdl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='../../etc/passwd',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_cwl_bundle_rejects_traversal_in_main_workflow_file(self):
        """Property: CWL bundle linting rejects ../ traversal in main_workflow_file."""
        workflow_files = {
            'main.cwl': 'class: Workflow\ncwlVersion: v1.0',
        }

        result = await self.cwl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='../../etc/passwd',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_wdl_bundle_rejects_rce_via_module_overwrite(self):
        """Property: WDL bundle blocks RCE via Python module path overwrite.

        Validates: Attacker cannot overwrite site-packages/WDL/__init__.py
        which would execute on the subsequent 'python -m WDL check' call.
        """
        workflow_files = {
            '../../../../lib/python3.10/site-packages/WDL/__init__.py': (
                'import os; os.system("echo pwned")'
            ),
            'main.wdl': 'version 1.0\nworkflow main {}',
        }

        result = await self.wdl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.wdl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_cwl_bundle_rejects_rce_via_module_overwrite(self):
        """Property: CWL bundle blocks RCE via Python module path overwrite.

        Validates: Attacker cannot overwrite site-packages/cwltool/__init__.py
        which would execute on the subsequent 'python -m cwltool --validate' call.
        """
        workflow_files = {
            '../../../../lib/python3.10/site-packages/cwltool/__init__.py': (
                'import os; os.system("echo pwned")'
            ),
            'main.cwl': 'class: Workflow\ncwlVersion: v1.0',
        }

        result = await self.cwl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.cwl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']

    @pytest.mark.asyncio
    async def test_traversal_does_not_write_files(self):
        """Property: No files are written when traversal is detected.

        Validates: Error is returned BEFORE any file I/O occurs.
        """
        import tempfile

        canary_dir = tempfile.mkdtemp()
        canary_path = os.path.join(canary_dir, 'canary.txt')

        traversal_path = f'../../../..{canary_path}'

        workflow_files = {
            traversal_path: 'MALICIOUS CONTENT',
            'main.wdl': 'version 1.0\nworkflow main {}',
        }

        result = await self.wdl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='main.wdl',
        )

        assert result['status'] == 'error'
        assert 'Path traversal detected' in result['message']
        assert not os.path.exists(canary_path), 'Traversal attack wrote a file outside temp dir!'

        os.rmdir(canary_dir)

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_wdl_bundle_allows_valid_subdirectory_paths(self, mock_subprocess):
        """Property: WDL bundle linting allows legitimate nested file paths."""
        mock_result = MagicMock()
        mock_result.stdout = 'Valid'
        mock_result.stderr = ''
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        workflow_files = {
            'workflows/main.wdl': 'version 1.0\nworkflow main {}',
            'tasks/align.wdl': 'version 1.0\ntask align { command {} }',
            'structs/types.wdl': 'version 1.0\nstruct Sample { String name }',
        }

        result = await self.wdl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='workflows/main.wdl',
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_cwl_bundle_allows_valid_subdirectory_paths(self, mock_subprocess):
        """Property: CWL bundle linting allows legitimate nested file paths."""
        mock_result = MagicMock()
        mock_result.stdout = 'Valid'
        mock_result.stderr = ''
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        workflow_files = {
            'workflows/main.cwl': 'class: Workflow\ncwlVersion: v1.0',
            'tools/align.cwl': 'class: CommandLineTool\ncwlVersion: v1.0',
        }

        result = await self.cwl_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            main_workflow_file='workflows/main.cwl',
        )

        assert result['status'] == 'success'


class TestResolveBundleContentTraversal:
    """Tests for path traversal prevention through the resolve_bundle_content pipeline."""

    @pytest.mark.asyncio
    async def test_rejects_traversal_in_local_path(self):
        """Property: resolve_bundle_content rejects local paths with traversal.

        The path traversal is caught by detect_content_input_type which classifies
        the input as inline content (since it fails path validation). The bundle
        resolver then rejects inline content strings, effectively blocking the attack.
        """
        with pytest.raises(ValueError, match='Cannot resolve bundle from inline content'):
            await resolve_bundle_content('../../../etc')

    @pytest.mark.asyncio
    async def test_zip_with_traversal_entries_rejected(self):
        """Property: ZIP files containing traversal entries are rejected during extraction."""
        import tempfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('valid.wdl', 'workflow valid {}')
            zf.writestr('../../../etc/crontab', '* * * * * evil')

        # Write ZIP to a temp file and try to resolve it
        tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        tmp.write(buf.getvalue())
        tmp.close()

        try:
            with pytest.raises(ValueError, match='Path traversal detected in ZIP entry'):
                await resolve_bundle_content(tmp.name)
        finally:
            os.unlink(tmp.name)

    @pytest.mark.asyncio
    async def test_dict_passthrough_does_not_validate_keys(self):
        """Property: Dict passthrough preserves backward compatibility.

        Note: When a dict is passed directly, validation happens at the
        consumer level (e.g., lint_workflow_bundle), not in resolve_bundle_content.
        This is by design for backward compatibility.
        """
        # Dict passthrough should work without validation at this layer
        result = await resolve_bundle_content(
            {
                'main.wdl': 'workflow main {}',
                'tasks/align.wdl': 'task align {}',
            }
        )
        assert 'main.wdl' in result.files
        assert 'tasks/align.wdl' in result.files
