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

"""Error handling helpers for DocumentDB MCP Server.

The MCP SDK returns the message of a ``ToolError`` to the client (the LLM) and
replaces any other exception with a generic "Error executing tool <name>".
``SafeToolError`` is a ``ToolError``, so it is the only error whose text the
client sees. Driver exceptions for connection and configuration problems carry
the cluster endpoint and the driver's topology description, so they are logged
server-side and replaced with a fixed ``SafeToolError`` message.
"""

import re
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError
from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure


CONNECTION_ERROR_MESSAGE = (
    'Failed to connect to the configured DocumentDB cluster. See server logs for details.'
)

# Errors whose text describes the cluster endpoint or connection configuration.
# ConnectionFailure covers AutoReconnect, NetworkTimeout and
# ServerSelectionTimeoutError; ConfigurationError covers InvalidURI.
_CONNECTION_ERRORS = (ConnectionFailure, ConfigurationError, OSError)

# The userinfo (credentials) part of a mongodb:// or mongodb+srv:// URI, up to the '@'.
_URI_USERINFO = re.compile(r'(mongodb(?:\+srv)?://)[^@/\s]+@', re.IGNORECASE)


class SafeToolError(ToolError, ValueError):
    """A tool error whose message is returned to the MCP client verbatim.

    Raise this only for messages the server writes itself (read-only denials,
    "not configured", invalid arguments) or has sanitized. It subclasses
    ``ValueError`` for compatibility with callers that catch ``ValueError``.
    """


def redact(text: str) -> str:
    """Remove userinfo (credentials) from any MongoDB URI in ``text``."""
    return _URI_USERINFO.sub(r'\1<redacted>@', text)


def tool_error(operation: str, error: Exception) -> ValueError:
    """Convert an exception raised inside a tool into the error to raise.

    Full detail is logged server-side (with URI credentials redacted). What the
    client sees depends on the error:

    - ``SafeToolError``: returned unchanged; the client sees its message.
    - Connection and configuration errors: a ``SafeToolError`` with a fixed
      message, so the cluster endpoint and topology description never reach the
      client.
    - ``OperationFailure``: a ``SafeToolError`` with the server's ``errmsg`` and
      ``code`` only, which the client needs to correct a bad query.
    - Anything else: a plain ``ValueError`` with URI credentials redacted. It is
      not a ``ToolError``, so the SDK shows the client only a generic message.

    Args:
        operation: Short description of the failed operation, e.g. 'query DocumentDB'.
        error: The exception that was raised.

    Returns:
        ValueError: The error to raise (a ``SafeToolError`` when client-visible).
    """
    if isinstance(error, SafeToolError):
        return error

    logger.error(f'Failed to {operation}: {type(error).__name__}: {redact(str(error))}')

    if isinstance(error, _CONNECTION_ERRORS):
        return SafeToolError(CONNECTION_ERROR_MESSAGE)

    if isinstance(error, OperationFailure):
        # str(error) appends the full server reply when details are present.
        errmsg = (error.details or {}).get('errmsg') if error.details else str(error)
        return SafeToolError(f'Failed to {operation}: {redact(str(errmsg))} (code {error.code})')

    return ValueError(f'Failed to {operation}: {redact(str(error))}')
