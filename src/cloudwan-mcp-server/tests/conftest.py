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


# pytest fixtures for AWS client mocking
import os
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from .mocking.aws import (
    AWSErrorCatalog,
    AWSServiceMocker,
    create_service_mocker,
)
from .security.credential_manager import credential_manager, get_secure_test_credentials


@pytest.fixture(scope="function", name="mock_get_aws_client_fixture")
def aws_client_mocker():
    """Mock the get_aws_client function with hierarchical service mocking.

    This fixture provides intelligent AWS service client mocking with:
    - Service-specific response configurations
    - Regional behavior simulation
    - Comprehensive error scenario coverage
    - Client cache lifecycle management

    Usage:
        def test_function(mock_get_aws_client_fixture):
            # Fixture automatically configures realistic AWS responses
            result = await list_core_networks("us-east-1")
    """
    clients = {}

    def _mock_client(service: str, region: str | None = None) -> Mock:
        """Create or retrieve cached service client mock."""
        region = region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        key = (service, region)

        if key not in clients:
            # Use hierarchical mocker for realistic service behavior
            service_mocker = AWSServiceMocker(service, region)
            clients[key] = service_mocker.client

        return clients[key]

    with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=_mock_client) as mock:
        yield mock

    # Clear LRU cache after tests to prevent state leakage
    try:
        from awslabs.cloudwan_mcp_server.server import _create_client

        _create_client.cache_clear()
    except (ImportError, AttributeError):
        # Handle cases where cache doesn't exist or isn't implemented
        pass


@pytest.fixture(scope="function")
def aws_error_catalog() -> AWSErrorCatalog:
    """Centralized AWS error catalog for comprehensive error scenario testing.

    Provides access to standardized AWS error responses including:
    - Common AWS errors (AccessDenied, ThrottlingException, etc.)
    - Service-specific errors (CoreNetworkNotFound, etc.)
    - Realistic error response structures with proper HTTP status codes

    Usage:
        def test_error_handling(aws_error_catalog):
            error = aws_error_catalog.get_error('access_denied', 'ListCoreNetworks')
            mock_client.list_core_networks.side_effect = error
    """
    return AWSErrorCatalog


@pytest.fixture(scope="function")
def mock_boto_error() -> ClientError:
    """Mock boto3 ClientError for comprehensive error handling tests.

    Provides a realistic ClientError instance that matches AWS API error
    response structure, including proper error codes, messages, and metadata.

    Usage:
        def test_error_handling(mock_boto_error):
            mock_client.operation.side_effect = mock_boto_error
            # Test error handling logic
    """
    error_response = {
        "Error": {"Code": "ResourceNotFoundException", "Message": "Test error message for resource not found"},
        "ResponseMetadata": {"RequestId": "test-request-id-123", "HTTPStatusCode": 404},
    }

    return ClientError(error_response, "TestOperation")


@pytest.fixture(scope="function")
def aws_service_mocker():
    """Factory fixture for creating AWS service mockers on demand.

    Provides a flexible way to create service-specific mockers with
    custom configurations during test execution.

    Usage:
        def test_custom_service(aws_service_mocker):
            nm_mocker = aws_service_mocker('networkmanager', 'us-west-2')
            nm_mocker.configure_error('AccessDenied', operation='list_core_networks')
    """
    return create_service_mocker


@pytest.fixture(scope="function")
def regional_aws_client():
    """Regional AWS client mock with environment-aware region selection.

    Automatically detects region from environment variables or test markers,
    enabling region-specific testing scenarios.

    Usage:
        @pytest.mark.aws_region("eu-west-1")
        def test_regional_behavior(regional_aws_client):
            # Client automatically configured for eu-west-1
            pass
    """

    def _get_regional_client(request):
        # Check for region marker
        region_marker = request.node.get_closest_marker("aws_region")
        if region_marker:
            region = region_marker.args[0]
        else:
            region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

        return create_service_mocker("networkmanager", region)

    return _get_regional_client


@pytest.fixture(scope="function", autouse=True)
def secure_aws_credentials(request):
    """Automatic secure credential setup for all tests.

    Provides enterprise-grade credential security with:
    - UUID-based credential generation
    - Automatic expiration (15 minutes)
    - Memory cleanup on test completion
    - SOC 2 audit trail logging
    """
    test_name = request.node.name
    credentials = get_secure_test_credentials(test_context=f"pytest-{test_name}")

    # Set secure environment variables
    original_env = {}
    env_vars = credentials.to_env_dict()

    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield credentials

    # Cleanup: restore original environment and cleanup credentials
    for key in env_vars.keys():
        if original_env[key] is not None:
            os.environ[key] = original_env[key]
        else:
            os.environ.pop(key, None)

    credentials.cleanup()


@pytest.fixture(scope="session", autouse=True)
def credential_cleanup_manager():
    """Session-level credential cleanup for security compliance."""
    yield

    # Emergency cleanup on test session end
    credential_manager.emergency_cleanup()

    # Log audit trail for compliance
    audit_trail = credential_manager.get_audit_trail()
    if audit_trail:
        print(f"\n[SECURITY] Processed {len(audit_trail)} credential lifecycle events")


@pytest.fixture(scope="session")
def mock_aws_context():
    """Provide AWS context for integration tests."""
    with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
        yield


# Legacy fixture for backward compatibility
@pytest.fixture(scope="function", name="mock_get_aws_client")
def aws_client_mocker():
    """Mock AWS client with hierarchical service mocking."""
    clients = {}

    def _mock_client(service: str, region: str | None = None) -> Mock:
        region = region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        key = (service, region)

        if key not in clients:
            service_mocker = AWSServiceMocker(service, region)
            clients[key] = service_mocker.client

        return clients[key]

    with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=_mock_client) as mock:
        yield mock

    # Clear LRU cache after tests
    try:
        from awslabs.cloudwan_mcp_server.server import _create_client

        _create_client.cache_clear()
    except (ImportError, AttributeError):
        pass
