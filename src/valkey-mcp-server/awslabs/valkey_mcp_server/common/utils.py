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

import struct
from typing import Any


def pack_embedding(embedding: list[float]) -> bytes:
    """Pack embedding vector to bytes for Valkey storage."""
    return struct.pack(f'{len(embedding)}f', *embedding)


def decode_value(val: Any) -> Any:
    """Recursively decode bytes in a Valkey response."""
    if isinstance(val, bytes):
        try:
            return val.decode()
        except UnicodeDecodeError:
            return repr(val)
    if isinstance(val, list):
        return [decode_value(v) for v in val]
    if isinstance(val, dict):
        return {decode_value(k): decode_value(v) for k, v in val.items()}
    if isinstance(val, set):
        return [decode_value(v) for v in val]
    return val


async def index_exists(client: Any, index_name: str) -> bool:
    """Check if a Valkey Search index exists (safe — no crash on missing index)."""
    from glide import ft

    existing = await ft.list(client)
    names = {i.decode() if isinstance(i, bytes) else str(i) for i in (existing or [])}
    return index_name in names
