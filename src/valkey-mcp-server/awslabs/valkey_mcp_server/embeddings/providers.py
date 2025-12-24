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

"""Concrete implementations of embeddings providers."""

import hashlib
import httpx
from .base import EmbeddingsProvider
from typing import List


class OllamaEmbeddings(EmbeddingsProvider):
    """Ollama embeddings provider (local, self-hosted).

    Example:
        provider = OllamaEmbeddings(
            base_url="http://localhost:11434",
            model="nomic-embed-text"
        )
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(self, base_url: str = 'http://localhost:11434', model: str = 'nomic-embed-text'):
        """Initialize Ollama embeddings provider."""
        self.base_url = base_url
        self.model = model
        self._dimensions = 768  # nomic-embed-text default

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/api/embeddings',
                json={'model': self.model, 'prompt': text},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()['embedding']

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f'Ollama ({self.model})'


class BedrockEmbeddings(EmbeddingsProvider):
    """AWS Bedrock embeddings provider.

    Requires: pip install boto3

    Example:
        provider = BedrockEmbeddings(
            region_name="us-east-1",
            model_id="amazon.titan-embed-text-v1"
        )
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(
        self,
        region_name: str = 'us-east-1',
        model_id: str = 'amazon.titan-embed-text-v1',
        normalize: bool | None = None,
        dimensions: int | None = None,
        input_type: str | None = None,
        max_attempts: int = 3,
        max_pool_connections: int = 50,
        retry_mode: str = 'adaptive',
    ):
        """Initialize Bedrock embeddings provider."""
        import boto3
        from botocore.config import Config
        from botocore.exceptions import NoCredentialsError, PartialCredentialsError

        config = Config(
            region_name=region_name,
            retries={'max_attempts': max_attempts, 'mode': retry_mode},
            max_pool_connections=max_pool_connections,
        )

        session = boto3.Session()
        self.client = session.client('bedrock-runtime', config=config)

        # Validate credentials are available
        try:
            sts_client = session.client('sts', config=config)
            sts_client.get_caller_identity()
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise ValueError(
                f'AWS credentials not found or incomplete. Please configure AWS credentials using '
                f'AWS CLI, environment variables, or IAM roles. Error: {e}'
            )

        self.model_id = model_id
        self.normalize = normalize
        self.dimensions = dimensions
        self.input_type = input_type
        self._dimensions = dimensions or 1536  # Titan default

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Bedrock."""
        import asyncio
        import json

        # Bedrock SDK is synchronous, run in executor
        def _invoke():
            body: dict[str, str | bool | int] = {'inputText': text}

            # Add optional parameters if specified
            if self.normalize is not None:
                body['normalize'] = self.normalize
            if self.dimensions is not None:
                body['dimensions'] = self.dimensions
            if self.input_type is not None:
                body['inputType'] = self.input_type

            response = self.client.invoke_model(modelId=self.model_id, body=json.dumps(body))
            return json.loads(response['body'].read())['embedding']

        return await asyncio.get_event_loop().run_in_executor(None, _invoke)

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f'AWS Bedrock ({self.model_id})'


class HashEmbeddings(EmbeddingsProvider):
    """Dummy embeddings provider for testing using basic hash algorithm.

    Example:
        provider = DummyEmbeddings(dimensions=128)
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(self, dimensions: int = 128):
        """Initialize dummy embeddings provider."""
        self._dimensions = dimensions

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate deterministic embedding using hash."""
        # Create a hash of the text
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()

        # Convert hash bytes to floats and normalize to [-1, 1] range
        embedding = []
        for i in range(self._dimensions):
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Normalize to [-1, 1] range
            normalized_val = (byte_val / 255.0) * 2.0 - 1.0
            embedding.append(normalized_val)

        return embedding

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f'Dummy ({self._dimensions}d)'


class OpenAIEmbeddings(EmbeddingsProvider):
    """OpenAI embeddings provider.

    Requires: pip install openai

    Example:
        provider = OpenAIEmbeddings(
            api_key="<your-api-key>",  # pragma: allowlist secret
            model="text-embedding-3-small"
        )
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(
        self, api_key: str | None, model: str = 'text-embedding-3-small'
    ):  # pragma: allowlist secret
        """Initialize OpenAI embeddings provider."""
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._dimensions = 1536 if '3-small' in model else 3072

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        response = await self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f'OpenAI ({self.model})'
