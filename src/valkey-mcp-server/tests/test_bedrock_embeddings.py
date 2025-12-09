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

"""Tests for Bedrock/Titan embeddings provider."""
import json
import sys
import pytest
from unittest.mock import MagicMock

@pytest.mark.integration
@pytest.mark.manual
class TestBedrockEmbeddings:
    """Integration tests for Bedrock embeddings provider."""

    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test basic embedding generation with real AWS Bedrock."""
        from awslabs.valkey_mcp_server.embeddings.providers import BedrockEmbeddings
        
        provider = BedrockEmbeddings(
            region_name="us-east-1",
            model_id="amazon.titan-embed-text-v1"
        )

        assert provider.get_dimensions() == 1536

        text = "Hello world"
        embedding = await provider.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

        second_embedding = await provider.generate_embedding(text)
        assert embedding == second_embedding


class TestBedrockEmbeddingsMocked:
    """Unit tests for Bedrock embeddings with mocked boto3."""

    @pytest.fixture(autouse=True)
    def mock_boto3(self, mocker):
        """Mock boto3 module before importing BedrockEmbeddings."""
        if 'boto3' not in sys.modules:
            mock_boto3_module = MagicMock()
            sys.modules['boto3'] = mock_boto3_module
            self._cleanup_boto3 = True
        else:
            self._cleanup_boto3 = False
        
        yield
        
        if self._cleanup_boto3 and 'boto3' in sys.modules:
            del sys.modules['boto3']

    @pytest.mark.asyncio
    async def test_generate_embedding_mocked(self, mocker):
        """Test embedding generation with mocked boto3."""
        mock_embedding = [0.1] * 1536
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({'embedding': mock_embedding}).encode()
        mock_response = {'body': mock_body}
        
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = mock_response
        
        import boto3
        boto3.client = MagicMock(return_value=mock_client)
        
        from awslabs.valkey_mcp_server.embeddings.providers import BedrockEmbeddings
        provider = BedrockEmbeddings()
        
        embedding = await provider.generate_embedding("test")
        
        assert embedding == mock_embedding
        mock_client.invoke_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dimensions_mocked(self):
        """Test dimensions with mocked boto3."""
        import boto3
        boto3.client = MagicMock()
        
        from awslabs.valkey_mcp_server.embeddings.providers import BedrockEmbeddings
        provider = BedrockEmbeddings()
        
        assert provider.get_dimensions() == 1536

    @pytest.mark.asyncio
    async def test_get_provider_name_mocked(self):
        """Test provider name with mocked boto3."""
        import boto3
        boto3.client = MagicMock()
        
        from awslabs.valkey_mcp_server.embeddings.providers import BedrockEmbeddings
        provider = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1")
        
        name = provider.get_provider_name()
        assert "Bedrock" in name
        assert "amazon.titan-embed-text-v1" in name
