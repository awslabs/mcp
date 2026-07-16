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


"""Thin streamable-http MCP client and offline-testable retry policy.

This module wraps the official MCP Python SDK's ``streamable-http`` client transport in a
small, purpose-built client (:class:`HarnessMcpClient`) used by the transport and isolation
integration tests, and provides a transport-agnostic retry helper (:func:`with_retries`).

The retry helper takes injectable ``sleep`` and ``now`` seams so the retry policy can be
property-tested fully offline with a fake clock (no real waiting, no AWS, no network). The
client itself performs no work until :meth:`HarnessMcpClient.open_session` is called, so
importing this module stays offline.
"""

from __future__ import annotations

import anyio
import enum
import time
from collections.abc import Awaitable, Callable, Collection, Mapping
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import timedelta
from integration.harness.headers import TENANT_TOKEN_HEADER
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, Tool
from typing import Any, Protocol, TypeVar, runtime_checkable


# Public type aliases mirroring the design's `ToolInfo` / `ToolResult` names.
ToolInfo = Tool
ToolResult = CallToolResult

T = TypeVar('T')

# Default per-operation timeouts (seconds), matching Requirements 4.1, 4.3, 4.4.
DEFAULT_CONNECT_TIMEOUT_S: float = 30.0
DEFAULT_LIST_TIMEOUT_S: float = 30.0
DEFAULT_CALL_TIMEOUT_S: float = 60.0

# Default retry policy (Requirement 4.7): the initial attempt plus up to 3 more.
DEFAULT_ATTEMPTS: int = 4
DEFAULT_MIN_INTERVAL_S: float = 1.0

# A default User-Agent sent on every request. The AWS WAF fronting the AgentCore Runtime
# endpoint rejects requests without a User-Agent header, and the MCP SDK does not set one, so
# the client injects a default (callers may override it via the headers they pass).
DEFAULT_USER_AGENT: str = 'aws-healthomics-mcp-itest/1.0'


def _default_is_transient(exc: BaseException) -> bool:
    """Treat any ``Exception`` (including timeouts) as transient/retryable by default.

    ``BaseException`` subclasses that are not ``Exception`` (e.g. cancellation) are not
    considered transient so cancellation still propagates promptly.
    """
    return isinstance(exc, Exception)


async def with_retries(
    op: Callable[[], Awaitable[T]],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
    is_transient: Callable[[BaseException], bool] = _default_is_transient,
    sleep: Callable[[float], Awaitable[Any]] = anyio.sleep,
    now: Callable[[], float] = time.monotonic,
) -> T:
    """Run ``op`` with bounded retries on transient failure.

    Makes at most ``attempts`` total attempts (the initial attempt plus up to
    ``attempts - 1`` additional ones), ensures at least ``min_interval_s`` seconds elapse
    between the starts of consecutive attempts, stops at the first success, and returns that
    success. If every attempt fails transiently within the budget, the last exception is
    re-raised. A non-transient exception is re-raised immediately without further attempts.

    The ``sleep`` and ``now`` seams are injectable so the policy is deterministic and
    offline-testable with a fake monotonic clock and fake sleep.

    Args:
        op: A zero-argument async callable performing one attempt.
        attempts: Maximum total attempts (must be >= 1). Defaults to 4.
        min_interval_s: Minimum spacing, in seconds, between consecutive attempt starts.
        is_transient: Predicate deciding whether a raised exception is retryable.
        sleep: Async sleep seam invoked with the number of seconds to wait.
        now: Monotonic clock seam returning a float number of seconds.

    Returns:
        The value returned by the first successful ``op`` invocation.

    Raises:
        ValueError: If ``attempts`` is less than 1.
        BaseException: The last transient exception if all attempts are exhausted, or a
            non-transient exception raised by ``op``.
    """
    if attempts < 1:
        raise ValueError('attempts must be >= 1')

    last_exc: BaseException | None = None
    last_attempt_at: float | None = None

    for _ in range(attempts):
        if last_attempt_at is not None and min_interval_s > 0:
            elapsed = now() - last_attempt_at
            wait = min_interval_s - elapsed
            if wait > 0:
                await sleep(wait)

        last_attempt_at = now()
        try:
            return await op()
        except BaseException as exc:  # noqa: BLE001 - re-raised below unless transient
            if not is_transient(exc):
                raise
            last_exc = exc

    # Exhausted the attempt budget without a success; surface the last transient failure.
    assert last_exc is not None
    raise last_exc


class HarnessMcpClient:
    """A thin ``streamable-http`` MCP client wrapping the MCP SDK transport.

    The client opens a single session against a deployment's fronting-layer endpoint,
    carrying the caller's headers (e.g. a per-tenant bearer token), and applies the
    harness's per-operation timeouts. It performs no I/O until :meth:`open_session` is
    called and can be used as an async context manager to guarantee cleanup.
    """

    def __init__(self) -> None:
        """Initialize an unopened client; no I/O is performed until ``open_session``."""
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def open_session(
        self,
        endpoint: str,
        headers: Mapping[str, str],
        connect_timeout_s: float = DEFAULT_CONNECT_TIMEOUT_S,
    ) -> ClientSession:
        """Open and initialize an MCP session over streamable-http.

        Establishes the transport and initializes the session within ``connect_timeout_s``
        seconds (Requirement 4.1). On timeout or failure the partially opened transport is
        closed before the error propagates.

        Args:
            endpoint: The fully-qualified streamable-http endpoint URL.
            headers: Request headers to attach (e.g. the caller's bearer token).
            connect_timeout_s: Maximum seconds to establish and initialize the session.

        Returns:
            The initialized :class:`ClientSession`.
        """
        await self.aclose()

        # Ensure a User-Agent is always present (the AgentCore WAF rejects requests without
        # one); caller-supplied headers take precedence so an explicit override still wins.
        request_headers = {'User-Agent': DEFAULT_USER_AGENT, **dict(headers)}

        # AgentCore Runtime strips the reserved Authorization header at its JWT authorizer and
        # does not forward it to the container. Mirror the bearer value into a non-reserved
        # header that AgentCore forwards (allow-listed on the runtime); the container entrypoint
        # maps it back onto Authorization. Harmless for other fronting layers, which ignore it.
        if TENANT_TOKEN_HEADER not in request_headers:
            authorization = next(
                (
                    value
                    for key, value in request_headers.items()
                    if key.lower() == 'authorization'
                ),
                None,
            )
            if authorization is not None:
                request_headers[TENANT_TOKEN_HEADER] = authorization

        exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream, _ = await exit_stack.enter_async_context(
                streamablehttp_client(
                    url=endpoint,
                    headers=request_headers,
                    timeout=connect_timeout_s,
                )
            )
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            with anyio.fail_after(connect_timeout_s):
                await session.initialize()
        except BaseException:
            await exit_stack.aclose()
            raise

        self._exit_stack = exit_stack
        self._session = session
        return session

    async def list_tools(self, timeout_s: float = DEFAULT_LIST_TIMEOUT_S) -> list[ToolInfo]:
        """List the tools advertised by the server within ``timeout_s`` seconds.

        Args:
            timeout_s: Maximum seconds to wait for the tool list (Requirement 4.3).

        Returns:
            The list of advertised tools.
        """
        session = self._require_session()
        with anyio.fail_after(timeout_s):
            result = await session.list_tools()
        return list(result.tools)

    async def call_tool(
        self,
        name: str,
        args: dict[str, Any],
        timeout_s: float = DEFAULT_CALL_TIMEOUT_S,
    ) -> ToolResult:
        """Invoke a tool by name within ``timeout_s`` seconds.

        A timeout is surfaced as an error (Requirement 4.4/4.5); it is never a silent hang.

        Args:
            name: The tool name to invoke.
            args: The tool arguments.
            timeout_s: Maximum seconds to wait for the tool result.

        Returns:
            The tool-call result.
        """
        session = self._require_session()
        with anyio.fail_after(timeout_s):
            return await session.call_tool(
                name,
                args,
                read_timeout_seconds=timedelta(seconds=timeout_s),
            )

    async def aclose(self) -> None:
        """Close the open session and underlying transport, if any. Idempotent."""
        exit_stack = self._exit_stack
        self._exit_stack = None
        self._session = None
        if exit_stack is not None:
            await exit_stack.aclose()

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError('open_session must be called before using the client')
        return self._session

    async def __aenter__(self) -> 'HarnessMcpClient':
        """Enter the async context, returning this client."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Exit the async context, closing the session and transport."""
        await self.aclose()


# A predicate deciding whether a tool name identifies a known HealthOmics tool.
ToolPredicate = Callable[[str], bool]


@runtime_checkable
class SupportsTransportVerification(Protocol):
    """The minimal client surface the transport verification driver depends on.

    :class:`HarnessMcpClient` satisfies this protocol, but so does any stub that implements
    the same three async operations, which keeps the driver unit-testable offline with a
    stubbed client (no transport, no AWS, no network).
    """

    async def open_session(
        self,
        endpoint: str,
        headers: Mapping[str, str],
        connect_timeout_s: float = ...,
    ) -> Any:
        """Open and initialize an MCP session."""
        ...

    async def list_tools(self, timeout_s: float = ...) -> list[ToolInfo]:
        """List the tools advertised by the server."""
        ...

    async def call_tool(
        self,
        name: str,
        args: dict[str, Any],
        timeout_s: float = ...,
    ) -> ToolResult:
        """Invoke a tool by name."""
        ...


class TransportVerificationStage(enum.Enum):
    """The ordered stages of the transport verification: session -> list -> invoke."""

    SESSION = 'session'
    LIST = 'list'
    INVOKE = 'invoke'


class TransportVerificationError(Exception):
    """Raised when transport verification fails, naming the stage that failed.

    The ``stage`` attribute identifies which of the ordered stages
    (:class:`TransportVerificationStage`) short-circuited the check, and ``detail`` carries a
    human-readable cause. Neither ever contains Credential_Material.
    """

    def __init__(self, stage: TransportVerificationStage, detail: str) -> None:
        """Initialize with the failed stage and a human-readable detail."""
        super().__init__(f'{stage.value}: {detail}')
        self.stage = stage
        self.detail = detail


@dataclass(frozen=True)
class TransportVerificationResult:
    """The successful outcome of transport verification.

    Attributes:
        tool_name: The name of the HealthOmics tool that was invoked.
        tools: The full tool list returned by the server, in advertised order.
        result: The non-error tool-call result returned by the invocation.
    """

    tool_name: str
    tools: tuple[ToolInfo, ...]
    result: ToolResult


def _as_tool_predicate(known_tools: ToolPredicate | Collection[str]) -> ToolPredicate:
    """Normalize a predicate or a collection of known tool names into a name predicate."""
    if callable(known_tools):
        return known_tools
    known = frozenset(known_tools)
    return lambda name: name in known


async def verify_transport(
    client: SupportsTransportVerification,
    endpoint: str,
    headers: Mapping[str, str],
    known_tools: ToolPredicate | Collection[str],
    *,
    tool_args: Mapping[str, Any] | None = None,
    connect_timeout_s: float = DEFAULT_CONNECT_TIMEOUT_S,
    list_timeout_s: float = DEFAULT_LIST_TIMEOUT_S,
    call_timeout_s: float = DEFAULT_CALL_TIMEOUT_S,
) -> TransportVerificationResult:
    """Verify end-to-end transport by driving the ordered sequence session -> list -> invoke.

    The driver enforces the stages strictly and short-circuits on the first failure:

    - **session** — if the session is not established within ``connect_timeout_s`` seconds (or
      establishing it errors), the check fails at the ``SESSION`` stage without listing tools
      or invoking anything (Requirement 4.2).
    - **list** — if the tool list cannot be retrieved, or it is empty, or it contains no known
      HealthOmics tool, the check fails at the ``LIST`` stage without invoking anything
      (Requirement 4.6).
    - **invoke** — the first known HealthOmics tool is invoked; if the invocation errors,
      times out within ``call_timeout_s`` seconds, or returns an error result, the check fails
      at the ``INVOKE`` stage (Requirement 4.5).

    The driver operates on the injected ``client`` and never constructs its own, so it can be
    exercised offline with a stubbed client. Known HealthOmics tools are identified by
    ``known_tools``, which may be either a predicate over tool names or a collection of known
    tool names.

    Args:
        client: The MCP client to drive; typically a :class:`HarnessMcpClient`.
        endpoint: The fully-qualified streamable-http endpoint URL.
        headers: Request headers to attach (e.g. the caller's bearer token).
        known_tools: A predicate over tool names, or a collection of known tool names, used to
            recognize a HealthOmics tool in the advertised list.
        tool_args: Arguments passed to the invoked tool. Defaults to an empty mapping.
        connect_timeout_s: Maximum seconds to establish the session (Requirement 4.2).
        list_timeout_s: Maximum seconds to list tools (Requirement 4.3).
        call_timeout_s: Maximum seconds to await the tool-call result (Requirement 4.5).

    Returns:
        A :class:`TransportVerificationResult` describing the invoked tool and its result.

    Raises:
        TransportVerificationError: If any stage fails; ``stage`` names the failed stage.
    """
    is_known = _as_tool_predicate(known_tools)
    args = dict(tool_args or {})

    # Stage 1: establish the session. On any failure we stop here without listing/invoking.
    try:
        await client.open_session(endpoint, headers, connect_timeout_s=connect_timeout_s)
    except Exception as exc:  # noqa: BLE001 - surfaced as a stage failure
        raise TransportVerificationError(
            TransportVerificationStage.SESSION,
            f'failed to establish an MCP session within {connect_timeout_s:g}s: {exc}',
        ) from exc

    # Stage 2: list tools. An empty or foreign tool list fails here without invoking.
    try:
        tools = await client.list_tools(timeout_s=list_timeout_s)
    except Exception as exc:  # noqa: BLE001 - surfaced as a stage failure
        raise TransportVerificationError(
            TransportVerificationStage.LIST,
            f'failed to list tools within {list_timeout_s:g}s: {exc}',
        ) from exc

    healthomics_tools = [tool for tool in tools if is_known(tool.name)]
    if not healthomics_tools:
        detail = (
            'server returned an empty tool list'
            if not tools
            else 'tool list contained no known HealthOmics tool'
        )
        raise TransportVerificationError(TransportVerificationStage.LIST, detail)

    target = healthomics_tools[0]

    # Stage 3: invoke the first known HealthOmics tool. An error or timeout fails the check.
    try:
        result = await client.call_tool(target.name, args, timeout_s=call_timeout_s)
    except Exception as exc:  # noqa: BLE001 - surfaced as a stage failure
        raise TransportVerificationError(
            TransportVerificationStage.INVOKE,
            f'invoking {target.name!r} failed within {call_timeout_s:g}s: {exc}',
        ) from exc

    if getattr(result, 'isError', False):
        raise TransportVerificationError(
            TransportVerificationStage.INVOKE,
            f'invoking {target.name!r} returned an error result',
        )

    return TransportVerificationResult(
        tool_name=target.name,
        tools=tuple(tools),
        result=result,
    )
