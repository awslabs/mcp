"""Tests for the Finch MCP server."""

import pytest
from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.models import (
    BuildImageRequest,
    CreateEcrRepoRequest,
    PushImageRequest,
)
from awslabs.finch_mcp_server.server import (
    ensure_vm_running,
    finch_build_container_image,
    finch_create_ecr_repo,
    finch_push_image,
    sensitive_data_filter,
)
from unittest.mock import MagicMock, patch


class TestSensitiveDataFilter:
    """Tests for the sensitive_data_filter function."""

    def test_filter_aws_access_key(self):
        """Test filtering AWS access keys."""
        record = {
            'message': 'AWS Access Key: AKIAIOSFODNN7EXAMPLE is sensitive'  # pragma: allowlist secret
        }

        sensitive_data_filter(record)

        assert 'AWS_ACCESS_KEY_REDACTED' in record['message']
        assert 'AKIAIOSFODNN7EXAMPLE' not in record['message']  # pragma: allowlist secret

    def test_filter_aws_secret_key(self):
        """Test filtering AWS secret keys."""
        record = {
            'message': 'AWS Secret Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY is sensitive'
        }

        sensitive_data_filter(record)

        assert 'AWS_SECRET_KEY_REDACTED' in record['message']
        assert (
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # pragma: allowlist secret
            not in record['message']
        )

    def test_filter_api_key(self):
        """Test filtering API keys."""
        record = {
            'message': "api_key='secret123'"  # pragma: allowlist secret
        }

        sensitive_data_filter(record)

        assert 'api_key=REDACTED' in record['message']
        assert 'secret123' not in record['message']

    def test_filter_password(self):
        """Test filtering passwords."""
        record = {
            'message': "password='mypassword'"  # pragma: allowlist secret
        }

        sensitive_data_filter(record)

        assert 'password=REDACTED' in record['message']
        assert 'mypassword' not in record['message']

    def test_filter_url_with_credentials(self):
        """Test filtering URLs with credentials."""
        record = {
            'message': 'Connection URL: https://username:password@example.com'  # pragma: allowlist secret
        }

        sensitive_data_filter(record)

        assert (
            'https://REDACTED:REDACTED@example.com'  # pragma: allowlist secret
            in record['message']
        )
        assert 'username:password' not in record['message']


class TestEnsureVmRunning:
    """Tests for the ensure_vm_running function."""

    @patch('awslabs.finch_mcp_server.server.get_vm_status')
    @patch('awslabs.finch_mcp_server.server.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.server.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.server.is_vm_running')
    @patch('awslabs.finch_mcp_server.server.initialize_vm')
    @patch('awslabs.finch_mcp_server.server.start_stopped_vm')
    @patch('awslabs.finch_mcp_server.server.format_result')
    @patch('sys.platform', 'darwin')
    def test_ensure_vm_running_already_running(
        self,
        mock_format_result,
        mock_start_vm,
        mock_initialize_vm,
        mock_is_running,
        mock_is_stopped,
        mock_is_nonexistent,
        mock_get_status,
    ):
        """Test ensure_vm_running function on macOS when VM is already running."""
        # VM is running
        mock_get_status.return_value = MagicMock()
        mock_is_nonexistent.return_value = False
        mock_is_stopped.return_value = False
        mock_is_running.return_value = True
        mock_format_result.return_value = {'status': STATUS_SUCCESS, 'message': 'VM is running'}

        result = ensure_vm_running()

        assert result['status'] == STATUS_SUCCESS
        mock_format_result.assert_called_with(STATUS_SUCCESS, 'Finch VM is already running.')
        mock_initialize_vm.assert_not_called()
        mock_start_vm.assert_not_called()

    @patch('awslabs.finch_mcp_server.server.get_vm_status')
    @patch('awslabs.finch_mcp_server.server.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.server.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.server.is_vm_running')
    @patch('awslabs.finch_mcp_server.server.initialize_vm')
    @patch('awslabs.finch_mcp_server.server.start_stopped_vm')
    @patch('awslabs.finch_mcp_server.server.format_result')
    @patch('sys.platform', 'darwin')
    def test_ensure_vm_running_stopped(
        self,
        mock_format_result,
        mock_start_vm,
        mock_initialize_vm,
        mock_is_running,
        mock_is_stopped,
        mock_is_nonexistent,
        mock_get_status,
    ):
        """Test ensure_vm_running function on macOS when VM is stopped."""
        # VM is stopped
        mock_get_status.return_value = MagicMock()
        mock_is_nonexistent.return_value = False
        mock_is_stopped.return_value = True
        mock_is_running.return_value = False
        mock_start_vm.return_value = {'status': STATUS_SUCCESS, 'message': 'VM started'}
        mock_format_result.return_value = {'status': STATUS_SUCCESS, 'message': 'VM started'}

        result = ensure_vm_running()

        assert result['status'] == STATUS_SUCCESS
        mock_start_vm.assert_called_once()
        mock_initialize_vm.assert_not_called()

    @patch('awslabs.finch_mcp_server.server.get_vm_status')
    @patch('awslabs.finch_mcp_server.server.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.server.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.server.is_vm_running')
    @patch('awslabs.finch_mcp_server.server.initialize_vm')
    @patch('awslabs.finch_mcp_server.server.start_stopped_vm')
    @patch('awslabs.finch_mcp_server.server.format_result')
    @patch('sys.platform', 'darwin')
    def test_ensure_vm_running_nonexistent(
        self,
        mock_format_result,
        mock_start_vm,
        mock_initialize_vm,
        mock_is_running,
        mock_is_stopped,
        mock_is_nonexistent,
        mock_get_status,
    ):
        """Test ensure_vm_running function on macOS when VM is nonexistent."""
        # VM is nonexistent
        mock_get_status.return_value = MagicMock()
        mock_is_nonexistent.return_value = True
        mock_is_stopped.return_value = False
        mock_is_running.return_value = False
        mock_initialize_vm.return_value = {'status': STATUS_SUCCESS, 'message': 'VM initialized'}
        mock_format_result.return_value = {'status': STATUS_SUCCESS, 'message': 'VM initialized'}

        result = ensure_vm_running()

        assert result['status'] == STATUS_SUCCESS
        mock_initialize_vm.assert_called_once()
        mock_start_vm.assert_not_called()

    @patch('awslabs.finch_mcp_server.server.get_vm_status')
    @patch('awslabs.finch_mcp_server.server.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.server.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.server.is_vm_running')
    @patch('awslabs.finch_mcp_server.server.initialize_vm')
    @patch('awslabs.finch_mcp_server.server.start_stopped_vm')
    @patch('awslabs.finch_mcp_server.server.format_result')
    @patch('sys.platform', 'darwin')  # Mock as macOS for testing
    def test_ensure_vm_running_failures(
        self,
        mock_format_result,
        mock_start_vm,
        mock_initialize_vm,
        mock_is_running,
        mock_is_stopped,
        mock_is_nonexistent,
        mock_get_status,
    ):
        """Test ensure_vm_running function on macOS when operations fail."""
        # Test VM start failure
        mock_get_status.return_value = MagicMock()
        mock_is_nonexistent.return_value = False
        mock_is_stopped.return_value = True
        mock_is_running.return_value = False
        mock_start_vm.return_value = {'status': STATUS_ERROR, 'message': 'Failed to start VM'}

        result = ensure_vm_running()

        assert result['status'] == STATUS_ERROR
        mock_start_vm.assert_called_once()
        mock_initialize_vm.assert_not_called()

        # Reset mocks for the next test
        mock_format_result.reset_mock()
        mock_initialize_vm.reset_mock()
        mock_start_vm.reset_mock()

        # Test VM initialization failure
        mock_is_nonexistent.return_value = True
        mock_is_stopped.return_value = False
        mock_is_running.return_value = False
        mock_initialize_vm.return_value = {
            'status': STATUS_ERROR,
            'message': 'Failed to initialize VM',
        }

        result = ensure_vm_running()

        assert result['status'] == STATUS_ERROR
        mock_initialize_vm.assert_called_once()
        mock_start_vm.assert_not_called()

    @patch('sys.platform', 'linux')
    @patch('awslabs.finch_mcp_server.server.format_result')
    def test_ensure_vm_running_on_linux(self, mock_format_result):
        """Test ensure_vm_running function on Linux."""
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'No VM operation required on Linux.',
        }

        result = ensure_vm_running()

        assert result['status'] == STATUS_SUCCESS
        assert result['message'] == 'No VM operation required on Linux.'
        mock_format_result.assert_called_with(STATUS_SUCCESS, 'No VM operation required on Linux.')


class TestFinchTools:
    """Tests for Finch operations in the server."""

    @pytest.mark.asyncio
    async def test_finch_build_container_image_success(self):
        """Test successful finch_build_container_image operation."""
        request = BuildImageRequest(
            dockerfile_path='/path/to/Dockerfile',
            context_path='/path/to/context',
            tags=['myimage:latest'],
            platforms=['linux/amd64'],
            no_cache=False,
            pull=True,
        )

        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.contains_ecr_reference') as mock_contains_ecr,
            patch('awslabs.finch_mcp_server.server.configure_ecr') as mock_configure_ecr,
            patch('awslabs.finch_mcp_server.server.stop_vm') as mock_stop_vm,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.build_image') as mock_build_image,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_contains_ecr.return_value = False
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_build_image.return_value = {
                'status': STATUS_SUCCESS,
                'message': 'Successfully built image',
            }

            result = await finch_build_container_image(request)

            assert result.status == STATUS_SUCCESS
            assert result.message == 'Successfully built image'

            mock_check_finch.assert_called_once()
            mock_contains_ecr.assert_called_once_with(request.dockerfile_path)
            mock_ensure_vm.assert_called_once()
            mock_build_image.assert_called_once()
            mock_configure_ecr.assert_not_called()
            mock_stop_vm.assert_not_called()

    @pytest.mark.asyncio
    async def test_finch_build_container_image_with_ecr(self):
        """Test finch_build_container_image with ECR reference."""
        request = BuildImageRequest(
            dockerfile_path='/path/to/Dockerfile',
            context_path='/path/to/context',
            tags=['123456789012.dkr.ecr.us-west-2.amazonaws.com/myrepo:latest'],
        )

        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.contains_ecr_reference') as mock_contains_ecr,
            patch('awslabs.finch_mcp_server.server.configure_ecr') as mock_configure_ecr,
            patch('awslabs.finch_mcp_server.server.stop_vm') as mock_stop_vm,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.build_image') as mock_build_image,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_contains_ecr.return_value = True
            mock_configure_ecr.return_value = {'status': STATUS_SUCCESS, 'changed': True}
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_build_image.return_value = {
                'status': STATUS_SUCCESS,
                'message': 'Successfully built image',
            }

            result = await finch_build_container_image(request)

            assert result.status == STATUS_SUCCESS
            assert result.message == 'Successfully built image'

            mock_check_finch.assert_called_once()
            mock_contains_ecr.assert_called_once_with(request.dockerfile_path)
            mock_configure_ecr.assert_called_once()
            mock_stop_vm.assert_called_once_with(force=True)
            mock_ensure_vm.assert_called_once()
            mock_build_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_build_container_image_finch_not_installed(self):
        """Test finch_build_container_image when Finch is not installed."""
        request = BuildImageRequest(
            dockerfile_path='/path/to/Dockerfile',
            context_path='/path/to/context',
        )

        with patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch:
            mock_check_finch.return_value = {
                'status': STATUS_ERROR,
                'message': 'Finch not installed',
            }

            result = await finch_build_container_image(request)

            assert result.status == STATUS_ERROR
            assert result.message == 'Finch not installed'

            mock_check_finch.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_build_container_image_vm_error(self):
        """Test finch_build_container_image when VM fails to start."""
        request = BuildImageRequest(
            dockerfile_path='/path/to/Dockerfile',
            context_path='/path/to/context',
        )

        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.contains_ecr_reference') as mock_contains_ecr,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_contains_ecr.return_value = False
            mock_ensure_vm.return_value = {'status': STATUS_ERROR, 'message': 'Failed to start VM'}

            result = await finch_build_container_image(request)

            assert result.status == STATUS_ERROR
            assert result.message == 'Failed to start VM'

            mock_check_finch.assert_called_once()
            mock_contains_ecr.assert_called_once_with(request.dockerfile_path)
            mock_ensure_vm.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_build_container_image_build_error(self):
        """Test finch_build_container_image when build fails."""
        request = BuildImageRequest(
            dockerfile_path='/path/to/Dockerfile',
            context_path='/path/to/context',
        )

        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.contains_ecr_reference') as mock_contains_ecr,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.build_image') as mock_build_image,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_contains_ecr.return_value = False
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_build_image.return_value = {'status': STATUS_ERROR, 'message': 'Build failed'}

            result = await finch_build_container_image(request)

            assert result.status == STATUS_ERROR
            assert result.message == 'Build failed'

            mock_check_finch.assert_called_once()
            mock_contains_ecr.assert_called_once_with(request.dockerfile_path)
            mock_ensure_vm.assert_called_once()
            mock_build_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_build_container_image_exception(self):
        """Test finch_build_container_image when an exception occurs."""
        request = BuildImageRequest(
            dockerfile_path='/path/to/Dockerfile',
            context_path='/path/to/context',
        )

        with patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch:
            mock_check_finch.side_effect = Exception('Unexpected error')

            result = await finch_build_container_image(request)

            assert result.status == STATUS_ERROR
            assert 'Error building Docker image: Unexpected error' in result.message

            mock_check_finch.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_push_image_success(self):
        """Test successful finch_push_image operation."""
        request = PushImageRequest(
            image='123456789012.dkr.ecr.us-west-2.amazonaws.com/myrepo:latest'
        )

        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.is_ecr_repository') as mock_is_ecr,
            patch('awslabs.finch_mcp_server.server.configure_ecr') as mock_configure_ecr,
            patch('awslabs.finch_mcp_server.server.stop_vm') as mock_stop_vm,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.push_image') as mock_push_image,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_is_ecr.return_value = True
            mock_configure_ecr.return_value = {'status': STATUS_SUCCESS, 'changed': True}
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_push_image.return_value = {
                'status': STATUS_SUCCESS,
                'message': 'Successfully pushed image',
            }

            result = await finch_push_image(request)

            assert result.status == STATUS_SUCCESS
            assert result.message == 'Successfully pushed image'

            mock_check_finch.assert_called_once()
            mock_is_ecr.assert_called_once_with(request.image)
            mock_configure_ecr.assert_called_once()
            mock_stop_vm.assert_called_once_with(force=True)
            mock_ensure_vm.assert_called_once()
            mock_push_image.assert_called_once_with(request.image)

    @pytest.mark.asyncio
    async def test_finch_push_image_non_ecr(self):
        """Test finch_push_image with non-ECR repository."""
        request = PushImageRequest(image='docker.io/library/nginx:latest')

        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.is_ecr_repository') as mock_is_ecr,
            patch('awslabs.finch_mcp_server.server.configure_ecr') as mock_configure_ecr,
            patch('awslabs.finch_mcp_server.server.stop_vm') as mock_stop_vm,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.push_image') as mock_push_image,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_is_ecr.return_value = False
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_push_image.return_value = {
                'status': STATUS_SUCCESS,
                'message': 'Successfully pushed image',
            }

            result = await finch_push_image(request)

            assert result.status == STATUS_SUCCESS
            assert result.message == 'Successfully pushed image'

            mock_check_finch.assert_called_once()
            mock_is_ecr.assert_called_once_with(request.image)
            mock_configure_ecr.assert_not_called()
            mock_stop_vm.assert_not_called()
            mock_ensure_vm.assert_called_once()
            mock_push_image.assert_called_once_with(request.image)

    @pytest.mark.asyncio
    async def test_finch_push_image_finch_not_installed(self):
        """Test finch_push_image when Finch is not installed."""
        request = PushImageRequest(image='docker.io/library/nginx:latest')

        with patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch:
            mock_check_finch.return_value = {
                'status': STATUS_ERROR,
                'message': 'Finch not installed',
            }

            result = await finch_push_image(request)

            assert result.status == STATUS_ERROR
            assert result.message == 'Finch not installed'

            mock_check_finch.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_push_image_vm_error(self):
        """Test finch_push_image when VM fails to start."""
        request = PushImageRequest(image='docker.io/library/nginx:latest')

        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.is_ecr_repository') as mock_is_ecr,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_is_ecr.return_value = False
            mock_ensure_vm.return_value = {'status': STATUS_ERROR, 'message': 'Failed to start VM'}

            result = await finch_push_image(request)

            assert result.status == STATUS_ERROR
            assert result.message == 'Failed to start VM'

            mock_check_finch.assert_called_once()
            mock_is_ecr.assert_called_once_with(request.image)
            mock_ensure_vm.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_push_image_push_error(self):
        """Test finch_push_image when push fails."""
        request = PushImageRequest(image='docker.io/library/nginx:latest')
        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.is_ecr_repository') as mock_is_ecr,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.push_image') as mock_push_image,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_is_ecr.return_value = False
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_push_image.return_value = {'status': STATUS_ERROR, 'message': 'Push failed'}

            result = await finch_push_image(request)

            assert result.status == STATUS_ERROR
            assert result.message == 'Push failed'

            mock_check_finch.assert_called_once()
            mock_is_ecr.assert_called_once_with(request.image)
            mock_ensure_vm.assert_called_once()
            mock_push_image.assert_called_once_with(request.image)

    @pytest.mark.asyncio
    async def test_finch_push_image_exception(self):
        """Test finch_push_image when an exception occurs."""
        request = PushImageRequest(image='docker.io/library/nginx:latest')

        with patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch:
            mock_check_finch.side_effect = Exception('Unexpected error')

            result = await finch_push_image(request)

            assert result.status == STATUS_ERROR
            assert 'Error pushing image: Unexpected error' in result.message

            mock_check_finch.assert_called_once()

    @pytest.mark.asyncio
    async def test_finch_create_ecr_repo_success(self):
        """Test successful finch_create_ecr_repo operation."""
        request = CreateEcrRepoRequest(app_name='test-repo', region='us-west-2')

        with patch(
            'awslabs.finch_mcp_server.server.create_ecr_repository'
        ) as mock_create_ecr_repository:
            mock_create_ecr_repository.return_value = {
                'status': STATUS_SUCCESS,
                'message': "Successfully created ECR repository 'test-repo'.",
                'repository_uri': '123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo',
                'exists': False,
            }

            result = await finch_create_ecr_repo(request)

            assert result.status == STATUS_SUCCESS
            assert "Successfully created ECR repository 'test-repo'" in result.message

            mock_create_ecr_repository.assert_called_once_with(
                app_name='test-repo', region='us-west-2'
            )

    @pytest.mark.asyncio
    async def test_finch_create_ecr_repo_already_exists(self):
        """Test finch_create_ecr_repo when repository already exists."""
        request = CreateEcrRepoRequest(app_name='test-repo', region='us-west-2')

        with patch(
            'awslabs.finch_mcp_server.server.create_ecr_repository'
        ) as mock_create_ecr_repository:
            mock_create_ecr_repository.return_value = {
                'status': STATUS_SUCCESS,
                'message': "ECR repository 'test-repo' already exists.",
                'repository_uri': '123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo',
                'exists': True,
            }

            result = await finch_create_ecr_repo(request)

            assert result.status == STATUS_SUCCESS
            assert 'already exists' in result.message

            mock_create_ecr_repository.assert_called_once_with(
                app_name='test-repo', region='us-west-2'
            )

    @pytest.mark.asyncio
    async def test_finch_create_ecr_repo_error(self):
        """Test finch_create_ecr_repo when creation fails."""
        request = CreateEcrRepoRequest(app_name='test-repo', region='us-west-2')

        with patch(
            'awslabs.finch_mcp_server.server.create_ecr_repository'
        ) as mock_create_ecr_repository:
            mock_create_ecr_repository.return_value = {
                'status': STATUS_ERROR,
                'message': "Failed to create ECR repository 'test-repo': Access denied",
            }

            result = await finch_create_ecr_repo(request)

            assert result.status == STATUS_ERROR
            assert 'Failed to create ECR repository' in result.message

            mock_create_ecr_repository.assert_called_once_with(
                app_name='test-repo', region='us-west-2'
            )

    @pytest.mark.asyncio
    async def test_finch_create_ecr_repo_exception(self):
        """Test finch_create_ecr_repo when an exception occurs."""
        request = CreateEcrRepoRequest(app_name='test-repo', region='us-west-2')

        with patch(
            'awslabs.finch_mcp_server.server.create_ecr_repository'
        ) as mock_create_ecr_repository:
            mock_create_ecr_repository.side_effect = Exception('Unexpected error')

            result = await finch_create_ecr_repo(request)

            assert result.status == STATUS_ERROR
            assert 'Error checking/creating ECR repository: Unexpected error' in result.message

            mock_create_ecr_repository.assert_called_once_with(
                app_name='test-repo', region='us-west-2'
            )
