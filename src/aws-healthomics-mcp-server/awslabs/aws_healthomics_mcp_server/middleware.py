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

"""Identity middleware for request-scoped, multi-tenant credential resolution.

This module defines the Phase 2 ASGI :class:`IdentityMiddleware` that wraps the
MCP SDK's ``streamable_http_app()`` / ``sse_app()`` Starlette applications, plus
the :class:`InboundMechanism` interface that the concrete inbound mechanisms
(SigV4, JWT exchange, explicit credentials) implement.

The middleware derives a :class:`~awslabs.aws_healthomics_mcp_server.utils.aws_utils.CredentialContext`
for each inbound HTTP request, installs it in a ``contextvars.ContextVar`` before
any tool for that request executes, and resets it on completion so it is never
available to a subsequent request. ``contextvars`` are task-isolated under async
concurrency, so concurrent requests never observe each other's context
(Requirement 8.5).

These symbols are introduced additively and are not referenced on any
single-tenant (Phase 1) code path.
"""

from awslabs.aws_healthomics_mcp_server.consts import INBOUND_PRECEDENCE
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    InboundAuthError,
    reset_credential_context,
    set_credential_context,
)
from loguru import logger
from typing import Awaitable, Callable, Protocol, runtime_checkable


# ASGI type aliases. These are typed loosely to avoid a hard dependency on a
# specific Starlette/ASGI type surface; ``scope`` is a mapping, and ``receive`` /
# ``send`` are async callables exchanging ASGI event dicts.
Scope = dict
Message = dict
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


@runtime_checkable
class InboundMechanism(Protocol):
    """Interface for an inbound identity mechanism.

    An inbound mechanism inspects an ASGI ``scope`` to decide whether it can
    derive an identity from the request (:meth:`applies`) and, if so, produces a
    :class:`CredentialContext` for that request (:meth:`derive`).

    Concrete mechanisms (SigV4, JWT exchange, explicit credentials) implement
    this Protocol. The middleware tries enabled mechanisms in precedence order
    and selects exactly one whose :meth:`applies` returns ``True``.

    Attributes:
        name: Short identifier for the mechanism (e.g. ``'sigv4'``).
    """

    name: str

    def applies(self, scope: Scope) -> bool:
        """Return whether this mechanism can derive an identity from the request.

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            bool: ``True`` if this mechanism can handle the request.
        """
        ...

    def derive(self, scope: Scope) -> CredentialContext:
        """Derive a :class:`CredentialContext` from the request.

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            CredentialContext: The per-request identity.

        Raises:
            InboundAuthError: If identity derivation fails.
        """
        ...


class IdentityMiddleware:
    """ASGI middleware that populates the per-request credential context.

    Wraps the MCP SDK's ``streamable_http_app()`` / ``sse_app()`` ASGI application
    so it runs before any tool handler. For each HTTP request it selects exactly
    one enabled inbound mechanism, derives a
    :class:`CredentialContext`, installs it in the request-scoped contextvar
    **before** dispatching to the wrapped app (Requirement 8.3), and resets it on
    completion (Requirement 12.3). Non-HTTP scopes (e.g. ``lifespan``,
    ``websocket``) pass through unchanged.

    On an :class:`InboundAuthError` — including a request that satisfies no enabled
    mechanism (Requirement 13.7) — the middleware rejects the request with an HTTP
    401 response and does not dispatch to the wrapped app, so no tool runs and no
    AWS service is called.

    Mechanism selection is deterministic and independent of the order in which the
    mechanisms are supplied: on construction they are sorted by their position in
    :data:`~awslabs.aws_healthomics_mcp_server.consts.INBOUND_PRECEDENCE` (the
    documented order ``('sigv4', 'jwt', 'explicit')``). For each request the
    middleware selects the first (highest-precedence) mechanism whose ``applies``
    returns ``True``, so exactly one mechanism derives the context even when more
    than one applies (Requirement 13.6).
    """

    def __init__(self, app: ASGIApp, enabled_mechanisms: list[InboundMechanism]):
        """Initialize the middleware.

        The supplied mechanisms are sorted once, here, into the documented
        deterministic precedence order so that per-request selection does not
        depend on the order in which they were passed in. Mechanisms are ordered
        by their index in
        :data:`~awslabs.aws_healthomics_mcp_server.consts.INBOUND_PRECEDENCE`; any
        mechanism whose ``name`` is not listed there is treated as lowest priority
        and appended after the known mechanisms, preserving the relative order in
        which such unknown mechanisms were supplied (a stable sort).

        Args:
            app: The wrapped ASGI application (the SDK's streamable-http / sse app).
            enabled_mechanisms: The enabled inbound mechanisms, in any order.
        """
        self.app = app
        self.mechanisms = self._order_by_precedence(enabled_mechanisms)

    @staticmethod
    def _order_by_precedence(
        mechanisms: list[InboundMechanism],
    ) -> list[InboundMechanism]:
        """Return the mechanisms sorted by documented precedence (stable).

        Known mechanisms are ordered by their index in
        :data:`~awslabs.aws_healthomics_mcp_server.consts.INBOUND_PRECEDENCE`.
        Unknown names sort after all known names; ties (including multiple unknown
        names) keep their original relative order because :func:`sorted` is stable.

        Args:
            mechanisms: The enabled inbound mechanisms, in any order.

        Returns:
            The mechanisms ordered by precedence, highest first.
        """

        def precedence_index(mechanism: InboundMechanism) -> int:
            try:
                return INBOUND_PRECEDENCE.index(mechanism.name)
            except ValueError:
                # Unknown names have no documented precedence; place them last.
                return len(INBOUND_PRECEDENCE)

        return sorted(mechanisms, key=precedence_index)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle an ASGI event, populating the credential context for HTTP requests.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope.get('type') != 'http':
            # Non-HTTP scopes (lifespan, websocket) pass through unchanged.
            await self.app(scope, receive, send)
            return

        try:
            ctx = self._derive_context(scope)
        except InboundAuthError as error:
            await self._reject(send, error)
            return

        token = set_credential_context(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            # Discard the request's context on completion so it is not available
            # to any subsequent request (Requirement 12.3).
            reset_credential_context(token)

    def _derive_context(self, scope: Scope) -> CredentialContext:
        """Select a mechanism and derive the credential context for the request.

        Iterates the enabled mechanisms in the deterministic precedence order
        established at construction (see :meth:`_order_by_precedence`) and selects
        the first (highest-precedence) one whose
        :meth:`InboundMechanism.applies` returns ``True``, then calls its
        :meth:`InboundMechanism.derive` to produce the context. Exactly one
        mechanism derives the context even when several apply (Requirement 13.6).
        If no enabled mechanism applies, raises an :class:`InboundAuthError` and
        makes no AWS call (Requirement 13.7).

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            CredentialContext: The per-request identity.

        Raises:
            InboundAuthError: If no enabled mechanism applies, or if the selected
                mechanism fails to derive a context.
        """
        for mechanism in self.mechanisms:
            if mechanism.applies(scope):
                return mechanism.derive(scope)
        raise InboundAuthError(
            'No enabled inbound identity mechanism could authenticate the request.'
        )

    async def _reject(self, send: Send, error: InboundAuthError) -> None:
        """Send a minimal HTTP 401 response without dispatching to the wrapped app.

        Does not leak credential details in the response body. No tool runs and no
        AWS service is called for the request.

        Args:
            send: The ASGI send callable.
            error: The inbound authentication error that triggered the rejection.
        """
        logger.warning('Rejecting inbound request with 401: {}', type(error).__name__)
        body = b'Unauthorized'
        await send(
            {
                'type': 'http.response.start',
                'status': 401,
                'headers': [
                    (b'content-type', b'text/plain; charset=utf-8'),
                    (b'content-length', str(len(body)).encode('ascii')),
                ],
            }
        )
        await send(
            {
                'type': 'http.response.body',
                'body': body,
            }
        )
