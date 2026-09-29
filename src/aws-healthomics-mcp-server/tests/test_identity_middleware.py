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

"""Minimal unit tests for the identity middleware.

Comprehensive multi-tenant integration tests are covered by task 10.2; these
tests cover the core middleware contract: non-HTTP passthrough, 401 rejection on
``InboundAuthError`` without dispatch, and contextvar set/reset around dispatch.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.middleware import (
    IdentityMiddleware,
    InboundMechanism,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    InboundAuthError,
    get_credential_context,
)


def _make_context(identity_key: str = 'caller-1') -> CredentialContext:
    """Build a CredentialContext for tests."""
    return CredentialContext(
        identity_key=identity_key,
        access_key_id='AKIAEXAMPLE',
        secret_access_key='secret',  # pragma: allowlist secret
        session_token=None,
        source='explicit',
    )


class _StubMechanism:
    """A configurable stub inbound mechanism."""

    def __init__(
        self,
        name: str,
        applies_result: bool,
        context: CredentialContext | None = None,
        error: InboundAuthError | None = None,
    ):
        self.name = name
        self._applies = applies_result
        self._context = context
        self._error = error
        self.derive_called = False

    def applies(self, scope: dict) -> bool:
        return self._applies

    def derive(self, scope: dict) -> CredentialContext:
        self.derive_called = True
        if self._error is not None:
            raise self._error
        assert self._context is not None
        return self._context


class _RecordingApp:
    """An ASGI app that records whether it was called and the active context."""

    def __init__(self):
        self.called = False
        self.observed_context = None

    async def __call__(self, scope, receive, send):
        self.called = True
        self.observed_context = get_credential_context()


async def _noop_receive():
    return {'type': 'http.request'}


def _make_send_collector():
    """Return (send, messages) where send appends ASGI messages to messages."""
    messages: list[dict] = []

    async def send(message):
        messages.append(message)

    return send, messages


def test_stub_mechanism_satisfies_protocol():
    """The stub conforms to the InboundMechanism Protocol."""
    assert isinstance(_StubMechanism('explicit', True), InboundMechanism)


@pytest.mark.asyncio
async def test_non_http_scope_passes_through_unchanged():
    """Non-HTTP scopes are dispatched without deriving or setting a context."""
    app = _RecordingApp()
    mechanism = _StubMechanism('explicit', applies_result=True, context=_make_context())
    middleware = IdentityMiddleware(app, [mechanism])
    send, messages = _make_send_collector()

    await middleware({'type': 'lifespan'}, _noop_receive, send)

    assert app.called is True
    assert mechanism.derive_called is False
    assert app.observed_context is None
    assert messages == []


@pytest.mark.asyncio
async def test_http_request_sets_context_before_dispatch_and_resets():
    """An HTTP request installs the context before dispatch and resets afterwards."""
    app = _RecordingApp()
    ctx = _make_context('caller-xyz')
    mechanism = _StubMechanism('explicit', applies_result=True, context=ctx)
    middleware = IdentityMiddleware(app, [mechanism])
    send, _ = _make_send_collector()

    assert get_credential_context() is None

    await middleware({'type': 'http'}, _noop_receive, send)

    # The wrapped app observed the request context during dispatch.
    assert app.called is True
    assert app.observed_context is ctx
    # The context is reset on completion (Requirement 12.3).
    assert get_credential_context() is None


@pytest.mark.asyncio
async def test_inbound_auth_error_rejects_with_401_and_no_dispatch():
    """An InboundAuthError yields a 401 and the wrapped app is never called."""
    app = _RecordingApp()
    mechanism = _StubMechanism(
        'explicit',
        applies_result=True,
        error=InboundAuthError('bad creds'),
    )
    middleware = IdentityMiddleware(app, [mechanism])
    send, messages = _make_send_collector()

    await middleware({'type': 'http'}, _noop_receive, send)

    assert app.called is False
    assert get_credential_context() is None
    assert messages[0]['type'] == 'http.response.start'
    assert messages[0]['status'] == 401
    assert messages[1]['type'] == 'http.response.body'
    # Body must not leak credential details.
    assert b'secret' not in messages[1]['body']


@pytest.mark.asyncio
async def test_no_mechanism_applies_rejects_with_401():
    """When no enabled mechanism applies, the request is rejected with 401."""
    app = _RecordingApp()
    mechanism = _StubMechanism('explicit', applies_result=False)
    middleware = IdentityMiddleware(app, [mechanism])
    send, messages = _make_send_collector()

    await middleware({'type': 'http'}, _noop_receive, send)

    assert app.called is False
    assert messages[0]['status'] == 401


@pytest.mark.asyncio
async def test_first_applicable_mechanism_is_selected():
    """The first mechanism whose applies() is True is selected (in-order)."""
    app = _RecordingApp()
    ctx_first = _make_context('first')
    ctx_second = _make_context('second')
    first = _StubMechanism('sigv4', applies_result=True, context=ctx_first)
    second = _StubMechanism('explicit', applies_result=True, context=ctx_second)
    middleware = IdentityMiddleware(app, [first, second])
    send, _ = _make_send_collector()

    await middleware({'type': 'http'}, _noop_receive, send)

    assert first.derive_called is True
    assert second.derive_called is False
    assert app.observed_context is ctx_first


@pytest.mark.asyncio
async def test_precedence_is_independent_of_input_order():
    """Selection follows INBOUND_PRECEDENCE regardless of the order supplied.

    Both mechanisms apply, but ``sigv4`` outranks ``explicit`` in the documented
    precedence order. Even when passed lowest-precedence-first, the higher-
    precedence mechanism derives the context (Requirement 13.6).
    """
    app = _RecordingApp()
    ctx_sigv4 = _make_context('sigv4-caller')
    ctx_explicit = _make_context('explicit-caller')
    sigv4 = _StubMechanism('sigv4', applies_result=True, context=ctx_sigv4)
    explicit = _StubMechanism('explicit', applies_result=True, context=ctx_explicit)
    # Pass in reverse precedence order: explicit first, then sigv4.
    middleware = IdentityMiddleware(app, [explicit, sigv4])
    send, _ = _make_send_collector()

    await middleware({'type': 'http'}, _noop_receive, send)

    assert sigv4.derive_called is True
    assert explicit.derive_called is False
    assert app.observed_context is ctx_sigv4


@pytest.mark.asyncio
async def test_highest_precedence_applicable_mechanism_wins_over_lower():
    """A lower-precedence mechanism is skipped when a higher one applies.

    ``jwt`` outranks ``explicit``; with both applicable and supplied in arbitrary
    order, the ``jwt`` mechanism derives the context.
    """
    app = _RecordingApp()
    ctx_jwt = _make_context('jwt-caller')
    ctx_explicit = _make_context('explicit-caller')
    jwt = _StubMechanism('jwt', applies_result=True, context=ctx_jwt)
    explicit = _StubMechanism('explicit', applies_result=True, context=ctx_explicit)
    middleware = IdentityMiddleware(app, [explicit, jwt])
    send, _ = _make_send_collector()

    await middleware({'type': 'http'}, _noop_receive, send)

    assert jwt.derive_called is True
    assert explicit.derive_called is False
    assert app.observed_context is ctx_jwt


@pytest.mark.asyncio
async def test_lower_precedence_applies_when_higher_does_not():
    """When the highest-precedence mechanism does not apply, the next one is used."""
    app = _RecordingApp()
    ctx_explicit = _make_context('explicit-caller')
    sigv4 = _StubMechanism('sigv4', applies_result=False)
    explicit = _StubMechanism('explicit', applies_result=True, context=ctx_explicit)
    # Supplied lowest-precedence-first to confirm ordering is by precedence.
    middleware = IdentityMiddleware(app, [explicit, sigv4])
    send, _ = _make_send_collector()

    await middleware({'type': 'http'}, _noop_receive, send)

    assert sigv4.derive_called is False
    assert explicit.derive_called is True
    assert app.observed_context is ctx_explicit


def test_unknown_mechanism_names_sort_after_known_names():
    """Unknown names are ordered after known ones, preserving their input order."""
    known = _StubMechanism('explicit', applies_result=False)
    unknown_a = _StubMechanism('custom-a', applies_result=False)
    unknown_b = _StubMechanism('custom-b', applies_result=False)
    middleware = IdentityMiddleware(_RecordingApp(), [unknown_b, known, unknown_a])

    ordered_names = [mechanism.name for mechanism in middleware.mechanisms]

    # Known 'explicit' comes first; the two unknown names keep their relative
    # input order (unknown_b before unknown_a) after the known mechanism.
    assert ordered_names == ['explicit', 'custom-b', 'custom-a']
