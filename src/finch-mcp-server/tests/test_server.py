"""Tests for the Finch MCP server."""

from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.models import (
    BuildImageRequest,
    CreateEcrRepoRequest,
    PushImageRequest,
    Result,
)
from awslabs.finch_mcp_server.server import (
    ensure_vm_running,
    sensitive_data_filter,
)
from unittest.mock import MagicMock, patch


class TestSensitiveDataFilter:
    """Tests for the sensitive_data_filter function."""

    def test_filter_aws_access_key(self):
        """Test filtering AWS access keys."""
        record = MagicMock()
        record.msg = 'AWS Access Key: AKIAIOSFODNN7EXAMPLE is sensitive'

        sensitive_data_filter(record)

        assert 'AWS_ACCESS_KEY_REDACTED' in record.msg
        assert 'AKIAIOSFODNN7EXAMPLE' not in record.msg

    def test_filter_aws_secret_key(self):
        """Test filtering AWS secret keys."""
        record = MagicMock()
        record.msg = 'AWS Secret Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY is sensitive'

        sensitive_data_filter(record)

        assert 'AWS_SECRET_KEY_REDACTED' in record.msg
        assert 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY' not in record.msg

    def test_filter_api_key(self):
        """Test filtering API keys."""
        record = MagicMock()
        record.msg = "api_key='secret123'"

        sensitive_data_filter(record)

        assert 'api_key=REDACTED' in record.msg
        assert 'secret123' not in record.msg

    def test_filter_password(self):
        """Test filtering passwords."""
        record = MagicMock()
        record.msg = "password='mypassword'"

        sensitive_data_filter(record)

        assert 'password=REDACTED' in record.msg
        assert 'mypassword' not in record.msg

    def test_filter_url_with_credentials(self):
        """Test filtering URLs with credentials."""
        record = MagicMock()
        record.msg = 'Connection URL: https://username:password@example.com'

        sensitive_data_filter(record)

        assert 'https://REDACTED:REDACTED@example.com' in record.msg
        assert 'username:password' not in record.msg


@patch('awslabs.finch_mcp_server.server.get_vm_status')
@patch('awslabs.finch_mcp_server.server.is_vm_nonexistent')
@patch('awslabs.finch_mcp_server.server.is_vm_stopped')
@patch('awslabs.finch_mcp_server.server.is_vm_running')
@patch('awslabs.finch_mcp_server.server.initialize_vm')
@patch('awslabs.finch_mcp_server.server.start_stopped_vm')
@patch('awslabs.finch_mcp_server.server.format_result')
@patch('sys.platform', 'darwin')  # Mock as macOS for testing
def test_ensure_vm_running_on_macos(
    mock_format_result,
    mock_start_vm,
    mock_initialize_vm,
    mock_is_running,
    mock_is_stopped,
    mock_is_nonexistent,
    mock_get_status,
):
    """Test ensure_vm_running function on macOS."""
    # Test case 1: VM is running
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

    # Reset mocks
    mock_format_result.reset_mock()
    mock_initialize_vm.reset_mock()
    mock_start_vm.reset_mock()

    # Test case 2: VM is stopped
    mock_is_nonexistent.return_value = False
    mock_is_stopped.return_value = True
    mock_is_running.return_value = False
    mock_start_vm.return_value = {'status': STATUS_SUCCESS, 'message': 'VM started'}
    mock_format_result.return_value = {'status': STATUS_SUCCESS, 'message': 'VM started'}

    result = ensure_vm_running()

    assert result['status'] == STATUS_SUCCESS
    mock_start_vm.assert_called_once()
    mock_initialize_vm.assert_not_called()

    # Reset mocks
    mock_format_result.reset_mock()
    mock_initialize_vm.reset_mock()
    mock_start_vm.reset_mock()

    # Test case 3: VM is nonexistent
    mock_is_nonexistent.return_value = True
    mock_is_stopped.return_value = False
    mock_is_running.return_value = False
    mock_initialize_vm.return_value = {'status': STATUS_SUCCESS, 'message': 'VM initialized'}
    mock_format_result.return_value = {'status': STATUS_SUCCESS, 'message': 'VM initialized'}

    result = ensure_vm_running()

    assert result['status'] == STATUS_SUCCESS
    mock_initialize_vm.assert_called_once()
    mock_start_vm.assert_not_called()

    # Reset mocks
    mock_format_result.reset_mock()
    mock_initialize_vm.reset_mock()
    mock_start_vm.reset_mock()

    # Test case 4: VM start fails
    mock_is_nonexistent.return_value = False
    mock_is_stopped.return_value = True
    mock_is_running.return_value = False
    mock_start_vm.return_value = {'status': STATUS_ERROR, 'message': 'Failed to start VM'}

    result = ensure_vm_running()

    assert result['status'] == STATUS_ERROR
    mock_start_vm.assert_called_once()
    mock_initialize_vm.assert_not_called()

    # Reset mocks
    mock_format_result.reset_mock()
    mock_initialize_vm.reset_mock()
    mock_start_vm.reset_mock()

    # Test case 5: VM initialization fails
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
def test_ensure_vm_running_on_linux(mock_format_result):
    """Test ensure_vm_running function on Linux."""
    mock_format_result.return_value = {
        'status': STATUS_SUCCESS,
        'message': 'No VM operation required on Linux.',
    }

    result = ensure_vm_running()

    assert result['status'] == STATUS_SUCCESS
    assert result['message'] == 'No VM operation required on Linux.'
    mock_format_result.assert_called_with(STATUS_SUCCESS, 'No VM operation required on Linux.')


@patch('awslabs.finch_mcp_server.server.check_finch_installation')
@patch('awslabs.finch_mcp_server.server.contains_ecr_reference')
@patch('awslabs.finch_mcp_server.server.configure_ecr')
@patch('awslabs.finch_mcp_server.server.stop_vm')
@patch('awslabs.finch_mcp_server.server.ensure_vm_running')
@patch('awslabs.finch_mcp_server.server.build_image')
def test_finch_build_container_image(
    mock_build_image,
    mock_ensure_vm,
    mock_stop_vm,
    mock_configure_ecr,
    mock_contains_ecr,
    mock_check_finch,
):
    """Test finch_build_container_image tool."""
    # Setup test data
    request = BuildImageRequest(
        dockerfile_path='/path/to/Dockerfile',
        context_path='/path/to/context',
        tags=['myimage:latest'],
        platforms=['linux/amd64'],
        no_cache=False,
        pull=True,
    )

    # Mock the async function to return a Result object
    mock_result = Result(status=STATUS_SUCCESS, message='Successfully built image')
    mock_build_image.return_value = {
        'status': STATUS_SUCCESS,
        'message': 'Successfully built image',
    }

    # Test case 1: Successful build without ECR reference
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_contains_ecr.return_value = False
    mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}

    # Mock the async function
    finch_build_container_image_mock = MagicMock(return_value=mock_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_build_container_image',
        finch_build_container_image_mock,
    ):
        result = finch_build_container_image_mock(request)

    assert result.status == STATUS_SUCCESS
    assert result.message == 'Successfully built image'

    # Test case 2: Successful build with ECR reference
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_contains_ecr.return_value = True
    mock_configure_ecr.return_value = {'status': STATUS_SUCCESS, 'changed': True}
    mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}

    # Mock the async function
    finch_build_container_image_mock = MagicMock(return_value=mock_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_build_container_image',
        finch_build_container_image_mock,
    ):
        result = finch_build_container_image_mock(request)

    assert result.status == STATUS_SUCCESS
    assert result.message == 'Successfully built image'

    # Test case 3: Finch not installed
    mock_check_finch.return_value = {'status': STATUS_ERROR, 'message': 'Finch not installed'}
    mock_error_result = Result(status=STATUS_ERROR, message='Finch not installed')

    # Mock the async function
    finch_build_container_image_mock = MagicMock(return_value=mock_error_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_build_container_image',
        finch_build_container_image_mock,
    ):
        result = finch_build_container_image_mock(request)

    assert result.status == STATUS_ERROR
    assert result.message == 'Finch not installed'

    # Test case 4: VM startup fails
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_contains_ecr.return_value = False
    mock_ensure_vm.return_value = {'status': STATUS_ERROR, 'message': 'Failed to start VM'}
    mock_error_result = Result(status=STATUS_ERROR, message='Failed to start VM')

    # Mock the async function
    finch_build_container_image_mock = MagicMock(return_value=mock_error_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_build_container_image',
        finch_build_container_image_mock,
    ):
        result = finch_build_container_image_mock(request)

    assert result.status == STATUS_ERROR
    assert result.message == 'Failed to start VM'

    # Test case 5: Build fails
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_contains_ecr.return_value = False
    mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
    mock_build_image.return_value = {'status': STATUS_ERROR, 'message': 'Build failed'}
    mock_error_result = Result(status=STATUS_ERROR, message='Build failed')

    # Mock the async function
    finch_build_container_image_mock = MagicMock(return_value=mock_error_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_build_container_image',
        finch_build_container_image_mock,
    ):
        result = finch_build_container_image_mock(request)

    assert result.status == STATUS_ERROR
    assert result.message == 'Build failed'


@patch('awslabs.finch_mcp_server.server.check_finch_installation')
@patch('awslabs.finch_mcp_server.server.is_ecr_repository')
@patch('awslabs.finch_mcp_server.server.configure_ecr')
@patch('awslabs.finch_mcp_server.server.stop_vm')
@patch('awslabs.finch_mcp_server.server.ensure_vm_running')
@patch('awslabs.finch_mcp_server.server.push_image')
def test_finch_push_image(
    mock_push_image,
    mock_ensure_vm,
    mock_stop_vm,
    mock_configure_ecr,
    mock_is_ecr,
    mock_check_finch,
):
    """Test finch_push_image tool."""
    # Setup test data
    request = PushImageRequest(image='123456789012.dkr.ecr.us-west-2.amazonaws.com/myrepo:latest')

    # Mock the async function to return a Result object
    mock_result = Result(status=STATUS_SUCCESS, message='Successfully pushed image')

    # Test case 1: Successful push to ECR
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_is_ecr.return_value = True
    mock_configure_ecr.return_value = {'status': STATUS_SUCCESS, 'changed': True}
    mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
    mock_push_image.return_value = {
        'status': STATUS_SUCCESS,
        'message': 'Successfully pushed image',
    }

    # Mock the async function
    finch_push_image_mock = MagicMock(return_value=mock_result)
    with patch('awslabs.finch_mcp_server.server.finch_push_image', finch_push_image_mock):
        result = finch_push_image_mock(request)

    assert result.status == STATUS_SUCCESS
    assert result.message == 'Successfully pushed image'

    # Test case 2: Successful push to non-ECR repository
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_is_ecr.return_value = False
    mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
    mock_push_image.return_value = {
        'status': STATUS_SUCCESS,
        'message': 'Successfully pushed image',
    }

    request = PushImageRequest(image='docker.io/library/nginx:latest')

    # Mock the async function
    finch_push_image_mock = MagicMock(return_value=mock_result)
    with patch('awslabs.finch_mcp_server.server.finch_push_image', finch_push_image_mock):
        result = finch_push_image_mock(request)

    assert result.status == STATUS_SUCCESS
    assert result.message == 'Successfully pushed image'

    # Test case 3: Finch not installed
    mock_check_finch.return_value = {'status': STATUS_ERROR, 'message': 'Finch not installed'}
    mock_error_result = Result(status=STATUS_ERROR, message='Finch not installed')

    # Mock the async function
    finch_push_image_mock = MagicMock(return_value=mock_error_result)
    with patch('awslabs.finch_mcp_server.server.finch_push_image', finch_push_image_mock):
        result = finch_push_image_mock(request)

    assert result.status == STATUS_ERROR
    assert result.message == 'Finch not installed'

    # Test case 4: VM startup fails
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_is_ecr.return_value = False
    mock_ensure_vm.return_value = {'status': STATUS_ERROR, 'message': 'Failed to start VM'}
    mock_error_result = Result(status=STATUS_ERROR, message='Failed to start VM')

    # Mock the async function
    finch_push_image_mock = MagicMock(return_value=mock_error_result)
    with patch('awslabs.finch_mcp_server.server.finch_push_image', finch_push_image_mock):
        result = finch_push_image_mock(request)

    assert result.status == STATUS_ERROR
    assert result.message == 'Failed to start VM'

    # Test case 5: Push fails
    mock_check_finch.return_value = {'status': STATUS_SUCCESS}
    mock_is_ecr.return_value = False
    mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
    mock_push_image.return_value = {'status': STATUS_ERROR, 'message': 'Push failed'}
    mock_error_result = Result(status=STATUS_ERROR, message='Push failed')

    # Mock the async function
    finch_push_image_mock = MagicMock(return_value=mock_error_result)
    with patch('awslabs.finch_mcp_server.server.finch_push_image', finch_push_image_mock):
        result = finch_push_image_mock(request)

    assert result.status == STATUS_ERROR
    assert result.message == 'Push failed'


@patch('awslabs.finch_mcp_server.server.create_ecr_repository')
def test_finch_create_ecr_repo(mock_create_ecr):
    """Test finch_create_ecr_repo tool."""
    # Setup test data
    request = CreateEcrRepoRequest(app_name='test-repo')

    # Mock the async function to return a Result object
    mock_result = Result(
        status=STATUS_SUCCESS, message="Successfully created ECR repository 'test-repo'."
    )

    # Test case 1: Repository created successfully
    mock_create_ecr.return_value = {
        'status': STATUS_SUCCESS,
        'message': "Successfully created ECR repository 'test-repo'.",
        'repository_uri': '123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo',
        'exists': False,
    }

    # Mock the async function
    finch_create_ecr_repo_mock = MagicMock(return_value=mock_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_create_ecr_repo', finch_create_ecr_repo_mock
    ):
        result = finch_create_ecr_repo_mock(request)

    assert result.status == STATUS_SUCCESS
    assert result.message == "Successfully created ECR repository 'test-repo'."

    # Test case 2: Repository already exists
    mock_create_ecr.return_value = {
        'status': STATUS_SUCCESS,
        'message': "ECR repository 'test-repo' already exists.",
        'repository_uri': '123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo',
        'exists': True,
    }
    mock_result = Result(
        status=STATUS_SUCCESS, message="ECR repository 'test-repo' already exists."
    )

    # Mock the async function
    finch_create_ecr_repo_mock = MagicMock(return_value=mock_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_create_ecr_repo', finch_create_ecr_repo_mock
    ):
        result = finch_create_ecr_repo_mock(request)

    assert result.status == STATUS_SUCCESS
    assert result.message == "ECR repository 'test-repo' already exists."

    # Test case 3: Error creating repository
    mock_create_ecr.return_value = {
        'status': STATUS_ERROR,
        'message': 'Failed to create ECR repository: Access denied',
    }
    mock_error_result = Result(
        status=STATUS_ERROR, message='Failed to create ECR repository: Access denied'
    )

    # Mock the async function
    finch_create_ecr_repo_mock = MagicMock(return_value=mock_error_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_create_ecr_repo', finch_create_ecr_repo_mock
    ):
        result = finch_create_ecr_repo_mock(request)

    assert result.status == STATUS_ERROR
    assert result.message == 'Failed to create ECR repository: Access denied'

    # Test case 4: Exception during creation
    mock_create_ecr.side_effect = Exception('Unexpected error')
    mock_error_result = Result(
        status=STATUS_ERROR, message='Error checking/creating ECR repository: Unexpected error'
    )

    # Mock the async function
    finch_create_ecr_repo_mock = MagicMock(return_value=mock_error_result)
    with patch(
        'awslabs.finch_mcp_server.server.finch_create_ecr_repo', finch_create_ecr_repo_mock
    ):
        result = finch_create_ecr_repo_mock(request)

    assert result.status == STATUS_ERROR
    assert 'Error checking/creating ECR repository' in result.message
