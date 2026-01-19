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
from .providers import OllamaEmbeddings, BedrockEmbeddings, OpenAIEmbeddings, HashEmbeddings
from awslabs.valkey_mcp_server.common.config import EMBEDDING_CFG


def create_embeddings_provider() -> EmbeddingsProvider:
    """Create an embeddings provider based on environment configuration.  This list of providers can be extended
    in the future to support additional embeddings providers such as OpenAI or Cohere etc.

    Configuration via environment variables:
    - EMBEDDINGS_PROVIDER: Provider type (ollama, bedrock, openai)

    For Ollama provider:
    - OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    - OLLAMA_EMBEDDING_MODEL: Ollama model name (default: nomic-embed-text)

    For Bedrock provider:
    - AWS_REGION: AWS region for Bedrock (default: us-east-1)
    - BEDROCK_MODEL_ID: Bedrock model ID (default: amazon.nova-2-multimodal-embeddings-v1:0)

    For OpenAI provider:
    - OPENAI_API_KEY: OpenAI API key (required)
    - OPENAI_MODEL: OpenAI model name (default: text-embedding-3-small)

    Returns:
        Configured embeddings provider instance

    Raises:
        ValueError: If provider type is unknown or required credentials are missing
    """
    provider_type = EMBEDDING_CFG.get('provider', 'bedrock').lower()

    if provider_type == 'ollama':
        return OllamaEmbeddings(
            base_url=EMBEDDING_CFG.get('ollama_host', 'http://localhost:11434'),
            model=EMBEDDING_CFG.get('ollama_embedding_model', 'nomic-embed-text'),
        )

    elif provider_type == 'bedrock':
        return BedrockEmbeddings(
            region_name=EMBEDDING_CFG.get('bedrock_region', 'us-east-1'),
            model_id=EMBEDDING_CFG.get(
                'bedrock_model_id', 'amazon.nova-2-multimodal-embeddings-v1:0'
            ),
            normalize=EMBEDDING_CFG.get('bedrock_normalize'),
            dimensions=EMBEDDING_CFG.get('bedrock_dimensions'),
            input_type=EMBEDDING_CFG.get('bedrock_input_type'),
            max_attempts=EMBEDDING_CFG.get('bedrock_max_attempts', 3),
            max_pool_connections=EMBEDDING_CFG.get('bedrock_max_pool_connections', 50),
            retry_mode=EMBEDDING_CFG.get('bedrock_retry_mode', 'adaptive'),
        )

    elif provider_type == 'openai':
        api_key = EMBEDDING_CFG.get('openai_api_key')
        if not api_key:
            raise ValueError('OPENAI_API_KEY environment variable is required for OpenAI provider')

        return OpenAIEmbeddings(
            api_key=api_key, model=EMBEDDING_CFG.get('openai_model', 'text-embedding-3-small')
        )

    elif provider_type == 'hash':
        return HashEmbeddings()

    else:
        raise ValueError(
            f'Unknown embeddings provider: {provider_type}. '
            f'Supported providers: ollama, bedrock, openai'
        )


__all__ = [
    'EmbeddingsProvider',
    'OllamaEmbeddings',
    'BedrockEmbeddings',
    'OpenAIEmbeddings',
    'HashEmbeddings',
    'create_embeddings_provider',
]
