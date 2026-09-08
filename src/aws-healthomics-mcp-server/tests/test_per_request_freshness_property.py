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

"""Property-based tests for per-request credential freshness.

Property: Per-request credential freshness.

Validates: Requirements Per Request Credential Freshness.

These tests exercise the real
:class:`~awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange.InboundJwtExchange`
and the real
:class:`~awslabs.aws_healthomics_mcp_server.middleware.IdentityMiddleware` to
establish two arms of the freshness property across an arbitrary sequence of
requests with distinct caller identities:

- Fresh derivation per request: each request's ``derive`` performs a *distinct*
  ``sts:AssumeRole`` exchange (one call per request, never cached or reused), and
  the credentials it yields are the ones derived for that request's own identity.
- Discard on completion (and on error): after each request completes — whether it
  finishes normally or the wrapped app raises mid-dispatch — the middleware resets
  the request-scoped credential context so it is back to its default (``None``) and
  no subsequent request can read the prior request's credentials.

No real tokens, credentials, or AWS calls are used: JWTs are fabricated unsigned
tokens (see ``tests/test_jwt_derive_assume_role_shape.py``) and the STS client is a
recording stub that counts ``assume_role`` calls and returns fabricated
credentials derived from the caller identity. The boto3/ASGI plumbing mirrors the
patterns established in ``tests/test_middleware_context_lifecycle.py`` and the
Hypothesis conventions in ``tests/test_partition_cache_isolation.py``.
"""

import asyncio
import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.middleware import IdentityMiddleware
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_credential_context
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


ROLE_ARN = 'arn:aws:iam::123456789012:role/per-tenant-role'


# ---------------------------------------------------------------------------
# JWT / ASGI plumbing helpers (mirroring the sibling test modules).
# ---------------------------------------------------------------------------


def _make_jwt(claims: dict) -> str:
    """Build an unsigned compact JWT carrying the given claims (no signature)."""

    def _b64(obj: dict) -> str:
        raw = json.dumps(obj).encode('utf-8')
        return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')

    header = _b64({'alg': 'none', 'typ': 'JWT'})
    payload = _b64(claims)
    return f'{header}.{payload}.'


def _bearer_scope(token: str) -> dict:
    """Build an ASGI HTTP scope with an ``Authorization: Bearer`` header."""
    return {
        'type': 'http',
        'headers': [(b'authorization', f'Bearer {token}'.encode('latin-1'))],
    }


async def _noop_receive():
    """A minimal ASGI receive callable."""
    return {'type': 'http.request'}


async def _noop_send(message):
    """A minimal ASGI send callable that discards messages."""
    return None


# ---------------------------------------------------------------------------
# Recording STS client stub.
# ---------------------------------------------------------------------------


class _RecordingStsClient:
    """Records every ``assume_role`` call and returns caller-derived credentials.

    Each call's fabricated credentials embed the caller identity (read from the
    request's ABAC ``caller`` session tag) and the call ordinal, so the credentials
    handed back for one request are always distinguishable from those of any other
    request — making credential reuse across requests observable.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def assume_role(self, **kwargs):
        self.calls.append(kwargs)
        caller = kwargs['Tags'][0]['Value']
        ordinal = len(self.calls)
        return {
            'Credentials': {
                'AccessKeyId': f'ASIA-{caller}-{ordinal}',
                'SecretAccessKey': f'secret-{caller}-{ordinal}',
                'SessionToken': f'token-{caller}-{ordinal}',
            },
            'AssumedRoleUser': {
                'Arn': f'{ROLE_ARN}/{caller}',
                'AssumedRoleId': f'AROAEXAMPLE:{caller}',
            },
        }


def _factory_for(client: _RecordingStsClient):
    """Return an ``sts_client_factory`` that always yields the given stub client."""

    def _make(region=None):
        return client

    return _make


# ---------------------------------------------------------------------------
# ASGI apps used to drive the middleware.
# ---------------------------------------------------------------------------


class _RecordingApp:
    """ASGI app that records the identity of the context active during dispatch."""

    def __init__(self):
        self.observed_identity_keys: list[str | None] = []

    async def __call__(self, scope, receive, send):
        ctx = get_credential_context()
        self.observed_identity_keys.append(ctx.identity_key if ctx is not None else None)


class _RaisingApp:
    """ASGI app that raises mid-dispatch to exercise the finally-block reset."""

    async def __call__(self, scope, receive, send):
        raise RuntimeError('boom during dispatch')


# ---------------------------------------------------------------------------
# Hypothesis strategies.
# ---------------------------------------------------------------------------

# Distinct caller identities. Printable, non-space ASCII keeps the derived session
# names and tag values readable; ``unique=True`` guarantees each request carries a
# distinct caller identity, which is what makes cross-request credential reuse
# observable.
distinct_callers = st.lists(
    st.text(
        alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
        min_size=1,
        max_size=10,
    ),
    unique=True,
    min_size=1,
    max_size=6,
)


@pytest.fixture(autouse=True)
def reset_context():
    """Ensure no credential context leaks across tests or Hypothesis examples."""
    from awslabs.aws_healthomics_mcp_server.utils.aws_utils import _credential_context

    _credential_context.set(None)
    yield
    _credential_context.set(None)


class TestPerRequestCredentialFreshness:
    """Property: Per-request credential freshness.

    Validates: Requirements Per Request Credential Freshness.
    """

    @given(callers=distinct_callers)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_each_request_triggers_a_distinct_assume_role(self, callers):
        """Property: Per-request credential freshness (fresh derivation per request).

        For any sequence of requests with distinct caller identities, each request's
        ``derive`` performs exactly one ``sts:AssumeRole`` exchange scoped to that
        request: the total number of ``assume_role`` calls equals the number of
        requests (never fewer, which caching or reuse would cause), each call carries
        the request's own caller session tag, and the credentials returned to each
        request are the ones derived for that request — never a prior request's.

        Validates: Requirements Per Request Credential Freshness.
        """
        client = _RecordingStsClient()
        mechanism = InboundJwtExchange(
            role_arn=ROLE_ARN,
            sts_client_factory=_factory_for(client),
        )

        derived_access_key_ids: list[str] = []
        for caller in callers:
            context = mechanism.derive(_bearer_scope(_make_jwt({'sub': caller})))
            # Each request's context carries its own identity and jwt source.
            assert context.identity_key == caller
            assert context.source == 'jwt'
            derived_access_key_ids.append(context.access_key_id)

        # One distinct assume_role exchange per request: no caching, no reuse.
        assert len(client.calls) == len(callers)

        # Each exchange presented the request's own caller as the ABAC session tag,
        # in request order — proving the exchange is scoped to that request.
        recorded_callers = [call['Tags'][0]['Value'] for call in client.calls]
        assert recorded_callers == callers

        # The credentials handed to each request are distinct per request, so no
        # request received credentials derived for a different request.
        assert len(set(derived_access_key_ids)) == len(callers)

    @given(callers=distinct_callers, error_flags=st.data())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_context_is_reset_after_each_request_including_errors(self, callers, error_flags):
        """Property: Per-request credential freshness (discard on completion/error).

        For any sequence of requests — each of which either completes normally or
        raises mid-dispatch — the middleware resets the request-scoped credential
        context after every request so it returns to its default (``None``). No
        request can read a prior request's credentials: before each request the
        context is ``None``, during dispatch it carries only that request's identity,
        and after the request (whether it succeeded or raised) it is ``None`` again.

        Validates: Requirements Per Request Credential Freshness.
        """
        client = _RecordingStsClient()
        mechanism = InboundJwtExchange(
            role_arn=ROLE_ARN,
            sts_client_factory=_factory_for(client),
        )

        # No context is present before the first request.
        assert get_credential_context() is None

        for caller in callers:
            # Draw, per request, whether the wrapped app raises mid-dispatch.
            raises_mid_request = error_flags.draw(st.booleans())
            scope = _bearer_scope(_make_jwt({'sub': caller}))

            if raises_mid_request:
                middleware = IdentityMiddleware(_RaisingApp(), [mechanism])
                with pytest.raises(RuntimeError, match='boom during dispatch'):
                    asyncio.run(middleware(scope, _noop_receive, _noop_send))
            else:
                app = _RecordingApp()
                middleware = IdentityMiddleware(app, [mechanism])
                asyncio.run(middleware(scope, _noop_receive, _noop_send))
                # During dispatch the app observed only this request's identity.
                assert app.observed_identity_keys == [caller]

            # After each request — success or error — the context is discarded so no
            # subsequent request can read this request's credentials.
            assert get_credential_context() is None
