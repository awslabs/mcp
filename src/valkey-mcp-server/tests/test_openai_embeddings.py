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

"""Tests for OpenAI embeddings provider."""
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.integration
@pytest.mark.manual
class TestOpenAIEmbeddings:
    """Integration tests for OpenAI embeddings provider."""

    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test basic embedding generation with real OpenAI API."""
        import os
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")
        
        from awslabs.valkey_mcp_server.embeddings.providers import OpenAIEmbeddings
        
        provider = OpenAIEmbeddings(
            api_key=api_key,
            model="text-embedding-3-small"
        )

        assert provider.get_dimensions() == 1536

        text = "Hello world"
        embedding = await provider.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)


class TestOpenAIEmbeddingsMocked:
    """Unit tests for OpenAI embeddings with mocked openai."""

    @pytest.fixture(autouse=True)
    def mock_openai(self, mocker):
        """Mock openai module before importing OpenAIEmbeddings."""
        if 'openai' not in sys.modules:
            mock_openai_module = MagicMock()
            sys.modules['openai'] = mock_openai_module
            self._cleanup_openai = True
        else:
            self._cleanup_openai = False
        
        yield
        
        if self._cleanup_openai and 'openai' in sys.modules:
            del sys.modules['openai']

    @pytest.mark.asyncio
    async def test_generate_embedding_mocked(self, mocker):
        """Test embedding generation with mocked openai."""
        mock_embedding = [0.1] * 1536
        mock_data = MagicMock()
        mock_data.embedding = mock_embedding
        mock_response = MagicMock()
        mock_response.data = [mock_data]
        
        mock_client = MagicMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        import openai
        openai.AsyncOpenAI = MagicMock(return_value=mock_client)
        
        from awslabs.valkey_mcp_server.embeddings.providers import OpenAIEmbeddings
        provider = OpenAIEmbeddings(api_key="sk-test-key")
        
        embedding = await provider.generate_embedding("test")
        
        assert embedding == mock_embedding
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="test"
        )

    @pytest.mark.asyncio
    async def test_get_dimensions_mocked(self):
        """Test dimensions with mocked openai."""
        import openai
        openai.AsyncOpenAI = MagicMock()
        
        from awslabs.valkey_mcp_server.embeddings.providers import OpenAIEmbeddings
        provider = OpenAIEmbeddings(api_key="sk-test-key", model="text-embedding-3-small")
        
        assert provider.get_dimensions() == 1536

    @pytest.mark.asyncio
    async def test_get_dimensions_large_model_mocked(self):
        """Test dimensions for large model with mocked openai."""
        import openai
        openai.AsyncOpenAI = MagicMock()
        
        from awslabs.valkey_mcp_server.embeddings.providers import OpenAIEmbeddings
        provider = OpenAIEmbeddings(api_key="sk-test-key", model="text-embedding-3-large")
        
        assert provider.get_dimensions() == 3072

    @pytest.mark.asyncio
    async def test_get_provider_name_mocked(self):
        """Test provider name with mocked openai."""
        import openai
        openai.AsyncOpenAI = MagicMock()
        
        from awslabs.valkey_mcp_server.embeddings.providers import OpenAIEmbeddings
        provider = OpenAIEmbeddings(api_key="sk-test-key", model="text-embedding-3-small")
        
        name = provider.get_provider_name()
        assert "OpenAI" in name
        assert "text-embedding-3-small" in name
