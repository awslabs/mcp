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

"""Property-based tests for deterministic single-mechanism selection.

These tests exercise the precedence-selection contract of
:class:`~awslabs.aws_healthomics_mcp_server.middleware.IdentityMiddleware`:
for any inbound request and any set of enabled mechanisms, when more than one
enabled mechanism applies the middleware derives exactly one context — the
highest-precedence applicable mechanism — and when none applies the request is
rejected with an authentication error and no AWS service call.
"""

import asyncio
from awslabs.aws_healthomics_mcp_server.consts import INBOUND_PRECEDENCE
from awslabs.aws_healthomics_mcp_server.middleware import IdentityMiddleware
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    get_credential_context,
)
from hypothesis import given, settings
from hypothesis import strategies as st


KNOWN_NAMES = ('sigv4', 'jwt', 'explicit')


def _make_context(identity_key: str) -> CredentialContext:
    """Build a distinct CredentialContext keyed by the mechanism name."""
    return CredentialContext(
        identity_key=identity_key,
        access_key_id='AKIAEXAMPLE',
        secret_access_key='secret',  # pragma: allowlist secret
        session_token=None,
        source='explicit',
    )


class _StubMechanism:
    """A configurable stub inbound mechanism that records derive() calls."""

    def __init__(self, name: str, applies_result: bool):
        self.name = name
        self._applies = applies_result
        self.context = _make_context(f'caller-{name}')
        self.derive_called = False

    def applies(self, scope: dict) -> bool:
        return self._applies

    def derive(self, scope: dict) -> CredentialContext:
        self.derive_called = True
        return self.context


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


def _precedence_index(name: str) -> int:
    """Return the documented precedence index, lowest priority for unknown names."""
    try:
        return INBOUND_PRECEDENCE.index(name)
    except ValueError:
        return len(INBOUND_PRECEDENCE)


def _expected_winner_name(ordered_specs: list[tuple[str, bool]]) -> str | None:
    """Replicate the middleware's deterministic selection over the input order.

    The middleware stably sorts the enabled mechanisms by precedence index and
    selects the first whose applies() is True. Replicating that here lets the
    test assert exactly which mechanism must derive the context.
    """
    ordered = sorted(ordered_specs, key=lambda spec: _precedence_index(spec[0]))
    for name, applies_flag in ordered:
        if applies_flag:
            return name
    return None


@st.composite
def _unknown_name_pool(draw) -> list[str]:
    """Generate a small pool of unique names outside the documented precedence."""
    suffixes = draw(
        st.lists(
            st.text(alphabet=st.characters(categories=('Ll',)), min_size=1, max_size=4),
            unique=True,
            max_size=3,
        )
    )
    return [f'custom-{suffix}' for suffix in suffixes]


@st.composite
def _multi_applicable_specs(draw) -> list[tuple[str, bool]]:
    """Generate enabled-mechanism specs where at least two mechanisms apply.

    Returns a list of (name, applies_flag) tuples in arbitrary input order, with
    unique names drawn from the documented mechanisms plus optional unknown ones,
    and at least two applicable mechanisms.
    """
    pool = list(KNOWN_NAMES) + draw(_unknown_name_pool())
    names = draw(st.lists(st.sampled_from(pool), unique=True, min_size=2, max_size=len(pool)))
    applicable = set(
        draw(st.lists(st.sampled_from(names), unique=True, min_size=2, max_size=len(names)))
    )
    ordered = draw(st.permutations(names))
    return [(name, name in applicable) for name in ordered]


@st.composite
def _none_applicable_specs(draw) -> list[tuple[str, bool]]:
    """Generate enabled-mechanism specs where no mechanism applies."""
    pool = list(KNOWN_NAMES) + draw(_unknown_name_pool())
    names = draw(st.lists(st.sampled_from(pool), unique=True, min_size=1, max_size=len(pool)))
    ordered = draw(st.permutations(names))
    return [(name, False) for name in ordered]


class TestDeterministicSingleMechanismSelection:
    """Property: Deterministic single-mechanism selection.

    Validates: Requirements Inbound identity mechanisms
    """

    @settings(max_examples=100)
    @given(specs=_multi_applicable_specs())
    def test_highest_precedence_applicable_mechanism_is_selected(
        self, specs: list[tuple[str, bool]]
    ):
        """When more than one enabled mechanism applies, exactly one derives.

        The selected mechanism is the highest in INBOUND_PRECEDENCE among the
        applicable ones; every other mechanism's derive() is never called, and the
        installed context is the winner's context (Requirement 13.6).
        """
        stubs = [_StubMechanism(name, applies_flag) for name, applies_flag in specs]
        app = _RecordingApp()
        middleware = IdentityMiddleware(app, list(stubs))
        send, _ = _make_send_collector()

        asyncio.run(middleware({'type': 'http'}, _noop_receive, send))

        winner_name = _expected_winner_name(specs)
        assert winner_name is not None

        winner = next(stub for stub in stubs if stub.name == winner_name)
        assert winner.derive_called is True
        for stub in stubs:
            if stub.name != winner_name:
                assert stub.derive_called is False

        # Exactly one mechanism derived the context.
        assert sum(1 for stub in stubs if stub.derive_called) == 1
        # The wrapped app observed the winner's context.
        assert app.called is True
        assert app.observed_context is winner.context
        # The context is reset on completion.
        assert get_credential_context() is None

    @settings(max_examples=100)
    @given(specs=_none_applicable_specs())
    def test_no_applicable_mechanism_rejects_without_side_effects(
        self, specs: list[tuple[str, bool]]
    ):
        """When no enabled mechanism applies, the request is rejected with 401.

        The wrapped app is never called, no mechanism derives a context, and the
        credential contextvar remains unset — so no AWS service call occurs
        (Requirement 13.7).
        """
        stubs = [_StubMechanism(name, applies_flag) for name, applies_flag in specs]
        app = _RecordingApp()
        middleware = IdentityMiddleware(app, list(stubs))
        send, messages = _make_send_collector()

        asyncio.run(middleware({'type': 'http'}, _noop_receive, send))

        # No mechanism derived a context.
        assert all(stub.derive_called is False for stub in stubs)
        # The wrapped app was never dispatched (no tool runs, no AWS call).
        assert app.called is False
        # A 401 response was produced.
        assert messages[0]['type'] == 'http.response.start'
        assert messages[0]['status'] == 401
        # The context remains unset after the rejected request.
        assert get_credential_context() is None
