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

"""Tests for embeddings module."""

import pytest
from awslabs.valkey_mcp_server.embeddings import create_embeddings_provider
from awslabs.valkey_mcp_server.embeddings.base import EmbeddingsProvider
from awslabs.valkey_mcp_server.embeddings.providers import (
    BedrockEmbeddings,
    HashEmbeddings,
    OllamaEmbeddings,
    OpenAIEmbeddings,
)
from unittest.mock import AsyncMock, Mock, patch


class TestEmbeddingsFactory:
    """Test embeddings provider factory function."""

    @patch('awslabs.valkey_mcp_server.embeddings.EMBEDDING_CFG')
    def test_create_ollama_provider(self, mock_config):
        """Test creating Ollama embeddings provider."""
        mock_config.get.side_effect = lambda key, default=None: {
            'provider': 'ollama',
            'ollama_host': 'http://test:11434',
            'ollama_embedding_model': 'test-model',
        }.get(key, default)

        provider = create_embeddings_provider()

        assert isinstance(provider, OllamaEmbeddings)
        assert provider.base_url == 'http://test:11434'
        assert provider.model == 'test-model'

    @patch('awslabs.valkey_mcp_server.embeddings.EMBEDDING_CFG')
    @patch('boto3.Session')
    def test_create_bedrock_provider(self, mock_session, mock_config):
        """Test creating Bedrock embeddings provider."""
        mock_config.get.side_effect = lambda key, default=None: {
            'provider': 'bedrock',
            'bedrock_region': 'us-west-2',
            'bedrock_model_id': 'test-model',
            'bedrock_normalize': True,
            'bedrock_dimensions': 1024,
            'bedrock_max_attempts': 5,
        }.get(key, default)

        # Mock the session and client
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_client = Mock()
        mock_session_instance.client.return_value = mock_client

        provider = create_embeddings_provider()

        assert isinstance(provider, BedrockEmbeddings)

    @patch('awslabs.valkey_mcp_server.embeddings.EMBEDDING_CFG')
    def test_create_openai_provider(self, mock_config):
        """Test creating OpenAI embeddings provider."""
        mock_config.get.side_effect = lambda key, default=None: {
            'provider': 'openai',
            'openai_api_key': 'test-key',  # pragma: allowlist secret
            'openai_model': 'test-model',
        }.get(key, default)

        provider = create_embeddings_provider()

        assert isinstance(provider, OpenAIEmbeddings)

    @patch('awslabs.valkey_mcp_server.embeddings.EMBEDDING_CFG')
    def test_create_openai_provider_missing_key(self, mock_config):
        """Test creating OpenAI provider without API key raises error."""
        mock_config.get.side_effect = lambda key, default=None: {
            'provider': 'openai',
            'openai_api_key': None,
        }.get(key, default)

        with pytest.raises(ValueError, match='OPENAI_API_KEY environment variable is required'):
            create_embeddings_provider()

    @patch('awslabs.valkey_mcp_server.embeddings.EMBEDDING_CFG')
    def test_create_hash_provider(self, mock_config):
        """Test creating hash embeddings provider."""
        mock_config.get.side_effect = lambda key, default=None: {'provider': 'hash'}.get(
            key, default
        )

        provider = create_embeddings_provider()

        assert isinstance(provider, HashEmbeddings)

    @patch('awslabs.valkey_mcp_server.embeddings.EMBEDDING_CFG')
    def test_create_unknown_provider(self, mock_config):
        """Test creating unknown provider raises error."""
        mock_config.get.side_effect = lambda key, default=None: {'provider': 'unknown'}.get(
            key, default
        )

        with pytest.raises(ValueError, match='Unknown embeddings provider: unknown'):
            create_embeddings_provider()


class TestEmbeddingsBase:
    """Test embeddings base class."""

    def test_embeddings_provider_is_abstract(self):
        """Test that EmbeddingsProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EmbeddingsProvider()  # type: ignore[abstract]

    def test_embeddings_provider_interface(self):
        """Test that EmbeddingsProvider defines required methods."""
        assert hasattr(EmbeddingsProvider, 'generate_embedding')
        assert hasattr(EmbeddingsProvider, 'get_dimensions')
        assert hasattr(EmbeddingsProvider, 'get_provider_name')


class TestOllamaEmbeddings:
    """Test Ollama embeddings provider."""

    def test_ollama_init(self):
        """Test Ollama provider initialization."""
        provider = OllamaEmbeddings('http://test:11434', 'test-model')

        assert provider.base_url == 'http://test:11434'
        assert provider.model == 'test-model'
        assert provider._dimensions == 768

    def test_ollama_get_dimensions(self):
        """Test getting dimensions."""
        provider = OllamaEmbeddings()
        assert provider.get_dimensions() == 768

    def test_ollama_get_provider_name(self):
        """Test getting provider name."""
        provider = OllamaEmbeddings(model='test-model')
        assert provider.get_provider_name() == 'Ollama (test-model)'

    @pytest.mark.asyncio
    async def test_ollama_generate_embedding(self):
        """Test generating embedding."""
        provider = OllamaEmbeddings()

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {'embedding': [0.1, 0.2, 0.3]}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            result = await provider.generate_embedding('test text')

            assert result == [0.1, 0.2, 0.3]


class TestHashEmbeddings:
    """Test hash embeddings provider."""

    def test_hash_init(self):
        """Test hash provider initialization."""
        provider = HashEmbeddings(256)
        assert provider._dimensions == 256

    def test_hash_get_dimensions(self):
        """Test getting dimensions."""
        provider = HashEmbeddings(512)
        assert provider.get_dimensions() == 512

    def test_hash_get_provider_name(self):
        """Test getting provider name."""
        provider = HashEmbeddings(128)
        assert provider.get_provider_name() == 'Dummy (128d)'

    @pytest.mark.asyncio
    async def test_hash_generate_embedding_consistency(self):
        """Test that hash embeddings are consistent."""
        provider = HashEmbeddings(64)

        result1 = await provider.generate_embedding('test text')
        result2 = await provider.generate_embedding('test text')

        assert result1 == result2
        assert len(result1) == 64

    @pytest.mark.asyncio
    async def test_hash_generate_embedding_different_texts(self):
        """Test that different texts produce different embeddings."""
        provider = HashEmbeddings(32)

        result1 = await provider.generate_embedding('text one')
        result2 = await provider.generate_embedding('text two')

        assert result1 != result2
        assert len(result1) == 32
        assert len(result2) == 32


class TestBedrockEmbeddings:
    """Test Bedrock embeddings provider."""

    @patch('boto3.Session')
    def test_bedrock_init_defaults(self, mock_session):
        """Test Bedrock provider initialization with defaults."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_client = Mock()
        mock_session_instance.client.return_value = mock_client

        provider = BedrockEmbeddings()

        assert provider.model_id == 'amazon.nova-2-multimodal-embeddings-v1:0'
        assert provider._dimensions == 3072

    @patch('boto3.Session')
    def test_bedrock_init_custom(self, mock_session):
        """Test Bedrock provider initialization with custom values."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_client = Mock()
        mock_session_instance.client.return_value = mock_client

        provider = BedrockEmbeddings(
            region_name='us-west-2', model_id='custom-model', dimensions=2048, normalize=False
        )

        assert provider.model_id == 'custom-model'
        assert provider._dimensions == 2048
        assert provider.normalize is False

    @patch('boto3.Session')
    def test_bedrock_get_provider_name(self, mock_session):
        """Test getting provider name."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_client = Mock()
        mock_session_instance.client.return_value = mock_client

        provider = BedrockEmbeddings(model_id='test-model')
        assert provider.get_provider_name() == 'AWS Bedrock (test-model)'


class TestOpenAIEmbeddings:
    """Test OpenAI embeddings provider."""

    def test_openai_init(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIEmbeddings('test-key', 'test-model')

        assert provider.model == 'test-model'
        assert provider._dimensions == 3072  # Default for non-3-small models

    def test_openai_init_small_model(self):
        """Test OpenAI provider with 3-small model."""
        provider = OpenAIEmbeddings('test-key', 'text-embedding-3-small')

        assert provider._dimensions == 1536

    def test_openai_init_large_model(self):
        """Test OpenAI provider with 3-large model."""
        provider = OpenAIEmbeddings('test-key', 'text-embedding-3-large')

        assert provider._dimensions == 3072

    def test_openai_get_dimensions(self):
        """Test getting dimensions."""
        provider = OpenAIEmbeddings('test-key', 'text-embedding-3-small')
        assert provider.get_dimensions() == 1536

    def test_openai_get_provider_name(self):
        """Test getting provider name."""
        provider = OpenAIEmbeddings('test-key', 'test-model')
        assert provider.get_provider_name() == 'OpenAI (test-model)'

    @pytest.mark.asyncio
    async def test_openai_generate_embedding(self):
        """Test generating embedding."""
        provider = OpenAIEmbeddings('test-key', 'test-model')

        # Mock the OpenAI client
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]

        provider.client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.generate_embedding('test text')

        assert result == [0.1, 0.2, 0.3]
        provider.client.embeddings.create.assert_called_once_with(
            model='test-model', input='test text'
        )
