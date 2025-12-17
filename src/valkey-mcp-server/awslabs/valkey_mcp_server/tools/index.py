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

"""Index operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from enum import Enum
from typing import Optional


class IndexType(Enum):
    """Valkey index type enumeration."""

    HASH = 'HASH'
    JSON = 'JSON'


class StructureType(Enum):
    """Valkey vector index structure type enumeration."""

    FLAT = 'FLAT'
    HNSW = 'HNSW'


class DistanceMetric(Enum):
    """Valkey distance metric enumeration."""

    L2 = 'L2'
    IP = 'IP'
    COSINE = 'COSINE'


async def create_vector_index(
    name: str,
    dimensions: int,
    index_type: IndexType = IndexType.HASH,
    prefix: Optional[list[str]] = None,
    embedding_field: str = 'embedding',
    embedding_field_alias: Optional[str] = None,
    structure_type: StructureType = StructureType.FLAT,
    distance_metric: DistanceMetric = DistanceMetric.L2,
    initial_size: Optional[int] = None,
    max_outgoing_edges: Optional[int] = None,
    ef_construction: Optional[int] = None,
    ef_runtime: Optional[int] = None,
):
    """Create a Valkey index intended for vector similarity search."""
    r = ValkeyConnectionManager.get_connection(decode_responses=True)
    create_args = ['FT.CREATE', name]

    if index_type == IndexType.JSON:
        create_args += ['JSON']
    elif index_type == IndexType.HASH:
        create_args += ['ON', 'HASH']
    else:
        raise ValueError(f'Unknown index type: {index_type}')

    if prefix is not None:
        create_args += ['PREFIX', str(len(prefix)), *prefix]

    create_args += ['SCHEMA', embedding_field]
    if embedding_field_alias is not None:
        create_args += ['AS', embedding_field_alias]

    sub_args = ['TYPE', 'FLOAT32', 'DIM', str(dimensions), 'DISTANCE_METRIC', distance_metric]
    if initial_size is not None:
        sub_args += ['INITIAL_CAP', str(initial_size)]
    if structure_type == StructureType.HNSW:
        if max_outgoing_edges is not None:
            sub_args += ['M', str(max_outgoing_edges)]
        if ef_construction is not None:
            sub_args += ['EF_CONSTRUCTION', str(ef_construction)]
        if ef_runtime is not None:
            sub_args += ['EF_RUNTIME', str(ef_runtime)]

    create_args += ['VECTOR', structure_type, str(len(sub_args)), *sub_args]

    return await r.execute_command(*create_args)
