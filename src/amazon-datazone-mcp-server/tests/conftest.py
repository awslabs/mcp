"""Test configuration and fixtures for Amazon DataZone MCP Server tests."""

import asyncio
import os
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from botocore.exceptions import ClientError
from mcp.server.fastmcp import FastMCP
from typing import Callable, Optional


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_datazone_client():
    """Mock Amazon DataZone client with pre-configured responses."""
    mock_client = Mock()

    # Domain responses
    mock_client.get_domain.return_value = {
        "id": "dzd_test123",
        "name": "Test Domain",
        "description": "Test domain description",
        "status": "AVAILABLE",
        "arn": os.getenv("ARN"),
        "portalUrl": "https://dzd_test123.datazone.aws.amazon.com",
        "domainVersion": "V2",
        "rootDomainUnitId": "root_unit_123",
    }

    mock_client.create_domain.return_value = {
        "id": "dzd_new123",
        "name": "New Test Domain",
        "description": "New test domain description",
        "status": "CREATING",
        "arn": os.getenv("ARN"),
        "portalUrl": "https://dzd_new123.datazone.aws.amazon.com",
        "domainVersion": "V2",
        "rootDomainUnitId": "root_unit_new123",
    }

    # Project responses
    mock_client.get_project.return_value = {
        "id": "prj_test123",
        "name": "Test Project",
        "description": "Test project description",
        "domainId": "dzd_test123",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "createdBy": "test-user",
    }

    mock_client.create_project.return_value = {
        "id": "prj_new123",
        "name": "New Test Project",
        "description": "New test project description",
        "domainId": "dzd_test123",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "createdBy": "test-user",
    }

    # Asset responses
    mock_client.get_asset.return_value = {
        "id": "asset_test123",
        "name": "Test Asset",
        "description": "Test asset description",
        "domainId": "dzd_test123",
        "projectId": "prj_test123",
        "status": "ACTIVE",
        "typeIdentifier": "amazon.datazone.S3Asset",
        "typeRevision": "1",
    }

    mock_client.create_asset.return_value = {
        "id": "asset_new123",
        "name": "New Test Asset",
        "description": "New test asset description",
        "domainId": "dzd_test123",
        "projectId": "prj_test123",
        "status": "ACTIVE",
        "typeIdentifier": "amazon.datazone.S3Asset",
        "typeRevision": "1",
    }

    # Environment responses
    mock_client.list_environments.return_value = {
        "items": [
            {
                "id": "env_test123",
                "name": "Test Environment",
                "description": "Test environment description",
                "domainId": "dzd_test123",
                "projectId": "prj_test123",
                "status": "ACTIVE",
            }
        ]
    }

    # Glossary responses
    mock_client.create_glossary.return_value = {
        "id": "glossary_new123",
        "name": "New Test Glossary",
        "description": "New test glossary description",
        "domainId": "dzd_test123",
        "status": "ENABLED",
    }

    return mock_client


@pytest.fixture
def mcp_server_with_tools(mock_datazone_client):
    """Create MCP server instance with all tools registered and mocked client."""
    mcp = FastMCP("test-datazone")
    import boto3

    # Start a persistent patch that will last for the entire test
    # Patch boto3.client to return our mock for datazone
    original_boto3_client: Callable = boto3.client

    def mock_boto3_client(service_name, **kwargs):
        if service_name == "datazone":
            return mock_datazone_client
        # For other services, use the original client function
        return original_boto3_client(service_name, **kwargs)

    original_boto3_client = boto3.client
    patcher = patch("boto3.client", side_effect=mock_boto3_client)
    patcher.start()

    try:
        # Now import and reload the modules to get the mocked client
        import importlib

        from awslabs.datazone_mcp_server.tools import common

        importlib.reload(common)  # This will recreate datazone_client with our mock

        from awslabs.datazone_mcp_server.tools import (
            data_management,
            domain_management,
            environment,
            glossary,
            project_management,
        )

        # Reload the tool modules to pick up the new common module
        importlib.reload(domain_management)
        importlib.reload(project_management)
        importlib.reload(data_management)
        importlib.reload(glossary)
        importlib.reload(environment)

        domain_management.register_tools(mcp)
        project_management.register_tools(mcp)
        data_management.register_tools(mcp)
        glossary.register_tools(mcp)
        environment.register_tools(mcp)

        # Store the mock client and patcher on the server for test access
        setattr(mcp, "_mock_client", mock_datazone_client)
        setattr(mcp, "_patcher", patcher)

        yield mcp

    finally:
        # Stop the patcher when the test is done
        patcher.stop()


@pytest.fixture
def client_error_helper():
    """Helper function to create ClientError exceptions for testing."""

    def create_client_error(error_code: str, message: Optional[str] = None):
        if message is None:
            message = f"An error occurred ({error_code})"

        error_response = {"Error": {"Code": error_code, "Message": message}}
        return ClientError(error_response, "TestOperation")

    return create_client_error


@pytest.fixture
def sample_domain_data():
    """Sample domain data for testing."""
    return {
        "name": "Test Domain",
        "description": "Test domain description",
        "domain_execution_role": os.getenv("DOMAIN_EXECUTION_ROLE"),
        "service_role": os.getenv("SERVICE_ROLE"),
        "domain_version": "V2",
    }


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "name": "Test Project",
        "description": "Test project description",
        "domain_identifier": "dzd_test123",
        "glossary_terms": ["term1", "term2"],
    }


@pytest.fixture
def sample_asset_data():
    """Sample asset data for testing."""
    return {
        "name": "Test Asset",
        "description": "Test asset description",
        "domain_identifier": "dzd_test123",
        "owning_project_identifier": "prj_test123",
        "type_identifier": "amazon.datazone.S3Asset",
        "type_revision": "1",
    }


@pytest.fixture
def sample_glossary_data():
    """Sample glossary data for testing."""
    return {
        "name": "Test Glossary",
        "description": "Test glossary description",
        "domain_identifier": "dzd_test123",
        "owning_project_identifier": "prj_test123",
    }


@pytest.fixture
def sample_environment_data():
    """Sample environment data for testing."""
    return {
        "domain_id": "dzd_test123",
        "project_id": "prj_test123",
        "environment_id": "env_test123",
    }


class TestDataHelper:
    """Helper class for generating consistent test data."""

    @staticmethod
    def get_domain_id() -> str:
        """get domain id."""
        return "dzd_test123"

    @staticmethod
    def get_project_id() -> str:
        """get project id."""
        return "prj_test123"

    @staticmethod
    def get_asset_id() -> str:
        """get asset id."""
        return "asset_test123"

    @staticmethod
    def get_glossary_id() -> str:
        """get glossary id."""
        return "glossary_test123"

    @staticmethod
    def get_environment_id() -> str:
        """get environment id."""
        return "env_test123"

    @staticmethod
    def get_project_response(project_id: str) -> Dict[str, Any]:
        """Generate a mock project response."""
        return {
            "id": project_id,
            "name": "Test Project",
            "description": "Test project description",
            "domainId": "dzd_test123",
            "status": "ACTIVE",
            "createdAt": "2024-01-01T00:00:00Z",
            "createdBy": "test-user",
        }

    @staticmethod
    def get_asset_response(asset_id: str) -> Dict[str, Any]:
        """Generate a mock asset response."""
        return {
            "id": asset_id,
            "name": "Test Asset",
            "description": "Test asset description",
            "domainId": "dzd_test123",
            "projectId": "prj_test123",
            "status": "ACTIVE",
            "typeIdentifier": "amazon.datazone.S3Asset",
            "typeRevision": "1",
        }


@pytest.fixture
def test_data_helper():
    """Test data helper instance."""
    return TestDataHelper()


@pytest.fixture
def aws_error_scenarios():
    """Common AWS error scenarios for testing."""
    return {
        "access_denied": {
            "error_code": "AccessDeniedException",
            "message": "User is not authorized to perform this action",
        },
        "resource_not_found": {
            "error_code": "ResourceNotFoundException",
            "message": "The requested resource was not found",
        },
        "conflict": {
            "error_code": "ConflictException",
            "message": "The request conflicts with the current state",
        },
        "validation_error": {
            "error_code": "ValidationException",
            "message": "The input fails to satisfy the constraints",
        },
        "throttling": {"error_code": "ThrottlingException", "message": "The request was throttled"},
        "internal_error": {
            "error_code": "InternalServerException",
            "message": "An internal server error occurred",
        },
    }


# Auto-mock AWS credentials to prevent real API calls during testing
@pytest.fixture(autouse=True)
def mock_aws_credentials():
    """Automatically mock AWS credentials for all tests."""
    with patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "testing", #pragma: allowlist secret
            "AWS_SECRET_ACCESS_KEY": "testing", #pragma: allowlist secret
            "AWS_SECURITY_TOKEN": "testing", #pragma: allowlist secret
            "AWS_SESSION_TOKEN": "testing", #pragma: allowlist secret
            "AWS_DEFAULT_REGION": "us-east-1", #pragma: allowlist secret
        },
    ):
        yield


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require AWS credentials)"
    )
    config.addinivalue_line("markers", "slow: marks tests as slow running")


def pytest_collection_modifyitems(config, items):
    """Automatically skip integration tests if SKIP_AWS_TESTS is set."""
    if os.getenv("SKIP_AWS_TESTS", "false").lower() == "true":
        skip_integration = pytest.mark.skip(reason="SKIP_AWS_TESTS environment variable is set")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


# Helper function to get tool from MCP server
def get_tool_function(mcp_server: FastMCP, tool_name: str):
    """Extract a tool function from the MCP server by name."""
    # Access the tool through the tool manager
    if hasattr(mcp_server, "_tool_manager"):
        tool_manager = mcp_server._tool_manager
        try:
            tool = tool_manager.get_tool(tool_name)
            if tool and hasattr(tool, "fn"):
                return tool.fn
        except Exception:
            pass

    raise ValueError(f"Tool '{tool_name}' not found in MCP server")


@pytest.fixture
def tool_extractor():
    """Fixture that provides the tool extraction helper function."""
    return get_tool_function


@pytest.fixture
def mock_fastmcp():
    """Mock FastMCP instance for testing tool registration."""
    mock_mcp = Mock()
    mock_mcp.tool = Mock()
    return mock_mcp


# Create an alias for compatibility
mock_client_error = client_error_helper
