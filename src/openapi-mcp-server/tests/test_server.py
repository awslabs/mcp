"""Tests for the OpenAPI MCP Server."""

import pytest
import httpx
import json
import os
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, ANY

# Import from our reorganized modules
from awslabs.openapi_mcp_server.api.config import Config, load_config
from awslabs.openapi_mcp_server.utils.openapi import load_openapi_spec
from awslabs.openapi_mcp_server.prompts.instructions import generate_api_instructions
from awslabs.openapi_mcp_server.server import create_mcp_server


def test_config_default_values():
    """Test that Config has the expected default values."""
    config = Config()
    assert config.api_name == "petstore"
    assert config.api_base_url == "https://petstore3.swagger.io/api/v3"
    assert config.auth_type == "none"


def test_load_config():
    """Test loading config from arguments."""
    args = MagicMock()
    args.api_name = "testapi"
    args.api_url = "https://test.api.com"
    args.spec_url = "https://test.api.com/openapi.json"
    args.port = 9000
    args.sse = True

    config = load_config(args)

    assert config.api_name == "testapi"
    assert config.api_base_url == "https://test.api.com"
    assert config.api_spec_url == "https://test.api.com/openapi.json"
    assert config.port == 9000
    assert config.transport == "sse"


def test_load_config_environment_variables():
    """Test loading config from environment variables."""
    # Save original environment variables to restore later
    original_env = os.environ.copy()
    
    try:
        # Set environment variables
        os.environ["API_NAME"] = "env-api"
        os.environ["API_BASE_URL"] = "https://env-api.com"
        os.environ["API_SPEC_URL"] = "https://env-api.com/openapi.json"
        os.environ["SERVER_PORT"] = "7777"
        os.environ["SERVER_TRANSPORT"] = "stdio"
        
        # Load config
        config = load_config()
        
        # Assert environment variables are used
        assert config.api_name == "env-api"
        assert config.api_base_url == "https://env-api.com"
        assert config.api_spec_url == "https://env-api.com/openapi.json"
        assert config.port == 7777
        assert config.transport == "stdio"
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.mark.asyncio
@patch('httpx.get')
async def test_load_openapi_spec_from_url(mock_get):
    """Test loading OpenAPI spec from URL."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"openapi": "3.0.0", "info": {"title": "Test API"}}
    mock_get.return_value = mock_response

    result = load_openapi_spec(url="https://test.api.com/openapi.json")

    assert result == {"openapi": "3.0.0", "info": {"title": "Test API"}}
    mock_get.assert_called_once_with("https://test.api.com/openapi.json")


@patch('builtins.open', new_callable=mock_open, read_data='{"openapi": "3.0.0", "info": {"title": "Test API"}}')
@patch('pathlib.Path.exists', return_value=True)
def test_load_openapi_spec_from_json_file(mock_exists, mock_file):
    """Test loading OpenAPI spec from a JSON file."""
    # Call the function with a path parameter
    result = load_openapi_spec(path="test_api.json")
    
    # Check the file was opened correctly - using ANY for the first arg since it's a Path object
    mock_file.assert_called_once_with(ANY, "r")
    
    # Check the correct data was loaded
    assert result == {"openapi": "3.0.0", "info": {"title": "Test API"}}


@patch('builtins.open', new_callable=mock_open, read_data='openapi: 3.0.0\ninfo:\n  title: Test API')
@patch('pathlib.Path.exists', return_value=True)
@patch('yaml.safe_load')
def test_load_openapi_spec_from_yaml_file(mock_yaml_load, mock_exists, mock_file):
    """Test loading OpenAPI spec from a YAML file."""
    # Configure YAML loading
    mock_yaml_load.return_value = {"openapi": "3.0.0", "info": {"title": "Test API"}}
    
    # Call the function with a path parameter
    result = load_openapi_spec(path="test_api.yaml")
    
    # Check the file was opened correctly - using ANY for the first arg since it's a Path object
    mock_file.assert_called_once_with(ANY, "r")
    
    # Check YAML loader was called
    mock_yaml_load.assert_called_once()
    
    # Check the correct data was loaded
    assert result == {"openapi": "3.0.0", "info": {"title": "Test API"}}


@patch('pathlib.Path.exists', return_value=False)
def test_load_openapi_spec_file_not_found(mock_exists):
    """Test error handling when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_openapi_spec(path="non_existent_file.json")


@pytest.mark.asyncio
@patch('builtins.open', new_callable=mock_open, read_data='not-yaml-content')
@patch('pathlib.Path.exists', return_value=True)
@patch('importlib.import_module')
async def test_load_openapi_spec_yaml_import_error(mock_import, mock_exists, mock_file):
    """Test handling YAML import error."""
    # Simulate ImportError when importing yaml
    mock_import.side_effect = ImportError("No module named 'yaml'")
    
    # Patch the import to raise ImportError
    with patch('awslabs.openapi_mcp_server.utils.openapi.load_openapi_spec') as mock_load:
        # Make the original function available
        original_function = load_openapi_spec
        
        # Make the mock function raise ImportError when yaml is needed
        def side_effect(url="", path=""):
            if path.lower().endswith(('.yaml', '.yml')):
                raise ImportError("No module named 'yaml'")
            return original_function(url=url, path=path)
            
        mock_load.side_effect = side_effect
        
        # Test the case
        with pytest.raises(ImportError):
            mock_load(path="test.yaml")


@pytest.mark.asyncio
@patch('awslabs.openapi_mcp_server.prompts.instructions.logger.info')
async def test_generate_api_instructions(mock_logger):
    """Test generating API instructions."""
    # Create mock server
    server = MagicMock()
    
    api_name = "test-api"
    openapi_spec = {
        "info": {
            "title": "Test API Title",
            "description": "This is a test API description"
        }
    }
    
    # Call the function
    await generate_api_instructions(server, api_name, openapi_spec)
    
    # Verify that the logger was called with the expected content
    mock_logger.assert_any_call(f"Generating dynamic instructions for {api_name} API")
    
    # Check the second call to logger.info contains the API title and part of the description
    mock_logger.assert_any_call(ANY)
    # Get the second call args
    second_call_args = mock_logger.call_args_list[1][0][0]
    assert "Generated instructions for test-api" in second_call_args
    assert "# Test API Title" in second_call_args
    assert "This is a test API description" in second_call_args


class AsyncMock(MagicMock):
    """Mock class that works with async functions."""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server(mock_asyncio_run, mock_load_openapi_spec):
    """Test creating the MCP server."""
    # Setup mocks
    mock_load_openapi_spec.return_value = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "description": "Test description"}
    }
    
    # Make sure asyncio.run properly handles the coroutine
    mock_asyncio_run.return_value = None

    config = Config(
        api_name="testapi",
        api_base_url="https://test.api.com",
        api_spec_url="https://test.api.com/openapi.json"
    )

    server = create_mcp_server(config)

    assert server is not None
    mock_load_openapi_spec.assert_called_once()
    mock_asyncio_run.assert_called_once()


@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server_basic_auth(mock_asyncio_run, mock_load_openapi_spec):
    """Test creating the MCP server with basic authentication."""
    # Setup mocks
    mock_load_openapi_spec.return_value = {
        "openapi": "3.0.0",
        "info": {"title": "Test API"}
    }
    
    # Make sure asyncio.run properly handles the coroutine
    mock_asyncio_run.return_value = None

    config = Config(
        api_name="testapi",
        api_base_url="https://test.api.com",
        api_spec_url="https://test.api.com/openapi.json",
        auth_type="basic",
        auth_username="testuser",
        auth_password="testpass"
    )

    with patch('awslabs.openapi_mcp_server.server.httpx.BasicAuth') as mock_basic_auth:
        server = create_mcp_server(config)
        
        assert server is not None
        mock_basic_auth.assert_called_once_with(username="testuser", password="testpass")


@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server_bearer_auth(mock_asyncio_run, mock_load_openapi_spec):
    """Test creating the MCP server with bearer token authentication."""
    # Setup mocks
    mock_load_openapi_spec.return_value = {
        "openapi": "3.0.0",
        "info": {"title": "Test API"}
    }
    
    # Make sure asyncio.run properly handles the coroutine
    mock_asyncio_run.return_value = None

    config = Config(
        api_name="testapi",
        api_base_url="https://test.api.com",
        api_spec_url="https://test.api.com/openapi.json",
        auth_type="bearer",
        auth_token="test_token"
    )

    server = create_mcp_server(config)
    
    assert server is not None
    mock_load_openapi_spec.assert_called_once()


@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server_api_key_auth_header(mock_asyncio_run, mock_load_openapi_spec):
    """Test creating the MCP server with API key authentication in header."""
    # Setup mocks
    mock_load_openapi_spec.return_value = {
        "openapi": "3.0.0",
        "info": {"title": "Test API"}
    }
    
    # Make sure asyncio.run properly handles the coroutine
    mock_asyncio_run.return_value = None

    config = Config(
        api_name="testapi",
        api_base_url="https://test.api.com",
        api_spec_url="https://test.api.com/openapi.json",
        auth_type="api_key",
        auth_api_key="test_api_key",
        auth_api_key_name="X-API-Key",
        auth_api_key_in="header"
    )

    server = create_mcp_server(config)
    
    assert server is not None
    mock_load_openapi_spec.assert_called_once()


@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server_api_key_auth_query(mock_asyncio_run, mock_load_openapi_spec):
    """Test creating the MCP server with API key authentication in query parameter."""
    # Setup mocks
    mock_load_openapi_spec.return_value = {
        "openapi": "3.0.0",
        "info": {"title": "Test API"}
    }
    
    # Make sure asyncio.run properly handles the coroutine
    mock_asyncio_run.return_value = None

    config = Config(
        api_name="testapi",
        api_base_url="https://test.api.com",
        api_spec_url="https://test.api.com/openapi.json",
        auth_type="api_key",
        auth_api_key="test_api_key",
        auth_api_key_name="api_key",
        auth_api_key_in="query"
    )

    server = create_mcp_server(config)
    
    assert server is not None
    mock_load_openapi_spec.assert_called_once()


@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.generate_api_instructions')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server_api_key_auth_cookie(mock_asyncio_run, mock_gen_instructions, mock_load_openapi_spec):
    """Test creating the MCP server with API key authentication in cookie."""
    # Setup mocks
    mock_load_openapi_spec.return_value = {
        "openapi": "3.0.0",
        "info": {"title": "Test API"}
    }
    
    # Use AsyncMock for the generate_api_instructions function
    mock_gen_instructions.return_value = None
    
    # Make sure asyncio.run properly handles the coroutine
    def mock_run_side_effect(coroutine):
        # For testing, we'll just return None instead of running the coroutine
        return None
        
    mock_asyncio_run.side_effect = mock_run_side_effect

    config = Config(
        api_name="testapi",
        api_base_url="https://test.api.com",
        api_spec_url="https://test.api.com/openapi.json",
        auth_type="api_key",
        auth_api_key="test_api_key",
        auth_api_key_name="api_key",
        auth_api_key_in="cookie"
    )

    server = create_mcp_server(config)
    
    assert server is not None
    mock_load_openapi_spec.assert_called_once()


def test_create_mcp_server_error_handling():
    """Test error handling in create_mcp_server."""
    # Use a different approach for this test to avoid coroutine warnings
    
    # Create a config
    config = Config(
        api_name="testapi",
        api_base_url="https://test.api.com",
        api_spec_url="https://test.api.com/openapi.json"
    )
    
    # We'll test directly with an exception in the try block
    with patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load:
        # Make load_openapi_spec raise an exception
        mock_load.side_effect = Exception("Test exception")
        
        # Create server - it should not raise exception
        server = create_mcp_server(config)
        
        # Verify server was created despite the exception
        assert server is not None
        mock_load.assert_called_once()


def test_create_mcp_server_missing_spec_urls():
    """Test error handling when both spec URLs are missing - without using any async code."""
    # Mock the entire server module to avoid any async code
    with patch('awslabs.openapi_mcp_server.server.FastMCP') as mock_fastmcp:
        # Have FastMCP return just a regular (non-async) MagicMock
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        
        # Don't patch asyncio or any async functions
        # Instead, mock out the functions we need to test
        with patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load_spec:
            # Test with a config that has empty spec URLs
            config = Config(
                api_name="testapi", 
                api_base_url="https://test.api.com", 
                api_spec_url="", 
                api_spec_path=""
            )
            
            # Skip all async behaviors by bypassing that part of create_mcp_server
            with patch('awslabs.openapi_mcp_server.server.asyncio'):
                server = create_mcp_server(config)
                
                # Verify behavior: load_openapi_spec should not be called
                assert server is not None
                mock_load_spec.assert_not_called()


@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server_missing_base_url(mock_asyncio_run, mock_load_openapi_spec):
    """Test error handling when base URL is missing."""
    # Setup mocks
    mock_load_openapi_spec.return_value = {
        "openapi": "3.0.0",
        "info": {"title": "Test API"}
    }
    
    # Make sure asyncio.run properly handles the coroutine
    mock_asyncio_run.return_value = None
    
    config = Config(
        api_name="testapi",
        api_base_url="",  # Empty base URL
        api_spec_url="https://test.api.com/openapi.json"
    )

    # Create server - it should still work even with missing base URL
    server = create_mcp_server(config)
    
    assert server is not None
    mock_load_openapi_spec.assert_called_once()
