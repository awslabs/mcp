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
transports (``streamable-http`` / ``sse``) it applies the resolved host, port,
and request path onto the ``FastMCP`` instance's settings before invoking
``mcp.run(transport=...)`` with exactly the selected mode.

The ``mcp`` object is a :class:`mcp.server.fastmcp.FastMCP` instance (the
official MCP Python SDK). ``FastMCP.run(transport=...)`` accepts ``stdio``,
``streamable-http``, and ``sse``. Network bind configuration is read from
``FastMCP.settings`` (a settings model exposing ``host``, ``port``,
``sse_path``, and ``streamable_http_path``), so those fields are set on the
instance before ``run()`` is called.
"""

from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    ServerConfig,
    UnsupportedTransportError,
    is_loopback,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
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
    def start(cls, mcp: FastMCP, config: ServerConfig) -> None:
        """Apply bind settings and the exposure check, then run the transport.

        For network transports the resolved host, port, and request path are
        applied onto ``mcp.settings`` before ``run()`` is invoked. The
        secure-by-default exposure check is then performed: a non-loopback host
        triggers exactly one warning (emitted before the server begins accepting
        requests) while startup still proceeds to bind. For the ``stdio``
        transport, bind settings and the exposure check are skipped. In all cases
        ``mcp.run(transport=mode)`` is invoked with exactly the selected mode.

        Args:
            mcp: The ``FastMCP`` instance to start.
            config: The resolved server configuration.

        Raises:
            UnsupportedTransportError: If the configured transport is not supported.
        """
        mode = cls.select(config)

        if mode in consts.NETWORK_TRANSPORTS:
            cls._apply_network_settings(mcp, config, mode)
            cls._check_secure_exposure(config)

        # ``mode`` is validated against SUPPORTED by ``select``; cast narrows it to
        # the literal type expected by ``FastMCP.run``.
        mcp.run(transport=cast(Literal['stdio', 'sse', 'streamable-http'], mode))

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

    @staticmethod
    def _apply_network_settings(mcp: FastMCP, config: ServerConfig, mode: str) -> None:
        """Apply host/port/path bind settings onto the FastMCP instance.

        Args:
            mcp: The ``FastMCP`` instance whose settings are updated.
            config: The resolved server configuration providing host/port/path.
            mode: The selected network transport mode determining which path
                setting (``streamable_http_path`` or ``sse_path``) is applied.
        """
        mcp.settings.host = config.host
        mcp.settings.port = config.port
        if mode == 'streamable-http':
            mcp.settings.streamable_http_path = config.path
        else:  # 'sse'
            mcp.settings.sse_path = config.path
