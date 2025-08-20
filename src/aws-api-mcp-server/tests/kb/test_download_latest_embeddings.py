import json
import pytest
import subprocess
import sys
import tempfile
from awscli.clidriver import __version__ as awscli_version
from awslabs.aws_api_mcp_server.scripts.download_latest_embeddings import (
    check_embeddings_file,
    check_gh_cli,
    check_local_embeddings,
    cleanup,
    copy_embeddings_file,
    download_artifact,
    get_latest_artifact,
    is_within_directory,
    run_command,
    safe_extract_tar,
    safe_extract_zip,
    try_download_latest_embeddings,
)
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


def test_run_command_success():
    """Test run_command with successful command execution."""
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'success output'
        mock_result.stderr = ''
        mock_run.return_value = mock_result

        result = run_command(['echo', 'test'])

        mock_run.assert_called_once_with(
            ['echo', 'test'], capture_output=True, text=True, check=True
        )
        assert result == mock_result


def test_run_command_with_stderr():
    """Test run_command with stderr output."""
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'success output'
        mock_result.stderr = 'warning message'
        mock_run.return_value = mock_result

        result = run_command(['echo', 'test'])

        # Should print stderr but not raise exception
        assert result == mock_result


def test_run_command_failure():
    """Test run_command with command failure."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=['echo', 'test'], output='error output', stderr='error message'
        )

        with pytest.raises(subprocess.CalledProcessError):
            run_command(['echo', 'test'])


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.run_command')
def test_get_latest_artifact_success(mock_run_command):
    """Test successful artifact retrieval."""
    mock_result = MagicMock()
    mock_result.stdout = json.dumps(
        {
            'artifacts': [
                {
                    'id': 123,
                    'created_at': '2023-01-01T00:00:00Z',
                    'workflow_run': {'head_branch': 'main'},
                }
            ]
        }
    )
    mock_run_command.return_value = mock_result

    artifact = get_latest_artifact()

    assert artifact is not None
    assert artifact['id'] == 123
    mock_run_command.assert_called_once()


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.run_command')
def test_get_latest_artifact_no_main_branch(mock_run_command):
    """Test when no main branch artifacts exist."""
    mock_result = MagicMock()
    mock_result.stdout = json.dumps(
        {
            'artifacts': [
                {
                    'id': 123,
                    'created_at': '2023-01-01T00:00:00Z',
                    'workflow_run': {'head_branch': 'feature'},
                }
            ]
        }
    )
    mock_run_command.return_value = mock_result

    artifact = get_latest_artifact()

    assert artifact is None


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.run_command')
def test_get_latest_artifact_no_artifacts(mock_run_command):
    """Test when no artifacts exist."""
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({'artifacts': []})
    mock_run_command.return_value = mock_result

    artifact = get_latest_artifact()

    assert artifact is None


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.run_command')
def test_get_latest_artifact_command_failure(mock_run_command):
    """Test when GitHub API command fails."""
    mock_run_command.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=['gh', 'api'], output='', stderr='API error'
    )

    artifact = get_latest_artifact()

    assert artifact is None


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.run_command')
def test_get_latest_artifact_invalid_json(mock_run_command):
    """Test when GitHub API returns invalid JSON."""
    mock_result = MagicMock()
    mock_result.stdout = 'invalid json'
    mock_run_command.return_value = mock_result

    artifact = get_latest_artifact()

    assert artifact is None


def test_is_within_directory_true():
    """Test when target is within directory."""
    directory = Path('/tmp/test')
    target = Path('/tmp/test/subdir/file.txt')

    result = is_within_directory(directory, target)
    assert result is True


def test_is_within_directory_false():
    """Test when target is outside directory."""
    directory = Path('/tmp/test')
    target = Path('/other/path/file.txt')

    result = is_within_directory(directory, target)
    assert result is False


def test_is_within_directory_exception():
    """Test when resolve raises exception."""
    directory = Path('/tmp/test')
    target = Path('/tmp/test/file.txt')

    with patch.object(Path, 'resolve', side_effect=Exception('resolve error')):
        result = is_within_directory(directory, target)
        assert result is False


def test_safe_extract_zip_normal_file():
    """Test safe extraction of normal file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a mock zip file
        mock_zip = MagicMock()
        mock_zip.namelist.return_value = ['test.txt']

        with patch('builtins.open', mock_open()):
            safe_extract_zip(mock_zip, temp_path)

            # Should create parent directories
            assert (temp_path / 'test.txt').parent.exists()


def test_safe_extract_zip_path_traversal():
    """Test that path traversal is prevented."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a mock zip file with path traversal
        mock_zip = MagicMock()
        mock_zip.namelist.return_value = ['../../../etc/passwd']

        with pytest.raises(Exception, match='Unsafe zip file member'):
            safe_extract_zip(mock_zip, temp_path)


def test_safe_extract_tar_normal_file():
    """Test safe extraction of normal file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a mock tar file
        mock_tar = MagicMock()
        mock_member = MagicMock()
        mock_member.name = 'test.txt'
        mock_tar.getmembers.return_value = [mock_member]

        safe_extract_tar(mock_tar, temp_path)

        mock_tar.extract.assert_called_once_with(mock_member, temp_path)


def test_safe_extract_tar_path_traversal():
    """Test that path traversal is prevented."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a mock tar file with path traversal
        mock_tar = MagicMock()
        mock_member = MagicMock()
        mock_member.name = '../../../etc/passwd'
        mock_tar.getmembers.return_value = [mock_member]

        with pytest.raises(Exception, match='Unsafe tar file member'):
            safe_extract_tar(mock_tar, temp_path)


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.subprocess.run')
@patch('zipfile.ZipFile')
@patch('tarfile.open')
@patch('builtins.open', new_callable=mock_open)
def test_download_artifact_success(mock_file_open, mock_tar_open, mock_zip_file, mock_run):
    """Test successful artifact download and extraction."""
    # Mock subprocess.run for download
    mock_result = MagicMock()
    mock_result.stdout = b'fake zip content'
    mock_run.return_value = mock_result

    # Mock zip file
    mock_zip = MagicMock()
    mock_zip.namelist.return_value = ['artifact.tar.gz']
    mock_zip_file.return_value.__enter__.return_value = mock_zip

    # Mock tar file
    mock_tar = MagicMock()
    mock_tar_open.return_value.__enter__.return_value = mock_tar

    # Mock artifact
    artifact = {
        'archive_download_url': 'https://api.github.com/repos/owner/repo/actions/artifacts/123/zip'
    }

    mock_tar_file = MagicMock()
    mock_tar_file.name = 'artifact.tar.gz'
    mock_extracted_dir = MagicMock()
    mock_extracted_dir.is_dir.return_value = True
    mock_extracted_dir.name = 'awslabs-mcp-server-123'

    with (
        patch.object(Path, 'glob', return_value=[mock_tar_file]),
        patch.object(Path, 'iterdir', return_value=[mock_extracted_dir]),
    ):
        success, extracted_path = download_artifact(artifact)

    assert success is True
    assert extracted_path is not None


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.subprocess.run')
def test_download_artifact_download_failure(mock_run):
    """Test when artifact download fails."""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=['gh', 'api'], output='', stderr=b'Download failed'
    )

    artifact = {
        'archive_download_url': 'https://api.github.com/repos/owner/repo/actions/artifacts/123/zip'
    }

    success, extracted_path = download_artifact(artifact)

    assert success is False
    assert extracted_path is None


def test_check_embeddings_file_found():
    """Test when embeddings file is found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        extracted_dir = Path(temp_dir)
        embeddings_dir = (
            extracted_dir / 'awslabs' / 'aws_api_mcp_server' / 'core' / 'data' / 'embeddings'
        )
        embeddings_dir.mkdir(parents=True)

        # Create embeddings file with correct version
        embeddings_file = embeddings_dir / f'knowledge-base-awscli-{awscli_version}.npz'
        embeddings_file.touch()

        result = check_embeddings_file(extracted_dir)

        assert result == embeddings_file


def test_check_embeddings_file_not_found():
    """Test when embeddings file is not found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        extracted_dir = Path(temp_dir)
        embeddings_dir = (
            extracted_dir / 'awslabs' / 'aws_api_mcp_server' / 'core' / 'data' / 'embeddings'
        )
        embeddings_dir.mkdir(parents=True)

        # Create embeddings file with wrong version
        embeddings_file = embeddings_dir / 'knowledge-base-awscli-1.0.0.npz'
        embeddings_file.touch()

        result = check_embeddings_file(extracted_dir)

        assert result is None


def test_check_embeddings_file_directory_not_found():
    """Test when embeddings directory doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        extracted_dir = Path(temp_dir)

        result = check_embeddings_file(extracted_dir)

        assert result is None


def test_copy_embeddings_file_success():
    """Test successful file copy."""
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir) / 'source'
        target_dir = Path(temp_dir) / 'target'

        source_dir.mkdir()
        source_file = source_dir / 'test.npz'
        source_file.write_text('test content')

        result = copy_embeddings_file(source_file, target_dir)

        assert result is True
        assert (target_dir / 'test.npz').exists()


def test_copy_embeddings_file_failure():
    """Test when file copy fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = Path(temp_dir) / 'nonexistent.npz'
        target_dir = Path(temp_dir) / 'target'

        result = copy_embeddings_file(source_file, target_dir)

        assert result is False


def test_cleanup_success():
    """Test successful cleanup."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / 'test.txt'
        test_file.touch()

        cleanup(temp_path)

        assert not temp_path.exists()


def test_cleanup_nonexistent_directory():
    """Test cleanup of nonexistent directory."""
    nonexistent_path = Path('/nonexistent/path')

    # Should not raise exception
    cleanup(nonexistent_path)


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.Path')
def test_check_local_embeddings_found(mock_path):
    """Test when local embeddings file is found."""
    # Create a mock that will be returned when Path is called
    mock_path_instance = MagicMock()
    mock_resolved = MagicMock()
    mock_parent1 = MagicMock()
    mock_parent2 = MagicMock()
    mock_core = MagicMock()
    mock_data = MagicMock()
    mock_embeddings_dir = MagicMock()

    # Set up the chain: Path(__file__).resolve().parent.parent
    mock_path_instance.resolve.return_value = mock_resolved
    mock_resolved.parent = mock_parent1
    mock_parent1.parent = mock_parent2

    # Chain the / 'core' / 'data' / 'embeddings'
    mock_parent2.__truediv__.return_value = mock_core
    mock_core.__truediv__.return_value = mock_data
    mock_data.__truediv__.return_value = mock_embeddings_dir

    # Set up the embeddings dir mock
    mock_embeddings_dir.exists.return_value = True
    mock_embeddings_dir.glob.return_value = [
        Path(f'/fake/path/knowledge-base-awscli-{awscli_version}.npz')
    ]

    # Make Path constructor return our mock
    mock_path.return_value = mock_path_instance

    result = check_local_embeddings()

    assert result is True


def test_check_local_embeddings_not_found():
    """Test when local embeddings file is not found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch(
            'awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.Path'
        ) as mock_path:
            # Mock Path(__file__) to return our temp directory
            mock_path.return_value = Path(temp_dir)

            result = check_local_embeddings()

            assert result is False


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.subprocess.run')
def test_check_gh_cli_available(mock_run):
    """Test when GitHub CLI is available."""
    mock_result = MagicMock()
    mock_result.stdout = 'gh version 2.0.0'
    mock_run.return_value = mock_result

    result = check_gh_cli()

    assert result is True
    mock_run.assert_called_once_with(
        ['gh', '--version'], capture_output=True, text=True, check=True
    )


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.subprocess.run')
def test_check_gh_cli_not_available(mock_run):
    """Test when GitHub CLI is not available."""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=['gh', '--version'], output='', stderr='command not found'
    )

    result = check_gh_cli()

    assert result is False


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_local_embeddings')
def test_try_download_latest_embeddings_local_exists(mock_check_local):
    """Test when local embeddings already exist."""
    mock_check_local.return_value = True

    result = try_download_latest_embeddings()

    assert result is True


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_local_embeddings')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_gh_cli')
def test_try_download_latest_embeddings_no_gh_cli(mock_check_gh, mock_check_local):
    """Test when GitHub CLI is not available."""
    mock_check_local.return_value = False
    mock_check_gh.return_value = False

    result = try_download_latest_embeddings()

    assert result is False


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_local_embeddings')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_gh_cli')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.get_latest_artifact')
def test_try_download_latest_embeddings_no_artifact(
    mock_get_artifact, mock_check_gh, mock_check_local
):
    """Test when no artifact is found."""
    mock_check_local.return_value = False
    mock_check_gh.return_value = True
    mock_get_artifact.return_value = None

    result = try_download_latest_embeddings()

    assert result is False


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_local_embeddings')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_gh_cli')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.get_latest_artifact')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.download_artifact')
def test_try_download_latest_embeddings_download_failure(
    mock_download, mock_get_artifact, mock_check_gh, mock_check_local
):
    """Test when artifact download fails."""
    mock_check_local.return_value = False
    mock_check_gh.return_value = True
    mock_get_artifact.return_value = {'id': 123}
    mock_download.return_value = (False, None)

    result = try_download_latest_embeddings()

    assert result is False


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_local_embeddings')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_gh_cli')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.get_latest_artifact')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.download_artifact')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_embeddings_file')
def test_try_download_latest_embeddings_no_embeddings_file(
    mock_check_embeddings, mock_download, mock_get_artifact, mock_check_gh, mock_check_local
):
    """Test when no embeddings file is found in artifact."""
    mock_check_local.return_value = False
    mock_check_gh.return_value = True
    mock_get_artifact.return_value = {'id': 123}
    mock_download.return_value = (True, Path('/mock/extracted'))
    mock_check_embeddings.return_value = None

    with patch(
        'awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.cleanup'
    ) as mock_cleanup:
        result = try_download_latest_embeddings()

        assert result is False
        mock_cleanup.assert_called_once()


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_local_embeddings')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_gh_cli')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.get_latest_artifact')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.download_artifact')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_embeddings_file')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.copy_embeddings_file')
def test_try_download_latest_embeddings_success(
    mock_copy,
    mock_check_embeddings,
    mock_download,
    mock_get_artifact,
    mock_check_gh,
    mock_check_local,
):
    """Test successful download and copy."""
    mock_check_local.return_value = False
    mock_check_gh.return_value = True
    mock_get_artifact.return_value = {'id': 123}
    mock_download.return_value = (True, Path('/mock/extracted'))
    mock_check_embeddings.return_value = Path('/mock/embeddings.npz')
    mock_copy.return_value = True

    with patch(
        'awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.cleanup'
    ) as mock_cleanup:
        result = try_download_latest_embeddings()

        assert result is True
        mock_cleanup.assert_called_once()


@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_local_embeddings')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_gh_cli')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.get_latest_artifact')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.download_artifact')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.check_embeddings_file')
@patch('awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.copy_embeddings_file')
def test_try_download_latest_embeddings_copy_failure(
    mock_copy,
    mock_check_embeddings,
    mock_download,
    mock_get_artifact,
    mock_check_gh,
    mock_check_local,
):
    """Test when copy fails."""
    mock_check_local.return_value = False
    mock_check_gh.return_value = True
    mock_get_artifact.return_value = {'id': 123}
    mock_download.return_value = (True, Path('/mock/extracted'))
    mock_check_embeddings.return_value = Path('/mock/embeddings.npz')
    mock_copy.return_value = False

    with patch(
        'awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.cleanup'
    ) as mock_cleanup:
        result = try_download_latest_embeddings()

        assert result is False
        mock_cleanup.assert_called_once()


@patch(
    'awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.try_download_latest_embeddings'
)
def test_main_success(mock_try_download):
    """Test main function with success."""
    mock_try_download.return_value = True

    with patch.object(sys, 'exit') as mock_exit:
        from awslabs.aws_api_mcp_server.scripts.download_latest_embeddings import main

        main()

        mock_exit.assert_called_once_with(0)


@patch(
    'awslabs.aws_api_mcp_server.scripts.download_latest_embeddings.try_download_latest_embeddings'
)
def test_main_failure(mock_try_download):
    """Test main function with failure."""
    mock_try_download.return_value = False

    with patch.object(sys, 'exit') as mock_exit:
        from awslabs.aws_api_mcp_server.scripts.download_latest_embeddings import main

        main()

        mock_exit.assert_called_once_with(1)
