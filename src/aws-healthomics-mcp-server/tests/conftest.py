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

"""Shared test fixtures and configuration."""

import os
import pytest
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_context():
    """Create a mock MCP context for testing."""
    context = AsyncMock(spec=Context)
    return context


@pytest.fixture
def mock_aws_session():
    """Create a mock AWS session."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_omics_client():
    """Create a mock HealthOmics client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_logs_client():
    """Create a mock CloudWatch Logs client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_boto_client():
    """Create a mock boto3 client for testing."""
    client = MagicMock()
    return client


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing.

    In addition to the server's own configuration defaults, this fixture installs
    a hard safety net that guarantees no test can ever resolve or use real AWS
    credentials or reach a real AWS endpoint:

    - Dummy static credentials (``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` /
      ``AWS_SESSION_TOKEN``) are exported. The environment credential provider has
      the highest precedence in botocore's default chain, so any un-stubbed
      ``boto3`` client resolves these placeholders instead of invoking a shared
      credentials file, an SSO/``credential_process`` (e.g. ``ada credentials
      print``), or EC2/ECS instance metadata.
    - ``AWS_CONFIG_FILE`` and ``AWS_SHARED_CREDENTIALS_FILE`` are redirected to
      ``os.devnull`` so a developer's ``~/.aws/config`` (including any
      ``credential_process``) is never read during tests.
    - ``AWS_EC2_METADATA_DISABLED`` is set so botocore never attempts an IMDS
      lookup if the placeholder credentials are somehow bypassed.

    This makes the test suite deterministic regardless of the machine's ambient
    AWS configuration. Tests MUST still mock the AWS clients/sessions they use
    (see ``.kiro/steering/tech.md``); these placeholders exist only to keep an
    accidental un-stubbed call from reaching real AWS or a real credential
    process.
    """
    # Set default test environment variables. The placeholder credential values
    # are intentionally non-empty and obviously fake.
    test_env = {
        'AWS_REGION': 'us-east-1',
        'AWS_DEFAULT_REGION': 'us-east-1',
        'FASTMCP_LOG_LEVEL': 'ERROR',
        'HEALTHOMICS_DEFAULT_MAX_RESULTS': '10',
        'AWS_ACCESS_KEY_ID': 'testing',  # pragma: allowlist secret
        'AWS_SECRET_ACCESS_KEY': 'testing',  # pragma: allowlist secret
        'AWS_SESSION_TOKEN': 'testing',  # pragma: allowlist secret
        'AWS_SECURITY_TOKEN': 'testing',  # pragma: allowlist secret
        'AWS_CONFIG_FILE': os.devnull,
        'AWS_SHARED_CREDENTIALS_FILE': os.devnull,
        'AWS_EC2_METADATA_DISABLED': 'true',
    }

    # Ambient profile selection is removed entirely (not blanked) so no named
    # profile -- which could carry a credential_process -- is consulted. An empty
    # AWS_PROFILE value is itself treated as a (missing) profile name and would
    # raise ProfileNotFound, so these must be unset rather than set to ''.
    profile_vars = ('AWS_PROFILE', 'AWS_DEFAULT_PROFILE')

    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    for key in profile_vars:
        original_env[key] = os.environ.get(key)
        os.environ.pop(key, None)

    yield

    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def sample_workflow_response():
    """Sample workflow response for testing."""
    return {
        'id': 'workflow-12345',
        'name': 'test-workflow',
        'description': 'A test workflow',
        'status': 'ACTIVE',
        'type': 'PRIVATE',
        'engine': 'WDL',
        'creationTime': '2023-01-01T00:00:00Z',
    }


@pytest.fixture
def sample_run_response():
    """Sample run response for testing."""
    return {
        'id': 'run-12345',
        'name': 'test-run',
        'workflowId': 'workflow-12345',
        'status': 'COMPLETED',
        'roleArn': 'arn:aws:iam::123456789012:role/HealthOmicsRole',
        'outputUri': 's3://test-bucket/outputs/',
        'creationTime': '2023-01-01T00:00:00Z',
        'startTime': '2023-01-01T00:01:00Z',
        'stopTime': '2023-01-01T01:00:00Z',
    }


@pytest.fixture
def sample_task_response():
    """Sample task response for testing."""
    return {
        'taskId': 'task-12345',
        'name': 'preprocessing',
        'status': 'COMPLETED',
        'cpus': 2,
        'memory': 4096,
        'creationTime': '2023-01-01T00:01:00Z',
        'startTime': '2023-01-01T00:02:00Z',
        'stopTime': '2023-01-01T00:30:00Z',
    }


@pytest.fixture
def sample_log_events():
    """Sample CloudWatch log events for testing."""
    return [
        {
            'timestamp': 1640995200000,  # 2022-01-01 00:00:00 UTC
            'message': 'Starting workflow execution',
        },
        {
            'timestamp': 1640995260000,  # 2022-01-01 00:01:00 UTC
            'message': 'Processing input files',
        },
        {
            'timestamp': 1640995320000,  # 2022-01-01 00:02:00 UTC
            'message': 'Workflow execution completed successfully',
        },
    ]


@pytest.fixture
def sample_failed_log_events():
    """Sample CloudWatch log events for failed runs."""
    return [
        {
            'timestamp': 1640995200000,
            'message': 'Starting workflow execution',
        },
        {
            'timestamp': 1640995260000,
            'message': 'Error: insufficient memory for task',
        },
        {
            'timestamp': 1640995320000,
            'message': 'Task failed with exit code 1',
        },
    ]
