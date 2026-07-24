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

"""Offline unit tests for the container entrypoint Authorization header shim.

Pure and offline: the shim is an ASGI wrapper exercised with a fake inner app that records the
scope it receives, so no server, network, or AWS access is involved. The tests prove the shim
maps the forwarded tenant-token header onto ``Authorization`` (so the unmodified server's
IdentityMiddleware sees the bearer token AgentCore would otherwise strip), while leaving
requests that already carry ``Authorization`` untouched.

Validates: Requirements Cross-tenant isolation verification, Remote transport end-to-end
verification.
"""

import os


# Establish a deterministic, offline AWS environment before importing the entrypoint (which
# imports the server package). Mirrors test_entrypoint.py's isolation.
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('AWS_REGION', 'us-east-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')  # pragma: allowlist secret
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')  # pragma: allowlist secret
os.environ.setdefault('AWS_SESSION_TOKEN', 'testing')  # pragma: allowlist secret

from awslabs.aws_healthomics_mcp_server import server as server_module  # noqa: E402
from integration.deploy.image import entrypoint  # noqa: E402
from integration.harness.headers import TENANT_TOKEN_HEADER  # noqa: E402


class _RecordingApp:
    """A fake inner ASGI app that records the scope it is called with."""

    def __init__(self) -> None:
        self.scope = None

    async def __call__(self, scope, receive, send) -> None:
        self.scope = scope


def _headers(scope) -> dict:
    """Return the scope's headers as a lowercased-name -> value (decoded) dict."""
    return {name.decode(): value.decode() for name, value in scope['headers']}


class TestAuthorizationHeaderShim:
    """The shim maps the forwarded tenant-token header onto Authorization.

    Validates: Requirements Cross-tenant isolation verification.
    """

    async def test_maps_tenant_token_header_to_authorization(self) -> None:
        """A request with only the tenant-token header gains an Authorization header."""
        inner = _RecordingApp()
        shim = entrypoint._AuthorizationHeaderShim(inner)
        scope = {
            'type': 'http',
            'headers': [(TENANT_TOKEN_HEADER.lower().encode(), b'Bearer tok')],
        }

        await shim(scope, None, None)

        assert _headers(inner.scope)['authorization'] == 'Bearer tok'

    async def test_existing_authorization_is_preserved(self) -> None:
        """A request that already has Authorization is passed through unchanged."""
        inner = _RecordingApp()
        shim = entrypoint._AuthorizationHeaderShim(inner)
        scope = {
            'type': 'http',
            'headers': [
                (b'authorization', b'Bearer real'),
                (TENANT_TOKEN_HEADER.lower().encode(), b'Bearer other'),
            ],
        }

        await shim(scope, None, None)

        authorization_values = [
            value for name, value in inner.scope['headers'] if name == b'authorization'
        ]
        assert authorization_values == [b'Bearer real']

    async def test_non_http_scope_passes_through(self) -> None:
        """A non-HTTP scope (e.g. lifespan) is forwarded unchanged."""
        inner = _RecordingApp()
        shim = entrypoint._AuthorizationHeaderShim(inner)
        scope = {'type': 'lifespan'}

        await shim(scope, None, None)

        assert inner.scope == {'type': 'lifespan'}


class TestHeaderShimInstalled:
    """Importing the entrypoint wraps the server's IdentityMiddleware with the shim.

    Validates: Requirements Cross-tenant isolation verification.
    """

    def test_identity_middleware_is_patched(self) -> None:
        """The server module's IdentityMiddleware is the shim-installing factory."""
        assert getattr(server_module.IdentityMiddleware, '_aho_header_shim_installed', False)

    def test_factory_wraps_real_middleware_in_shim(self) -> None:
        """The patched factory returns a shim wrapping the real IdentityMiddleware instance."""
        result = server_module.IdentityMiddleware(_RecordingApp(), [])
        assert isinstance(result, entrypoint._AuthorizationHeaderShim)


class TestStatelessHttpEnabled:
    """Importing the entrypoint puts the server into stateless-http mode for AgentCore.

    Validates: Requirements AgentCore deployment demonstration.
    """

    def test_stateless_http_is_enabled(self) -> None:
        """The imported mcp instance has ``stateless_http`` enabled (AgentCore requirement)."""
        from awslabs.aws_healthomics_mcp_server.server import mcp

        assert mcp.settings.stateless_http is True

    def test_dns_rebinding_protection_disabled(self) -> None:
        """DNS-rebinding Host allow-listing is disabled so AgentCore's Host is accepted."""
        from awslabs.aws_healthomics_mcp_server.server import mcp

        assert mcp.settings.transport_security.enable_dns_rebinding_protection is False
