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

"""Unit tests for embeddings factory and providers."""

import pytest
from awslabs.valkey_mcp_server.embeddings.providers import (
    BedrockEmbeddings,
    HashEmbeddings,
    OllamaEmbeddings,
    OpenAIEmbeddings,
)
from unittest.mock import AsyncMock, MagicMock, patch


pytestmark = pytest.mark.asyncio

FACTORY_MODULE = 'awslabs.valkey_mcp_server.embeddings.factory'
INIT_MODULE = 'awslabs.valkey_mcp_server.embeddings'


class TestFactory:
    def test_creates_ollama(self):
        with patch(
            f'{FACTORY_MODULE}.EMBEDDING_CFG',
            {
                'provider': 'ollama',
                'ollama_host': 'http://localhost:11434',
                'ollama_embedding_model': 'nomic-embed-text',
                'embedding_dimensions': None,
            },
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert isinstance(provider, OllamaEmbeddings)

    def test_creates_ollama_with_dimensions(self):
        with patch(
            f'{FACTORY_MODULE}.EMBEDDING_CFG',
            {
                'provider': 'ollama',
                'ollama_host': 'http://localhost:11434',
                'ollama_embedding_model': 'nomic-embed-text',
                'embedding_dimensions': 512,
            },
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert provider.get_dimensions() == 512

    def test_creates_hash(self):
        with patch(f'{FACTORY_MODULE}.EMBEDDING_CFG', {'provider': 'hash'}):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert isinstance(provider, HashEmbeddings)

    def test_creates_openai(self):
        with patch(
            f'{FACTORY_MODULE}.EMBEDDING_CFG',
            {
                'provider': 'openai',
                'openai_api_key': 'sk-test',  # pragma: allowlist secret
                'openai_model': 'text-embedding-3-small',
                'embedding_dimensions': None,
            },
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert isinstance(provider, OpenAIEmbeddings)

    def test_creates_openai_with_dimensions(self):
        with patch(
            f'{FACTORY_MODULE}.EMBEDDING_CFG',
            {
                'provider': 'openai',
                'openai_api_key': 'sk-test',  # pragma: allowlist secret
                'openai_model': 'text-embedding-3-small',
                'embedding_dimensions': 256,
            },
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert provider.get_dimensions() == 256

    def test_openai_missing_key_raises(self):
        with (
            patch(
                f'{FACTORY_MODULE}.EMBEDDING_CFG', {'provider': 'openai', 'openai_api_key': None}
            ),
            pytest.raises(ValueError, match='OPENAI_API_KEY'),
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            create_embeddings_provider()

    def test_unknown_provider_raises(self):
        with (
            patch(f'{FACTORY_MODULE}.EMBEDDING_CFG', {'provider': 'bogus'}),
            pytest.raises(ValueError, match='Unknown'),
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            create_embeddings_provider()

    def test_creates_bedrock(self):
        with patch(
            f'{FACTORY_MODULE}.EMBEDDING_CFG',
            {
                'provider': 'bedrock',
                'bedrock_region': 'us-east-1',
                'bedrock_model_id': 'amazon.titan-embed-text-v2:0',
                'bedrock_normalize': None,
                'bedrock_dimensions': None,
                'bedrock_input_type': None,
                'bedrock_max_attempts': 3,
                'bedrock_max_pool_connections': 50,
                'bedrock_retry_mode': 'adaptive',
            },
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert isinstance(provider, BedrockEmbeddings)


class TestSingleton:
    def test_get_provider_returns_same_instance(self):
        mock_provider = MagicMock()
        with patch(f'{INIT_MODULE}.create_embeddings_provider', return_value=mock_provider):
            from awslabs.valkey_mcp_server.embeddings import get_provider, reset_provider

            reset_provider()
            p1 = get_provider()
            p2 = get_provider()
            assert p1 is p2
            reset_provider()

    def test_has_provider_true(self):
        mock_provider = MagicMock()
        with patch(f'{INIT_MODULE}.create_embeddings_provider', return_value=mock_provider):
            from awslabs.valkey_mcp_server.embeddings import has_provider, reset_provider

            reset_provider()
            assert has_provider() is True
            reset_provider()

    def test_has_provider_false_on_error(self):
        with patch(
            f'{INIT_MODULE}.create_embeddings_provider', side_effect=ValueError('no creds')
        ):
            from awslabs.valkey_mcp_server.embeddings import has_provider, reset_provider

            reset_provider()
            assert has_provider() is False
            reset_provider()

    def test_reset_clears_provider(self):
        mock1 = MagicMock()
        mock2 = MagicMock()
        with patch(f'{INIT_MODULE}.create_embeddings_provider', side_effect=[mock1, mock2]):
            from awslabs.valkey_mcp_server.embeddings import get_provider, reset_provider

            reset_provider()
            p1 = get_provider()
            reset_provider()
            p2 = get_provider()
            assert p1 is not p2
            reset_provider()


class TestHashEmbeddings:
    async def test_deterministic(self):
        provider = HashEmbeddings(dimensions=64)
        e1 = await provider.generate_embedding('hello')
        e2 = await provider.generate_embedding('hello')
        assert e1 == e2

    async def test_different_text_different_embedding(self):
        provider = HashEmbeddings(dimensions=64)
        e1 = await provider.generate_embedding('hello')
        e2 = await provider.generate_embedding('world')
        assert e1 != e2

    async def test_correct_dimensions(self):
        provider = HashEmbeddings(dimensions=32)
        emb = await provider.generate_embedding('test')
        assert len(emb) == 32

    def test_provider_name(self):
        assert 'Hash' in HashEmbeddings(dimensions=128).get_provider_name()

    def test_get_dimensions(self):
        assert HashEmbeddings(dimensions=256).get_dimensions() == 256

    async def test_values_in_range(self):
        provider = HashEmbeddings(dimensions=128)
        emb = await provider.generate_embedding('test')
        assert all(-1.0 <= v <= 1.0 for v in emb)


class TestOllamaEmbeddings:
    def test_default_dimensions(self):
        provider = OllamaEmbeddings()
        assert provider.get_dimensions() == 768

    def test_custom_dimensions(self):
        provider = OllamaEmbeddings(dimensions=1024)
        assert provider.get_dimensions() == 1024

    def test_provider_name(self):
        provider = OllamaEmbeddings(model='mxbai-embed-large')
        assert 'mxbai-embed-large' in provider.get_provider_name()


class TestOpenAIEmbeddings:
    def test_default_dimensions_small(self):
        provider = OpenAIEmbeddings(
            api_key='sk-test',  # pragma: allowlist secret
            model='text-embedding-3-small',
        )
        assert provider.get_dimensions() == 1536

    def test_default_dimensions_large(self):
        provider = OpenAIEmbeddings(
            api_key='sk-test',  # pragma: allowlist secret
            model='text-embedding-3-large',
        )  # pragma: allowlist secret
        assert provider.get_dimensions() == 3072

    def test_custom_dimensions_override(self):
        provider = OpenAIEmbeddings(
            api_key='sk-test',  # pragma: allowlist secret
            model='text-embedding-3-small',
            dimensions=256,  # pragma: allowlist secret
        )  # pragma: allowlist secret
        assert provider.get_dimensions() == 256

    def test_provider_name(self):
        provider = OpenAIEmbeddings(
            api_key='sk-test',  # pragma: allowlist secret
            model='text-embedding-3-small',
        )
        assert 'OpenAI' in provider.get_provider_name()

    async def test_generate_embedding(self):
        provider = OpenAIEmbeddings(
            api_key='sk-test',  # pragma: allowlist secret
            model='text-embedding-3-small',
        )
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        provider.client = AsyncMock()
        provider.client.embeddings.create = AsyncMock(return_value=mock_response)
        result = await provider.generate_embedding('hello')
        assert result == [0.1, 0.2, 0.3]
        provider.client.embeddings.create.assert_called_once_with(
            model='text-embedding-3-small', input='hello'
        )


class TestBedrockEmbeddings:
    def test_titan_default_dimensions(self):
        provider = BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0')
        assert provider.get_dimensions() == 1536

    def test_nova_default_dimensions(self):
        provider = BedrockEmbeddings(model_id='amazon.nova-2-multimodal-embeddings-v1:0')
        assert provider.get_dimensions() == 3072

    def test_custom_dimensions(self):
        provider = BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0', dimensions=512)
        assert provider.get_dimensions() == 512

    def test_provider_name(self):
        provider = BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0')
        assert 'Bedrock' in provider.get_provider_name()

    def test_nova_model_detection(self):
        provider = BedrockEmbeddings(model_id='amazon.nova-2-multimodal-embeddings-v1:0')
        assert provider._is_nova_model is True

    def test_titan_model_detection(self):
        provider = BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0')
        assert provider._is_nova_model is False

    def test_credentials_not_validated_at_init(self):
        provider = BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0')
        assert provider._credentials_validated is False


class TestOllamaClose:
    async def test_close(self):
        provider = OllamaEmbeddings()
        provider._client = AsyncMock()
        await provider.close()
        provider._client.aclose.assert_called_once()

    def test_auto_prepend_http(self):
        provider = OllamaEmbeddings(base_url='myhost:11434')
        assert provider.base_url == 'http://myhost:11434'

    def test_dimensions_zero_uses_default(self):
        """dimensions=0 is preserved (not treated as None/falsy)."""
        provider = OllamaEmbeddings(dimensions=0)
        assert provider.get_dimensions() == 0
