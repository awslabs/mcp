"""
Integration tests for the Bedrock Advisor MCP server.

This module tests the end-to-end functionality of the MCP server,
including tool registration, request handling, and response formatting.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from awslabs.bedrock_advisor_mcp_server.models.bedrock import (
    BedrockModel,
    ModelAvailability,
    ModelCapabilities,
    ModelPerformance,
    ModelPricing,
    ModelStatus,
)
from awslabs.bedrock_advisor_mcp_server.server import BedrockAdvisorServer


@pytest.fixture
def mock_model_service():
    """Create a mock model service for testing."""
    mock_service = MagicMock()

    # Create test models
    today = "2025-06-18"

    test_models = [
        BedrockModel(
            model_id="test.general-purpose-v1:0",
            model_name="Test General Purpose",
            provider_name="TestProvider",
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            response_streaming_supported=True,
            customizations_supported=[],
            inference_types_supported=["ON_DEMAND"],
            max_tokens=4096,
            context_length=32000,
            pricing=ModelPricing(
                input_token_price=0.001,
                output_token_price=0.002,
                currency="USD",
                unit="per 1K tokens",
                last_updated=today
            ),
            capabilities=ModelCapabilities(
                text_generation=True,
                code_generation=True,
                summarization=True,
                question_answering=True,
                translation=True,
                classification=True,
                embedding=False,
                multimodal=False,
                function_calling=True,
                reasoning=True,
                mathematics=True,
                creative=True
            ),
            performance=ModelPerformance(
                latency_ms=1000,
                throughput_tokens_per_second=100,
                accuracy_score=0.85
            ),
            availability=ModelAvailability(
                regions=["us-east-1", "us-west-2", "eu-west-1"],
                status=ModelStatus.ACTIVE,
                last_checked=today
            )
        ),
        BedrockModel(
            model_id="test.code-expert-v1:0",
            model_name="Test Code Expert",
            provider_name="TestProvider",
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            response_streaming_supported=True,
            customizations_supported=[],
            inference_types_supported=["ON_DEMAND"],
            max_tokens=8192,
            context_length=64000,
            pricing=ModelPricing(
                input_token_price=0.002,
                output_token_price=0.004,
                currency="USD",
                unit="per 1K tokens",
                last_updated=today
            ),
            capabilities=ModelCapabilities(
                text_generation=True,
                code_generation=True,
                summarization=False,
                question_answering=True,
                translation=False,
                classification=False,
                embedding=False,
                multimodal=False,
                function_calling=True,
                reasoning=True,
                mathematics=True,
                creative=False
            ),
            performance=ModelPerformance(
                latency_ms=1500,
                throughput_tokens_per_second=80,
                accuracy_score=0.92
            ),
            availability=ModelAvailability(
                regions=["us-east-1", "us-west-2"],
                status=ModelStatus.ACTIVE,
                last_checked=today
            )
        )
    ]

    # Configure mock methods
    mock_service.get_all_models.return_value = test_models
    mock_service.get_model.side_effect = lambda model_id: next(
        (m for m in test_models if m.model_id == model_id),
        None
    )
    mock_service.get_api_status.return_value = {
        "using_api": True,
        "total_models": len(test_models),
        "cache_valid": True,
        "last_refresh": today
    }

    # Mock async method
    async def mock_refresh_models():
        return len(test_models)

    mock_service.refresh_models = mock_refresh_models

    return mock_service


@pytest.fixture
def mock_data_updater():
    """Create a mock data updater for testing."""
    mock_updater = MagicMock()

    # Mock async method
    async def mock_initialize():
        return

    mock_updater._initialize_dynamic_data = mock_initialize

    return mock_updater


@pytest.fixture
def server(mock_model_service, mock_data_updater):
    """Create a BedrockAdvisorServer with mocked dependencies."""
    with patch('bedrock_advisor.server.ModelDataService', return_value=mock_model_service), \
         patch('bedrock_advisor.server.BedrockDataUpdater', return_value=mock_data_updater):

        server = BedrockAdvisorServer()
        server.model_service = mock_model_service
        server.data_updater = mock_data_updater

        return server


@pytest.mark.asyncio
async def test_list_tools(server):
    """Test listing available tools."""
    # Get the list_tools function
    list_tools_func = None
    for decorator in server.server._list_tools_decorators:
        list_tools_func = decorator.func

    assert list_tools_func is not None

    # Call the function
    tools = await list_tools_func()

    # Verify we have the expected tools
    assert len(tools) > 0

    # Check for specific tools
    tool_names = [tool.name for tool in tools]
    assert "recommend_model" in tool_names
    assert "get_model_info" in tool_names
    assert "list_models" in tool_names
    assert "refresh_models" in tool_names


@pytest.mark.asyncio
async def test_recommend_model_tool(server):
    """Test the recommend_model tool."""
    # Get the call_tool function
    call_tool_func = None
    for decorator in server.server._call_tool_decorators:
        call_tool_func = decorator.func

    assert call_tool_func is not None

    # Call the function with recommend_model arguments
    arguments = {
        "use_case": {
            "primary": "text-generation"
        },
        "max_recommendations": 2
    }

    result = await call_tool_func("recommend_model", arguments)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse the JSON response
    response = json.loads(result[0].text)

    # Verify the response structure
    assert "recommendations" in response
    assert "summary" in response
    assert len(response["recommendations"]) == 2


@pytest.mark.asyncio
async def test_get_model_info_tool(server):
    """Test the get_model_info tool."""
    # Get the call_tool function
    call_tool_func = None
    for decorator in server.server._call_tool_decorators:
        call_tool_func = decorator.func

    assert call_tool_func is not None

    # Call the function with get_model_info arguments
    arguments = {
        "model_id": "test.general-purpose-v1:0"
    }

    result = await call_tool_func("get_model_info", arguments)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse the JSON response
    response = json.loads(result[0].text)

    # Verify the response structure
    assert "model" in response
    assert response["model"]["model_id"] == "test.general-purpose-v1:0"
    assert "capabilities" in response
    assert "api_status" in response


@pytest.mark.asyncio
async def test_list_models_tool(server):
    """Test the list_models tool."""
    # Get the call_tool function
    call_tool_func = None
    for decorator in server.server._call_tool_decorators:
        call_tool_func = decorator.func

    assert call_tool_func is not None

    # Call the function with list_models arguments
    arguments = {
        "provider": "TestProvider"
    }

    result = await call_tool_func("list_models", arguments)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse the JSON response
    response = json.loads(result[0].text)

    # Verify the response structure
    assert "models" in response
    assert "total_count" in response
    assert response["total_count"] == 2


@pytest.mark.asyncio
async def test_refresh_models_tool(server):
    """Test the refresh_models tool."""
    # Get the call_tool function
    call_tool_func = None
    for decorator in server.server._call_tool_decorators:
        call_tool_func = decorator.func

    assert call_tool_func is not None

    # Call the function with refresh_models arguments
    arguments = {
        "force_refresh": True
    }

    result = await call_tool_func("refresh_models", arguments)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse the JSON response
    response = json.loads(result[0].text)

    # Verify the response structure
    assert "success" in response
    assert "models_loaded" in response
    assert "api_status" in response


@pytest.mark.asyncio
async def test_error_handling(server):
    """Test error handling in the server."""
    # Get the call_tool function
    call_tool_func = None
    for decorator in server.server._call_tool_decorators:
        call_tool_func = decorator.func

    assert call_tool_func is not None

    # Call the function with an unknown tool
    result = await call_tool_func("unknown_tool", {})

    # Verify the result contains an error
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse the JSON response
    response = json.loads(result[0].text)

    # Verify the error structure
    assert "error" in response
    assert "message" in response
    assert "troubleshooting" in response
    assert response["tool"] == "unknown_tool"


@pytest.mark.asyncio
async def test_validation_error(server):
    """Test validation error handling."""
    # Get the call_tool function
    call_tool_func = None
    for decorator in server.server._call_tool_decorators:
        call_tool_func = decorator.func

    assert call_tool_func is not None

    # Call recommend_model with invalid arguments (missing required field)
    arguments = {
        "max_recommendations": 2
        # Missing required "use_case" field
    }

    result = await call_tool_func("recommend_model", arguments)

    # Verify the result contains an error
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse the JSON response
    response = json.loads(result[0].text)

    # Verify the error structure
    assert "error" in response
    assert "message" in response
    assert "troubleshooting" in response
