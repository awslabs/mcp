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

"""Unified search tool — semantic, text, hybrid, and find-similar (GLIDE)."""

from __future__ import annotations

import logging
import struct
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import (
    pack_embedding,
)
from awslabs.valkey_mcp_server.embeddings import get_provider, has_provider
from glide import ft
from glide_shared.commands.server_modules.ft_options.ft_search_options import (
    FtSearchLimit,
    FtSearchOptions,
)
from glide_shared.exceptions import RequestError
from typing import Any


logger = logging.getLogger(__name__)


def _decode_docs(results, return_fields=None, skip_field=None) -> list[dict[str, Any]]:
    """Decode GLIDE ft.search results into list of dicts.

    GLIDE returns: [count, {b'key': {b'field': b'value', ...}, ...}]
    """
    count = results[0]
    docs = []
    if count > 0 and len(results) > 1:
        for key, fields in results[1].items():
            str_key = key.decode() if isinstance(key, bytes) else key
            d: dict[str, Any] = {'id': str_key}
            for fk, fv in fields.items():
                str_fk = fk.decode() if isinstance(fk, bytes) else fk
                if str_fk == skip_field:
                    continue
                try:
                    str_fv = fv.decode() if isinstance(fv, bytes) else fv
                    d[str_fk] = str_fv
                except (UnicodeDecodeError, AttributeError):
                    continue
            if return_fields:
                d = {k: v for k, v in d.items() if k in return_fields or k == 'id'}
            docs.append(d)
    return docs


@mcp.tool()
async def search(
    index_name: str,
    query_text: str | None = None,
    document_id: str | None = None,
    vector_field: str = 'embedding',
    filter_expression: str | None = None,
    return_fields: list[str] | None = None,
    offset: int = 0,
    limit: int = 10,
    mode: str | None = None,
    hybrid_weight: float = 0.5,
) -> dict[str, Any]:
    """Search a Valkey Search index with auto-detected mode.

    Modes (auto-detected from parameters, or set explicitly via mode):

    - Text: query_text + no embedding provider (or mode="text")
    - Hybrid: mode="hybrid" or hybrid_weight explicitly set
    - Semantic: query_text + embedding provider configured (default)
    - Find-similar: document_id provided

    Args:
        index_name: Valkey Search index name
        query_text: Natural language or text query
        document_id: Key of existing document for find-similar
        vector_field: Vector field name (default: "embedding")
        filter_expression: Valkey filter (e.g., "@year:[2020 2024]")
        return_fields: Fields to return. None = all.
        offset: Pagination offset (default: 0)
        limit: Max results (default: 10)
        mode: Explicit mode override — "semantic", "text", "hybrid", "find_similar"
        hybrid_weight: Advisory — reserved for future weighted scoring. Currently
            controls mode auto-detection only (non-0.5 triggers hybrid mode).

    Returns:
        Dict with "status", "mode", and "results" list.
    """
    if not query_text and not document_id:
        return {'status': 'error', 'reason': "Provide 'query_text' or 'document_id'"}

    try:
        client = await get_client()

        if document_id:
            return await _find_similar(
                client,
                index_name,
                document_id,
                vector_field,
                filter_expression,
                return_fields,
                offset,
                limit,
            )

        embeddings_available = has_provider()
        if mode == 'text' or (not mode and not embeddings_available):
            return await _text(
                client,
                index_name,
                query_text,
                filter_expression,
                return_fields,
                offset,
                limit,
            )
        if mode == 'hybrid' or (embeddings_available and hybrid_weight != 0.5):
            return await _hybrid(
                client,
                index_name,
                query_text,
                vector_field,
                filter_expression,
                return_fields,
                offset,
                limit,
                hybrid_weight,
            )
        return await _semantic(
            client,
            index_name,
            query_text,
            vector_field,
            filter_expression,
            return_fields,
            offset,
            limit,
        )

    except RequestError as e:
        return {'status': 'error', 'reason': str(e)}
    except Exception as e:
        logger.exception('search failed: %s', e)
        return {'status': 'error', 'reason': str(e)}


def _build_text_query(query_text: str, filt: str | None) -> str:
    """Build a text query string, combining filter and query safely.

    Note: A bare '*' query may return "Invalid: query string syntax" on some
    Valkey Search versions. When a filter is present, we use the filter alone
    instead of '*' to avoid this. If Valkey Search fixes this in a future
    release, this workaround can be simplified.
    """
    if filt and query_text.strip() == '*':
        return filt
    if filt:
        return f'({filt}) {query_text}'
    return query_text


async def _semantic(client, index_name, query_text, vector_field, filt, ret, offset, limit):
    provider = get_provider()
    emb = await provider.generate_embedding(query_text)
    blob = pack_embedding(emb)
    f = filt or '*'
    query = f'{f}=>[KNN {limit} @{vector_field} $vector AS score]'
    results = await ft.search(
        client=client,
        index_name=index_name,
        query=query,
        options=FtSearchOptions(params={'vector': blob}, limit=FtSearchLimit(offset, limit)),
    )
    docs = _decode_docs(results, ret, skip_field=vector_field)
    return {'status': 'success', 'mode': 'semantic', 'results': docs, 'total': results[0]}


async def _text(client, index_name, query_text, filt, ret, offset, limit):
    qs = _build_text_query(query_text, filt)
    results = await ft.search(
        client=client,
        index_name=index_name,
        query=qs,
        options=FtSearchOptions(limit=FtSearchLimit(offset, limit)),
    )
    docs = _decode_docs(results, ret)
    return {'status': 'success', 'mode': 'text', 'results': docs, 'total': results[0]}


async def _find_similar(client, index_name, doc_id, vector_field, filt, ret, offset, limit):
    raw = await client.hget(doc_id, vector_field)
    if not raw:
        return {'status': 'error', 'reason': f"'{doc_id}' not found or no '{vector_field}' field"}
    if isinstance(raw, str):
        raw = raw.encode('latin-1')
    n = len(raw) // 4
    emb = list(struct.unpack(f'{n}f', raw))
    blob = pack_embedding(emb)
    f = filt or '*'
    query = f'{f}=>[KNN {limit + offset + 1} @{vector_field} $vector AS score]'
    results = await ft.search(
        client=client,
        index_name=index_name,
        query=query,
        options=FtSearchOptions(
            params={'vector': blob}, limit=FtSearchLimit(0, limit + offset + 1)
        ),
    )
    docs = _decode_docs(results, ret, skip_field=vector_field)
    docs = [d for d in docs if d.get('id') != doc_id][offset : offset + limit]
    return {'status': 'success', 'mode': 'find_similar', 'results': docs, 'total': len(docs)}


async def _hybrid(client, index_name, query_text, vector_field, filt, ret, offset, limit, weight):
    provider = get_provider()
    emb = await provider.generate_embedding(query_text)
    blob = pack_embedding(emb)
    tf = _build_text_query(query_text, filt)
    query = f'{tf}=>[KNN {limit} @{vector_field} $vector AS score]'
    results = await ft.search(
        client=client,
        index_name=index_name,
        query=query,
        options=FtSearchOptions(params={'vector': blob}, limit=FtSearchLimit(offset, limit)),
    )
    docs = _decode_docs(results, ret, skip_field=vector_field)
    return {
        'status': 'success',
        'mode': 'hybrid',
        'hybrid_weight': weight,
        'results': docs,
        'total': results[0],
    }
