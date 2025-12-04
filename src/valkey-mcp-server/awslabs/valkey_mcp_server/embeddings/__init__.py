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

"""Embeddings provider abstraction layer."""

import os
from .base import EmbeddingsProvider
from .providers import OllamaEmbeddings, BedrockEmbeddings


def create_embeddings_provider() -> EmbeddingsProvider:
    """Create an embeddings provider based on environment configuration.  This list of providers can be extended
    in the future to support additional embeddings providers such as OpenAI or Cohere etc.

    Configuration via environment variables:
    - EMBEDDINGS_PROVIDER: Provider type (ollama, bedrock)

    For Ollama provider:
    - OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    - OLLAMA_EMBEDDING_MODEL: Ollama model name (default: nomic-embed-text)

    For Titan / Bedrock provider:
    - AWS_REGION: AWS region for Bedrock (default: us-east-1)
    - BEDROCK_MODEL_ID: Bedrock model ID (default: amazon.titan-embed-text-v1)

    Returns:
        Configured embeddings provider instance

    Raises:
        ValueError: If provider type is unknown or required credentials are missing
    """
    provider_type = os.getenv('EMBEDDINGS_PROVIDER', 'ollama').lower()

    if provider_type == 'ollama':
        return OllamaEmbeddings(
            base_url=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
            model=os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
        )

    elif provider_type == 'bedrock':
        return BedrockEmbeddings(
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            model_id=os.getenv('BEDROCK_MODEL_ID', 'amazon.titan-embed-text-v1')
        )

    else:
        raise ValueError(
            f"Unknown embeddings provider: {provider_type}. "
            f"Supported providers: ollama, openai, bedrock, cohere, hash"
        )


__all__ = [
    'EmbeddingsProvider',
    'OllamaEmbeddings',
    'BedrockEmbeddings',
    'create_embeddings_provider'
]
