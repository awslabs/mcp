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

"""Property-based tests for JWT-to-STS exchange failure side effects.

Covers Property 19 (JWT exchange failure produces auth error without side
effects) from the remote-transport-multi-tenant design, validating Requirements
13.4: for any JWT-exchange request whose STS assume-role call fails, the
mechanism/middleware returns an authentication error, populates no credential
context, and makes no other AWS service call for that request.

These tests never use real tokens, credentials, or AWS calls. The JWT is a
fabricated unsigned token carrying only a ``sub`` claim, and the STS client is a
stub that records every attribute access (so we can assert no AWS call other than
the single failing ``assume_role`` is made).
"""

import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import (
    InboundJwtExchange,
)
from awslabs.aws_healthomics_mcp_server.middleware import IdentityMiddleware
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialDerivationError,
    InboundAuthError,
    get_credential_context,
)
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
)
from botocore.exceptions import (
    ConnectionError as BotoConnectionError,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


ROLE_ARN = 'arn:aws:iam::123456789012:role/per-tenant-role'


def _make_jwt(claims: dict) -> str:
    """Build an unsigned compact JWT carrying the given claims (no signature)."""

    def _b64(obj: dict) -> str:
        raw = json.dumps(obj).encode('utf-8')
        return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')

    header = _b64({'alg': 'none', 'typ': 'JWT'})
    payload = _b64(claims)
    return f'{header}.{payload}.'


def _bearer_scope(token: str) -> dict:
    """Build an ASGI HTTP scope with an Authorization: Bearer header."""
    return {
        'type': 'http',
        'headers': [(b'authorization', f'Bearer {token}'.encode('latin-1'))],
    }


class _RecordingStsClient:
    """STS stub whose ``assume_role`` always fails, recording all access.

    Records every assume_role call and flags any access to a *different*
    attribute (which would represent some other AWS call on the same client).
    """

    def __init__(self, error: Exception):
        self._error = error
        self.assume_role_calls: list[dict] = []
        self.other_attribute_access: list[str] = []

    def assume_role(self, **kwargs):
        self.assume_role_calls.append(kwargs)
        raise self._error

    def __getattr__(self, item: str):
        # assume_role is a real attribute resolved before __getattr__; any other
        # attribute access here would be an attempt at a different AWS call.
        self.other_attribute_access.append(item)
        raise AssertionError(f'Unexpected AWS client attribute access: {item!r}')


def _factory(client: _RecordingStsClient):
    """Return an sts_client_factory yielding the given recording stub."""
    factory_calls: list[object] = []

    def _make(region=None):
        factory_calls.append(region)
        return client

    _make.factory_calls = factory_calls  # type: ignore[attr-defined]
    return _make


# Strategy over STS failure modes: ClientError with varied error codes, plus
# representative BotoCoreError subclasses and the base BotoCoreError.
_CLIENT_ERROR_CODES = [
    'AccessDenied',
    'ExpiredTokenException',
    'InvalidIdentityToken',
    'RegionDisabledException',
    'MalformedPolicyDocument',
    'PackedPolicyTooLarge',
    'ThrottlingException',
]


def _client_error(code: str) -> ClientError:
    """Build a botocore ClientError for the AssumeRole operation."""
    return ClientError(
        error_response={'Error': {'Code': code, 'Message': f'{code} message'}},
        operation_name='AssumeRole',
    )


def _sts_errors() -> st.SearchStrategy[Exception]:
    """Strategy producing STS failure exceptions (ClientError / BotoCoreError)."""
    client_errors = st.sampled_from(_CLIENT_ERROR_CODES).map(_client_error)
    botocore_errors = st.sampled_from(
        [
            BotoCoreError(),
            BotoConnectionError(error='boom'),
            EndpointConnectionError(endpoint_url='https://sts.amazonaws.com'),
        ]
    )
    return st.one_of(client_errors, botocore_errors)


# Caller 'sub' claim strategy: non-empty text spanning a wide character range so
# session-name sanitization is exercised too.
_callers = st.text(min_size=1, max_size=40).filter(lambda value: value.strip() != '')


async def _noop_receive():
    return {'type': 'http.request'}


def _make_send_collector():
    """Return (send, messages) where send appends ASGI messages to messages."""
    messages: list[dict] = []

    async def send(message):
        messages.append(message)

    return send, messages


class _RecordingApp:
    """ASGI app that records whether it was dispatched and the active context."""

    def __init__(self):
        self.called = False
        self.observed_context = None

    async def __call__(self, scope, receive, send):
        self.called = True
        self.observed_context = get_credential_context()


class TestJwtExchangeFailureSideEffects:
    """Property 19: JWT exchange failure produces auth error without side effects.

    Validates: Requirements Inbound identity mechanisms (Requirement 13.4).
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(sts_error=_sts_errors(), caller=_callers)
    def test_mechanism_derive_failure_has_no_side_effects(self, sts_error: Exception, caller: str):
        """A failing STS exchange raises an auth error with no credential side effects.

        For any failing assume-role (varied error type/code) and any caller
        ``sub`` claim, ``derive`` raises ``CredentialDerivationError`` (an
        ``InboundAuthError``), the stub records exactly one ``assume_role`` call,
        no other AWS call is attempted, and no credential context is populated.

        Validates: Requirements Inbound identity mechanisms.
        """
        # The contextvar must be clean before and after; assert and clean up.
        assert get_credential_context() is None
        client = _RecordingStsClient(error=sts_error)
        token = _make_jwt({'sub': caller})
        mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

        try:
            with pytest.raises(CredentialDerivationError) as exc_info:
                mechanism.derive(_bearer_scope(token))

            # Authentication error surfaced as an InboundAuthError.
            assert isinstance(exc_info.value, InboundAuthError)
            # Exactly one assume_role call; no other AWS call attempted.
            assert len(client.assume_role_calls) == 1
            assert client.other_attribute_access == []
            # No credential context was populated for this request.
            assert get_credential_context() is None
        finally:
            assert get_credential_context() is None

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(sts_error=_sts_errors(), caller=_callers)
    @pytest.mark.asyncio
    async def test_middleware_rejects_with_401_and_no_dispatch(
        self, sts_error: Exception, caller: str
    ):
        """The middleware returns 401 and never dispatches the wrapped app on failure.

        For any failing assume-role and any caller ``sub`` claim, the
        ``IdentityMiddleware`` wrapping a recording app responds with HTTP 401,
        never calls the wrapped app (no tool dispatch), leaves the contextvar
        ``None`` afterwards, and triggers exactly one (failing) assume_role with
        no other AWS call.

        Validates: Requirements Inbound identity mechanisms.
        """
        assert get_credential_context() is None
        client = _RecordingStsClient(error=sts_error)
        token = _make_jwt({'sub': caller})
        mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))
        app = _RecordingApp()
        middleware = IdentityMiddleware(app, [mechanism])
        send, messages = _make_send_collector()

        try:
            await middleware(_bearer_scope(token), _noop_receive, send)

            # The wrapped app was never dispatched: no tool ran.
            assert app.called is False
            # The middleware responded with a 401 authentication rejection.
            assert messages[0]['type'] == 'http.response.start'
            assert messages[0]['status'] == 401
            # The contextvar is reset (None) after the request completes.
            assert get_credential_context() is None
            # Exactly one assume_role call; no other AWS call attempted.
            assert len(client.assume_role_calls) == 1
            assert client.other_attribute_access == []
        finally:
            assert get_credential_context() is None
