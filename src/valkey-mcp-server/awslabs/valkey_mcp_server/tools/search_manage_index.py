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

"""Index management tool for Valkey Search (GLIDE)."""

import logging
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import index_exists
from awslabs.valkey_mcp_server.context import Context
from glide import ft
from glide_shared.commands.server_modules.ft_options.ft_create_options import (
    DataType,
    DistanceMetricType,
    FtCreateOptions,
    NumericField,
    TagField,
    TextField,
    VectorAlgorithm,
    VectorField,
    VectorFieldAttributesFlat,
    VectorFieldAttributesHnsw,
    VectorType,
)
from glide_shared.exceptions import RequestError
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

VALID_FIELD_TYPES = {'TEXT', 'NUMERIC', 'TAG', 'GEO', 'VECTOR'}
VALID_DISTANCE_METRICS = {'COSINE', 'L2', 'IP'}
VALID_STRUCTURE_TYPES = {'FLAT', 'HNSW'}
VALID_INDEX_TYPES = {'HASH', 'JSON'}

_DISTANCE_MAP = {
    'COSINE': DistanceMetricType.COSINE,
    'L2': DistanceMetricType.L2,
    'IP': DistanceMetricType.IP,
}

_ALGORITHM_MAP = {
    'FLAT': VectorAlgorithm.FLAT,
    'HNSW': VectorAlgorithm.HNSW,
}

_DATA_TYPE_MAP = {
    'HASH': DataType.HASH,
    'JSON': DataType.JSON,
}


def _build_field(field: Dict[str, Any], structure_type: str, distance_metric: str):
    """Translate a schema field dict into a GLIDE Field object."""
    name = field['name']
    ftype = field.get('type', 'TEXT').upper()
    if ftype not in VALID_FIELD_TYPES:
        raise ValueError(
            f"Invalid field type '{ftype}' for '{name}'. Must be: {VALID_FIELD_TYPES}"
        )

    if ftype == 'VECTOR':
        dims = field.get('dimensions')
        if not dims:
            raise ValueError(f"VECTOR field '{name}' requires 'dimensions'")
        st = field.get('structure_type', structure_type).upper()
        dm = field.get('distance_metric', distance_metric).upper()
        algo = _ALGORITHM_MAP[st]
        metric = _DISTANCE_MAP[dm]
        if st == 'HNSW':
            attrs = VectorFieldAttributesHnsw(
                dimensions=dims,
                distance_metric=metric,
                type=VectorType.FLOAT32,
            )
        else:
            attrs = VectorFieldAttributesFlat(
                dimensions=dims,
                distance_metric=metric,
                type=VectorType.FLOAT32,
            )
        return VectorField(name, algo, attrs)
    if ftype == 'TAG':
        return TagField(name)
    if ftype == 'NUMERIC':
        return NumericField(name)
    return TextField(name)


@mcp.tool()
async def manage_index(
    action: str,
    index_name: Optional[str] = None,
    schema: Optional[List[Dict[str, Any]]] = None,
    prefix: Optional[List[str]] = None,
    index_type: str = 'HASH',
    structure_type: str = 'HNSW',
    distance_metric: str = 'COSINE',
) -> Dict[str, Any]:
    """Manage Valkey Search indices: create, drop, inspect, or list.

    Handles FT.CREATE, FT.DROPINDEX, FT.INFO, and FT._LIST through structured
    input, eliminating the need to construct raw Valkey search syntax.

    Args:
        action: "create", "drop", "info", or "list"
        index_name: Index name (required for create, drop, info)
        schema: Field definitions for create. Each field dict needs "name" and
            "type" (TEXT, NUMERIC, TAG, GEO, VECTOR). VECTOR fields also need
            "dimensions". Example:
            [{"name": "title", "type": "TEXT"},
             {"name": "embedding", "type": "VECTOR", "dimensions": 768},
             {"name": "year", "type": "NUMERIC"},
             {"name": "category", "type": "TAG"}]
        prefix: Key prefix filter (e.g., ["docs:"])
        index_type: "HASH" (default) or "JSON"
        structure_type: Vector algorithm — "HNSW" (default) or "FLAT"
        distance_metric: Vector metric — "COSINE" (default), "L2", or "IP"

    Returns:
        Dict with "status" ("success"/"error") and action-specific data.
    """
    action = action.lower()
    try:
        client = await get_client()

        if action == 'list':
            raw = await ft.list(client)
            names = [i.decode() if isinstance(i, bytes) else str(i) for i in (raw or [])]
            return {'status': 'success', 'indices': names}

        if not index_name:
            return {'status': 'error', 'reason': f"'index_name' required for '{action}'"}

        # Pre-validate: avoid GLIDE crashes on error responses
        index_found = await index_exists(client, index_name)

        if action == 'info':
            if not index_found:
                return {'status': 'error', 'reason': f"Index '{index_name}' does not exist"}
            info = await ft.info(client, index_name)
            return {'status': 'success', 'index_name': index_name, 'info': info}

        if action == 'drop':
            if Context.readonly_mode():
                return {'status': 'error', 'reason': 'Readonly mode'}
            if not index_found:
                return {'status': 'error', 'reason': f"Index '{index_name}' does not exist"}
            await ft.dropindex(client, index_name)
            return {'status': 'success', 'index_name': index_name, 'dropped': True}

        if action == 'create':
            if Context.readonly_mode():
                return {'status': 'error', 'reason': 'Readonly mode'}
            if not schema:
                return {'status': 'error', 'reason': "'schema' required for create"}
            if index_found:
                return {'status': 'error', 'reason': f"Index '{index_name}' already exists"}

            it = index_type.upper()
            st = structure_type.upper()
            dm = distance_metric.upper()
            for val, name, valid in [
                (it, 'index_type', VALID_INDEX_TYPES),
                (st, 'structure_type', VALID_STRUCTURE_TYPES),
                (dm, 'distance_metric', VALID_DISTANCE_METRICS),
            ]:
                if val not in valid:
                    return {
                        'status': 'error',
                        'reason': f"Invalid {name} '{val}'. Must be: {valid}",
                    }

            fields = []
            for f in schema:
                if 'name' not in f:
                    return {'status': 'error', 'reason': "Each field needs a 'name' key"}
                fields.append(_build_field(f, st, dm))

            options = FtCreateOptions(data_type=_DATA_TYPE_MAP[it])
            if prefix:
                typed_prefixes: list[str | bytes | bytearray | memoryview] = list(prefix)
                options = FtCreateOptions(data_type=_DATA_TYPE_MAP[it], prefixes=typed_prefixes)

            await ft.create(client, index_name, fields, options)
            return {'status': 'success', 'index_name': index_name, 'created': True}

        return {
            'status': 'error',
            'reason': f"Unknown action '{action}'. Use: create, drop, info, list",
        }

    except RequestError as e:
        return {'status': 'error', 'reason': str(e)}
    except Exception as e:
        logger.exception('manage_index failed: %s', e)
        return {'status': 'error', 'reason': str(e)}
