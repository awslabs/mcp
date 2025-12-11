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

import boto3
import os
import psutil
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from botocore.exceptions import ClientError, EndpointConnectionError
from loguru import logger
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class DynamoDBLocalConfig:
    """Configuration constants for DynamoDB Local setup."""

    DEFAULT_PORT = 8000
    CONTAINER_NAME = 'dynamodb-local-setup-for-data-model-validation'
    DOCKER_IMAGE = 'amazon/dynamodb-local'
    DOWNLOAD_URL = 'https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.tar.gz'
    TAR_FILENAME = 'dynamodb_local_latest.tar.gz'
    TEMP_DIR_NAME = 'dynamodb-local-model-validation'
    MAX_ATTEMPTS = 7
    SLEEP_INTERVAL = 5
    JAVA_PROPERTY_NAME = CONTAINER_NAME.replace('-', '.')
    DOWNLOAD_TIMEOUT = 30
    BATCH_SIZE = 25


class ContainerTools:
    """Supported container tools in order of preference."""

    TOOLS = ['docker', 'finch', 'podman', 'nerdctl']


class DynamoDBClientConfig:
    """Configuration for DynamoDB client setup."""

    DUMMY_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
    DUMMY_SECRET_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # pragma: allowlist secret
    DEFAULT_REGION = 'us-east-1'


def _create_dynamodb_client(endpoint_url: Optional[str] = None):
    """Create a DynamoDB client with appropriate configuration.

    Args:
        endpoint_url: Optional endpoint URL for local DynamoDB

    Returns:
        boto3.client: Configured DynamoDB client
    """
    client_kwargs = {'endpoint_url': endpoint_url} if endpoint_url else {}
    if endpoint_url:
        client_kwargs.update(
            {
                'aws_access_key_id': DynamoDBClientConfig.DUMMY_ACCESS_KEY,  # pragma: allowlist secret
                'aws_secret_access_key': DynamoDBClientConfig.DUMMY_SECRET_KEY,  # pragma: allowlist secret
                'region_name': os.environ.get('AWS_REGION', DynamoDBClientConfig.DEFAULT_REGION),
            }
        )

    return boto3.client('dynamodb', **client_kwargs)


def _run_subprocess_safely(
    cmd: list, timeout: int = 5, **kwargs
) -> Optional[subprocess.CompletedProcess]:
    """Run subprocess with consistent error handling.

    Args:
        cmd: Command to execute
        timeout: Timeout in seconds
        **kwargs: Additional subprocess arguments

    Returns:
        Optional[subprocess.CompletedProcess]: Result if successful, None if failed
    """
    # Safeguards against direct calls
    if not cmd or not isinstance(cmd, list):
        logger.warning('Invalid command format')
        return None

    # Restrict to only allowed commands used in this codebase
    allowed_commands = {
        'docker',
        'finch',
        'podman',
        'nerdctl',  # Container tools
        'java',  # Java executable
    }

    # Extract base command name (handle both full paths and command names)
    base_cmd = os.path.basename(cmd[0]) if cmd else ''

    # Remove .exe extension for Windows compatibility
    if base_cmd.endswith('.exe'):
        base_cmd = base_cmd[:-4]

    if base_cmd not in allowed_commands:
        logger.warning(f'Command not allowed: {base_cmd}')
        return None

    try:
        return subprocess.run(
            cmd, check=True, timeout=timeout, capture_output=True, text=True, **kwargs
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug(f'Subprocess failed: {cmd[0]} - {e}')
        return None


def _parse_container_port(ports_output: str) -> Optional[str]:
    """Parse port from container port mapping output.

    Args:
        ports_output: Container port mapping string (e.g., "0.0.0.0:8001->8000/tcp")

    Returns:
        Optional[str]: Host port if found, None otherwise
    """
    if '->' in ports_output:
        return ports_output.split('->')[0].split(':')[-1]
    return None


def _container_exists(container_path: str) -> bool:
    """Check if container exists (running or stopped)."""
    check_cmd = [
        container_path,
        'ps',
        '-a',
        '-q',
        '-f',
        f'name={DynamoDBLocalConfig.CONTAINER_NAME}',
    ]
    result = _run_subprocess_safely(check_cmd)
    return result is not None and result.stdout.strip()


def _container_is_running(container_path: str) -> bool:
    """Check if container is currently running."""
    running_cmd = [container_path, 'ps', '-q', '-f', f'name={DynamoDBLocalConfig.CONTAINER_NAME}']
    result = _run_subprocess_safely(running_cmd)
    return result is not None and result.stdout.strip()


def _restart_container(container_path: str) -> bool:
    """Restart a stopped container."""
    logger.info(f'Restarting stopped container: {DynamoDBLocalConfig.CONTAINER_NAME}')
    restart_cmd = [container_path, 'start', DynamoDBLocalConfig.CONTAINER_NAME]
    result = _run_subprocess_safely(restart_cmd)
    return result is not None


def _get_container_port(container_path: str) -> Optional[str]:
    """Get the host port for the container."""
    ports_cmd = [
        container_path,
        'ps',
        '--format',
        '{{.Ports}}',
        '-f',
        f'name={DynamoDBLocalConfig.CONTAINER_NAME}',
    ]
    result = _run_subprocess_safely(ports_cmd)

    if result and result.stdout.strip():
        return _parse_container_port(result.stdout.strip())
    return None


def _extract_port_from_cmdline(cmdline: list) -> Optional[int]:
    """Extract port number from Java command line arguments.

    Args:
        cmdline: List of command line arguments from process

    Returns:
        Optional[int]: Port number if found and valid, None otherwise
    """
    for i, arg in enumerate(cmdline):
        if arg == '-port' and i + 1 < len(cmdline):
            try:
                return int(cmdline[i + 1])
            except ValueError:
                return None
    return None


def _safe_extract_members(members):
    """Filter tar members to prevent path traversal attacks.

    Args:
        members: Iterable of tar members

    Yields:
        Safe tar members that don't contain path traversal sequences
    """
    for member in members:
        if os.path.isabs(member.name) or '..' in member.name:
            continue
        yield member


def _get_dynamodb_local_paths() -> tuple[str, str, str]:
    """Get paths for DynamoDB Local artifacts."""
    dynamodb_dir = os.path.join(tempfile.gettempdir(), DynamoDBLocalConfig.TEMP_DIR_NAME)
    jar_path = os.path.join(dynamodb_dir, 'DynamoDBLocal.jar')
    lib_path = os.path.join(dynamodb_dir, 'DynamoDBLocal_lib')
    return dynamodb_dir, jar_path, lib_path


def _validate_download_url(url: str) -> None:
    """Validate download URL to prevent security issues.

    Args:
        url: URL to validate

    Raises:
        ValueError: If URL is not safe to use
    """
    # Only allow the exact DynamoDB Local download URL
    if url != DynamoDBLocalConfig.DOWNLOAD_URL:
        raise ValueError(
            f'Only DynamoDB Local download URL is allowed: {DynamoDBLocalConfig.DOWNLOAD_URL}'
        )


def _download_and_extract_jar(dynamodb_dir: str, jar_path: str, lib_path: str) -> None:
    """Download and extract DynamoDB Local JAR."""
    tar_path = os.path.join(dynamodb_dir, DynamoDBLocalConfig.TAR_FILENAME)

    logger.info('Downloading DynamoDB Local...')

    try:
        # Validate URL before download
        _validate_download_url(DynamoDBLocalConfig.DOWNLOAD_URL)

        # Download with timeout
        with urllib.request.urlopen(  # nosec B310
            DynamoDBLocalConfig.DOWNLOAD_URL, timeout=DynamoDBLocalConfig.DOWNLOAD_TIMEOUT
        ) as response:
            # Validate content type
            content_type = response.headers.get('content-type', '')
            if content_type and not content_type.startswith(
                ('application/gzip', 'application/x-gzip', 'application/octet-stream')
            ):
                raise ValueError(f'Unexpected content type: {content_type}')

            with open(tar_path, 'wb') as f:
                f.write(response.read())

        # Validate tar contents before extraction
        with tarfile.open(tar_path, 'r:gz') as tar:
            if 'DynamoDBLocal.jar' not in tar.getnames():
                raise RuntimeError('DynamoDBLocal.jar not found in archive')

            if hasattr(tarfile, 'data_filter'):
                tar.extractall(dynamodb_dir, members=_safe_extract_members(tar), filter='data')  # nosec B202
            else:
                tar.extractall(dynamodb_dir, members=_safe_extract_members(tar))  # nosec B202

        # Clean up tar file
        os.remove(tar_path)

        logger.info(f'Downloaded and extracted DynamoDB Local to {jar_path}')

    except Exception as e:
        if os.path.exists(dynamodb_dir):
            shutil.rmtree(dynamodb_dir)
        raise RuntimeError(f'Failed to download DynamoDB Local: {e}')


def _try_container_setup() -> Optional[str]:
    """Try to setup DynamoDB Local using container tools."""
    container_path = get_container_path()
    if not container_path:
        return None

    try:
        # Check if our container is already running
        existing_endpoint = get_existing_container_dynamodb_local_endpoint(container_path)
        if existing_endpoint:
            return existing_endpoint

        # Find available port and start container
        port = find_available_port(DynamoDBLocalConfig.DEFAULT_PORT)
        return start_container(container_path, port)

    except RuntimeError as e:
        logger.debug(f'Container setup failed: {e}')
        return None


def _try_java_setup() -> Optional[str]:
    """Try to setup DynamoDB Local using Java."""
    java_path = get_java_path()
    if not java_path:
        return None

    try:
        # Check if our Java process is already running
        existing_endpoint = get_existing_java_dynamodb_local_endpoint()
        if existing_endpoint:
            return existing_endpoint

        # Find available port and start Java process
        port = find_available_port(DynamoDBLocalConfig.DEFAULT_PORT)
        return start_java_process(java_path, port)

    except RuntimeError as e:
        logger.debug(f'Java setup failed: {e}')
        return None


def get_container_path() -> Optional[str]:
    """Get Docker-compatible executable path with running daemon.

    Searches for available container tools (Docker, Podman, Finch, nerdctl) and
    returns the first one with a running daemon. Tests daemon connectivity by
    running 'tool ps' command.

    Returns:
        Optional[str]: Path to working container tool executable, or None if no
                      working tool is found.
    """
    errors = []

    for tool in ContainerTools.TOOLS:
        path = shutil.which(tool)
        if path:
            result = _run_subprocess_safely([path, 'ps'])
            if result:
                return path
            else:
                errors.append(f'{tool}: daemon not running or not accessible')

    if errors:
        logger.debug(f'Container tool errors: {"; ".join(errors)}')
    else:
        logger.debug('No container tools found')

    return None


def find_available_port(start_port: int = DynamoDBLocalConfig.DEFAULT_PORT) -> int:
    """Find an available port for DynamoDB Local.

    Args:
        start_port: Preferred port number to try first

    Returns:
        int: Available port number that can be used for binding
    """
    # First try the requested port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('localhost', start_port))
            return start_port
    except OSError:
        # Requested port not available, let kernel assign one
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('localhost', 0))
            _, port = sock.getsockname()
            return port


def get_existing_container_dynamodb_local_endpoint(container_path: str) -> Optional[str]:
    """Check if DynamoDB Local container exists and return its endpoint.

    Args:
        container_path: Path to container tool executable

    Returns:
        Optional[str]: DynamoDB Local endpoint URL if container exists and is
                      accessible, None otherwise.
    """
    try:
        if not _container_exists(container_path):
            return None

        # Ensure container is running
        if not _container_is_running(container_path):
            if not _restart_container(container_path):
                return None

        # Get port mapping
        host_port = _get_container_port(container_path)
        if host_port:
            endpoint = f'http://localhost:{host_port}'
            logger.info(f'DynamoDB Local container available at {endpoint}')
            return endpoint

    except Exception as e:
        logger.debug(f'Error checking for existing container: {e}')

    return None


def start_container(container_path: str, port: int) -> str:
    """Start DynamoDB Local container and verify readiness.

    Args:
        container_path: Path to container tool executable
        port: Host port to map to container's DynamoDB port

    Returns:
        str: DynamoDB Local endpoint URL (http://localhost:port)

    Raises:
        RuntimeError: If container fails to start or become ready within timeout
    """
    cmd = [
        container_path,
        'run',
        '-d',
        '--name',
        DynamoDBLocalConfig.CONTAINER_NAME,
        '-p',
        f'127.0.0.1:{port}:{DynamoDBLocalConfig.DEFAULT_PORT}',
        DynamoDBLocalConfig.DOCKER_IMAGE,
    ]

    logger.info(f'Starting DynamoDB Local container on port {port}')
    result = _run_subprocess_safely(cmd, timeout=30)

    if not result:
        raise RuntimeError('Failed to start Docker container')

    endpoint = f'http://localhost:{port}'
    return check_dynamodb_readiness(endpoint)


def get_java_path() -> Optional[str]:
    """Get Java executable path using cross-platform approach.

    Attempts to locate Java executable by:
    1. Checking JAVA_HOME environment variable and validating executable exists and is runnable
    2. Falling back to searching system PATH for 'java' command

    Returns:
        Optional[str]: Full path to Java executable if found and executable, None otherwise
    """
    # 1. Check JAVA_HOME environment variable
    java_home = os.environ.get('JAVA_HOME')
    if java_home:
        # Determine executable name based on platform
        java_executable = 'java.exe' if sys.platform == 'win32' else 'java'
        java_exe = os.path.join(java_home, 'bin', java_executable)
        if os.path.isfile(java_exe) and os.access(java_exe, os.X_OK):
            return java_exe

    # 2. Fall back to searching PATH
    return shutil.which('java')


def get_existing_java_dynamodb_local_endpoint() -> Optional[str]:
    """Check if DynamoDB Local Java process is already running and return its endpoint.

    Returns:
        Optional[str]: DynamoDB Local endpoint URL (http://localhost:port) if found, None otherwise

    Note:
        Only detects processes started by this tool with the specific system property
    """
    try:
        # Find Java processes with our system property
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'java' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline and any(
                        DynamoDBLocalConfig.JAVA_PROPERTY_NAME in arg for arg in cmdline
                    ):
                        port = _extract_port_from_cmdline(cmdline)
                        if port:
                            endpoint = f'http://localhost:{port}'
                            logger.info(
                                f'Found existing DynamoDB Local Java process at {endpoint}'
                            )
                            return endpoint
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                ValueError,
                IndexError,
            ) as e:
                logger.debug(
                    f'Error processing Java process {proc.info.get("pid", "unknown")}: {e}'
                )
                continue
    except Exception as e:
        logger.debug(f'Error checking for existing Java process: {e}')

    return None


def download_dynamodb_local_jar() -> tuple[str, str]:
    """Download DynamoDB Local JAR and return JAR path and lib path.

    Returns:
        tuple[str, str]: (jar_path, lib_path) where:
            - jar_path: Full path to DynamoDBLocal.jar
            - lib_path: Full path to DynamoDBLocal_lib directory containing native libraries

    Raises:
        RuntimeError: If download fails, extraction fails, or JAR not found after extraction
    """
    dynamodb_dir, jar_path, lib_path = _get_dynamodb_local_paths()
    os.makedirs(dynamodb_dir, exist_ok=True)

    # Check if both JAR and lib directory exist
    if os.path.exists(jar_path) and os.path.exists(lib_path):
        return jar_path, lib_path

    _download_and_extract_jar(dynamodb_dir, jar_path, lib_path)
    return jar_path, lib_path


def start_java_process(java_path: str, port: int) -> str:
    """Start DynamoDB Local using Java and return endpoint URL.

    Args:
        java_path: Full path to Java executable
        port: Port number for DynamoDB Local to listen on

    Returns:
        str: DynamoDB Local endpoint URL (http://localhost:port)

    Raises:
        RuntimeError: If Java process fails to start, JAR download fails, or service
                     doesn't become ready within timeout period
    """
    jar_path, lib_path = download_dynamodb_local_jar()

    cmd = [
        java_path,
        f'-D{DynamoDBLocalConfig.JAVA_PROPERTY_NAME}=true',
        f'-Djava.library.path={lib_path}',
        '-jar',
        jar_path,
        '-bindAddress',
        '127.0.0.1',
        '-port',
        str(port),
        '-inMemory',
    ]

    try:
        # Validate command before execution
        base_cmd = os.path.basename(java_path)
        if base_cmd.endswith('.exe'):
            base_cmd = base_cmd[:-4]
        if base_cmd != 'java':
            raise RuntimeError(f'Invalid Java executable: {base_cmd}')

        logger.info(f'Starting DynamoDB Local with Java on port {port}')

        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        time.sleep(DynamoDBLocalConfig.SLEEP_INTERVAL)
        if process.poll() is not None:
            _, stderr = process.communicate()
            raise RuntimeError(f'Java process failed to start: {stderr.decode()}')

        endpoint = f'http://localhost:{port}'
        return check_dynamodb_readiness(endpoint)

    except Exception as e:
        raise RuntimeError(f'Failed to start DynamoDB Local with Java: {e}')


def check_dynamodb_readiness(endpoint: str) -> str:
    """Check if DynamoDB Local is ready to accept connections and return endpoint.

    Args:
        endpoint: DynamoDB Local endpoint URL (e.g., 'http://localhost:8000')

    Returns:
        str: The same endpoint URL if service is ready and responding

    Raises:
        RuntimeError: If DynamoDB Local doesn't become ready within timeout period
    """
    client = _create_dynamodb_client(endpoint)

    for i in range(DynamoDBLocalConfig.MAX_ATTEMPTS):
        try:
            client.list_tables()
            logger.info(f'DynamoDB Local ready at {endpoint}')
            return endpoint
        except (ClientError, EndpointConnectionError) as e:
            if i == DynamoDBLocalConfig.MAX_ATTEMPTS - 1:
                total_timeout = (
                    DynamoDBLocalConfig.MAX_ATTEMPTS * DynamoDBLocalConfig.SLEEP_INTERVAL
                )
                raise RuntimeError(
                    f'DynamoDB Local failed to start at {endpoint} after {total_timeout} seconds. '
                    f'Last error: {e}'
                )
            logger.debug(
                f'DynamoDB Local not ready, retrying in {DynamoDBLocalConfig.SLEEP_INTERVAL}s (attempt {i + 1}/{DynamoDBLocalConfig.MAX_ATTEMPTS})'
            )
            time.sleep(DynamoDBLocalConfig.SLEEP_INTERVAL)

    # This should never be reached due to the exception in the loop, but added for type safety
    raise RuntimeError(f'DynamoDB Local failed to start at {endpoint}')


def setup_dynamodb_local() -> str:
    """Setup DynamoDB Local environment.

    Returns:
        str: DynamoDB Local endpoint URL

    Raises:
        RuntimeError: If neither Docker nor Java is available or setup fails
    """
    # Try container setup first
    endpoint = _try_container_setup()
    if endpoint:
        return endpoint

    # Fallback to Java
    endpoint = _try_java_setup()
    if endpoint:
        return endpoint

    raise RuntimeError(
        'No working container tool or Java found. Please install and start a container tool (Docker, Finch, Podman, or nerdctl) or install Java JRE version 17.x or newer and set JAVA_HOME or system PATH to run DynamoDB Local for data model validation.'
    )


def create_validation_resources(
    resources: Dict[str, Any], endpoint_url: Optional[str] = None
) -> Dict[str, Any]:
    """Create DynamoDB resources for data model validation.

    Args:
        resources: Valid dictionary containing tables and items
        endpoint_url: DynamoDB endpoint URL

    Returns:
        Dictionary with response from both table creation and item insertion
    """
    dynamodb_client = _create_dynamodb_client(endpoint_url)

    logger.info('Cleaning up existing tables in DynamoDB local for Model Validation')
    cleanup_validation_resources(dynamodb_client)

    tables = resources.get('tables', [])
    items = resources.get('items', {})

    # Validate data types
    if not isinstance(tables, list):
        tables = []
    if not isinstance(items, dict):
        items = {}

    table_creation_response = create_tables(dynamodb_client, tables)
    item_insertion_response = insert_items(dynamodb_client, items)

    return {'tables': table_creation_response, 'items': item_insertion_response}


def cleanup_validation_resources(dynamodb_client) -> Dict[str, Any]:
    """Clean up all existing tables in DynamoDB Local from previous DynamoDB data model validation.

    This function removes all tables that were created during previous validation runs,
    ensuring a clean state for new data model validation operations.

    Args:
        dynamodb_client: Valid boto3 DynamoDB client configured for DynamoDB Local

    Returns:
        Dictionary with cleanup response for each table, containing status and messages.
    """
    # SAFETY CHECK: Ensure we're only deleting from localhost
    endpoint_url = dynamodb_client.meta.endpoint_url
    if endpoint_url:
        parsed = urlparse(endpoint_url)
        hostname = parsed.hostname
        if hostname not in ('localhost', '127.0.0.1'):
            raise ValueError(
                f'SAFETY VIOLATION: Table deletion must only run on localhost. '
                f'Got endpoint: {endpoint_url}. This prevents accidental production table deletion.'
            )

    cleanup_response = {}

    table_names = list_tables(dynamodb_client)

    for table_name in table_names:
        try:
            dynamodb_client.delete_table(TableName=table_name)
            cleanup_response[table_name] = {
                'status': 'deleted',
                'message': f'Table {table_name} deleted successfully',
            }
        except dynamodb_client.exceptions.ResourceNotFoundException:
            cleanup_response[table_name] = {
                'status': 'not_found',
                'message': f'Table {table_name} not found',
            }
        except Exception as e:
            cleanup_response[table_name] = {'status': 'error', 'error': str(e)}

    return cleanup_response


def list_tables(dynamodb_client) -> list:
    """List all DynamoDB tables in the local environment for data model validation.

    Retrieves all table names from DynamoDB Local to support cleanup and validation operations.

    Args:
        dynamodb_client: Valid boto3 DynamoDB client configured for DynamoDB Local

    Returns:
        List of table names, or empty list if the operation fails.
    """
    try:
        response = dynamodb_client.list_tables()
        return response['TableNames']
    except Exception:
        return []


def create_tables(dynamodb_client, tables: list) -> Dict[str, Any]:
    """Create DynamoDB tables.

    Args:
        dynamodb_client: Valid boto3 DynamoDB client
        tables: Array of table configurations

    Returns:
        Dictionary with table creation response for each table.
    """
    table_creation_response = {}

    for table_config in tables:
        if not isinstance(table_config, dict) or 'TableName' not in table_config:
            continue
        table_name = table_config['TableName']

        try:
            response = dynamodb_client.create_table(**table_config)
            table_creation_response[table_name] = {
                'status': 'success',
                'table_arn': response['TableDescription']['TableArn'],
            }
        except dynamodb_client.exceptions.ResourceInUseException:
            table_creation_response[table_name] = {
                'status': 'exists',
                'message': f'Table {table_name} already exists',
            }
        except Exception as e:
            table_creation_response[table_name] = {'status': 'error', 'error': str(e)}

    return table_creation_response


def insert_items(dynamodb_client, items: dict) -> Dict[str, Any]:
    """Insert items into DynamoDB tables using batch_write_item.

    Args:
        dynamodb_client: Valid boto3 DynamoDB client
        items: Dictionary of table names to item lists

    Returns:
        Dictionary with insertion response for each table.
    """
    item_insertion_response = {}

    for table_name, table_items in items.items():
        if not isinstance(table_items, list):
            continue

        total_items = len(table_items)
        processed_items = 0

        try:
            # Process items in batches
            for i in range(0, total_items, DynamoDBLocalConfig.BATCH_SIZE):
                batch_items = table_items[i : i + DynamoDBLocalConfig.BATCH_SIZE]
                response = dynamodb_client.batch_write_item(RequestItems={table_name: batch_items})
                processed_items += len(batch_items) - len(
                    response.get('UnprocessedItems', {}).get(table_name, [])
                )

            item_insertion_response[table_name] = {
                'status': 'success',
                'items_processed': processed_items,
            }
        except Exception as e:
            item_insertion_response[table_name] = {'status': 'error', 'error': str(e)}

    return item_insertion_response


def get_validation_result_transform_prompt() -> str:
    """Provides transformation prompt for converting DynamoDB access pattern validation result to markdown format.

    This tool returns instructions for transforming dynamodb_model_validation.json (generated by execute_access_patterns)
    into a comprehensive, readable markdown report. The transformation includes:

    - Summary statistics of validation results
    - Detailed breakdown of each access pattern test
    - Success/failure indicators with clear formatting
    - Professional markdown structure with proper code blocks
    - Error details and troubleshooting information

    Input: Reads dynamodb_model_validation.json from current working directory
    Output: Creates dynamodb_model_validation.md and displays the formatted results

    Returns: Complete transformation prompt for converting JSON validation results to markdown
    """
    prompt_file = Path(__file__).parent / 'prompts' / 'transform_model_validation_result.md'
    return prompt_file.read_text(encoding='utf-8')
