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

"""Harness deployment entrypoint for the remote-deployment integration tests.

This module is harness-owned code that lives inside the deployed container/process
only. It imports the *unmodified* server ``mcp`` instance and ``main`` entrypoint and
registers a single additional read-only ``WhoAmI`` tool used by the cross-tenant
isolation tests to observe the effective assumed-role identity of a request.

No server-package source is modified: the extra tool is attached to the already
constructed ``mcp`` instance at import time, and the server is started via its own
``main()``.

Because ``get_aws_session()`` resolves through the active credential resolver (the
``RequestScopedCredentialResolver`` when multi-tenant mode is enabled), the STS
identity returned by ``WhoAmI`` reflects the per-request assumed Tenant_Role — exactly
the signal the isolation tests compare against the expected Tenant_Role (Req 6.2).

The tool is strictly read-only and returns no Credential_Material: only the caller's
STS ARN, account id, and user id are returned.
"""

from awslabs.aws_healthomics_mcp_server import server as server_module
from awslabs.aws_healthomics_mcp_server.server import main, mcp
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from integration.harness.headers import TENANT_TOKEN_HEADER
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any, Dict


@mcp.tool(name='WhoAmI')
async def who_am_i(ctx: Context) -> Dict[str, Any]:
    """Return the caller's effective STS identity for isolation verification.

    The STS client is built from ``get_aws_session()``, so the call flows through the
    active request-scoped credential resolver and reports the identity of the role the
    server assumed for this request. The response contains no Credential_Material — only
    the STS ARN, account id, and user id.

    Args:
        ctx: MCP context for error reporting.

    Returns:
        Dictionary with the caller's ``arn``, ``account``, and ``user_id``.
    """
    try:
        sts = get_aws_session().client('sts')
        identity = sts.get_caller_identity()
        return {
            'arn': identity['Arn'],
            'account': identity['Account'],
            'user_id': identity['UserId'],
        }
    except Exception as e:
        error_message = f'Error resolving caller identity: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


class _AuthorizationHeaderShim:
    """ASGI shim that maps the forwarded tenant-token header onto ``Authorization``.

    AgentCore Runtime does not forward the reserved ``Authorization`` header to the container,
    so the harness forwards the bearer token in the non-reserved :data:`TENANT_TOKEN_HEADER`
    (allow-listed on the runtime). This shim wraps the server's ``IdentityMiddleware`` on the
    *outside* so that, before the middleware inspects the request, a request that carries the
    tenant-token header but no ``Authorization`` header has ``Authorization`` populated from it.
    Requests that already carry ``Authorization`` are passed through unchanged, so this is inert
    for any other fronting layer (e.g. the API Gateway deployment).

    This is harness-owned deployment glue that runs only inside the deployed container; it does
    not modify the server package source.
    """

    def __init__(self, app: Any) -> None:
        """Wrap the given ASGI application (the server's IdentityMiddleware)."""
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """Populate ``Authorization`` from the forwarded tenant-token header for HTTP scopes."""
        if scope.get('type') == 'http':
            headers = list(scope.get('headers') or [])
            has_authorization = any(name.lower() == b'authorization' for name, _ in headers)
            if not has_authorization:
                token_header = TENANT_TOKEN_HEADER.lower().encode('latin-1')
                forwarded = next(
                    (value for name, value in headers if name.lower() == token_header), None
                )
                if forwarded is not None:
                    scope = dict(scope)
                    scope['headers'] = [*headers, (b'authorization', forwarded)]
        await self.app(scope, receive, send)


def _relax_transport_security() -> None:
    """Disable the server's DNS-rebinding Host allow-list so AgentCore requests are accepted.

    The server's streamable-http transport enables DNS-rebinding protection with an allow-list
    of only loopback hosts. AgentCore Runtime forwards requests to the container with a
    non-loopback ``Host`` header, which that protection rejects with HTTP 421 (Misdirected
    Request). DNS-rebinding protection guards browser-origin attacks against locally-bound
    servers; behind AgentCore the container is not browser-reachable and AgentCore is the sole,
    authenticated ingress, so disabling the check is safe here. Harness deployment glue -- no
    server-package source is modified.
    """
    try:
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
    except (AttributeError, ImportError):  # pragma: no cover - SDK without this setting
        pass


def _enable_stateless_http() -> None:
    """Put the server's streamable-http transport into stateless mode for AgentCore.

    AgentCore Runtime automatically injects an ``Mcp-Session-Id`` header on every request. A
    stateful MCP server treats that as an unknown session and rejects the request with HTTP 421
    (Misdirected Request). AgentCore therefore requires the hosted MCP server to run stateless.
    This sets ``stateless_http`` on the already-constructed ``mcp`` instance's settings before
    ``main()`` builds the app -- harness deployment glue that changes no server-package source.
    """
    try:
        mcp.settings.stateless_http = True
    except AttributeError:  # pragma: no cover - SDK without this setting
        pass


def _install_header_shim() -> None:
    """Patch the server's ``IdentityMiddleware`` so it is wrapped by the header shim.

    The server builds its network app as ``IdentityMiddleware(base_app, mechanisms)``. Replacing
    the name in the server module with a factory that wraps the real middleware in
    :class:`_AuthorizationHeaderShim` inserts the shim *outside* ``IdentityMiddleware`` so it runs
    first and can populate ``Authorization`` before the middleware reads it. Idempotent.
    """
    if getattr(server_module.IdentityMiddleware, '_aho_header_shim_installed', False):
        return
    real_identity_middleware = server_module.IdentityMiddleware

    def _wrapped(app: Any, enabled_mechanisms: Any) -> _AuthorizationHeaderShim:
        return _AuthorizationHeaderShim(real_identity_middleware(app, enabled_mechanisms))

    _wrapped._aho_header_shim_installed = True  # type: ignore[attr-defined]
    server_module.IdentityMiddleware = _wrapped  # type: ignore[assignment]


# Install the shim and stateless-http setting at import time (before ``main()`` serves) so the
# deployed server both receives the caller's bearer token via Authorization and runs stateless
# as AgentCore Runtime requires.
_install_header_shim()
_enable_stateless_http()
_relax_transport_security()


if __name__ == '__main__':
    main()
