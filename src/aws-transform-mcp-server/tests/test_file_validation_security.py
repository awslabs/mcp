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

"""Regression coverage for credential path blocklist gaps."""
# ruff: noqa: D103

import json
import os
import pytest
from awslabs.aws_transform_mcp_server import file_validation, upload_helper
from awslabs.aws_transform_mcp_server.tools import artifact, hitl
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def dummy_home(tmp_path, monkeypatch):
    """Relocate credential directory rules without reading the user's real home."""
    home = tmp_path / 'home'
    home.mkdir()
    original_home = file_validation._HOME
    blocked = tuple(
        str(home) + entry[len(original_home) :]
        if entry.startswith(original_home + os.sep)
        else entry
        for entry in file_validation.BLOCKED_READ_DIRS
    )
    monkeypatch.setattr(file_validation, 'BLOCKED_READ_DIRS', blocked)
    monkeypatch.setattr(file_validation, '_ALLOWED_WRITE_BASE', str(home))
    return home


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
@pytest.mark.parametrize(
    'relative', ['.AWS/sso/cache/token.json', '.SSH/config', '.SSH/probe_key']
)
def test_recased_sensitive_directories_are_blocked(dummy_home, monkeypatch, platform, relative):
    monkeypatch.setattr(file_validation.sys, 'platform', platform)
    with pytest.raises(ValueError, match='sensitive directory'):
        file_validation.validate_read_path(str(dummy_home / relative))


def test_linux_denylist_comparison_preserves_case(dummy_home, monkeypatch):
    monkeypatch.setattr(file_validation.sys, 'platform', 'linux')
    assert file_validation._in_blocked_dir(str(dummy_home / '.ssh/config'))
    assert not file_validation._in_blocked_dir(str(dummy_home / '.SSH/config'))


def test_similarly_named_directory_is_not_blocked(dummy_home):
    assert not file_validation._in_blocked_dir(str(dummy_home / '.ssh-backup/report.txt'))


@pytest.mark.parametrize(
    'relative',
    [
        '.kube/config',
        '.config/gcloud/application_default_credentials.json',
        '.azure/accessTokens.json',
        '.config/gh/hosts.yml',
        '.terraform.d/credentials.tfrc.json',
        '.config/terraform/credentials.tfrc.json',
    ],
)
def test_additional_credential_locations_are_blocked(dummy_home, relative):
    with pytest.raises(ValueError, match='sensitive directory'):
        file_validation.validate_read_path(str(dummy_home / relative))


def test_terraformrc_is_blocked(dummy_home):
    with pytest.raises(ValueError, match='Blocked filename'):
        file_validation.validate_read_path(str(dummy_home / '.terraformrc'))


@pytest.mark.parametrize(
    'path', ['/etc/passwd', '/etc/shadow', '/etc/master.passwd', '/etc/gshadow']
)
def test_system_paths_are_blocked_after_resolution(path):
    # Path validation only: no system file is opened.
    with pytest.raises(ValueError, match='sensitive directory'):
        file_validation.validate_read_path(path)
    with pytest.raises(ValueError, match='sensitive directory'):
        file_validation.validate_read_path(os.path.realpath(path))


def test_symlinked_sensitive_directory_is_blocked(dummy_home, tmp_path):
    target = tmp_path / 'ssh-target'
    target.mkdir()
    (dummy_home / '.ssh').symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='sensitive directory'):
        file_validation.validate_read_path(str(dummy_home / '.ssh/config'))


@pytest.mark.parametrize('path_kind', ['absolute', 'relative', 'symlink'])
def test_safe_files_outside_working_directory_remain_allowed(tmp_path, monkeypatch, path_kind):
    working = tmp_path / 'server'
    working.mkdir()
    outside = tmp_path / 'report.txt'
    outside.write_text('DUMMY')
    monkeypatch.chdir(working)
    if path_kind == 'absolute':
        requested = str(outside)
    elif path_kind == 'relative':
        requested = '../report.txt'
    else:
        link = working / 'report-link.txt'
        link.symlink_to(outside)
        requested = str(link)
    assert file_validation.validate_read_path(requested) == str(outside)


def test_recased_sensitive_download_directory_is_blocked(dummy_home, monkeypatch):
    monkeypatch.setattr(file_validation.sys, 'platform', 'darwin')
    with pytest.raises(ValueError, match='sensitive directory'):
        file_validation.validate_write_path(str(dummy_home / '.SSH'), 'config')


@pytest.mark.parametrize('relative', ['.SSH/config', '.kube/config', '.config/gh/hosts.yml'])
async def test_upload_handler_blocks_before_read_or_network(
    dummy_home, monkeypatch, relative, mock_context
):
    path = dummy_home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('DUMMY-NOT-A-CREDENTIAL')
    monkeypatch.setattr(file_validation.sys, 'platform', 'darwin')
    with (
        patch.object(artifact, 'is_fes_available', return_value=True),
        patch.object(artifact, 'call_transform_api', new_callable=AsyncMock) as api,
        patch.object(artifact.httpx, 'AsyncClient') as http_client,
        patch('builtins.open') as open_file,
    ):
        result = await artifact.ArtifactHandler(MagicMock()).upload_artifact(
            mock_context, workspaceId='test-workspace', jobId='test-job', content=str(path)
        )
    assert json.loads(result['content'][0]['text'])['success'] is False
    open_file.assert_not_called()
    api.assert_not_called()
    http_client.assert_not_called()


async def test_upload_handler_accepts_file_outside_working_directory(
    tmp_path, monkeypatch, mock_context
):
    working = tmp_path / 'server'
    working.mkdir()
    outside = tmp_path / 'outside.txt'
    outside.write_bytes(b'DUMMY')
    monkeypatch.chdir(working)
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.put.return_value = MagicMock(status_code=200)
    with (
        patch.object(artifact, 'is_fes_available', return_value=True),
        patch.object(
            artifact,
            'call_transform_api',
            new_callable=AsyncMock,
            side_effect=[
                {'artifactId': 'test-artifact', 's3PreSignedUrl': 'https://example.com/upload'},
                {},
            ],
        ) as api,
        patch.object(artifact.httpx, 'AsyncClient', return_value=client),
    ):
        result = await artifact.ArtifactHandler(MagicMock()).upload_artifact(
            mock_context, workspaceId='test-workspace', jobId='test-job', content=str(outside)
        )
    assert json.loads(result['content'][0]['text'])['success'] is True
    assert client.put.call_args.kwargs['content'] == b'DUMMY'
    assert [call.args[0] for call in api.call_args_list] == [
        'CreateArtifactUploadUrl',
        'CompleteArtifactUpload',
    ]


async def test_file_upload_helper_blocks_before_read_or_upload(dummy_home):
    path = dummy_home / '.kube/config'
    path.parent.mkdir()
    path.write_text('DUMMY')
    with (
        patch.object(upload_helper, 'call_transform_api', new_callable=AsyncMock) as api,
        patch.object(upload_helper.httpx, 'AsyncClient') as http_client,
        patch('builtins.open') as open_file,
        pytest.raises(ValueError, match='sensitive directory'),
    ):
        await upload_helper.upload_file_artifact('test-workspace', 'test-job', str(path))
    api.assert_not_called()
    http_client.assert_not_called()
    open_file.assert_not_called()


@pytest.mark.parametrize('relative', ['.SSH/config', '.config/gcloud/credentials.json'])
async def test_complete_task_cannot_upload_sensitive_file(
    dummy_home, monkeypatch, relative, mock_context
):
    path = dummy_home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('DUMMY')
    monkeypatch.setattr(file_validation.sys, 'platform', 'darwin')
    task = {'taskId': 'test-task', 'uxComponentId': 'TextInput', 'severity': 'STANDARD'}
    with (
        patch.object(hitl, 'is_fes_available', return_value=True),
        patch.object(
            hitl, 'call_transform_api', new_callable=AsyncMock, return_value={'task': task}
        ) as api,
        patch.object(hitl, 'upload_file_artifact', new_callable=AsyncMock) as file_upload,
        patch.object(hitl, 'upload_json_artifact', new_callable=AsyncMock) as json_upload,
        patch('builtins.open') as open_file,
    ):
        result = await hitl.HitlHandler(MagicMock()).complete_task(
            mock_context,
            workspaceId='test-workspace',
            jobId='test-job',
            taskId='test-task',
            filePath=str(path),
        )
    assert json.loads(result['content'][0]['text'])['success'] is False
    assert [call.args[0] for call in api.call_args_list] == ['GetHitlTask']
    file_upload.assert_not_called()
    json_upload.assert_not_called()
    open_file.assert_not_called()
