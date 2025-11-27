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
from .providers import (
    OllamaEmbeddings,
    OpenAIEmbeddings,
    BedrockEmbeddings,
    CohereEmbeddings,
    HashEmbeddings
)


def create_embeddings_provider() -> EmbeddingsProvider:
    """Create an embeddings provider based on environment configuration.

    Configuration via environment variables:
    - EMBEDDINGS_PROVIDER: Provider type (ollama, openai, bedrock, cohere, hash)
    - OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    - OLLAMA_EMBEDDING_MODEL: Ollama model name (default: nomic-embed-text)
    - OPENAI_API_KEY: OpenAI API key
    - OPENAI_EMBEDDING_MODEL: OpenAI model name (default: text-embedding-3-small)
    - AWS_REGION: AWS region for Bedrock (default: us-east-1)
    - BEDROCK_MODEL_ID: Bedrock model ID (default: amazon.titan-embed-text-v1)
    - COHERE_API_KEY: Cohere API key
    - COHERE_EMBEDDING_MODEL: Cohere model name (default: embed-english-v3.0)
    - HASH_EMBEDDING_DIMENSIONS: Dimensions for hash embeddings (default: 384)

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

    elif provider_type == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
        return OpenAIEmbeddings(
            api_key=api_key,
            model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
        )

    elif provider_type == 'bedrock':
        return BedrockEmbeddings(
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            model_id=os.getenv('BEDROCK_MODEL_ID', 'amazon.titan-embed-text-v1')
        )

    elif provider_type == 'cohere':
        api_key = os.getenv('COHERE_API_KEY')
        if not api_key:
            raise ValueError("COHERE_API_KEY environment variable is required for Cohere provider")
        return CohereEmbeddings(
            api_key=api_key,
            model=os.getenv('COHERE_EMBEDDING_MODEL', 'embed-english-v3.0')
        )

    elif provider_type == 'hash':
        dimensions = int(os.getenv('HASH_EMBEDDING_DIMENSIONS', '384'))
        return HashEmbeddings(dimensions=dimensions)

    else:
        raise ValueError(
            f"Unknown embeddings provider: {provider_type}. "
            f"Supported providers: ollama, openai, bedrock, cohere, hash"
        )


__all__ = [
    'EmbeddingsProvider',
    'OllamaEmbeddings',
    'OpenAIEmbeddings',
    'BedrockEmbeddings',
    'CohereEmbeddings',
    'HashEmbeddings',
    'create_embeddings_provider'
]
