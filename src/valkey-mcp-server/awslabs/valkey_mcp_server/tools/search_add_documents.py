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

"""Document ingestion tool for Valkey Search (GLIDE)."""

from __future__ import annotations

import json
import logging
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import (
    index_exists,
    pack_embedding,
    readonly_guard,
)
from awslabs.valkey_mcp_server.context import Context
from awslabs.valkey_mcp_server.embeddings import get_provider as _get_provider
from glide import ft
from glide_shared.commands.server_modules.ft_options.ft_create_options import (
    DataType,
    DistanceMetricType,
    FtCreateOptions,
    VectorAlgorithm,
    VectorField,
    VectorFieldAttributesHnsw,
    VectorType,
)
from typing import Any


logger = logging.getLogger(__name__)


async def _auto_create_index(client, index_name, prefix, embedding_field, dimensions):
    """Create a minimal vector index for auto-creation."""
    schema: list = [
        VectorField(
            embedding_field,
            VectorAlgorithm.HNSW,
            VectorFieldAttributesHnsw(
                dimensions=dimensions,
                distance_metric=DistanceMetricType.COSINE,
                type=VectorType.FLOAT32,
            ),
        ),
    ]
    prefixes: list[str | bytes | bytearray | memoryview] = [prefix]
    await ft.create(
        client,
        index_name,
        schema,
        FtCreateOptions(data_type=DataType.HASH, prefixes=prefixes),
    )


@mcp.tool()
@readonly_guard
async def add_documents(
    index_name: str,
    documents: list[dict[str, Any]],
    id_field: str = 'id',
    prefix: str | None = None,
    embedding_field: str | None = None,
    text_fields: list[str] | None = None,
    embedding_dimensions: int | None = None,
) -> dict[str, Any]:
    """Add documents to a Valkey Search index with optional embedding generation.

    Stores documents as Valkey hashes. When embedding_field and text_fields are
    provided, generates vector embeddings via the configured provider (Bedrock,
    OpenAI, or Ollama), binary-packs them, and stores alongside document data.
    Auto-creates the index if it doesn't exist and embeddings are generated.

    Args:
        index_name: Name of the Valkey Search index
        documents: List of dicts, each must contain a field matching id_field
        id_field: Field to use as document ID (default: "id")
        prefix: Key prefix (e.g., "docs:"). Defaults to "{index_name}:"
        embedding_field: Vector field name. None = no embeddings generated.
        text_fields: Fields to concatenate for embedding. Required with embedding_field.
        embedding_dimensions: Vector dimensions. Auto-detected if omitted.

    Returns:
        Dict with "status", "added" count, "errors" count, and provider info.
    """
    if Context.readonly_mode():
        return {'status': 'error', 'added': 0, 'reason': 'Readonly mode'}

    if embedding_field and not text_fields:
        return {
            'status': 'error',
            'added': 0,
            'reason': "'text_fields' required when 'embedding_field' is set",
        }

    if prefix is None:
        prefix = f'{index_name}:'

    try:
        client = await get_client()
        added = 0
        errors = 0
        actual_dims = embedding_dimensions
        index_checked = False

        for doc in documents:
            doc_id = doc.get(id_field)
            if doc_id is None:
                logger.warning("Document missing '%s', skipping", id_field)
                errors += 1
                continue

            try:
                mapping: dict[
                    str | bytes | bytearray | memoryview, str | bytes | bytearray | memoryview
                ] = {}
                for k, v in doc.items():
                    if k == id_field:
                        continue
                    mapping[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)

                if embedding_field and text_fields:
                    text = ' '.join(str(doc.get(f, '')) for f in text_fields)
                    provider = _get_provider()
                    embedding = await provider.generate_embedding(text)

                    if actual_dims is None:
                        actual_dims = len(embedding)
                    if not index_checked:
                        if not await index_exists(client, index_name):
                            await _auto_create_index(
                                client, index_name, prefix, embedding_field, actual_dims
                            )
                        index_checked = True

                    mapping[embedding_field] = pack_embedding(embedding)

                await client.hset(f'{prefix}{doc_id}', mapping)
                added += 1
            except Exception as e:
                logger.warning('Failed to process document %s: %s', doc_id, e)
                errors += 1

        status = 'success' if added > 0 else 'error'
        result: dict[str, Any] = {
            'status': status,
            'added': added,
            'errors': errors,
            'index_name': index_name,
        }
        if embedding_field:
            result['embedding_dimensions'] = actual_dims
            result['embeddings_provider'] = _get_provider().get_provider_name()
        return result

    except Exception as e:
        return {'status': 'error', 'added': 0, 'reason': str(e)}
