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


"""Unit tests for the transport verification driver.

These tests are pure and offline: they exercise the ordered session -> list -> invoke
driver in ``integration/harness/mcp_client.py`` using a hand-written STUB client that
records which operations were called. No real MCP transport, AWS access, or network is
involved. They live in ``integration/harness_tests/`` — separate from the opt-in-gated
``integration/tests/`` suite and from the offline ``tests/`` suite — and are not gated by
the Opt_In_Signal.

The core behaviors covered are the driver's short-circuiting guarantees: a session that
cannot be established stops before any list/invoke, and an empty or foreign (no known
HealthOmics tool) tool list stops before any invocation. A positive control asserts the
happy path returns a result naming the invoked tool.

Validates: Requirements Remote transport end-to-end verification.
"""

from collections.abc import Mapping
from integration.harness.mcp_client import (
    TransportVerificationError,
    TransportVerificationResult,
    TransportVerificationStage,
    verify_transport,
)
from types import SimpleNamespace
from typing import Any


# Representative known HealthOmics tool names standing in for the server's registered tools.
_KNOWN_TOOLS = frozenset({'ListAHOWorkflows', 'GetAHORun'})
_ENDPOINT = 'https://example.invalid/mcp'
_HEADERS: Mapping[str, str] = {'authorization': 'Bearer test-token'}


class StubClient:
    """A hand-written stub MCP client that records which operations were called.

    The stub implements the three async operations the driver depends on
    (``open_session``, ``list_tools``, ``call_tool``) and appends each invocation name to
    ``calls`` so tests can assert the driver short-circuits before later stages. Each
    operation's behavior is configured per test: ``open_error`` / ``list_error`` /
    ``call_error`` raise, while ``tools`` / ``call_result`` are returned.
    """

    def __init__(
        self,
        *,
        open_error: BaseException | None = None,
        tools: list[Any] | None = None,
        list_error: BaseException | None = None,
        call_result: Any = None,
        call_error: BaseException | None = None,
    ) -> None:
        """Configure the stub's recorded behavior for each stage."""
        self.calls: list[str] = []
        self._open_error = open_error
        self._tools = tools if tools is not None else []
        self._list_error = list_error
        self._call_result = call_result
        self._call_error = call_error

    async def open_session(
        self,
        endpoint: str,
        headers: Mapping[str, str],
        connect_timeout_s: float = 30.0,
    ) -> object:
        """Record the call and either raise the configured error or succeed."""
        self.calls.append('open_session')
        if self._open_error is not None:
            raise self._open_error
        return object()

    async def list_tools(self, timeout_s: float = 30.0) -> list[Any]:
        """Record the call and either raise the configured error or return the tools."""
        self.calls.append('list_tools')
        if self._list_error is not None:
            raise self._list_error
        return list(self._tools)

    async def call_tool(
        self,
        name: str,
        args: dict[str, Any],
        timeout_s: float = 60.0,
    ) -> Any:
        """Record the call (with the tool name) and return/raise the configured result."""
        self.calls.append(f'call_tool:{name}')
        if self._call_error is not None:
            raise self._call_error
        return self._call_result


def _tool(name: str) -> SimpleNamespace:
    """Build a tiny stand-in tool object exposing only the ``.name`` attribute."""
    return SimpleNamespace(name=name)


class TestSessionStageShortCircuits:
    """A session failure stops before listing tools or invoking any tool.

    Validates: Requirements Remote transport end-to-end verification.
    """

    async def test_session_timeout_fails_at_session_stage_without_list_or_invoke(
        self,
    ) -> None:
        """A session that times out fails at SESSION and never lists/invokes (Req 4.2)."""
        client = StubClient(open_error=TimeoutError('connect timed out'))

        try:
            await verify_transport(client, _ENDPOINT, _HEADERS, _KNOWN_TOOLS)
        except TransportVerificationError as exc:
            assert exc.stage == TransportVerificationStage.SESSION
        else:
            raise AssertionError('expected TransportVerificationError at SESSION stage')

        # Only open_session ran; list_tools and call_tool were never called.
        assert client.calls == ['open_session']
        assert 'list_tools' not in client.calls
        assert not any(call.startswith('call_tool') for call in client.calls)


class TestListStageShortCircuits:
    """An empty or foreign tool list stops before any invocation.

    Validates: Requirements Remote transport end-to-end verification.
    """

    async def test_empty_tool_list_fails_at_list_stage_without_invoke(self) -> None:
        """An empty tool list fails at LIST and never invokes a tool (Req 4.6)."""
        client = StubClient(tools=[])

        try:
            await verify_transport(client, _ENDPOINT, _HEADERS, _KNOWN_TOOLS)
        except TransportVerificationError as exc:
            assert exc.stage == TransportVerificationStage.LIST
        else:
            raise AssertionError('expected TransportVerificationError at LIST stage')

        # Session opened and tools listed, but no tool was invoked.
        assert client.calls == ['open_session', 'list_tools']
        assert not any(call.startswith('call_tool') for call in client.calls)

    async def test_foreign_tool_list_fails_at_list_stage_without_invoke(self) -> None:
        """A list with no known HealthOmics tool fails at LIST without invoking (Req 4.6)."""
        client = StubClient(tools=[_tool('SomeOtherTool'), _tool('AnotherForeignTool')])

        try:
            await verify_transport(client, _ENDPOINT, _HEADERS, _KNOWN_TOOLS)
        except TransportVerificationError as exc:
            assert exc.stage == TransportVerificationStage.LIST
        else:
            raise AssertionError('expected TransportVerificationError at LIST stage')

        assert client.calls == ['open_session', 'list_tools']
        assert not any(call.startswith('call_tool') for call in client.calls)


class TestHappyPath:
    """A known tool and a non-error result yield a passing verification result.

    Validates: Requirements Remote transport end-to-end verification.
    """

    async def test_known_tool_and_non_error_result_returns_result(self) -> None:
        """The driver invokes a known tool and returns a result naming it."""
        tool = _tool('ListAHOWorkflows')
        call_result = SimpleNamespace(isError=False)
        client = StubClient(tools=[tool], call_result=call_result)

        result = await verify_transport(client, _ENDPOINT, _HEADERS, _KNOWN_TOOLS)

        assert isinstance(result, TransportVerificationResult)
        assert result.tool_name == 'ListAHOWorkflows'
        assert result.result is call_result
        # All three stages ran in order, ending with an invocation of the known tool.
        assert client.calls == ['open_session', 'list_tools', 'call_tool:ListAHOWorkflows']
