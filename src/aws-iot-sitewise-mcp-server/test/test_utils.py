import os
import sys
from unittest.mock import patch

import pytest

from awslabs.aws_iot_sitewise_mcp_server.utils import (
    get_package_version,
    validate_amazon_login,
)

# Add paths to make imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


@patch("importlib.metadata.version")
def test_get_package_version_success(mock_version):
    """Test successful package version retrieval."""
    # Setup the mock to return a fixed version
    mock_version.return_value = "1.0.0"

    # Call the function
    version = get_package_version()

    # Assert the result and mock calls
    assert version == "1.0.0"
    mock_version.assert_called_once_with("awslabs.aws_iot_sitewise_mcp_server")


@patch("importlib.metadata.version")
def test_get_package_version_failure(mock_version):
    """Test package version retrieval failure."""
    # Setup the mock to raise an exception
    mock_version.side_effect = Exception("Package not found")

    # Call the function - it should return a default version instead of raising
    version = get_package_version()

    # Assert we got the default version
    assert version == "0.1.0"


# validate_amazon_login tests
@pytest.mark.parametrize(
    "login",
    [
        "abc",
        "abcdefgh",
        "abcde",
    ],
)
def test_valid_login(login):
    """Test that valid logins pass validation."""
    # This should not raise any exceptions
    validate_amazon_login(login)


@pytest.mark.parametrize(
    "login",
    [
        "looooooooong",
        "hello!",
        "s",
        "aaa1",
        "UPPER",
        " ",
    ],
)
def test_invalid_login_raises_error(login):
    """Test that invalid logins raise ValueError, using parameterized tests."""
    with pytest.raises(ValueError, match=r"Invalid login syntax.*"):
        validate_amazon_login(login)
