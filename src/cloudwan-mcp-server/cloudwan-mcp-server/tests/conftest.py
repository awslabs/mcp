"""Pytest configuration and fixtures for CloudWAN MCP server tests."""

import os
import sys
from pathlib import Path

import pytest

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up test environment variables
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_PROFILE", "test-profile")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically set up test environment for all tests."""
    # Ensure clean environment for each test
    original_env = dict(os.environ)
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    return {
        "aws_access_key_id": "test-key-id",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
        "region_name": "us-east-1",
    }