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

"""Audit logging for MCP tool invocations, auth events, and security errors."""

import functools
import inspect
from loguru import logger


# Parameter names that must never appear in logs.
_SENSITIVE_PARAMS = frozenset(
    {
        'sessionCookie',
        'cookie',
        'bearer_token',
        'token',
        'secret',
        'password',
        'credential',
        'content',
        'clientSecretArn',
        'startUrl',
    }
)


def _safe_args(func, args, kwargs):
    """Extract non-sensitive keyword arguments for logging."""
    sig = inspect.signature(func)
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    return {
        k: v
        for k, v in bound.arguments.items()
        if k not in _SENSITIVE_PARAMS and k not in ('self', 'ctx') and v is not None
    }


def audited_tool(mcp, name, **tool_kwargs):
    """Register an MCP tool with automatic audit logging.

    Usage:  audited_tool(mcp, 'create_job')(self.create_job)
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            safe: dict = {}
            try:
                safe = _safe_args(func, args, kwargs)
                logger.info('[tool:{}] invoked | {}', name, safe)
            except Exception:
                logger.warning('[tool:{}] invoked (audit args failed)', name)
            try:
                result = await func(*args, **kwargs)
                if isinstance(result, dict) and result.get('isError'):
                    error_text = _extract_error(result)
                    logger.warning('[tool:{}] error response | {} | {}', name, safe, error_text)
                return result
            except Exception as exc:
                logger.opt(exception=True).warning(
                    '[tool:{}] exception | {} | {}', name, safe, exc
                )
                raise

        mcp.tool(name=name, **tool_kwargs)(wrapper)
        return wrapper

    return decorator


def _extract_error(result: dict) -> str:
    """Best-effort extract of error text from an MCP result envelope."""
    try:
        import json

        payload = json.loads(result['content'][0]['text'])
        err = payload.get('error', {})
        parts = [err.get('code', ''), err.get('message', '')]
        action = err.get('suggestedAction')
        if action:
            parts.append(action)
        return ' | '.join(p for p in parts if p)
    except Exception:
        return '(could not extract error)'
