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

from typing import List
import httpx
import hashlib
from .base import EmbeddingsProvider


class OllamaEmbeddings(EmbeddingsProvider):
    """Ollama embeddings provider (local, self-hosted).

    Example:
        provider = OllamaEmbeddings(
            base_url="http://localhost:11434",
            model="nomic-embed-text"
        )
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.base_url = base_url
        self.model = model
        self._dimensions = 768  # nomic-embed-text default

    async def generate_embedding(self, text: str) -> List[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["embedding"]

    def get_dimensions(self) -> int:
        return self._dimensions

    def get_provider_name(self) -> str:
        return f"Ollama ({self.model})"


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

    def __init__(self, region_name: str = "us-east-1", model_id: str = "amazon.titan-embed-text-v1"):
        import boto3
        self.client = boto3.client('bedrock-runtime', region_name=region_name)
        self.model_id = model_id
        self._dimensions = 1536  # Titan default

    async def generate_embedding(self, text: str) -> List[float]:
        import json
        import asyncio

        # Bedrock SDK is synchronous, run in executor
        def _invoke():
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({"inputText": text})
            )
            return json.loads(response['body'].read())['embedding']

        return await asyncio.get_event_loop().run_in_executor(None, _invoke)

    def get_dimensions(self) -> int:
        return self._dimensions

    def get_provider_name(self) -> str:
        return f"AWS Bedrock ({self.model_id})"


class OpenAIEmbeddings(EmbeddingsProvider):
    """OpenAI embeddings provider.

    Requires: pip install openai

    Example:
        provider = OpenAIEmbeddings(
            api_key="sk-...",
            model="text-embedding-3-small"
        )
        embedding = await provider.generate_embedding("Hello world")
    """

    def __init__(self, api_key: str | None, model: str = "text-embedding-3-small"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._dimensions = 1536 if "3-small" in model else 3072

    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    def get_dimensions(self) -> int:
        return self._dimensions

    def get_provider_name(self) -> str:
        return f"OpenAI ({self.model})"

