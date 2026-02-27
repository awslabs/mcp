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

"""Tests for Ollama and OpenAI embeddings providers."""

import pytest
from awslabs.valkey_mcp_server.embeddings.providers import OllamaEmbeddings, OpenAIEmbeddings
from unittest.mock import AsyncMock, MagicMock, patch


class TestOllamaEmbeddingsUnit:
    """Unit tests for Ollama embeddings provider."""

    @pytest.mark.asyncio
    async def test_ollama_connection_error(self):
        """Test Ollama connection error handling."""
        provider = OllamaEmbeddings(base_url='http://invalid-host:11434')

        with pytest.raises(Exception):  # Should raise connection error
            await provider.generate_embedding('test')

    @pytest.mark.asyncio
    async def test_ollama_http_error(self):
        """Test Ollama HTTP error handling."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception('HTTP Error')
            mock_post.return_value = mock_response

            provider = OllamaEmbeddings()

            with pytest.raises(Exception):
                await provider.generate_embedding('test')

    @pytest.mark.asyncio
    async def test_ollama_successful_embedding(self):
        """Test successful Ollama embedding generation."""
        mock_embedding = [0.1, 0.2, 0.3]

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {'embedding': mock_embedding}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            provider = OllamaEmbeddings()
            result = await provider.generate_embedding('test')

            assert result == mock_embedding


class TestOpenAIEmbeddingsUnit:
    """Unit tests for OpenAI embeddings provider."""

    @pytest.mark.asyncio
    async def test_openai_connection_error(self):
        """Test OpenAI connection error handling."""
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.embeddings.create = AsyncMock(side_effect=Exception('Connection error'))
            mock_openai.return_value = mock_client

            provider = OpenAIEmbeddings(api_key='test-key')

            with pytest.raises(Exception):
                await provider.generate_embedding('test')

    @pytest.mark.asyncio
    async def test_openai_successful_embedding(self):
        """Test successful OpenAI embedding generation."""
        mock_embedding = [0.1, 0.2, 0.3]

        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=mock_embedding)]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            provider = OpenAIEmbeddings(api_key='test-key')
            result = await provider.generate_embedding('test')

            assert result == mock_embedding
            mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_large_model_dimensions(self):
        """Test OpenAI large model dimensions."""
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = MagicMock()

            provider = OpenAIEmbeddings(api_key='test-key', model='text-embedding-3-large')
            assert provider.get_dimensions() == 3072

            provider = OpenAIEmbeddings(api_key='test-key', model='text-embedding-3-small')
            assert provider.get_dimensions() == 1536
