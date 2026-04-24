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

from __future__ import annotations

import hashlib
import httpx
from .base import EmbeddingsProvider
from typing import Any


class OllamaEmbeddings(EmbeddingsProvider):
    """Ollama embeddings provider (local, self-hosted).

    Example:
        provider = OllamaEmbeddings(
            base_url="http://localhost:11434",
            model="nomic-embed-text"
        )
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(
        self,
        base_url: str = 'http://localhost:11434',
        model: str = 'nomic-embed-text',
        dimensions: int = 768,
    ):
        """Initialize Ollama embeddings provider."""
        self.base_url = base_url if '://' in base_url else f'http://{base_url}'
        self.model = model
        self._dimensions = dimensions
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the httpx client."""
        await self._client.aclose()

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using Ollama."""
        response = await self._client.post(
            f'{self.base_url}/api/embeddings',
            json={'model': self.model, 'prompt': text},
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
            model_id="amazon.nova-2-multimodal-embeddings-v1:0"
        )
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(
        self,
        region_name: str = 'us-east-1',
        model_id: str = 'amazon.nova-2-multimodal-embeddings-v1:0',
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

        config = Config(
            region_name=region_name,
            retries={'max_attempts': max_attempts, 'mode': retry_mode},
            max_pool_connections=max_pool_connections,
        )

        session = boto3.Session()
        self.client = session.client('bedrock-runtime', config=config)
        self._session = session
        self._config = config
        self._credentials_validated = False

        self._model_id: str | None = None
        self._is_nova_model = False
        self.model_id = model_id  # Use property setter
        self.normalize = normalize
        self.dimensions = dimensions
        self.input_type = input_type

        # Set default dimensions based on model type
        if self._is_nova_model:
            self._dimensions = dimensions or 3072  # Nova default
        else:
            self._dimensions = dimensions or 1536  # Titan default

    @property
    def model_id(self) -> str:
        """Get the model ID."""
        if self._model_id is None:
            raise ValueError('Model ID not set')
        return self._model_id

    @model_id.setter
    def model_id(self, value: str) -> None:
        """Set the model ID and update cached Nova check."""
        import re

        self._model_id = value
        self._is_nova_model = bool(re.match(r'^\w+\.nova\b', value))

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using Bedrock."""
        import asyncio
        import json

        # Validate credentials on first use (deferred from __init__ to avoid
        # blocking the event loop at startup)
        if not self._credentials_validated:
            from botocore.exceptions import NoCredentialsError, PartialCredentialsError

            def _validate():
                sts_client = self._session.client('sts', config=self._config)
                sts_client.get_caller_identity()

            try:
                await asyncio.get_running_loop().run_in_executor(None, _validate)
                self._credentials_validated = True
            except (NoCredentialsError, PartialCredentialsError) as e:
                raise ValueError(
                    'AWS credentials not found or incomplete. Please configure AWS credentials '
                    f'using AWS CLI, environment variables, or IAM roles. Error: {e}'
                ) from e

        # boto3 is synchronous — run in executor to avoid blocking the event loop.
        def _invoke():
            # Check if this is a Nova model using cached result
            if self._is_nova_model:
                # Nova multimodal embeddings format
                body: dict[str, Any] = {
                    'taskType': 'SINGLE_EMBEDDING',
                    'singleEmbeddingParams': {
                        'embeddingPurpose': 'GENERIC_INDEX',
                        'text': {'truncationMode': 'END', 'value': text},
                    },
                }

                # Add optional parameters if specified
                if self.dimensions is not None:
                    body['singleEmbeddingParams']['embeddingDimension'] = self.dimensions

                response = self.client.invoke_model(modelId=self.model_id, body=json.dumps(body))
                result = json.loads(response['body'].read())
                return result['embeddings'][0]['embedding']
            else:
                # Titan embeddings format
                body: dict[str, Any] = {'inputText': text}

                # Add optional parameters if specified
                if self.normalize is not None:
                    body['normalize'] = self.normalize
                if self.dimensions is not None:
                    body['dimensions'] = self.dimensions
                if self.input_type is not None:
                    body['inputType'] = self.input_type

                response = self.client.invoke_model(modelId=self.model_id, body=json.dumps(body))
                return json.loads(response['body'].read())['embedding']

        # boto3 is synchronous — run in executor to avoid blocking the event loop.
        return await asyncio.get_running_loop().run_in_executor(None, _invoke)

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f'AWS Bedrock ({self.model_id})'


class HashEmbeddings(EmbeddingsProvider):
    """Hash-based embeddings provider for testing.

    Example:
        provider = HashEmbeddings(dimensions=128)
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(self, dimensions: int = 128):
        """Initialize dummy embeddings provider."""
        self._dimensions = dimensions

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate deterministic embedding using hash-seeded PRNG."""
        import random

        hash_hex = hashlib.sha256(text.encode('utf-8')).hexdigest()
        rng = random.Random(hash_hex)  # nosec B311 — not used for security, only test embeddings
        return [rng.uniform(-1, 1) for _ in range(self._dimensions)]

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f'Hash ({self._dimensions}d)'


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

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using OpenAI."""
        response = await self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f'OpenAI ({self.model})'
