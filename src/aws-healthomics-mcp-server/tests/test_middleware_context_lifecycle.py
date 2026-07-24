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

"""Integration tests for the identity middleware credential-context lifecycle.

These end-to-end tests exercise the real
:class:`~awslabs.aws_healthomics_mcp_server.middleware.IdentityMiddleware` together
with real inbound mechanisms
(:class:`~awslabs.aws_healthomics_mcp_server.mechanisms.explicit.InboundExplicitCredentials`,
:class:`~awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange.InboundJwtExchange`)
and the real
:class:`~awslabs.aws_healthomics_mcp_server.utils.aws_utils.RequestScopedCredentialResolver`,
mocking only the AWS boundary (``boto3.Session`` / STS) so no real AWS call is ever
made.

They cover the credential-context lifecycle contract:

- Requirement Request-scoped credential resolution: the middleware populates the
  Credential_Context before any tool for the request executes (8.3), and when no
  Credential_Context is present the resolver returns an authentication error, makes
  no AWS call, and does not fall back to another context (8.6). Concurrent requests
  each use only their own Credential_Context (8.5).
- Requirement Per-request credential freshness: the request's Credential_Context is
  discarded on completion so it is not available to any subsequent request (12.3),
  and when credential derivation fails the middleware returns an authentication
  error without calling any AWS service and without falling back (12.4).
"""

import asyncio
import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.explicit import InboundExplicitCredentials
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.middleware import IdentityMiddleware
from awslabs.aws_healthomics_mcp_server.utils import aws_utils
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialRequest,
    NoRequestIdentityError,
    RequestScopedCredentialResolver,
    get_credential_context,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# ASGI plumbing helpers.
# ---------------------------------------------------------------------------


def _http_scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    """Build a minimal ASGI HTTP scope with the given raw header tuples."""
    return {'type': 'http', 'headers': headers or []}


def _explicit_headers(
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None = None,
) -> list[tuple[bytes, bytes]]:
    """Build ASGI headers carrying explicit AWS credentials."""
    headers = [
        (b'x-aws-access-key-id', access_key_id.encode('latin-1')),
        (b'x-aws-secret-access-key', secret_access_key.encode('latin-1')),
    ]
    if session_token is not None:
        headers.append((b'x-aws-session-token', session_token.encode('latin-1')))
    return headers


def _bearer_headers(claims: dict) -> list[tuple[bytes, bytes]]:
    """Build an ``Authorization: Bearer <jwt>`` header for the given claims."""

    def _b64url(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')

    header_segment = _b64url(json.dumps({'alg': 'none', 'typ': 'JWT'}).encode('utf-8'))
    payload_segment = _b64url(json.dumps(claims).encode('utf-8'))
    token = f'{header_segment}.{payload_segment}.'  # empty signature (not verified)
    return [(b'authorization', f'Bearer {token}'.encode('latin-1'))]


async def _noop_receive():
    """A minimal ASGI receive callable."""
    return {'type': 'http.request'}


def _make_send_collector():
    """Return (send, messages) where send appends ASGI messages to messages."""
    messages: list[dict] = []

    async def send(message):
        messages.append(message)

    return send, messages


class _RecordingApp:
    """ASGI app that records dispatch, the active context, and a resolved session.

    During dispatch it reads the active Credential_Context and, when
    ``resolve_session`` is set, uses a real
    :class:`RequestScopedCredentialResolver` to build a session from that context —
    confirming a usable session is derived from the request's identity.
    """

    def __init__(self, resolve_session: bool = False):
        self.called = False
        self.observed_context = None
        self.observed_identity_key: str | None = None
        self.resolved_session = None
        self._resolve_session = resolve_session

    async def __call__(self, scope, receive, send):
        self.called = True
        ctx = get_credential_context()
        self.observed_context = ctx
        self.observed_identity_key = ctx.identity_key if ctx is not None else None
        if self._resolve_session:
            self.resolved_session = RequestScopedCredentialResolver().resolve(CredentialRequest())


class _RaisingApp:
    """ASGI app that raises during dispatch (to exercise the finally reset)."""

    def __init__(self):
        self.called = False

    async def __call__(self, scope, receive, send):
        self.called = True
        raise RuntimeError('boom during dispatch')


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_context():
    """Ensure no credential context leaks across tests."""
    from awslabs.aws_healthomics_mcp_server.utils.aws_utils import _credential_context

    assert get_credential_context() is None
    yield
    # Force-clear in case a test left a context installed.
    _credential_context.set(None)


@pytest.fixture
def patched_boto_session(monkeypatch):
    """Patch ``boto3.Session`` in aws_utils so session building never hits AWS.

    Returns the MagicMock standing in for the ``boto3.Session`` class so tests can
    assert whether a session was (or was not) constructed.
    """
    session_factory = MagicMock(name='boto3.Session')
    monkeypatch.setattr(aws_utils.boto3, 'Session', session_factory)
    return session_factory


# ---------------------------------------------------------------------------
# 1. Context set before dispatch, reset after completion.
# ---------------------------------------------------------------------------


async def test_context_set_before_dispatch_and_reset_after(patched_boto_session):
    """Context is installed before dispatch and discarded on completion.

    Validates: Requirement Request-scoped credential resolution (middleware
    populates the Credential_Context before any tool executes) and Requirement
    Per-request credential freshness (the context is discarded on completion).

    The wrapped app resolves a session from the active context via the real
    RequestScopedCredentialResolver during dispatch, confirming a usable session is
    built from the request identity; ``boto3.Session`` is patched so no AWS call
    occurs.
    """
    app = _RecordingApp(resolve_session=True)
    middleware = IdentityMiddleware(app, [InboundExplicitCredentials()])
    send, _ = _make_send_collector()
    scope = _http_scope(_explicit_headers('AKIAEXAMPLE', 'secret', 'token-123'))

    assert get_credential_context() is None

    await middleware(scope, _noop_receive, send)

    # The context was present during dispatch and carried the request identity.
    assert app.called is True
    assert app.observed_context is not None
    assert app.observed_identity_key == 'AKIAEXAMPLE'
    assert app.observed_context.source == 'explicit'
    # A usable session was built from the request context (no AWS call: patched).
    assert app.resolved_session is patched_boto_session.return_value
    assert patched_boto_session.call_count == 1
    # The context is reset on completion.
    assert get_credential_context() is None


# ---------------------------------------------------------------------------
# 2. Concurrent request isolation.
# ---------------------------------------------------------------------------


async def test_concurrent_requests_observe_only_their_own_context(patched_boto_session):
    """Concurrent requests each observe only their own identity's context.

    Validates: Requirement Request-scoped credential resolution (concurrent
    requests each use their own Credential_Context and never another concurrent
    request's context).
    """

    class _InterleavingApp:
        def __init__(self):
            self.observed_identity_key: str | None = None

        async def __call__(self, scope, receive, send):
            # Read, yield to let the other request run, then read again to catch
            # any cross-request contextvar bleed.
            first = get_credential_context()
            await asyncio.sleep(0.01)
            second = get_credential_context()
            assert first is second
            self.observed_identity_key = second.identity_key if second else None

    app_a = _InterleavingApp()
    app_b = _InterleavingApp()
    mw_a = IdentityMiddleware(app_a, [InboundExplicitCredentials()])
    mw_b = IdentityMiddleware(app_b, [InboundExplicitCredentials()])
    send_a, _ = _make_send_collector()
    send_b, _ = _make_send_collector()
    scope_a = _http_scope(_explicit_headers('AKIA-A', 'secret-a'))
    scope_b = _http_scope(_explicit_headers('AKIA-B', 'secret-b'))

    await asyncio.gather(
        mw_a(scope_a, _noop_receive, send_a),
        mw_b(scope_b, _noop_receive, send_b),
    )

    assert app_a.observed_identity_key == 'AKIA-A'
    assert app_b.observed_identity_key == 'AKIA-B'
    # No context leaks after both complete.
    assert get_credential_context() is None


# ---------------------------------------------------------------------------
# 3. Missing context / no mechanism applies.
# ---------------------------------------------------------------------------


async def test_no_mechanism_applies_rejects_without_dispatch_or_aws(patched_boto_session):
    """No applicable mechanism yields 401, no dispatch, and no AWS call.

    Validates: Requirement Request-scoped credential resolution (when no
    Credential_Context is present the request returns an authentication error, no
    AWS service is called, and there is no fallback).
    """
    app = _RecordingApp(resolve_session=True)
    # Explicit mechanism enabled, but the request carries no matching headers.
    middleware = IdentityMiddleware(app, [InboundExplicitCredentials()])
    send, messages = _make_send_collector()
    scope = _http_scope(headers=[(b'content-type', b'application/json')])

    await middleware(scope, _noop_receive, send)

    # The wrapped app was never dispatched (no tool runs).
    assert app.called is False
    # A 401 rejection was produced.
    assert messages[0]['type'] == 'http.response.start'
    assert messages[0]['status'] == 401
    # No AWS session was ever built.
    assert patched_boto_session.call_count == 0
    # No context remains after the rejected request.
    assert get_credential_context() is None


async def test_resolver_without_context_raises_and_makes_no_aws_call(patched_boto_session):
    """A tool path resolving with no context raises without any AWS call.

    Validates: Requirement Request-scoped credential resolution (no
    Credential_Context present -> authentication error, no AWS call, no fallback).
    """
    assert get_credential_context() is None

    with pytest.raises(NoRequestIdentityError):
        RequestScopedCredentialResolver().resolve(CredentialRequest())

    assert patched_boto_session.call_count == 0


# ---------------------------------------------------------------------------
# 4. Failed derivation.
# ---------------------------------------------------------------------------


async def test_failed_derivation_rejects_without_dispatch_or_context(patched_boto_session):
    """A derivation failure yields 401, no dispatch, no context, no session build.

    Validates: Requirement Per-request credential freshness (when credential
    derivation fails, an authentication error is returned, no AWS service is called
    for the request, and there is no fallback to process-level or previously derived
    credentials).

    A JWT exchange mechanism is wired with an injected STS client whose
    ``assume_role`` raises, so :meth:`derive` raises CredentialDerivationError.
    """
    sts_client = MagicMock(name='sts')
    sts_client.assume_role.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}}, 'AssumeRole'
    )
    sts_factory = MagicMock(name='sts_factory', return_value=sts_client)

    jwt_mechanism = InboundJwtExchange(
        role_arn='arn:aws:iam::123456789012:role/tenant-role',
        sts_client_factory=sts_factory,
    )
    app = _RecordingApp(resolve_session=True)
    middleware = IdentityMiddleware(app, [jwt_mechanism])
    send, messages = _make_send_collector()
    scope = _http_scope(_bearer_headers({'sub': 'caller-1'}))

    await middleware(scope, _noop_receive, send)

    # The STS exchange was attempted and failed.
    assert sts_client.assume_role.call_count == 1
    # The wrapped app was never dispatched.
    assert app.called is False
    # A 401 rejection was produced.
    assert messages[0]['status'] == 401
    # No request-scoped session was ever built from a context (no fallback).
    assert patched_boto_session.call_count == 0
    # No context was installed.
    assert get_credential_context() is None


# ---------------------------------------------------------------------------
# 5. Reset even when the wrapped app raises.
# ---------------------------------------------------------------------------


async def test_context_reset_when_wrapped_app_raises(patched_boto_session):
    """The finally block resets the context even if dispatch raises.

    Validates: Requirement Per-request credential freshness (the request's
    Credential_Context is discarded on completion, including on error paths, so it
    is not available to any subsequent request).
    """
    app = _RaisingApp()
    middleware = IdentityMiddleware(app, [InboundExplicitCredentials()])
    send, _ = _make_send_collector()
    scope = _http_scope(_explicit_headers('AKIAEXAMPLE', 'secret'))

    with pytest.raises(RuntimeError, match='boom during dispatch'):
        await middleware(scope, _noop_receive, send)

    # The app was dispatched (context was set before it ran) but the finally block
    # still discarded the context.
    assert app.called is True
    assert get_credential_context() is None
