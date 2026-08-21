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

"""Offline unit tests for HarnessMcpClient request headers.

Pure and offline: the streamable-http transport and MCP client session are patched with
fakes, so opening a session performs no network I/O. The tests assert that a default
``User-Agent`` header is always sent (the AWS WAF fronting the AgentCore endpoint rejects
requests without one, which manifested as a silent connection timeout), and that a
caller-supplied ``User-Agent`` overrides the default.

Validates: Requirements Remote transport end-to-end verification.
"""

from contextlib import asynccontextmanager
from integration.harness import mcp_client
from integration.harness.mcp_client import DEFAULT_USER_AGENT, HarnessMcpClient


class _FakeSession:
    """A stand-in MCP client session whose initialize is a no-op."""

    def __init__(self, _read, _write) -> None:
        pass

    async def __aenter__(self) -> '_FakeSession':
        return self

    async def __aexit__(self, *_exc) -> bool:
        return False

    async def initialize(self) -> None:
        return None


def _patch_transport(monkeypatch) -> dict:
    """Patch the transport + session seams and return a dict capturing the sent headers."""
    captured: dict = {}

    @asynccontextmanager
    async def _fake_streamable(url, headers, timeout):
        captured['url'] = url
        captured['headers'] = headers
        captured['timeout'] = timeout
        yield ('read', 'write', None)

    monkeypatch.setattr(mcp_client, 'streamablehttp_client', _fake_streamable)
    monkeypatch.setattr(mcp_client, 'ClientSession', _FakeSession)
    return captured


class TestUserAgentHeader:
    """The client always sends a User-Agent unless the caller overrides it.

    Validates: Requirements Remote transport end-to-end verification.
    """

    async def test_default_user_agent_injected(self, monkeypatch) -> None:
        """A default User-Agent is added alongside the caller's Authorization header."""
        captured = _patch_transport(monkeypatch)

        client = HarnessMcpClient()
        async with client:
            await client.open_session('https://example.test/mcp', {'Authorization': 'Bearer tok'})

        assert captured['headers']['User-Agent'] == DEFAULT_USER_AGENT
        assert captured['headers']['Authorization'] == 'Bearer tok'

    async def test_caller_user_agent_overrides_default(self, monkeypatch) -> None:
        """A caller-supplied User-Agent takes precedence over the default."""
        captured = _patch_transport(monkeypatch)

        client = HarnessMcpClient()
        async with client:
            await client.open_session('https://example.test/mcp', {'User-Agent': 'custom-agent/9'})

        assert captured['headers']['User-Agent'] == 'custom-agent/9'


class TestTenantTokenHeaderMirroring:
    """The client mirrors the Authorization bearer into the AgentCore-forwarded header.

    Validates: Requirements Remote transport end-to-end verification, Cross-tenant isolation
    verification.
    """

    async def test_authorization_mirrored_into_tenant_token_header(self, monkeypatch) -> None:
        """The Authorization value is copied into the forwarded tenant-token header."""
        from integration.harness.headers import TENANT_TOKEN_HEADER

        captured = _patch_transport(monkeypatch)

        client = HarnessMcpClient()
        async with client:
            await client.open_session('https://example.test/mcp', {'Authorization': 'Bearer tok'})

        assert captured['headers'][TENANT_TOKEN_HEADER] == 'Bearer tok'
        # The original Authorization header is preserved for the fronting-layer authorizer.
        assert captured['headers']['Authorization'] == 'Bearer tok'

    async def test_existing_tenant_token_header_not_overwritten(self, monkeypatch) -> None:
        """A caller-supplied tenant-token header is left untouched."""
        from integration.harness.headers import TENANT_TOKEN_HEADER

        captured = _patch_transport(monkeypatch)

        client = HarnessMcpClient()
        async with client:
            await client.open_session(
                'https://example.test/mcp',
                {'Authorization': 'Bearer tok', TENANT_TOKEN_HEADER: 'Bearer explicit'},
            )

        assert captured['headers'][TENANT_TOKEN_HEADER] == 'Bearer explicit'
