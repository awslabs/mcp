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
import pytest
import sys
from tests import acquire_bedrock_embeddings
from unittest.mock import MagicMock


class TestBedrockEmbeddings:
    """Integration tests for Bedrock embeddings provider."""

    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test basic embedding generation with real AWS Bedrock."""
        provider = await acquire_bedrock_embeddings(
            region_name='us-east-1', model_id='amazon.titan-embed-text-v1'
        )

        assert provider.get_dimensions() == 1536

        text = 'Hello world'
        embedding = await provider.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

        second_embedding = await provider.generate_embedding(text)
        assert embedding == second_embedding

    @pytest.mark.asyncio
    async def test_titan_v2_with_dimensions(self):
        """Test Titan v2 with custom dimensions."""
        provider = await acquire_bedrock_embeddings(
            region_name='us-east-1', model_id='amazon.titan-embed-text-v2:0', dimensions=256
        )

        assert provider.get_dimensions() == 256

        embedding = await provider.generate_embedding('Test text')

        assert isinstance(embedding, list)
        assert len(embedding) == 256
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_titan_v2_with_normalize(self):
        """Test Titan v2 with normalize parameter."""
        provider = await acquire_bedrock_embeddings(
            region_name='us-east-1', model_id='amazon.titan-embed-text-v2:0', normalize=True
        )

        embedding = await provider.generate_embedding('Test text')

        assert isinstance(embedding, list)
        assert len(embedding) == 1024  # v2 default

        # Check normalization (L2 norm should be ~1.0)
        import math

        norm = math.sqrt(sum(x * x for x in embedding))
        assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_titan_v2_with_all_parameters(self):
        """Test Titan v2 with all parameters combined."""
        provider = await acquire_bedrock_embeddings(
            region_name='us-east-1',
            model_id='amazon.titan-embed-text-v2:0',
            dimensions=512,
            normalize=True,
        )

        assert provider.get_dimensions() == 512

        embedding = await provider.generate_embedding('Combined parameters test')

        assert isinstance(embedding, list)
        assert len(embedding) == 512
        assert all(isinstance(x, float) for x in embedding)

        # Verify normalization
        import math

        norm = math.sqrt(sum(x * x for x in embedding))
        assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_nova_2_multimodal_embeddings(self):
        """Test Amazon Nova 2 multimodal embeddings model."""
        try:
            provider = await acquire_bedrock_embeddings(
                region_name='us-east-1', model_id='amazon.nova-2-multimodal-embeddings-v1:0'
            )

            # Nova 2 default dimensions are 3072
            assert provider.get_dimensions() == 3072

            text = 'Test text for Nova 2 multimodal embeddings'
            embedding = await provider.generate_embedding(text)

            assert isinstance(embedding, list)
            assert len(embedding) == 3072
            assert all(isinstance(x, float) for x in embedding)

            # Test consistency
            second_embedding = await provider.generate_embedding(text)
            assert embedding == second_embedding
        except Exception as e:
            if 'invalid' in str(e).lower() or 'not found' in str(e).lower():
                pytest.skip(f'Nova 2 model not available: {e}')
            raise

    @pytest.mark.asyncio
    async def test_nova_2_multimodal_with_custom_dimensions(self):
        """Test Nova 2 multimodal embeddings with custom dimensions."""
        try:
            provider = await acquire_bedrock_embeddings(
                region_name='us-east-1',
                model_id='amazon.nova-2-multimodal-embeddings-v1:0',
                dimensions=1024,
            )

            assert provider.get_dimensions() == 1024

            embedding = await provider.generate_embedding('Test with 1024 dimensions')

            assert isinstance(embedding, list)
            assert len(embedding) == 1024
            assert all(isinstance(x, float) for x in embedding)
        except Exception as e:
            if 'invalid' in str(e).lower() or 'not found' in str(e).lower():
                pytest.skip(f'Nova 2 model not available: {e}')
            raise


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

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response

        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {}

        mock_session = MagicMock()

        def client_side_effect(service, **kwargs):
            if service == 'bedrock-runtime':
                return mock_bedrock_client
            elif service == 'sts':
                return mock_sts_client
            return MagicMock()

        mock_session.client.side_effect = client_side_effect

        import boto3

        boto3.Session = MagicMock(return_value=mock_session)

        provider = await acquire_bedrock_embeddings()

        embedding = await provider.generate_embedding('test')

        assert embedding == mock_embedding
        mock_bedrock_client.invoke_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dimensions_mocked(self):
        """Test dimensions with mocked boto3."""
        import boto3

        boto3.client = MagicMock()

        provider = await acquire_bedrock_embeddings()

        assert provider.get_dimensions() == 1536

    @pytest.mark.asyncio
    async def test_get_provider_name_mocked(self):
        """Test provider name with mocked boto3."""
        import boto3

        boto3.client = MagicMock()

        provider = await acquire_bedrock_embeddings(model_id='amazon.titan-embed-text-v1')

        name = provider.get_provider_name()
        assert 'Bedrock' in name
        assert 'amazon.titan-embed-text-v1' in name

    @pytest.mark.asyncio
    async def test_credential_validation_failure(self):
        """Test that BedrockEmbeddings raises ValueError when credentials are invalid."""
        from botocore.exceptions import NoCredentialsError

        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.side_effect = NoCredentialsError()

        mock_bedrock_client = MagicMock()

        import boto3

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service, **kwargs: (
            mock_sts_client if service == 'sts' else mock_bedrock_client
        )
        boto3.Session = MagicMock(return_value=mock_session)

        from awslabs.valkey_mcp_server.embeddings.providers import BedrockEmbeddings

        with pytest.raises(ValueError, match='AWS credentials not found'):
            BedrockEmbeddings()

    @pytest.mark.asyncio
    async def test_nova_2_multimodal_mocked(self, mocker):
        """Test Nova 2 multimodal embeddings with mocked boto3."""
        mock_embedding = [0.1] * 3072  # Nova default dimensions
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(
            {'embeddings': [{'embedding': mock_embedding}]}
        ).encode()
        mock_response = {'body': mock_body}

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response

        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {}

        mock_session = MagicMock()

        def client_side_effect(service, **kwargs):
            if service == 'bedrock-runtime':
                return mock_bedrock_client
            elif service == 'sts':
                return mock_sts_client
            return MagicMock()

        mock_session.client.side_effect = client_side_effect

        import boto3

        boto3.Session = MagicMock(return_value=mock_session)

        provider = await acquire_bedrock_embeddings(
            model_id='amazon.nova-2-multimodal-embeddings-v1:0'
        )

        embedding = await provider.generate_embedding('test')

        assert embedding == mock_embedding
        assert len(embedding) == 3072
        mock_bedrock_client.invoke_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_id_property_error(self, mocker):
        """Test model_id property getter when not set."""
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {}

        mock_session = MagicMock()
        mock_session.client.return_value = mock_sts_client

        import boto3

        boto3.Session = MagicMock(return_value=mock_session)

        from awslabs.valkey_mcp_server.embeddings.providers import BedrockEmbeddings

        provider = BedrockEmbeddings.__new__(BedrockEmbeddings)
        provider._model_id = None

        with pytest.raises(ValueError, match='Model ID not set'):
            _ = provider.model_id

    @pytest.mark.asyncio
    async def test_titan_model_mocked(self, mocker):
        """Test Titan model path with mocked boto3."""
        mock_embedding = [0.1] * 1536  # Titan default dimensions
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({'embedding': mock_embedding}).encode()
        mock_response = {'body': mock_body}

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response

        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {}

        mock_session = MagicMock()

        def client_side_effect(service, **kwargs):
            if service == 'bedrock-runtime':
                return mock_bedrock_client
            elif service == 'sts':
                return mock_sts_client
            return MagicMock()

        mock_session.client.side_effect = client_side_effect

        import boto3

        boto3.Session = MagicMock(return_value=mock_session)

        provider = await acquire_bedrock_embeddings(model_id='amazon.titan-embed-text-v1')

        embedding = await provider.generate_embedding('test')

        assert embedding == mock_embedding
        assert len(embedding) == 1536
        mock_bedrock_client.invoke_model.assert_called_once()
