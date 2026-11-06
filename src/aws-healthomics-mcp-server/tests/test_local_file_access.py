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

"""Tests that network transports cannot read or write caller-selected local paths.

``conftest.stdio_local_file_access`` enables local access for every test (the
stdio startup state). Tests here that cover network transports use the explicit
``network_mode`` fixture to disable it.
"""

import base64
import io
import json
import os
import pathlib
import pytest
import subprocess  # nosec B404 - runs this interpreter on a fixed script
import sys
import zipfile
from awslabs.aws_healthomics_mcp_server import server
from awslabs.aws_healthomics_mcp_server.consts import (
    ERROR_LINT_UNAVAILABLE_OVER_NETWORK,
    ERROR_LOCAL_FILE_ACCESS_DISABLED,
)
from awslabs.aws_healthomics_mcp_server.tools import workflow_linting
from awslabs.aws_healthomics_mcp_server.tools.helper_tools import package_workflow
from awslabs.aws_healthomics_mcp_server.tools.workflow_management import (
    create_workflow,
    create_workflow_version,
)
from awslabs.aws_healthomics_mcp_server.utils import local_file_access
from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
    ContentInputType,
    _read_local_directory,
    _read_local_file,
    detect_content_input_type,
    resolve_bundle_content,
    resolve_single_content,
)
from awslabs.aws_healthomics_mcp_server.utils.local_file_access import (
    LocalFileAccessDisabledError,
    configure_local_file_access,
    is_local_file_access_allowed,
    looks_like_local_path,
)
from awslabs.aws_healthomics_mcp_server.utils.path_utils import (
    write_svg_to_local,
    write_zip_to_local,
)
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
    ReadmeInputType,
    detect_readme_input_type,
)
from unittest.mock import AsyncMock, MagicMock, patch


SAMPLE_WDL = 'version 1.0\nworkflow Test {\n  call A\n}\n'
SECRET = 'do-not-leak-7f3c'  # pragma: allowlist secret


def _zip_b64() -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr('main.wdl', SAMPLE_WDL)
    return base64.b64encode(buffer.getvalue()).decode('ascii')


ZIP_B64 = _zip_b64()


@pytest.fixture
def network_mode():
    """Disable local file access, as startup does for every network transport."""
    local_file_access._local_file_access_allowed = False
    yield
    # conftest.stdio_local_file_access restores the previous value.


def _called_from_server_code() -> bool:
    """Return whether any frame on the current stack belongs to the server package."""
    frame = sys._getframe(2)
    while frame is not None:
        if frame.f_globals.get('__name__', '').startswith('awslabs.'):
            return True
        frame = frame.f_back
    return False


@pytest.fixture
def no_fs_probes(monkeypatch):
    """Fail the test if anything stats, probes, or opens a path.

    ``os.path``, ``os.walk``, ``os.access`` and ``builtins.open`` fail on any call.
    The lower-level ``os.stat``/``os.lstat``/``os.scandir``/``os.listdir``,
    ``io.open``, and ``pathlib.Path`` probes are also used by pytest itself
    (failure reporting, ``linecache``), so they fail only when reached from
    server code and otherwise delegate to the real function.
    """

    def _forbidden(*_args, **_kwargs):
        raise AssertionError('filesystem was probed')

    def _forbidden_from_server(real):
        def _guard(*args, **kwargs):
            if _called_from_server_code():
                raise AssertionError('filesystem was probed')
            return real(*args, **kwargs)

        return _guard

    for name in ('isfile', 'isdir', 'exists', 'getsize'):
        monkeypatch.setattr(os.path, name, _forbidden)
    monkeypatch.setattr(os, 'access', _forbidden)
    monkeypatch.setattr(os, 'walk', _forbidden)
    monkeypatch.setattr('builtins.open', _forbidden)

    for name in ('stat', 'lstat', 'scandir', 'listdir'):
        monkeypatch.setattr(os, name, _forbidden_from_server(getattr(os, name)))
    monkeypatch.setattr(io, 'open', _forbidden_from_server(io.open))
    for name in (
        'exists',
        'is_file',
        'is_dir',
        'stat',
        'lstat',
        'open',
        'read_text',
        'read_bytes',
        'iterdir',
    ):
        monkeypatch.setattr(
            pathlib.Path, name, _forbidden_from_server(getattr(pathlib.Path, name))
        )


@pytest.fixture
def secret_files(tmp_path, monkeypatch):
    """Create local files a network caller might try to name, and chdir to them."""
    (tmp_path / 'main.wdl').write_text(SECRET)
    (tmp_path / 'README.md').write_text(SECRET)
    (tmp_path / 'wf.zip').write_bytes(base64.b64decode(ZIP_B64))
    (tmp_path / 'dir').mkdir()
    (tmp_path / 'dir' / 'main.cwl').write_text(SECRET)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _s3_session(body: bytes) -> MagicMock:
    s3 = MagicMock()
    s3.head_object.return_value = {'ContentLength': len(body)}
    s3.get_object.return_value = {'Body': MagicMock(read=MagicMock(return_value=body))}
    session = MagicMock()
    session.client.return_value = s3
    return session


# ---------------------------------------------------------------------------
# Policy module and startup wiring
# ---------------------------------------------------------------------------


def test_module_default_is_fail_closed_for_direct_tool_import(tmp_path):
    """A fresh interpreter that imports and calls a tool cannot read a local file."""
    target = tmp_path / 'main.wdl'
    target.write_text(SECRET)
    script = (
        'import asyncio\n'
        'from unittest.mock import AsyncMock\n'
        'from awslabs.aws_healthomics_mcp_server.utils import local_file_access as p\n'
        'assert p.is_local_file_access_allowed() is False\n'
        'from awslabs.aws_healthomics_mcp_server.tools.helper_tools import package_workflow\n'
        'r = asyncio.run(package_workflow(ctx=AsyncMock(), main_file_content=%r,\n'
        "    main_file_name='main.wdl', additional_files=None, output_path=None))\n"
        "assert isinstance(r, dict) and 'error' in r, r\n"
        'assert %r not in str(r)\n'
        "print('ok')\n"
    ) % (str(target), SECRET)
    result = subprocess.run(  # nosec B603 - fixed interpreter and script, no shell
        [sys.executable, '-c', script], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith('ok')


@pytest.mark.parametrize(
    'transport,allowed', [('stdio', True), ('streamable-http', False), ('sse', False)]
)
def test_configure_local_file_access(transport, allowed):
    """Only stdio enables local file access."""
    configure_local_file_access(transport)
    assert is_local_file_access_allowed() is allowed


@pytest.mark.parametrize(
    'argv,allowed',
    [
        (['--transport', 'stdio'], True),
        (['--transport', 'streamable-http'], False),
        (['--transport', 'sse'], False),
    ],
)
def test_main_sets_access_before_serving_single_tenant(monkeypatch, argv, allowed):
    """main() configures local access before the transport starts serving."""
    local_file_access._local_file_access_allowed = not allowed
    monkeypatch.setattr(sys, 'argv', ['awslabs.aws-healthomics-mcp-server', *argv])
    seen = []
    with patch.object(
        server.TransportSelector,
        'start',
        side_effect=lambda *_a, **_k: seen.append(is_local_file_access_allowed()),
    ):
        server.main()
    assert seen == [allowed]


@pytest.mark.parametrize('transport', ['streamable-http', 'sse'])
def test_main_disables_access_before_serving_multi_tenant(monkeypatch, transport):
    """Multi-tenant network servers also start with local access disabled."""
    monkeypatch.setattr(
        sys,
        'argv',
        ['awslabs.aws-healthomics-mcp-server', '--transport', transport, '--multi-tenant', 'true'],
    )
    seen = []
    with patch.object(
        server,
        '_run_multi_tenant',
        side_effect=lambda *_a, **_k: seen.append(is_local_file_access_allowed()),
    ):
        server.main()
    assert seen == [False]


# ---------------------------------------------------------------------------
# Classification without filesystem probes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'value',
    [
        '/proc/self/environ',
        '/etc/passwd',
        '/tmp/some dir/with spaces',
        'main.wdl',
        'README.md',
        'dir/main.cwl',
        'workflow.ZIP',
        'params.json',
        'conf/a.yml',
        'conf/b.yaml',
        'main.nf',
        '~/x.wdl',
    ],
)
def test_looks_like_local_path_matches_path_attempts(value):
    """Absolute paths and suffixed whitespace-free relative paths are path attempts."""
    assert looks_like_local_path(value) is True


@pytest.mark.parametrize(
    'value',
    [
        '',
        SAMPLE_WDL,
        '/* comment */\nworkflow',
        ZIP_B64,
        '# Title\n\nSee main.wdl',
        'Use main.wdl for details.md',
        '.md',
        'just-text',
        'https://example.com/main.wdl',
    ],
)
def test_looks_like_local_path_keeps_inline_content(value):
    """Multi-line text, base64, sentences, and URLs stay inline content."""
    assert looks_like_local_path(value) is False


def test_detect_content_input_type_never_probes(network_mode, no_fs_probes):
    """No-access classification is a pure string check; S3 is detected first."""
    assert detect_content_input_type('s3://bucket/main.wdl') == ContentInputType.S3_URI
    assert detect_content_input_type('/proc/self/environ') == ContentInputType.LOCAL_FILE
    assert detect_content_input_type('main.wdl') == ContentInputType.LOCAL_FILE
    assert detect_content_input_type('workflows') == ContentInputType.INLINE_CONTENT
    assert detect_content_input_type(SAMPLE_WDL) == ContentInputType.INLINE_CONTENT
    assert detect_content_input_type(ZIP_B64) == ContentInputType.INLINE_CONTENT


def test_detect_readme_input_type_never_probes(network_mode, no_fs_probes):
    """README classification in no-access mode never touches the filesystem."""
    assert detect_readme_input_type('s3://bucket/README.md') == ReadmeInputType.S3_URI
    assert detect_readme_input_type('README.md') == ReadmeInputType.LOCAL_FILE
    assert detect_readme_input_type('/etc/README.md') == ReadmeInputType.LOCAL_FILE
    assert detect_readme_input_type('/etc/passwd') == ReadmeInputType.LOCAL_FILE
    assert detect_readme_input_type('/proc/self/environ') == ReadmeInputType.LOCAL_FILE
    assert detect_readme_input_type('docs/main.wdl') == ReadmeInputType.LOCAL_FILE
    assert detect_readme_input_type('# Title\n\nBody') == ReadmeInputType.MARKDOWN_CONTENT
    assert detect_readme_input_type('# /etc/passwd\n\nBody') == ReadmeInputType.MARKDOWN_CONTENT
    assert detect_readme_input_type('Plain one-line README') == ReadmeInputType.MARKDOWN_CONTENT


def test_detect_readme_input_type_stdio_requires_existing_md(tmp_path, monkeypatch):
    """Over stdio only an existing .md file is LOCAL_FILE; other paths stay markdown."""
    (tmp_path / 'README.md').write_text('# Title')
    monkeypatch.chdir(tmp_path)
    assert detect_readme_input_type('README.md') == ReadmeInputType.LOCAL_FILE
    assert detect_readme_input_type('missing.md') == ReadmeInputType.MARKDOWN_CONTENT
    assert detect_readme_input_type('/etc/passwd') == ReadmeInputType.MARKDOWN_CONTENT


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['/proc/self/environ', 'main.wdl', 'README.md', 'dir/main.cwl'])
async def test_resolve_single_content_rejects_paths(network_mode, no_fs_probes, value):
    """Path attempts are rejected before any filesystem access."""
    with pytest.raises(LocalFileAccessDisabledError) as excinfo:
        await resolve_single_content(value)
    assert str(excinfo.value) == ERROR_LOCAL_FILE_ACCESS_DISABLED


@pytest.mark.asyncio
async def test_resolve_bundle_content_rejects_paths(network_mode, no_fs_probes):
    """Bundle resolution rejects local ZIP paths without probing."""
    with pytest.raises(LocalFileAccessDisabledError):
        await resolve_bundle_content('/srv/bundle.zip')


def test_private_readers_require_access(network_mode, no_fs_probes):
    """The private local readers fail closed even if called directly."""
    with pytest.raises(LocalFileAccessDisabledError):
        _read_local_file('/etc/hostname', 'text', None)
    with pytest.raises(LocalFileAccessDisabledError):
        _read_local_directory('/etc', None)


@pytest.mark.asyncio
async def test_inline_base64_and_s3_unaffected(network_mode, no_fs_probes):
    """Inline text, base64, and S3 input keep working over a network transport."""
    text = await resolve_single_content(SAMPLE_WDL, mode='text')
    assert text.content == SAMPLE_WDL

    binary = await resolve_single_content(ZIP_B64, mode='binary')
    assert binary.content == base64.b64decode(ZIP_B64)

    with patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session',
        return_value=_s3_session(SAMPLE_WDL.encode()),
    ):
        s3 = await resolve_single_content('s3://my-bucket/main.wdl', mode='text')
    assert s3.content == SAMPLE_WDL
    assert s3.input_type == ContentInputType.S3_URI


# ---------------------------------------------------------------------------
# Local writes
# ---------------------------------------------------------------------------


def test_write_helpers_require_access(network_mode, tmp_path):
    """Local write helpers fail closed and create nothing."""
    with pytest.raises(LocalFileAccessDisabledError):
        write_zip_to_local(b'PK', str(tmp_path / 'out' / 'wf.zip'))
    with pytest.raises(LocalFileAccessDisabledError):
        write_svg_to_local('<svg/>', str(tmp_path / 'out' / 'timeline.svg'))
    assert not (tmp_path / 'out').exists()


# ---------------------------------------------------------------------------
# PackageAHOWorkflow
# ---------------------------------------------------------------------------


async def _package(**overrides):
    kwargs = {
        'ctx': AsyncMock(),
        'main_file_content': SAMPLE_WDL,
        'main_file_name': 'main.wdl',
        'additional_files': None,
        'output_path': None,
    }
    kwargs.update(overrides)
    return await package_workflow(**kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['/proc/self/environ', 'main.wdl', 'dir/main.cwl'])
async def test_package_main_file_path_blocked(network_mode, secret_files, value):
    """main_file_content cannot name a local file."""
    result = await _package(main_file_content=value)
    assert isinstance(result, dict)
    assert ERROR_LOCAL_FILE_ACCESS_DISABLED in result['error']
    assert SECRET not in str(result)


@pytest.mark.asyncio
async def test_package_additional_file_path_blocked(network_mode, secret_files):
    """additional_files values cannot name a local file."""
    result = await _package(additional_files={'README.md': 'README.md'})
    assert isinstance(result, dict)
    assert ERROR_LOCAL_FILE_ACCESS_DISABLED in result['error']
    assert SECRET not in str(result)


@pytest.mark.asyncio
async def test_package_local_output_path_blocked(network_mode, tmp_path):
    """A local output_path is rejected and nothing is written."""
    target = tmp_path / 'out.zip'
    result = await _package(output_path=str(target))
    assert ERROR_LOCAL_FILE_ACCESS_DISABLED in result
    assert not target.exists()


@pytest.mark.asyncio
async def test_package_local_output_path_fails_before_resolving_inputs(network_mode, tmp_path):
    """A local output_path fails before input resolution (S3 reads) or STS lookups."""
    target = tmp_path / 'out.zip'
    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.resolve_single_content',
            new_callable=AsyncMock,
        ) as mock_resolve,
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_account_id',
        ) as mock_account,
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.create_zip_file',
        ) as mock_zip,
    ):
        result = await _package(
            main_file_content='s3://bucket/main.wdl',
            additional_files={'tasks.wdl': 's3://bucket/tasks.wdl'},
            output_path=str(target),
        )
    assert isinstance(result, str)
    assert json.loads(result) == {
        'error': f'Error writing packaged workflow: {ERROR_LOCAL_FILE_ACCESS_DISABLED}'
    }
    mock_resolve.assert_not_called()
    mock_account.assert_not_called()
    mock_zip.assert_not_called()
    assert not target.exists()


@pytest.mark.parametrize('output_path', [None, 's3://bucket/out.zip'])
def test_require_local_output_access_allows_none_and_s3(network_mode, output_path):
    """None and S3 destinations pass the early local-output check over a network transport."""
    local_file_access.require_local_output_access(output_path)


@pytest.mark.parametrize('output_path', ['/tmp/out.svg', 'out.svg', 'relative dir/out'])
def test_require_local_output_access_rejects_local(network_mode, output_path):
    """Any non-S3 output_path is rejected over a network transport without probing."""
    with pytest.raises(LocalFileAccessDisabledError):
        local_file_access.require_local_output_access(output_path)


# ---------------------------------------------------------------------------
# GenerateAHORunTimeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_local_output_path_blocked_before_aws(network_mode, tmp_path):
    """A local output_path fails before any AWS or pricing work and creates no file."""
    from awslabs.aws_healthomics_mcp_server.tools.run_timeline import generate_run_timeline
    from tests.test_helpers import MCPToolTestWrapper
    from tests.test_run_timeline_output import _build_timeline_mocks

    target = tmp_path / 'out' / 'timeline.svg'
    mock_omics_client, mock_logs, ctx = _build_timeline_mocks()
    module = 'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
    with (
        patch(f'{module}.get_omics_client', return_value=mock_omics_client) as mock_get_client,
        patch(
            f'{module}.get_run_manifest_logs_internal',
            new_callable=AsyncMock,
            return_value=mock_logs,
        ) as mock_manifest,
        patch(f'{module}.CostAnalyzer') as mock_cost,
        patch(f'{module}.get_account_id') as mock_account,
    ):
        result = await MCPToolTestWrapper(generate_run_timeline).call(
            ctx, run_id='test-run', output_path=str(target)
        )
    assert json.loads(result) == {
        'error': f'Error writing timeline output: {ERROR_LOCAL_FILE_ACCESS_DISABLED}'
    }
    mock_get_client.assert_not_called()
    mock_omics_client.get_run.assert_not_called()
    mock_manifest.assert_not_called()
    mock_cost.assert_not_called()
    mock_account.assert_not_called()
    assert not target.exists()
    assert not target.parent.exists()


@pytest.mark.asyncio
async def test_package_inline_returns_zip_in_response(network_mode, no_fs_probes):
    """Inline content without output_path returns the ZIP in the response."""
    result = await _package(additional_files={'tasks.wdl': 'task A {\n}\n'})
    assert isinstance(result, str)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(result))) as zf:
        assert sorted(zf.namelist()) == ['main.wdl', 'tasks.wdl']


# ---------------------------------------------------------------------------
# CreateAHOWorkflow / CreateAHOWorkflowVersion
# ---------------------------------------------------------------------------


def _omics_client() -> MagicMock:
    client = MagicMock()
    client.create_workflow.return_value = {'id': 'wfl-1', 'arn': 'arn', 'status': 'CREATING'}
    client.create_workflow_version.return_value = {
        'id': 'wfl-1',
        'arn': 'arn',
        'status': 'CREATING',
        'name': 'wf',
    }
    return client


async def _create(tool, **kwargs):
    client = _omics_client()
    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=client,
    ):
        if tool == 'workflow':
            result = await create_workflow(ctx=AsyncMock(), name='wf', **kwargs)
        else:
            result = await create_workflow_version(
                ctx=AsyncMock(), workflow_id='wfl-1', version_name='v2', **kwargs
            )
    return result, client


@pytest.mark.asyncio
@pytest.mark.parametrize('tool', ['workflow', 'version'])
@pytest.mark.parametrize('source', ['wf.zip', '/srv/wf.zip'])
async def test_definition_source_path_blocked(network_mode, secret_files, tool, source):
    """definition_source cannot name a local ZIP."""
    result, client = await _create(tool, definition_source=source)
    assert ERROR_LOCAL_FILE_ACCESS_DISABLED in result['error']
    client.create_workflow.assert_not_called()
    client.create_workflow_version.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('tool', ['workflow', 'version'])
@pytest.mark.parametrize('readme', ['README.md', '/etc/README.md', '/etc/passwd'])
async def test_readme_path_blocked(network_mode, secret_files, tool, readme):
    """The readme argument cannot name a local .md file."""
    result, client = await _create(tool, definition_source=ZIP_B64, readme=readme)
    assert ERROR_LOCAL_FILE_ACCESS_DISABLED in result['error']
    assert SECRET not in str(result)
    client.create_workflow.assert_not_called()
    client.create_workflow_version.assert_not_called()


@pytest.mark.asyncio
async def test_create_workflow_inline_definition_and_readme(network_mode, no_fs_probes):
    """Base64 definitions and markdown READMEs keep working over a network transport."""
    result, client = await _create('workflow', definition_source=ZIP_B64, readme='# Title\n\nBody')
    assert 'error' not in result
    kwargs = client.create_workflow.call_args.kwargs
    assert kwargs['definitionZip'] == base64.b64decode(ZIP_B64)
    assert kwargs['readmeMarkdown'] == '# Title\n\nBody'


# ---------------------------------------------------------------------------
# Lint tools
# ---------------------------------------------------------------------------


@pytest.fixture
def no_lint_work(monkeypatch):
    """Fail the test if lint resolves content, creates temp files, or runs a linter."""

    def _forbidden(*_args, **_kwargs):
        raise AssertionError('lint did work before failing closed')

    monkeypatch.setattr(workflow_linting, 'resolve_single_content', _forbidden)
    monkeypatch.setattr(workflow_linting, 'resolve_bundle_content', _forbidden)
    monkeypatch.setattr(workflow_linting, 'get_linter', _forbidden)
    monkeypatch.setattr(workflow_linting.tempfile, 'NamedTemporaryFile', _forbidden)
    monkeypatch.setattr(workflow_linting.tempfile, 'TemporaryDirectory', _forbidden)
    monkeypatch.setattr(subprocess, 'run', _forbidden)


@pytest.mark.asyncio
@pytest.mark.parametrize('content', [SAMPLE_WDL, 's3://bucket/main.wdl', '/etc/main.wdl'])
async def test_lint_definition_fails_closed(network_mode, no_lint_work, content):
    """LintAHOWorkflowDefinition returns the lint error schema before doing any work."""
    ctx = AsyncMock()
    result = await workflow_linting.lint_workflow_definition(
        ctx=ctx, workflow_content=content, workflow_format='WDL', filename=None
    )
    assert result == {
        'status': 'error',
        'format': 'wdl',
        'message': ERROR_LINT_UNAVAILABLE_OVER_NETWORK,
    }
    ctx.error.assert_awaited_once_with(ERROR_LINT_UNAVAILABLE_OVER_NETWORK)


@pytest.mark.asyncio
@pytest.mark.parametrize('files', [{'main.cwl': 'cwlVersion: v1.2'}, 's3://bucket/prefix/'])
async def test_lint_bundle_fails_closed(network_mode, no_lint_work, files):
    """LintAHOWorkflowBundle returns the lint error schema before doing any work."""
    result = await workflow_linting.lint_workflow_bundle(
        ctx=AsyncMock(),
        workflow_files=files,
        workflow_format='cwl',
        main_workflow_file='main.cwl',
    )
    assert result == {
        'status': 'error',
        'format': 'cwl',
        'message': ERROR_LINT_UNAVAILABLE_OVER_NETWORK,
    }


# ---------------------------------------------------------------------------
# stdio behavior is unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stdio_reads_relative_local_file(secret_files):
    """Over stdio a relative local path is still read."""
    assert detect_content_input_type('main.wdl') == ContentInputType.LOCAL_FILE
    resolved = await resolve_single_content('main.wdl')
    assert resolved.content == SECRET
    assert detect_readme_input_type('README.md') == ReadmeInputType.LOCAL_FILE


@pytest.mark.asyncio
async def test_stdio_package_reads_paths_and_writes_output(secret_files):
    """Over stdio PackageAHOWorkflow still reads local inputs and writes local output."""
    result = await _package(
        main_file_content='main.wdl',
        additional_files={'tasks.cwl': 'dir/main.cwl'},
        output_path='out/wf.zip',
    )
    assert '"status": "success"' in result
    with zipfile.ZipFile(secret_files / 'out' / 'wf.zip') as zf:
        assert zf.read('main.wdl').decode() == SECRET
        assert zf.read('tasks.cwl').decode() == SECRET


@pytest.mark.asyncio
async def test_stdio_lint_still_runs_linter():
    """Over stdio the lint tools still resolve content and call the linter."""
    linter = AsyncMock()
    linter.lint_workflow.return_value = {'status': 'success', 'format': 'wdl'}
    with patch.object(workflow_linting, 'get_linter', return_value=linter):
        result = await workflow_linting.lint_workflow_definition(
            ctx=AsyncMock(), workflow_content=SAMPLE_WDL, workflow_format='wdl', filename=None
        )
    assert result == {'status': 'success', 'format': 'wdl'}
    linter.lint_workflow.assert_awaited_once()
