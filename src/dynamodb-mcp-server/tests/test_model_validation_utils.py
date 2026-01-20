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

import os
import pytest
from awslabs.dynamodb_mcp_server.model_validation_utils import (
    _extract_port_from_cmdline,
    _safe_extract_members,
    _validate_download_url,
    check_dynamodb_readiness,
    cleanup_validation_resources,
    create_tables,
    create_validation_resources,
    download_dynamodb_local_jar,
    find_available_port,
    get_container_path,
    get_existing_container_dynamodb_local_endpoint,
    get_existing_java_dynamodb_local_endpoint,
    get_java_path,
    get_validation_result_transform_prompt,
    insert_items,
    list_tables,
    setup_dynamodb_local,
    start_container,
    start_java_process,
)
from botocore.exceptions import ClientError, EndpointConnectionError
from unittest.mock import MagicMock, Mock, PropertyMock, mock_open, patch


# Test Data Factories
class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_table_config(name='test-table', **kwargs):
        """Create a table configuration for testing."""
        config = {'TableName': name, 'KeySchema': []}
        config.update(kwargs)
        return config

    @staticmethod
    def create_item_request(item_id='1', **kwargs):
        """Create an item request for testing."""
        item = {'PutRequest': {'Item': {'id': {'S': item_id}}}}
        item['PutRequest']['Item'].update(kwargs)
        return item

    @staticmethod
    def create_resources_dict(table_name='test-table', item_count=1):
        """Create a resources dictionary for testing."""
        return {
            'tables': [TestDataFactory.create_table_config(table_name)],
            'items': {
                table_name: [
                    TestDataFactory.create_item_request(str(i)) for i in range(1, item_count + 1)
                ]
            },
        }


# Test Fixtures
@pytest.fixture
def mock_dynamodb_client():
    """Create a mock DynamoDB client with common setup."""
    client = Mock()
    client.list_tables.return_value = {'TableNames': []}
    client.create_table.return_value = {
        'TableDescription': {'TableArn': 'arn:aws:dynamodb:us-east-1:123456789012:table/test'}
    }
    client.batch_write_item.return_value = {'UnprocessedItems': {}}

    # Setup exception classes
    class ResourceInUseException(Exception):
        pass

    class ResourceNotFoundException(Exception):
        pass

    client.exceptions.ResourceInUseException = ResourceInUseException
    client.exceptions.ResourceNotFoundException = ResourceNotFoundException

    return client


@pytest.fixture
def sample_resources():
    """Provide sample resources for testing."""
    return TestDataFactory.create_resources_dict()


# Helper Functions
def assert_successful_result(result, table_name='test-table'):
    """Assert that a result indicates success for a given table."""
    assert result[table_name]['status'] == 'success'


def assert_error_result(result, table_name, error_message=None):
    """Assert that a result indicates an error for a given table."""
    assert result[table_name]['status'] == 'error'
    if error_message:
        assert error_message in result[table_name]['error']


class TestDynamoDBLocalSetup:
    """Test cases for DynamoDB Local setup functionality."""

    def test_find_first_available_port(self):
        """Test finding available port when first port is free."""
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock

            port = find_available_port(8000)
            assert port == 8000
            mock_sock.bind.assert_called_once_with(('localhost', 8000))

    def test_find_next_available_port(self):
        """Test finding available port when first port is busy."""
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            # First bind fails (port busy), second bind succeeds and returns port from getsockname
            mock_sock.bind.side_effect = [OSError('Port in use'), None]
            mock_sock.getsockname.return_value = ('localhost', 8001)

            port = find_available_port(8000)
            assert port == 8001
            assert mock_sock.bind.call_count == 2

    def test_get_existing_container_dynamodb_local_endpoint_found(self):
        """Test getting endpoint when container is running."""
        with patch('subprocess.run') as mock_run:
            # Mock the three subprocess calls in order
            mock_run.side_effect = [
                MagicMock(stdout='container_id'),  # ps -a -q (container exists)
                MagicMock(stdout='container_id'),  # ps -q (container is running)
                MagicMock(stdout='0.0.0.0:8001->8000/tcp'),  # ps --format (get ports)
            ]

            endpoint = get_existing_container_dynamodb_local_endpoint('/usr/local/bin/docker')
            assert endpoint == 'http://localhost:8001'

            assert mock_run.call_count == 3

    def test_get_existing_container_dynamodb_local_endpoint_not_found(self):
        """Test getting endpoint when no container is running."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = ''

            endpoint = get_existing_container_dynamodb_local_endpoint('/usr/local/bin/docker')
            assert endpoint is None

    def test_get_existing_container_dynamodb_local_endpoint_stopped_container(self):
        """Test getting endpoint when container exists but is stopped."""
        with patch('subprocess.run') as mock_run:
            # Mock the subprocess calls: container exists, not running, then restart and get ports
            mock_run.side_effect = [
                MagicMock(stdout='container_id'),  # ps -a -q (container exists)
                MagicMock(stdout=''),  # ps -q (container not running)
                MagicMock(stdout=''),  # docker start (restart container)
                MagicMock(
                    stdout='0.0.0.0:8002->8000/tcp'
                ),  # ps --format (get ports after restart)
            ]

            endpoint = get_existing_container_dynamodb_local_endpoint('/usr/local/bin/docker')
            assert endpoint == 'http://localhost:8002'

            assert mock_run.call_count == 4

    def test_start_container_success(self):
        """Test Docker container start success."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
            ) as mock_run_safe,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._create_dynamodb_client'
            ) as mock_create_client,
        ):
            # Mock subprocess call
            mock_run_safe.return_value = MagicMock()

            # Mock DynamoDB client and list_tables call
            mock_client = MagicMock()
            mock_create_client.return_value = mock_client
            mock_client.list_tables.return_value = {'TableNames': []}

            endpoint = start_container('/usr/local/bin/docker', 8000)
            assert endpoint == 'http://localhost:8000'

            # Verify the subprocess call
            mock_run_safe.assert_called_once_with(
                [
                    '/usr/local/bin/docker',
                    'run',
                    '-d',
                    '--name',
                    'dynamodb-local-setup-for-data-model-validation',
                    '-p',
                    '127.0.0.1:8000:8000',
                    'amazon/dynamodb-local',
                ],
                timeout=30,
            )

            # Verify DynamoDB client creation and usage
            mock_create_client.assert_called_once_with('http://localhost:8000')
            mock_client.list_tables.assert_called_once()

    def test_setup_dynamodb_local_reuse_existing(self):
        """Test setup reuses existing container."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_existing_container_dynamodb_local_endpoint'
            ) as mock_get_endpoint,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_container_path'
            ) as mock_get_container,
        ):
            mock_get_container.return_value = '/usr/local/bin/docker'
            mock_get_endpoint.return_value = 'http://localhost:8001'

            endpoint = setup_dynamodb_local()
            assert endpoint == 'http://localhost:8001'

    def test_setup_dynamodb_local_new_container(self):
        """Test setup creates new container when none exists."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_existing_container_dynamodb_local_endpoint'
            ) as mock_get_endpoint,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_container_path'
            ) as mock_get_path,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.find_available_port'
            ) as mock_find_port,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.start_container'
            ) as mock_start_container,
        ):
            mock_get_path.return_value = '/usr/local/bin/docker'
            mock_get_endpoint.return_value = None
            mock_find_port.return_value = 8001
            mock_start_container.return_value = 'http://localhost:8001'

            endpoint = setup_dynamodb_local()

            assert endpoint == 'http://localhost:8001'
            mock_find_port.assert_called_once_with(8000)
            mock_start_container.assert_called_once_with('/usr/local/bin/docker', 8001)

    def test_setup_dynamodb_local_java_fallback(self):
        """Test setup falls back to Java when Docker is not available."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_container_path'
            ) as mock_get_container,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_java_path'
            ) as mock_get_java,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_existing_java_dynamodb_local_endpoint'
            ) as mock_get_java_endpoint,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.find_available_port'
            ) as mock_find_port,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.start_java_process'
            ) as mock_start_java,
        ):
            # Docker not available
            mock_get_container.return_value = None

            # Java available
            mock_get_java.return_value = '/usr/bin/java'
            mock_get_java_endpoint.return_value = None
            mock_find_port.return_value = 8002
            mock_start_java.return_value = 'http://localhost:8002'

            endpoint = setup_dynamodb_local()

            assert endpoint == 'http://localhost:8002'
            mock_start_java.assert_called_once_with('/usr/bin/java', 8002)

    def test_setup_dynamodb_local_neither_available(self):
        """Test setup fails when neither Docker nor Java is available."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_container_path'
            ) as mock_get_container,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_java_path'
            ) as mock_get_java,
        ):
            mock_get_container.return_value = None  # Docker not available
            mock_get_java.return_value = None  # Java not available

            with pytest.raises(RuntimeError) as exc_info:
                setup_dynamodb_local()

            assert 'No working container tool or Java found' in str(exc_info.value)

    def test_parse_container_port_no_arrow(self):
        """Test _parse_container_port when no arrow is present."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _parse_container_port

        result = _parse_container_port('8000/tcp')
        assert result is None

    def test_parse_container_port_with_arrow(self):
        """Test _parse_container_port with arrow present."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _parse_container_port

        result = _parse_container_port('0.0.0.0:8001->8000/tcp')
        assert result == '8001'

    def test_container_exists_no_output(self):
        """Test _container_exists when no container output."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _container_exists

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
        ) as mock_run:
            mock_run.return_value = MagicMock(stdout='')

            result = _container_exists('/usr/bin/docker')
            assert result == ''  # Empty string is falsy but not False

    def test_container_is_running_no_output(self):
        """Test _container_is_running when no container output."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _container_is_running

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
        ) as mock_run:
            mock_run.return_value = MagicMock(stdout='')

            result = _container_is_running('/usr/bin/docker')
            assert result == ''  # Empty string is falsy but not False

    def test_restart_container_failure(self):
        """Test _restart_container when restart fails."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _restart_container

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
        ) as mock_run:
            mock_run.return_value = None

            result = _restart_container('/usr/bin/docker')
            assert result is False

    def test_get_container_port_no_output(self):
        """Test _get_container_port when no port output."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _get_container_port

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
        ) as mock_run:
            mock_run.return_value = MagicMock(stdout='')

            result = _get_container_port('/usr/bin/docker')
            assert result is None

    def test_get_existing_container_endpoint_restart_failure(self):
        """Test get_existing_container_dynamodb_local_endpoint when restart fails."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._container_exists'
            ) as mock_exists,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._container_is_running'
            ) as mock_running,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._restart_container'
            ) as mock_restart,
        ):
            mock_exists.return_value = True
            mock_running.return_value = False
            mock_restart.return_value = False

            result = get_existing_container_dynamodb_local_endpoint('/usr/bin/docker')
            assert result is None

    def test_get_existing_container_endpoint_exception(self):
        """Test get_existing_container_dynamodb_local_endpoint with exception."""
        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils._container_exists'
        ) as mock_exists:
            mock_exists.side_effect = Exception('Container check failed')

            result = get_existing_container_dynamodb_local_endpoint('/usr/bin/docker')
            assert result is None

    def test_start_container_failure(self):
        """Test start_container when subprocess fails."""
        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
        ) as mock_run:
            mock_run.return_value = None

            with pytest.raises(RuntimeError, match='Failed to start Docker container'):
                start_container('/usr/bin/docker', 8000)

    def test_get_existing_java_endpoint_process_exceptions(self):
        """Test get_existing_java_dynamodb_local_endpoint with process exceptions."""
        import psutil

        with patch('psutil.process_iter') as mock_process_iter:
            # Create a mock process that raises exception when accessing info
            def mock_proc_generator():
                mock_proc = MagicMock()
                mock_proc.info = {'pid': 12345, 'name': 'java', 'cmdline': ['java']}
                # Make accessing info raise an exception
                type(mock_proc).info = PropertyMock(side_effect=psutil.NoSuchProcess(12345))
                yield mock_proc

            mock_process_iter.return_value = mock_proc_generator()

            result = get_existing_java_dynamodb_local_endpoint()
            assert result is None

    def test_get_existing_java_endpoint_general_exception(self):
        """Test get_existing_java_dynamodb_local_endpoint with general exception."""
        with patch('psutil.process_iter') as mock_process_iter:
            mock_process_iter.side_effect = Exception('Process iteration failed')

            result = get_existing_java_dynamodb_local_endpoint()
            assert result is None

    def test_get_existing_java_endpoint_general_exception_in_process_loop(self):
        """Test get_existing_java_dynamodb_local_endpoint with exception in process loop."""
        with patch('psutil.process_iter') as mock_process_iter:
            # Create a mock process that raises exception when accessing info
            def mock_proc_generator():
                mock_proc = MagicMock()
                # Make accessing info raise a general exception
                type(mock_proc).info = PropertyMock(side_effect=Exception('General error'))
                yield mock_proc

            mock_process_iter.return_value = mock_proc_generator()

            result = get_existing_java_dynamodb_local_endpoint()
            assert result is None

    def test_start_java_process_failure(self):
        """Test start_java_process when Java process fails to start."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.download_dynamodb_local_jar'
            ) as mock_download,
            patch('subprocess.Popen') as mock_popen,
            patch('time.sleep'),
        ):
            mock_download.return_value = ('DynamoDBLocal.jar', '/tmp/lib')
            mock_process = Mock()
            mock_process.poll.return_value = 1  # Process failed
            mock_process.communicate.return_value = ('', b'Java error')  # stderr is bytes
            mock_popen.return_value = mock_process

            with pytest.raises(RuntimeError, match='Java process failed to start: Java error'):
                start_java_process('/usr/bin/java', 8000)

    def test_start_java_process_invalid_executable(self):
        """Test start_java_process with invalid Java executable."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.download_dynamodb_local_jar'
            ) as mock_download,
        ):
            mock_download.return_value = ('DynamoDBLocal.jar', '/tmp/lib')

            with pytest.raises(RuntimeError, match='Invalid Java executable: malicious'):
                start_java_process('/usr/bin/malicious', 8000)

    def test_try_container_setup_runtime_error(self):
        """Test _try_container_setup with RuntimeError."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _try_container_setup

        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_container_path'
            ) as mock_get_path,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_existing_container_dynamodb_local_endpoint'
            ) as mock_get_endpoint,
        ):
            mock_get_path.return_value = '/usr/bin/docker'
            mock_get_endpoint.side_effect = RuntimeError('Container setup failed')

            result = _try_container_setup()
            assert result is None

    def test_try_java_setup_runtime_error(self):
        """Test _try_java_setup with RuntimeError."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _try_java_setup

        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_java_path'
            ) as mock_get_path,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.get_existing_java_dynamodb_local_endpoint'
            ) as mock_get_endpoint,
        ):
            mock_get_path.return_value = '/usr/bin/java'
            mock_get_endpoint.side_effect = RuntimeError('Java setup failed')

            result = _try_java_setup()
            assert result is None

    def test_run_subprocess_safely_file_not_found(self):
        """Test _run_subprocess_safely with FileNotFoundError."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _run_subprocess_safely

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError('Command not found')

            result = _run_subprocess_safely(['docker', 'ps'])
            assert result is None

    def test_run_subprocess_safely_allowed_commands(self):
        """Test _run_subprocess_safely allows whitelisted commands."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _run_subprocess_safely

        allowed_commands = [
            ['docker', 'ps'],
            ['/usr/bin/docker', 'ps'],
            ['finch', 'ps'],
            ['podman', 'ps'],
            ['nerdctl', 'ps'],
            ['java', '-version'],
            ['/usr/bin/java', '-version'],
            ['docker.exe', 'ps'],  # Windows
        ]

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock()

            for cmd in allowed_commands:
                result = _run_subprocess_safely(cmd)
                assert result is not None

    def test_run_subprocess_safely_blocked_commands(self):
        """Test _run_subprocess_safely blocks non-whitelisted commands."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _run_subprocess_safely

        blocked_commands = [
            ['rm', '-rf', '/'],
            ['curl', 'http://malicious.com'],
            ['wget', 'http://evil.com'],
            ['bash', '-c', 'rm -rf /'],
            ['python', 'malicious_script.py'],
            ['node', 'malware.js'],
            ['arbitrary_command'],
        ]

        with patch('subprocess.run') as mock_run:
            for cmd in blocked_commands:
                result = _run_subprocess_safely(cmd)
                assert result is None
                mock_run.assert_not_called()

    def test_run_subprocess_safely_windows_exe_handling(self):
        """Test _run_subprocess_safely handles .exe extension on Windows."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _run_subprocess_safely

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock()

            # Test .exe extension is stripped for validation
            result = _run_subprocess_safely(['docker.exe', 'ps'])
            assert result is not None

            result = _run_subprocess_safely(['java.exe', '-version'])
            assert result is not None

    def test_run_subprocess_safely_timeout_expired(self):
        """Test _run_subprocess_safely handles TimeoutExpired exception."""
        import subprocess
        from awslabs.dynamodb_mcp_server.model_validation_utils import _run_subprocess_safely

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(['docker', 'ps'], 5)

            result = _run_subprocess_safely(['docker', 'ps'])
            assert result is None

    def test_run_subprocess_safely_called_process_error(self):
        """Test _run_subprocess_safely handles CalledProcessError exception."""
        import subprocess
        from awslabs.dynamodb_mcp_server.model_validation_utils import _run_subprocess_safely

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ['docker', 'ps'])

            result = _run_subprocess_safely(['docker', 'ps'])
            assert result is None

    def test_run_subprocess_safely_invalid_input(self):
        """Test _run_subprocess_safely with invalid input."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import _run_subprocess_safely

        invalid_inputs = [
            None,
            [],
            'not_a_list',
            123,
        ]

        with patch('subprocess.run') as mock_run:
            for invalid_input in invalid_inputs:
                result = _run_subprocess_safely(invalid_input)
                assert result is None
                mock_run.assert_not_called()

    def test_start_java_process_success(self):
        """Test Java process start success."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.download_dynamodb_local_jar'
            ) as mock_download,
            patch('subprocess.Popen') as mock_popen,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.check_dynamodb_readiness'
            ) as mock_readiness,
            patch('time.sleep'),
        ):
            mock_download.return_value = ('DynamoDBLocal.jar', '/tmp/DynamoDBLocal_lib')
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            mock_readiness.return_value = 'http://localhost:8003'

            endpoint = start_java_process('/usr/bin/java', 8003)
            assert endpoint == 'http://localhost:8003'

            mock_download.assert_called_once()
            mock_popen.assert_called_once()
            mock_readiness.assert_called_once_with('http://localhost:8003')

    def test_get_existing_java_dynamodb_local_endpoint_found(self):
        """Test finding existing Java process."""
        with patch('psutil.process_iter') as mock_process_iter:
            # Mock process with Java name and our property in cmdline
            mock_proc = MagicMock()
            mock_proc.info = {
                'pid': 12345,
                'name': 'java',
                'cmdline': [
                    'java',
                    '-Ddynamodb.local.setup.for.data.model.validation=true',
                    '-jar',
                    'DynamoDBLocal.jar',
                    '-bindAddress',
                    '127.0.0.1',
                    '-port',
                    '8004',
                    '-inMemory',
                    '-sharedDb',
                ],
            }
            mock_process_iter.return_value = [mock_proc]

            endpoint = get_existing_java_dynamodb_local_endpoint()
            assert endpoint == 'http://localhost:8004'

    def test_get_existing_java_dynamodb_local_endpoint_not_found(self):
        """Test when no Java process is found."""
        with patch('psutil.process_iter') as mock_process_iter:
            # Mock no processes or processes without our property
            mock_proc = MagicMock()
            mock_proc.info = {
                'pid': 12345,
                'name': 'java',
                'cmdline': ['java', '-jar', 'other-app.jar'],  # Different Java app
            }
            mock_process_iter.return_value = [mock_proc]

            endpoint = get_existing_java_dynamodb_local_endpoint()
            assert endpoint is None


class TestCreateValidationResources:
    """Test cases for create_validation_resources function."""

    def test_create_validation_resources_success(self, sample_resources):
        """Test successful creation of validation resources."""
        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.boto3.client'
            ) as mock_client_factory,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.create_tables'
            ) as mock_create_tables,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.insert_items'
            ) as mock_insert_items,
        ):
            # Mock the client with proper endpoint_url attribute
            mock_client = Mock()
            mock_client.meta.endpoint_url = 'http://localhost:8000'
            mock_client_factory.return_value = mock_client

            mock_create_tables.return_value = {'test-table': {'status': 'success'}}
            mock_insert_items.return_value = {'test-table': {'status': 'success'}}

            result = create_validation_resources(sample_resources)

            assert 'tables' in result
            assert 'items' in result
            mock_create_tables.assert_called_once()
            mock_insert_items.assert_called_once()

    def test_create_validation_resources_invalid_types(self):
        """Test create_validation_resources with invalid data types."""
        resources = {
            'tables': 'not_a_list',  # Should be converted to []
            'items': 'not_a_dict',  # Should be converted to {}
        }

        with (
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._create_dynamodb_client'
            ) as mock_client_factory,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.cleanup_validation_resources'
            ),
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.create_tables'
            ) as mock_create_tables,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.insert_items'
            ) as mock_insert_items,
        ):
            mock_client = Mock()
            mock_client.meta.endpoint_url = 'http://localhost:8000'
            mock_client_factory.return_value = mock_client

            mock_create_tables.return_value = {}
            mock_insert_items.return_value = {}

            create_validation_resources(resources)

            # Verify that empty list and dict were passed
            mock_create_tables.assert_called_once_with(mock_client, [])
            mock_insert_items.assert_called_once_with(mock_client, {})


class TestCreateTables:
    """Test cases for create_tables function."""

    def test_create_tables_already_exists(self, mock_dynamodb_client):
        """Test table creation when table already exists."""
        mock_dynamodb_client.create_table.side_effect = (
            mock_dynamodb_client.exceptions.ResourceInUseException()
        )

        tables = [TestDataFactory.create_table_config('existing-table')]
        result = create_tables(mock_dynamodb_client, tables)

        assert result['existing-table']['status'] == 'exists'
        assert 'already exists' in result['existing-table']['message']

    def test_create_tables_error(self, mock_dynamodb_client):
        """Test table creation error handling."""
        mock_dynamodb_client.create_table.side_effect = Exception('Test error')

        tables = [TestDataFactory.create_table_config('error-table')]
        result = create_tables(mock_dynamodb_client, tables)

        assert_error_result(result, 'error-table', 'Test error')

    def test_create_tables_multiple_tables(self, mock_dynamodb_client):
        """Test creation of multiple tables."""
        tables = [
            TestDataFactory.create_table_config('table1'),
            TestDataFactory.create_table_config('table2'),
        ]
        result = create_tables(mock_dynamodb_client, tables)

        assert len(result) == 2
        assert_successful_result(result, 'table1')
        assert_successful_result(result, 'table2')

    def test_create_tables_invalid_config(self, mock_dynamodb_client):
        """Test create_tables with invalid table configurations."""
        # Test with non-dict config
        tables = ['invalid_config', {'missing_table_name': 'value'}]
        result = create_tables(mock_dynamodb_client, tables)

        assert result == {}
        mock_dynamodb_client.create_table.assert_not_called()


class TestInsertItems:
    """Test cases for insert_items function."""

    def test_insert_items_success(self, mock_dynamodb_client):
        """Test successful item insertion."""
        items = {
            'test-table': [
                TestDataFactory.create_item_request('1'),
                TestDataFactory.create_item_request('2'),
            ]
        }
        result = insert_items(mock_dynamodb_client, items)

        assert_successful_result(result, 'test-table')
        assert result['test-table']['items_processed'] == 2

    def test_insert_items_with_unprocessed(self, mock_dynamodb_client):
        """Test item insertion with unprocessed items."""
        unprocessed_item = TestDataFactory.create_item_request('1')
        mock_dynamodb_client.batch_write_item.return_value = {
            'UnprocessedItems': {'test-table': [unprocessed_item]}
        }

        items = {'test-table': [unprocessed_item]}
        result = insert_items(mock_dynamodb_client, items)

        assert_successful_result(result, 'test-table')
        assert result['test-table']['items_processed'] == 0  # 1 item - 1 unprocessed = 0 processed

    def test_insert_items_error(self, mock_dynamodb_client):
        """Test item insertion error handling."""
        mock_dynamodb_client.batch_write_item.side_effect = Exception('Batch write error')

        items = {'test-table': [TestDataFactory.create_item_request('1')]}
        result = insert_items(mock_dynamodb_client, items)

        assert_error_result(result, 'test-table', 'Batch write error')

    def test_insert_items_multiple_tables(self, mock_dynamodb_client):
        """Test item insertion across multiple tables."""
        items = {
            'table1': [TestDataFactory.create_item_request('1')],
            'table2': [TestDataFactory.create_item_request('2')],
        }
        result = insert_items(mock_dynamodb_client, items)

        assert len(result) == 2
        assert_successful_result(result, 'table1')
        assert_successful_result(result, 'table2')

    def test_insert_items_empty_items(self, mock_dynamodb_client):
        """Test item insertion with empty items dictionary."""
        result = insert_items(mock_dynamodb_client, {})

        assert result == {}
        mock_dynamodb_client.batch_write_item.assert_not_called()

    def test_insert_items_invalid_items(self, mock_dynamodb_client):
        """Test insert_items with invalid item configurations."""
        # Test with non-list items
        items = {'table1': 'invalid_items', 'table2': {'not': 'a_list'}}
        result = insert_items(mock_dynamodb_client, items)

        assert result == {}
        mock_dynamodb_client.batch_write_item.assert_not_called()


class TestCleanupValidationResources:
    """Test cases for cleanup_validation_resources function."""

    def test_cleanup_validation_resources_success(self):
        """Test successful cleanup of validation resources."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = 'http://localhost:8000'

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils.list_tables'
        ) as mock_list_tables:
            mock_list_tables.return_value = ['table1', 'table2']

            result = cleanup_validation_resources(mock_client)

            assert len(result) == 2
            assert result['table1']['status'] == 'deleted'
            assert result['table2']['status'] == 'deleted'
            assert mock_client.delete_table.call_count == 2

    def test_cleanup_validation_resources_safety_check_localhost(self):
        """Test safety check allows localhost endpoints."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = 'http://localhost:8000'

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils.list_tables'
        ) as mock_list_tables:
            mock_list_tables.return_value = ['test-table']

            result = cleanup_validation_resources(mock_client)
            assert result['test-table']['status'] == 'deleted'

    def test_cleanup_validation_resources_safety_check_127_0_0_1(self):
        """Test safety check allows 127.0.0.1 endpoints."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = 'http://127.0.0.1:8000'

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils.list_tables'
        ) as mock_list_tables:
            mock_list_tables.return_value = ['test-table']

            result = cleanup_validation_resources(mock_client)
            assert result['test-table']['status'] == 'deleted'

    def test_cleanup_validation_resources_safety_check_blocks_production(self):
        """Test safety check blocks production endpoints."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = 'https://dynamodb.us-east-1.amazonaws.com'

        with pytest.raises(ValueError) as exc_info:
            cleanup_validation_resources(mock_client)

        assert 'SAFETY VIOLATION' in str(exc_info.value)
        assert 'Table deletion must only run on localhost' in str(exc_info.value)
        assert 'Got endpoint:' in str(exc_info.value)

    def test_cleanup_validation_resources_safety_check_blocks_remote_ip(self):
        """Test safety check blocks remote IP addresses."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = 'http://192.168.1.100:8000'

        with pytest.raises(ValueError) as exc_info:
            cleanup_validation_resources(mock_client)

        assert 'SAFETY VIOLATION' in str(exc_info.value)
        assert 'Got endpoint:' in str(exc_info.value)

    def test_cleanup_validation_resources_safety_check_blocks_bypass_attempts(self):
        """Test safety check blocks potential bypass attempts with localhost in path."""
        mock_client = Mock()
        # Test potential bypass attempts
        bypass_urls = [
            'https://malicious.com/localhost',
            'https://127.0.0.1.evil.com',
            'https://evil.com/path/localhost/data',
            'https://localhost.evil.com',
        ]

        for url in bypass_urls:
            mock_client.meta.endpoint_url = url
            with pytest.raises(ValueError) as exc_info:
                cleanup_validation_resources(mock_client)

            assert 'SAFETY VIOLATION' in str(exc_info.value)
            assert url in str(exc_info.value)

    def test_cleanup_validation_resources_safety_check_allows_none_endpoint(self):
        """Test safety check allows None endpoint (default AWS)."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = None

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils.list_tables'
        ) as mock_list_tables:
            mock_list_tables.return_value = ['test-table']

            result = cleanup_validation_resources(mock_client)
            assert result['test-table']['status'] == 'deleted'

    def test_cleanup_validation_resources_safety_check_allows_valid_localhost_variants(self):
        """Test safety check allows valid localhost variants."""
        valid_urls = [
            'http://localhost:8000',
            'https://localhost:8000',
            'http://127.0.0.1:8000',
            'https://127.0.0.1:8000',
        ]

        for url in valid_urls:
            mock_client = Mock()
            mock_client.meta.endpoint_url = url

            with patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils.list_tables'
            ) as mock_list_tables:
                mock_list_tables.return_value = ['test-table']

                result = cleanup_validation_resources(mock_client)
                assert result['test-table']['status'] == 'deleted'

    def test_cleanup_validation_resources_resource_not_found(self):
        """Test cleanup when resource is not found."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = 'http://localhost:8000'
        mock_client.exceptions.ResourceNotFoundException = Exception
        mock_client.delete_table.side_effect = mock_client.exceptions.ResourceNotFoundException()

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils.list_tables'
        ) as mock_list_tables:
            mock_list_tables.return_value = ['missing-table']

            result = cleanup_validation_resources(mock_client)

            assert result['missing-table']['status'] == 'not_found'
            assert 'not found' in result['missing-table']['message']

    def test_cleanup_validation_resources_delete_error(self):
        """Test cleanup error handling during table deletion."""
        mock_client = Mock()
        mock_client.meta.endpoint_url = 'http://localhost:8000'
        mock_client.exceptions.ResourceNotFoundException = type(
            'ResourceNotFoundException', (Exception,), {}
        )
        mock_client.delete_table.side_effect = Exception('Delete failed')

        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils.list_tables'
        ) as mock_list_tables:
            mock_list_tables.return_value = ['error-table']

            result = cleanup_validation_resources(mock_client)

            assert result['error-table']['status'] == 'error'
            assert result['error-table']['error'] == 'Delete failed'


class TestListTables:
    """Test cases for list_tables function."""

    def test_list_tables_success(self):
        """Test successful table listing."""
        mock_client = Mock()
        mock_client.list_tables.return_value = {'TableNames': ['table1', 'table2', 'table3']}

        result = list_tables(mock_client)

        assert result == ['table1', 'table2', 'table3']

    def test_list_tables_error(self):
        """Test table listing error handling."""
        mock_client = Mock()
        mock_client.list_tables.side_effect = Exception('List failed')

        result = list_tables(mock_client)

        assert result == []


class TestGetContainerPath:
    """Test cases for get_container_path function."""

    def test_get_container_path_docker_available(self):
        """Test when Docker is available and working."""
        with (
            patch('shutil.which') as mock_which,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
            ) as mock_run_safe,
        ):
            mock_which.side_effect = lambda tool: '/usr/bin/docker' if tool == 'docker' else None
            mock_run_safe.return_value = MagicMock()

            result = get_container_path()
            assert result == '/usr/bin/docker'

            mock_run_safe.assert_called_once_with(['/usr/bin/docker', 'ps'])

    def test_get_container_path_finch_available(self):
        """Test when Docker fails but Finch is available."""
        with (
            patch('shutil.which') as mock_which,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
            ) as mock_run_safe,
        ):

            def which_side_effect(tool):
                if tool == 'docker':
                    return '/usr/bin/docker'
                elif tool == 'finch':
                    return '/usr/bin/finch'
                return None

            mock_which.side_effect = which_side_effect

            # Docker fails, Finch succeeds
            mock_run_safe.side_effect = [
                None,  # Docker fails
                MagicMock(),  # Finch succeeds
            ]

            result = get_container_path()
            assert result == '/usr/bin/finch'
            assert mock_run_safe.call_count == 2

    def test_get_container_path_no_tools_found(self):
        """Test when no container tools are found in PATH."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None

            result = get_container_path()
            assert result is None

    def test_get_container_path_all_tools_fail(self):
        """Test when all container tools are found but none work."""
        with (
            patch('shutil.which') as mock_which,
            patch(
                'awslabs.dynamodb_mcp_server.model_validation_utils._run_subprocess_safely'
            ) as mock_run_safe,
        ):
            mock_which.return_value = '/usr/bin/tool'  # All tools found
            mock_run_safe.return_value = None  # All tools fail

            result = get_container_path()
            assert result is None
            assert mock_run_safe.call_count == 4  # All 4 tools tried


class TestGetJavaPath:
    """Test cases for get_java_path function."""

    def test_get_java_path_java_home_unix(self):
        """Test Java path resolution using JAVA_HOME on Unix systems."""
        with (
            patch.dict(os.environ, {'JAVA_HOME': '/usr/lib/jvm/java-11'}),
            patch('sys.platform', 'linux'),
            patch('os.path.isfile') as mock_isfile,
            patch('os.access') as mock_access,
        ):
            mock_isfile.return_value = True
            mock_access.return_value = True

            result = get_java_path()
            assert result == '/usr/lib/jvm/java-11/bin/java'

            mock_isfile.assert_called_once_with('/usr/lib/jvm/java-11/bin/java')
            mock_access.assert_called_once_with('/usr/lib/jvm/java-11/bin/java', os.X_OK)

    def test_get_java_path_java_home_windows(self):
        """Test Java path resolution using JAVA_HOME on Windows."""
        with (
            patch.dict(os.environ, {'JAVA_HOME': 'C:\\Program Files\\Java\\jdk-11'}),
            patch('sys.platform', 'win32'),
            patch('os.path.isfile') as mock_isfile,
            patch('os.access') as mock_access,
        ):
            mock_isfile.return_value = True
            mock_access.return_value = True

            result = get_java_path()
            # Use os.path.join to handle path separators correctly
            expected_path = os.path.join('C:\\Program Files\\Java\\jdk-11', 'bin', 'java.exe')
            assert result == expected_path

    def test_get_java_path_java_home_not_executable(self):
        """Test when JAVA_HOME points to non-executable file."""
        with (
            patch.dict(os.environ, {'JAVA_HOME': '/usr/lib/jvm/java-11'}),
            patch('sys.platform', 'linux'),
            patch('os.path.isfile') as mock_isfile,
            patch('os.access') as mock_access,
            patch('shutil.which') as mock_which,
        ):
            mock_isfile.return_value = True
            mock_access.return_value = False  # Not executable
            mock_which.return_value = '/usr/bin/java'

            result = get_java_path()
            assert result == '/usr/bin/java'
            mock_which.assert_called_once_with('java')

    @pytest.mark.parametrize(
        'which_return_value,expected_result',
        [
            ('/usr/bin/java', '/usr/bin/java'),  # Java found in PATH
            (None, None),  # Java not found anywhere
        ],
    )
    def test_get_java_path_fallback_to_path(self, which_return_value, expected_result):
        """Test fallback to PATH when JAVA_HOME is not set."""
        with patch.dict(os.environ, {}, clear=True), patch('shutil.which') as mock_which:
            mock_which.return_value = which_return_value

            result = get_java_path()
            assert result == expected_result
            mock_which.assert_called_once_with('java')


class TestExtractPortFromCmdline:
    """Test cases for _extract_port_from_cmdline function."""

    @pytest.mark.parametrize(
        'cmdline,expected_port',
        [
            (['java', '-jar', 'DynamoDBLocal.jar', '-port', '8080', '-inMemory'], 8080),
            (['java', '-jar', 'DynamoDBLocal.jar', '-inMemory', '-port'], None),
            (['java', '-jar', 'DynamoDBLocal.jar', '-port', 'invalid', '-inMemory'], None),
            (['java', '-jar', 'DynamoDBLocal.jar', '-inMemory'], None),
            ([], None),
        ],
    )
    def test_extract_port_from_cmdline(self, cmdline, expected_port):
        """Test port extraction from various command line scenarios."""
        result = _extract_port_from_cmdline(cmdline)
        assert result == expected_port


class TestDownloadDynamodbLocalJar:
    """Test cases for download_dynamodb_local_jar function."""

    def test_download_dynamodb_local_jar_already_exists(self):
        """Test when JAR and lib directory already exist."""
        with patch('tempfile.gettempdir') as mock_tempdir, patch('os.path.exists') as mock_exists:
            mock_tempdir.return_value = '/tmp'
            mock_exists.return_value = True

            jar_path, lib_path = download_dynamodb_local_jar()

            expected_jar = '/tmp/dynamodb-local-model-validation/DynamoDBLocal.jar'
            expected_lib = '/tmp/dynamodb-local-model-validation/DynamoDBLocal_lib'

            assert jar_path == expected_jar
            assert lib_path == expected_lib

    def test_download_dynamodb_local_jar_download_success(self):
        """Test successful download and extraction."""
        with (
            patch('tempfile.gettempdir') as mock_tempdir,
            patch('os.path.exists') as mock_exists,
            patch('os.makedirs') as mock_makedirs,
            patch('urllib.request.urlopen') as mock_urlopen,
            patch('tarfile.open') as mock_tarfile,
            patch('os.remove') as mock_remove,
        ):
            mock_tempdir.return_value = '/tmp'
            mock_exists.side_effect = lambda path: path.endswith(
                'DynamoDBLocal.jar'
            )  # Only JAR exists after extraction

            # Mock download
            mock_response = MagicMock()
            mock_response.read.return_value = b'fake_tar_content'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Mock tar extraction
            mock_tar = MagicMock()
            mock_tar.getnames.return_value = ['DynamoDBLocal.jar', 'DynamoDBLocal_lib/file.so']
            mock_tarfile.return_value.__enter__.return_value = mock_tar

            with patch('builtins.open', mock_open()):
                jar_path, lib_path = download_dynamodb_local_jar()

            expected_jar = '/tmp/dynamodb-local-model-validation/DynamoDBLocal.jar'
            expected_lib = '/tmp/dynamodb-local-model-validation/DynamoDBLocal_lib'

            assert jar_path == expected_jar
            assert lib_path == expected_lib

            mock_makedirs.assert_called_once()
            mock_urlopen.assert_called_once()
            # Verify safe extraction was used
            call_args = mock_tar.extractall.call_args
            assert call_args[0][0] == '/tmp/dynamodb-local-model-validation'
            assert 'members' in call_args[1]
            mock_remove.assert_called_once()

    def test_download_dynamodb_local_jar_download_failure(self):
        """Test download failure handling."""
        with (
            patch('tempfile.gettempdir') as mock_tempdir,
            patch('os.makedirs'),
            patch('urllib.request.urlopen') as mock_urlopen,
            patch('shutil.rmtree') as mock_rmtree,
        ):
            mock_tempdir.return_value = '/tmp'
            mock_urlopen.side_effect = Exception('Network error')

            # Mock os.path.exists to return False for JAR/lib (so it tries to download)
            # and True for dynamodb_dir (so it gets cleaned up)
            def exists_side_effect(path):
                if path.endswith('DynamoDBLocal.jar') or path.endswith('DynamoDBLocal_lib'):
                    return False
                elif 'dynamodb-local-model-validation' in path:
                    return True
                return False

            with patch('os.path.exists', side_effect=exists_side_effect):
                with pytest.raises(RuntimeError) as exc_info:
                    download_dynamodb_local_jar()

            assert 'Failed to download DynamoDB Local' in str(exc_info.value)
            mock_rmtree.assert_called_once()

    def test_download_dynamodb_local_jar_extraction_failure(self):
        """Test when JAR is not found in archive."""
        with (
            patch('tempfile.gettempdir') as mock_tempdir,
            patch('os.path.exists') as mock_exists,
            patch('os.makedirs'),
            patch('urllib.request.urlopen') as mock_urlopen,
            patch('tarfile.open') as mock_tarfile,
            patch('os.remove'),
        ):
            mock_tempdir.return_value = '/tmp'
            mock_exists.return_value = False  # JAR never exists

            # Mock successful download and extraction
            mock_response = MagicMock()
            mock_response.read.return_value = b'fake_tar_content'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            mock_tar = MagicMock()
            mock_tar.getnames.return_value = ['other_file.txt']  # JAR not in archive
            mock_tarfile.return_value.__enter__.return_value = mock_tar

            with patch('builtins.open', mock_open()):
                with pytest.raises(RuntimeError) as exc_info:
                    download_dynamodb_local_jar()

            assert 'DynamoDBLocal.jar not found in archive' in str(exc_info.value)

    def test_download_jar_with_data_filter(self):
        """Test download_dynamodb_local_jar with tarfile data filter."""
        with (
            patch('tempfile.gettempdir') as mock_tempdir,
            patch('os.path.exists') as mock_exists,
            patch('os.makedirs'),
            patch('urllib.request.urlopen') as mock_urlopen,
            patch('tarfile.open') as mock_tarfile,
            patch('os.remove'),
        ):
            mock_tempdir.return_value = '/tmp'
            mock_exists.side_effect = lambda path: path.endswith('DynamoDBLocal.jar')

            # Mock download
            mock_response = MagicMock()
            mock_response.read.return_value = b'fake_tar_content'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Mock tar extraction with data filter
            mock_tar = MagicMock()
            mock_tar.getnames.return_value = ['DynamoDBLocal.jar', 'DynamoDBLocal_lib/file.so']
            mock_tarfile.return_value.__enter__.return_value = mock_tar

            # Mock tarfile module to have data_filter attribute
            with patch('tarfile.data_filter', create=True), patch('builtins.open', mock_open()):
                jar_path, lib_path = download_dynamodb_local_jar()

            # Verify data filter was used with safe extraction
            call_args = mock_tar.extractall.call_args
            assert call_args[0][0] == '/tmp/dynamodb-local-model-validation'
            assert 'members' in call_args[1]
            assert call_args[1]['filter'] == 'data'

    def test_download_jar_invalid_content_type(self):
        """Test download_dynamodb_local_jar with invalid content type."""
        with (
            patch('tempfile.gettempdir') as mock_tempdir,
            patch('os.path.exists') as mock_exists,
            patch('os.makedirs'),
            patch('urllib.request.urlopen') as mock_urlopen,
            patch('shutil.rmtree') as mock_rmtree,
        ):
            mock_tempdir.return_value = '/tmp'

            # Mock exists calls: JAR doesn't exist, lib doesn't exist, then directory exists for cleanup
            def exists_side_effect(path):
                if path.endswith('DynamoDBLocal.jar') or path.endswith('DynamoDBLocal_lib'):
                    return False  # Files don't exist, so download is attempted
                elif 'dynamodb-local-model-validation' in path:
                    return True  # Directory exists for cleanup
                return False

            mock_exists.side_effect = exists_side_effect

            # Mock response with invalid content type
            mock_response = MagicMock()
            mock_response.headers.get.return_value = 'text/html'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with pytest.raises(RuntimeError) as exc_info:
                download_dynamodb_local_jar()

            assert 'Failed to download DynamoDB Local' in str(exc_info.value)
            mock_rmtree.assert_called_once()

    def test_download_jar_already_exists_both_files(self):
        """Test download_dynamodb_local_jar when both JAR and lib already exist."""
        with (
            patch('tempfile.gettempdir') as mock_tempdir,
            patch('os.path.exists') as mock_exists,
        ):
            mock_tempdir.return_value = '/tmp'
            # Both JAR and lib exist
            mock_exists.return_value = True

            jar_path, lib_path = download_dynamodb_local_jar()

            expected_jar = '/tmp/dynamodb-local-model-validation/DynamoDBLocal.jar'
            expected_lib = '/tmp/dynamodb-local-model-validation/DynamoDBLocal_lib'

            assert jar_path == expected_jar
            assert lib_path == expected_lib


class TestCheckDynamodbReadiness:
    """Test cases for check_dynamodb_readiness function."""

    def test_check_dynamodb_readiness_success_first_attempt(self):
        """Test successful readiness check on first attempt."""
        with patch(
            'awslabs.dynamodb_mcp_server.model_validation_utils.boto3.client'
        ) as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            mock_client.list_tables.return_value = {'TableNames': []}

            result = check_dynamodb_readiness('http://localhost:8000')
            assert result == 'http://localhost:8000'

            mock_client.list_tables.assert_called_once()

    def test_check_dynamodb_readiness_success_after_retries(self):
        """Test successful readiness check after some retries."""
        with (
            patch('awslabs.dynamodb_mcp_server.model_validation_utils.boto3.client') as mock_boto3,
            patch('time.sleep') as mock_sleep,
        ):
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client

            # Fail twice, then succeed
            mock_client.list_tables.side_effect = [
                ClientError({'Error': {'Code': 'ResourceNotFoundException'}}, 'ListTables'),
                EndpointConnectionError(endpoint_url='http://localhost:8000'),
                {'TableNames': []},
            ]

            result = check_dynamodb_readiness('http://localhost:8000')
            assert result == 'http://localhost:8000'

            assert mock_client.list_tables.call_count == 3
            assert mock_sleep.call_count == 2

    def test_check_dynamodb_readiness_timeout(self):
        """Test readiness check timeout after max attempts."""
        with (
            patch('awslabs.dynamodb_mcp_server.model_validation_utils.boto3.client') as mock_boto3,
            patch('time.sleep') as mock_sleep,
        ):
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            mock_client.list_tables.side_effect = ClientError(
                {'Error': {'Code': 'ResourceNotFoundException'}}, 'ListTables'
            )

            with pytest.raises(RuntimeError) as exc_info:
                check_dynamodb_readiness('http://localhost:8000')

            assert 'DynamoDB Local failed to start' in str(exc_info.value)
            assert 'after 35 seconds' in str(exc_info.value)
            assert mock_client.list_tables.call_count == 7  # MAX_ATTEMPTS
            assert mock_sleep.call_count == 6  # MAX_ATTEMPTS - 1

    def test_check_dynamodb_readiness_with_aws_region(self):
        """Test readiness check with custom AWS region."""
        with (
            patch('awslabs.dynamodb_mcp_server.model_validation_utils.boto3.client') as mock_boto3,
            patch.dict(os.environ, {'AWS_REGION': 'eu-west-1'}),
        ):
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            mock_client.list_tables.return_value = {'TableNames': []}

            result = check_dynamodb_readiness('http://localhost:8000')
            assert result == 'http://localhost:8000'

            mock_boto3.assert_called_once_with(
                'dynamodb',
                endpoint_url='http://localhost:8000',
                aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                region_name='eu-west-1',
            )


class TestValidateDownloadUrl:
    """Test cases for _validate_download_url function."""

    def test_validate_download_url_valid_exact_url(self):
        """Test validation passes for exact DynamoDB Local URL."""
        from awslabs.dynamodb_mcp_server.model_validation_utils import DynamoDBLocalConfig

        _validate_download_url(DynamoDBLocalConfig.DOWNLOAD_URL)  # Should not raise

    def test_validate_download_url_rejects_different_url(self):
        """Test validation rejects any URL that doesn't match exactly."""
        different_urls = [
            'https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/different_file.tar.gz',
            'http://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.tar.gz',
            'https://malicious.example.com/dynamodb_local_latest.tar.gz',
            'file:///etc/passwd',
            'https://d1ni2b6xgvw0s0.cloudfront.net/v3.x/dynamodb_local_latest.tar.gz',
        ]

        for url in different_urls:
            with pytest.raises(ValueError, match='Only DynamoDB Local download URL is allowed'):
                _validate_download_url(url)


class TestSafeExtractMembers:
    """Test cases for _safe_extract_members function."""

    def test_safe_extract_members_allows_safe_paths(self):
        """Test safe extraction allows normal file paths."""

        class MockMember:
            def __init__(self, name):
                self.name = name

        safe_members = [
            MockMember('DynamoDBLocal.jar'),
            MockMember('DynamoDBLocal_lib/file.so'),
            MockMember('subdir/file.txt'),
        ]

        result = list(_safe_extract_members(safe_members))
        assert len(result) == 3
        assert all(
            member.name in ['DynamoDBLocal.jar', 'DynamoDBLocal_lib/file.so', 'subdir/file.txt']
            for member in result
        )

    def test_safe_extract_members_blocks_absolute_paths(self):
        """Test safe extraction blocks absolute paths."""

        class MockMember:
            def __init__(self, name):
                self.name = name

        dangerous_members = [
            MockMember('/etc/passwd'),
            MockMember('/usr/bin/malware'),
            MockMember('safe_file.txt'),
        ]

        result = list(_safe_extract_members(dangerous_members))
        assert len(result) == 1
        assert result[0].name == 'safe_file.txt'

    def test_safe_extract_members_blocks_directory_traversal(self):
        """Test safe extraction blocks directory traversal sequences."""

        class MockMember:
            def __init__(self, name):
                self.name = name

        dangerous_members = [
            MockMember('../../../etc/passwd'),
            MockMember('subdir/../../../malware'),
            MockMember('safe_file.txt'),
        ]

        result = list(_safe_extract_members(dangerous_members))
        assert len(result) == 1
        assert result[0].name == 'safe_file.txt'


class TestGetValidationResultTransformPrompt:
    """Test cases for get_validation_result_transform_prompt function."""

    def test_get_validation_result_transform_prompt_success(self):
        """Test successful reading of transform prompt file."""
        mock_content = '# Transform Validation Results\n\nThis is a test prompt.'

        with patch('pathlib.Path.read_text') as mock_read_text:
            mock_read_text.return_value = mock_content

            result = get_validation_result_transform_prompt()
            assert result == mock_content

            mock_read_text.assert_called_once_with(encoding='utf-8')

    @pytest.mark.parametrize(
        'exception_type,exception_args',
        [
            (FileNotFoundError, ('File not found',)),
            (PermissionError, ('Permission denied',)),
            (UnicodeDecodeError, ('utf-8', b'', 0, 1, 'invalid start byte')),
        ],
    )
    def test_get_validation_result_transform_prompt_exceptions(
        self, exception_type, exception_args
    ):
        """Test handling of various file reading exceptions."""
        with patch('pathlib.Path.read_text') as mock_read_text:
            mock_read_text.side_effect = exception_type(*exception_args)

            with pytest.raises(exception_type):
                get_validation_result_transform_prompt()
