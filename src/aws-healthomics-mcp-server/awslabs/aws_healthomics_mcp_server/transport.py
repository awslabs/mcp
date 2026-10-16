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

"""Transport selection and startup wiring (Phase 1).

This module selects the configured MCP transport and starts it. For network
transports (``streamable-http`` / ``sse``) the resolved host, port, and
request path are passed straight through as ``mcp.run(transport=...)``
keyword arguments.

The ``mcp`` object is a :class:`mcp.server.mcpserver.MCPServer` instance (the
official MCP Python SDK, v2). ``MCPServer.run(transport=...)`` accepts
``stdio``, ``streamable-http``, and ``sse``; for the two network transports it
forwards its keyword arguments (``host``, ``port``, and either
``streamable_http_path`` or ``sse_path``) to the corresponding async runner.
"""

from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    ServerConfig,
    UnsupportedTransportError,
    is_loopback,
)
from loguru import logger
from mcp.server.mcpserver import MCPServer
from typing import Literal, Optional, cast


class TransportSelector:
    """Selects and starts the configured transport."""

    SUPPORTED: tuple[str, ...] = consts.SUPPORTED_TRANSPORTS

    @staticmethod
    def normalize(raw: Optional[str]) -> Optional[str]:
        """Trim surrounding whitespace and treat empty/whitespace/None as unset.

        An absent, empty, or whitespace-only value normalizes to ``None`` (unset),
        which :meth:`select` resolves to the default ``stdio`` transport. Any other
        value is returned with surrounding whitespace stripped; validation against
        the supported modes is performed by :meth:`select`.

        Args:
            raw: The raw transport value from CLI or environment, or ``None``.

        Returns:
            The trimmed transport string, or ``None`` when the value is unset.
        """
        if raw is None:
            return None

        trimmed = raw.strip()
        if trimmed == '':
            return None

        return trimmed

    @classmethod
    def select(cls, config: ServerConfig) -> str:
        """Return a supported transport mode for the given configuration.

        The configured transport is normalized (trimmed; empty/whitespace/None
        treated as unset) and matched case-sensitively against the supported
        modes. An unset transport resolves to the default ``stdio`` transport.

        Args:
            config: The resolved server configuration.

        Returns:
            A supported transport mode string.

        Raises:
            UnsupportedTransportError: If a non-empty transport value does not
                match a supported transport mode.
        """
        mode = cls.normalize(config.transport)
        if mode is None:
            return consts.DEFAULT_TRANSPORT

        if mode not in cls.SUPPORTED:
            raise UnsupportedTransportError(
                consts.ERROR_UNSUPPORTED_TRANSPORT.format(mode, ', '.join(cls.SUPPORTED))
            )

        return mode

    @classmethod
    def start(cls, mcp: MCPServer, config: ServerConfig) -> None:
        """Apply the exposure check, then run the transport.

        For network transports the secure-by-default exposure check is
        performed first: a non-loopback host triggers exactly one warning
        (emitted before the server begins accepting requests) while startup
        still proceeds to bind. For the ``stdio`` transport the exposure check
        is skipped. In all cases ``mcp.run(transport=mode, ...)`` is invoked
        with exactly the selected mode; for network transports the resolved
        host, port, and request path are passed as keyword arguments.

        Args:
            mcp: The ``MCPServer`` instance to start.
            config: The resolved server configuration.

        Raises:
            UnsupportedTransportError: If the configured transport is not supported.
        """
        mode = cls.select(config)

        if mode not in consts.NETWORK_TRANSPORTS:
            mcp.run(transport=cast(Literal['stdio'], mode))
            return

        cls._check_secure_exposure(config)

        network_mode = cast(Literal['sse', 'streamable-http'], mode)
        if network_mode == 'streamable-http':
            mcp.run(
                transport=network_mode,
                host=config.host,
                port=config.port,
                streamable_http_path=config.path,
            )
        else:  # 'sse'
            mcp.run(
                transport=network_mode,
                host=config.host,
                port=config.port,
                sse_path=config.path,
            )

    @staticmethod
    def _check_secure_exposure(config: ServerConfig) -> None:
        """Apply the secure-by-default exposure check for a network transport.

        Loopback hosts (IPv4 ``127.0.0.0/8`` or IPv6 ``::1``) bind silently. A
        valid non-loopback host emits exactly one ``logger.warning`` indicating
        that non-loopback exposure requires an external fronting authentication
        layer; startup then continues to bind without exiting. Phase 1 performs
        no inbound authentication of its own.

        This must run before the server begins accepting requests (i.e. before
        ``mcp.run`` is invoked).

        Args:
            config: The resolved server configuration providing the bind host.
        """
        if is_loopback(config.host):
            return

        logger.warning(consts.WARN_NON_LOOPBACK_EXPOSURE.format(config.host))
