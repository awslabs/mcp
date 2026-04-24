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

from __future__ import annotations

import os
from dotenv import load_dotenv


load_dotenv()

MCP_TRANSPORT = os.getenv('MCP_TRANSPORT', 'stdio')

VALKEY_CFG = {
    'host': os.getenv('VALKEY_HOST', '127.0.0.1'),
    'port': int(os.getenv('VALKEY_PORT', 6379)),
    'username': os.getenv('VALKEY_USERNAME', None),
    'password': os.getenv('VALKEY_PWD', ''),
    'ssl': os.getenv('VALKEY_USE_SSL', False) in ('true', '1', 't'),
    'ssl_ca_certs': os.getenv('VALKEY_SSL_CA_CERTS', None),
    'cluster_mode': os.getenv('VALKEY_CLUSTER_MODE', False) in ('true', '1', 't'),
    'vector_algorithm': os.getenv('VALKEY_VECTOR_ALGORITHM', 'HNSW').upper(),
    'vector_distance_metric': os.getenv('VALKEY_VECTOR_DISTANCE_METRIC', 'COSINE').upper(),
}


def _build_embedding_config() -> dict:
    """Build embedding configuration with conditional logic."""
    config = {
        'provider': os.getenv('EMBEDDING_PROVIDER', 'bedrock').lower(),
        'ollama_host': os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
        'ollama_embedding_model': os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text'),
        'bedrock_region': os.getenv('AWS_REGION', 'us-east-1'),
        'bedrock_model_id': os.getenv(
            'BEDROCK_MODEL_ID', 'amazon.nova-2-multimodal-embeddings-v1:0'
        ),
        'bedrock_max_attempts': int(os.getenv('BEDROCK_MAX_ATTEMPTS', '3')),
        'bedrock_max_pool_connections': int(os.getenv('BEDROCK_MAX_POOL_CONNECTIONS', '50')),
        'bedrock_retry_mode': os.getenv('BEDROCK_RETRY_MODE', 'adaptive'),
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'openai_model': os.getenv('OPENAI_MODEL', 'text-embedding-3-small'),
    }

    # Handle optional bedrock_normalize with conditional logic
    normalize_env = os.getenv('BEDROCK_NORMALIZE')
    config['bedrock_normalize'] = (
        normalize_env.lower() in ('true', '1', 't') if normalize_env else None
    )

    # Handle optional bedrock_dimensions with conditional logic
    dimensions_env = os.getenv('BEDROCK_DIMENSIONS')
    config['bedrock_dimensions'] = int(dimensions_env) if dimensions_env else None

    # Handle optional bedrock_input_type
    config['bedrock_input_type'] = os.getenv('BEDROCK_INPUT_TYPE')

    return config


EMBEDDING_CFG = _build_embedding_config()
