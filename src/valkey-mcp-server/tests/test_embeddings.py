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
from awslabs.valkey_mcp_server.embeddings.providers import HashEmbeddings, OllamaEmbeddings
from unittest.mock import patch


pytestmark = pytest.mark.asyncio

FACTORY_MODULE = 'awslabs.valkey_mcp_server.embeddings.factory'


class TestFactory:
    def test_creates_ollama(self):
        with patch(
            f'{FACTORY_MODULE}.EMBEDDING_CFG',
            {
                'provider': 'ollama',
                'ollama_host': 'http://localhost:11434',
                'ollama_embedding_model': 'nomic-embed-text',
            },
        ):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert isinstance(provider, OllamaEmbeddings)

    def test_creates_hash(self):
        with patch(f'{FACTORY_MODULE}.EMBEDDING_CFG', {'provider': 'hash'}):
            from awslabs.valkey_mcp_server.embeddings.factory import create_embeddings_provider

            provider = create_embeddings_provider()
        assert isinstance(provider, HashEmbeddings)

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
