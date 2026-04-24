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


def readonly_guard(fn):
    """Decorator that returns an error dict if readonly mode is active."""
    from functools import wraps

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        from awslabs.valkey_mcp_server.context import Context

        if Context.readonly_mode():
            return {'status': 'error', 'reason': 'Readonly mode'}
        return await fn(*args, **kwargs)

    return wrapper


def tool_errors(fn):
    """Decorator that catches Valkey/GLIDE errors and returns structured error dicts.

    Only catches RequestError (Valkey operational errors). Programming errors
    (TypeError, AttributeError, etc.) propagate for debugging.
    """
    from functools import wraps
    from glide_shared.exceptions import RequestError

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except RequestError as e:
            return {'status': 'error', 'reason': str(e)}

    return wrapper
