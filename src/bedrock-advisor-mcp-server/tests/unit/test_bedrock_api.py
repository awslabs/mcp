"""
Unit tests for the Bedrock API service.

This module tests the Bedrock API service's ability to fetch and process
model data from the AWS Bedrock API.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bedrock_advisor.services.bedrock_api import BedrockAPIService
from bedrock_advisor.utils.errors import ModelNotFoundError, ServiceUnavailableError


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client for testing."""
    mock_client = MagicMock()

    # Mock list_foundation_models response
    mock_client.list_foundation_models.return_value = {
        "modelSummaries": [
            {
                "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                "modelName": "Claude 3 Sonnet",
                "providerName": "Anthropic",
                "inputModalities": ["TEXT", "IMAGE"],
                "outputModalities": ["TEXT"],
                "responseStreamingSupported": True,
                "customizationsSupported": [],
                "inferenceTypesSupported": ["ON_DEMAND"],
            },
            {
                "modelId": "amazon.titan-text-express-v1:0",
                "modelName": "Titan Text Express",
                "providerName": "Amazon",
                "inputModalities": ["TEXT"],
                "outputModalities": ["TEXT"],
                "responseStreamingSupported": True,
                "customizationsSupported": [],
                "inferenceTypesSupported": ["ON_DEMAND"],
            },
        ]
    }

    # Mock get_foundation_model response
    def get_foundation_model_side_effect(modelIdentifier, **kwargs):
        if modelIdentifier == "anthropic.claude-3-sonnet-20240229-v1:0":
            return {
                "modelDetails": {
                    "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "modelName": "Claude 3 Sonnet",
                    "providerName": "Anthropic",
                    "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1",
                    "inputModalities": ["TEXT", "IMAGE"],
                    "outputModalities": ["TEXT"],
                    "responseStreamingSupported": True,
                    "customizationsSupported": [],
                    "inferenceTypesSupported": ["ON_DEMAND"],
                }
            }
        elif modelIdentifier == "amazon.titan-text-express-v1:0":
            return {
                "modelDetails": {
                    "modelId": "amazon.titan-text-express-v1:0",
                    "modelName": "Titan Text Express",
                    "providerName": "Amazon",
                    "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-text-express-v1",
                    "inputModalities": ["TEXT"],
                    "outputModalities": ["TEXT"],
                    "responseStreamingSupported": True,
                    "customizationsSupported": [],
                    "inferenceTypesSupported": ["ON_DEMAND"],
                }
            }
        else:
            from botocore.exceptions import ClientError

            error_response = {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": f"Model {modelIdentifier} not found",
                }
            }
            raise ClientError(error_response, "GetFoundationModel")

    mock_client.get_foundation_model.side_effect = get_foundation_model_side_effect

    return mock_client


@pytest.fixture
def api_service(mock_bedrock_client):
    """Create a BedrockAPIService with a mocked client."""
    with patch(
        "bedrock_advisor.services.bedrock_api.boto3.client",
        return_value=mock_bedrock_client,
    ):
        service = BedrockAPIService(region="us-east-1")
        service._bedrock_client = mock_bedrock_client
        return service


@pytest.mark.asyncio
async def test_get_all_models(api_service, mock_bedrock_client):
    """Test fetching all models from the API."""
    models = await api_service.get_all_models()

    # Verify the API was called
    mock_bedrock_client.list_foundation_models.assert_called_once()

    # Verify we got the expected number of models
    assert len(models) == 2

    # Verify model properties were correctly extracted
    assert models[0].model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
    assert models[0].model_name == "Claude 3 Sonnet"
    assert models[0].provider_name == "Anthropic"
    assert "TEXT" in models[0].input_modalities
    assert "IMAGE" in models[0].input_modalities
    assert models[0].response_streaming_supported is True

    # Verify capabilities were inferred
    assert models[0].capabilities.text_generation is True
    assert models[0].capabilities.multimodal is True


@pytest.mark.asyncio
async def test_get_model(api_service, mock_bedrock_client):
    """Test fetching a specific model by ID."""
    model = await api_service.get_model("anthropic.claude-3-sonnet-20240229-v1:0")

    # Verify the API was called with the correct model ID
    mock_bedrock_client.get_foundation_model.assert_called_with(
        modelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0"
    )

    # Verify model properties
    assert model.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
    assert model.model_name == "Claude 3 Sonnet"
    assert model.provider_name == "Anthropic"


@pytest.mark.asyncio
async def test_get_model_not_found(api_service, mock_bedrock_client):
    """Test handling of model not found errors."""
    with pytest.raises(ModelNotFoundError):
        await api_service.get_model("nonexistent.model-v1:0")


@pytest.mark.asyncio
async def test_retry_with_backoff():
    """Test the retry with backoff mechanism."""
    api_service = BedrockAPIService()

    # Create a mock function that fails twice then succeeds
    mock_func = AsyncMock()
    mock_func.side_effect = [
        Exception("Throttling"),
        Exception("Throttling"),
        "success",
    ]

    # Test with a short delay for testing
    result = await api_service._retry_with_backoff(
        mock_func, "arg1", "arg2", max_retries=3, base_delay=0.01, kwarg1="value1"
    )

    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3

    # Verify the correct arguments were passed
    mock_func.assert_called_with("arg1", "arg2", kwarg1="value1")

    # Verify the result
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_with_backoff_max_retries_exceeded():
    """Test retry mechanism when max retries are exceeded."""
    api_service = BedrockAPIService()

    # Create a mock function that always fails
    mock_func = AsyncMock()
    mock_func.side_effect = Exception("Throttling")

    # Test with a short delay for testing
    with pytest.raises(Exception):
        await api_service._retry_with_backoff(mock_func, max_retries=2, base_delay=0.01)

    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3  # Initial call + 2 retries


@pytest.mark.asyncio
async def test_create_model_from_api(api_service):
    """Test creating a BedrockModel from API response."""
    model_summary = {
        "modelId": "test.model-v1:0",
        "modelName": "Test Model",
        "providerName": "TestProvider",
        "inputModalities": ["TEXT"],
        "outputModalities": ["TEXT"],
        "responseStreamingSupported": True,
        "customizationsSupported": [],
        "inferenceTypesSupported": ["ON_DEMAND"],
    }

    model = await api_service._create_model_from_api(model_summary)

    # Verify basic properties
    assert model.model_id == "test.model-v1:0"
    assert model.model_name == "Test Model"
    assert model.provider_name == "TestProvider"

    # Verify derived properties
    assert model.capabilities is not None
    assert model.performance is not None
    assert model.availability is not None


def test_infer_capabilities(api_service):
    """Test capability inference from model metadata."""
    # Test Claude-like model
    capabilities = api_service._infer_capabilities(
        "anthropic.claude-3-sonnet-v1:0",
        "Claude 3 Sonnet",
        "Anthropic",
        ["TEXT", "IMAGE"],
        ["TEXT"],
    )

    assert capabilities.text_generation is True
    assert capabilities.code_generation is True
    assert capabilities.multimodal is True
    assert capabilities.function_calling is True

    # Test embedding model
    capabilities = api_service._infer_capabilities(
        "amazon.titan-embed-text-v1:0",
        "Titan Embeddings",
        "Amazon",
        ["TEXT"],
        ["EMBEDDING"],
    )

    assert capabilities.text_generation is False
    assert capabilities.embedding is True


def test_estimate_performance(api_service):
    """Test performance estimation based on model type."""
    # Test fast model
    performance = api_service._estimate_performance(
        "anthropic.claude-3-haiku-v1:0", "Claude 3 Haiku", "Anthropic"
    )

    assert performance.latency_ms == 500
    assert performance.throughput_tokens_per_second == 150

    # Test large model
    performance = api_service._estimate_performance(
        "anthropic.claude-3-opus-v1:0", "Claude 3 Opus", "Anthropic"
    )

    assert performance.latency_ms == 2500
    assert performance.throughput_tokens_per_second == 60


def test_get_current_pricing(api_service):
    """Test pricing information retrieval."""
    # Test Claude model pricing
    pricing = api_service._get_current_pricing(
        "anthropic.claude-3-sonnet-v1:0", "Anthropic"
    )

    assert pricing is not None
    assert pricing.input_token_price == 0.003
    assert pricing.output_token_price == 0.015

    # Test unknown model pricing (should use provider defaults)
    pricing = api_service._get_current_pricing("unknown.model-v1:0", "Anthropic")

    assert pricing is not None
    assert pricing.input_token_price == 0.003
    assert pricing.output_token_price == 0.015


def test_get_max_tokens(api_service):
    """Test max tokens extraction based on model type."""
    assert api_service._get_max_tokens("claude-3", "Claude 3 Sonnet") == 8192
    assert api_service._get_max_tokens("titan-text", "Titan Text") == 3000
    assert api_service._get_max_tokens("embed", "Embeddings") is None


def test_get_context_length(api_service):
    """Test context length extraction based on model type."""
    assert api_service._get_context_length("claude-3", "Claude 3 Sonnet") == 200000
    assert api_service._get_context_length("titan-text", "Titan Text") == 32000
    assert api_service._get_context_length("unknown", "Unknown Model") == 32000


@pytest.mark.asyncio
async def test_check_model_availability(api_service):
    """Test model availability checking."""
    availability = await api_service._check_model_availability("test.model-v1:0")

    assert availability is not None
    assert len(availability.regions) > 0
    assert availability.status.value == "ACTIVE"


@pytest.mark.asyncio
async def test_service_unavailable(mock_bedrock_client):
    """Test handling of service unavailable errors."""
    # Mock boto3.client to raise NoCredentialsError
    with patch(
        "bedrock_advisor.services.bedrock_api.boto3.client",
        side_effect=Exception("No credentials"),
    ):
        # Create service (should not raise exception yet)
        service = BedrockAPIService()

        # Accessing bedrock_client property should raise ServiceUnavailableError
        with pytest.raises(ServiceUnavailableError):
            client = service.bedrock_client


@pytest.mark.asyncio
async def test_cache_validity(api_service):
    """Test cache validity checking."""
    # Initially cache should be invalid
    assert api_service._is_cache_valid() is False

    # After getting models, cache should be valid
    await api_service.get_all_models()
    assert api_service._is_cache_valid() is True

    # Manually set cache timestamp to old value
    api_service._cache_timestamp = datetime.now().replace(year=2020)
    assert api_service._is_cache_valid() is False
