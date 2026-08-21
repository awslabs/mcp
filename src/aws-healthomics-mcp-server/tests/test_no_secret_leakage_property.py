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

"""Property test: No secret leakage.

Property: No secret leakage
Validates: Requirements No Credential Logging

For arbitrary fabricated bearer tokens and fabricated STS credentials (access
key id, secret access key, and session token):

(a) ``repr(CredentialContext(...))`` redacts the credential material, so neither
    the secret access key nor the session token (nor the access key id) appears
    in the rendered string.
(b) When ``InboundJwtExchange.derive`` fails (the STS ``AssumeRole`` call raises,
    or the bearer token is malformed), the raised ``CredentialDerivationError``
    message and any captured loguru output contain none of: the bearer token, the
    secret access key, or the session token.

No real tokens, credentials, or AWS calls are used. Bearer tokens are fabricated
unsigned JWTs (see ``tests/test_jwt_derive_assume_role_shape.py``) and the STS
client is a raising stub whose error message deliberately embeds the fabricated
secret material to prove the code never forwards it into its own error or logs.
Hypothesis conventions mirror ``tests/test_partition_cache_isolation.py``.
"""

import base64
import contextlib
import json
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import StaticRoleResolver
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
)
from botocore.exceptions import ClientError
from hypothesis import given, settings
from hypothesis import strategies as st
from loguru import logger


ROLE_ARN = 'arn:aws:iam::123456789012:role/per-tenant-role'
IDENTITY_KEY = 'identity-under-test'


# Non-trivial secret substrings. A minimum length keeps accidental empty-string
# or single-character matches from producing false negatives, and the printable,
# non-space ASCII alphabet keeps generated values away from whitespace-formatted
# log scaffolding. ``source`` is sampled from the valid mechanism identifiers so
# the redacted repr is otherwise fully determined.
secret_text = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=12,
    max_size=48,
)

# A caller identifier for the JWT ``sub`` claim. It becomes the (non-secret)
# identity_key, so it is generated independently of the secret material.
caller_text = st.text(
    alphabet=st.characters(min_codepoint=0x30, max_codepoint=0x7A),
    min_size=1,
    max_size=12,
)

# Malformed bearer token: a non-trivial string carrying no '.' so it can never be
# split into JWT segments and always decodes-fails closed.
malformed_token_text = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E, exclude_characters='.'),
    min_size=12,
    max_size=48,
)

source_strategy = st.sampled_from(['sigv4', 'jwt', 'explicit'])


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


class _RaisingStsClient:
    """STS stub whose ``assume_role`` raises a ClientError embedding secrets.

    The error message deliberately carries the fabricated secret access key and
    session token so the test can prove ``derive`` never copies STS error text
    into its own raised error or into any log line.
    """

    def __init__(self, error: Exception):
        self.error = error

    def assume_role(self, **kwargs):
        raise self.error


def _factory(client):
    """Return an ``sts_client_factory`` yielding the given stub client."""

    def _make(region=None):
        return client

    return _make


@contextlib.contextmanager
def _capture_loguru():
    """Capture all loguru output (DEBUG and above) into a list of strings.

    loguru does not integrate with pytest's ``caplog``; a temporary sink is added
    with ``logger.add`` and removed on exit so no capture state leaks across the
    many inputs generated by ``@given``.
    """
    captured: list[str] = []

    def _sink(message):
        captured.append(str(message))

    handler_id = logger.add(_sink, level='DEBUG')
    try:
        yield captured
    finally:
        logger.remove(handler_id)


class TestNoSecretLeakage:
    """Property: No secret leakage.

    Validates: Requirements No Credential Logging.
    """

    @given(
        access_key_id=secret_text,
        secret_access_key=secret_text,
        session_token=secret_text,
        source=source_strategy,
    )
    @settings(max_examples=100)
    def test_credential_context_repr_redacts_secrets(
        self, access_key_id, secret_access_key, session_token, source
    ):
        """Property: No secret leakage (redacted repr arm).

        For any fabricated credential material, rendering a ``CredentialContext``
        as a string redacts the secret fields: none of the access key id, secret
        access key, or session token substrings appear in the repr.

        Validates: Requirements No Credential Logging.
        """
        context = CredentialContext(
            identity_key=IDENTITY_KEY,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            source=source,
        )

        rendered = repr(context)

        assert secret_access_key not in rendered
        assert session_token not in rendered
        assert access_key_id not in rendered
        # The redaction placeholder is present and identity/source remain visible.
        assert "'***'" in rendered
        assert IDENTITY_KEY in rendered

    @given(
        caller=caller_text,
        access_key_id=secret_text,
        secret_access_key=secret_text,
        session_token=secret_text,
    )
    @settings(max_examples=100)
    def test_sts_failure_never_leaks_token_or_secrets(
        self, caller, access_key_id, secret_access_key, session_token
    ):
        """Property: No secret leakage (STS failure arm).

        For any fabricated bearer token and fabricated STS credentials, when the
        STS ``AssumeRole`` call fails, neither the bearer token nor the secret
        access key nor the session token appears in the raised
        ``CredentialDerivationError`` message or in any captured log output --
        even when the STS error itself embeds that secret material.

        Validates: Requirements No Credential Logging.
        """
        token = _make_jwt({'sub': caller})
        # The STS error deliberately embeds secret material; the code must not
        # forward it into its own error or logs.
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': f'{access_key_id} {secret_access_key} {session_token}',
                }
            },
            operation_name='AssumeRole',
        )
        mechanism = InboundJwtExchange(
            role_resolver=StaticRoleResolver(ROLE_ARN),
            sts_client_factory=_factory(_RaisingStsClient(error)),
        )

        with _capture_loguru() as captured:
            try:
                mechanism.derive(_bearer_scope(token))
                raise AssertionError('derive should have failed closed on STS error')
            except CredentialDerivationError as exc:
                message = str(exc)

        combined_logs = '\n'.join(captured)
        for secret in (token, secret_access_key, session_token):
            assert secret not in message
            assert secret not in combined_logs

    @given(token=malformed_token_text)
    @settings(max_examples=100)
    def test_malformed_token_failure_never_leaks_token(self, token):
        """Property: No secret leakage (malformed-token arm).

        For any malformed bearer token, the fail-closed
        ``CredentialDerivationError`` message and any captured log output never
        contain the token substring, so the rejected token is never disclosed.

        Validates: Requirements No Credential Logging.
        """
        mechanism = InboundJwtExchange(
            role_resolver=StaticRoleResolver(ROLE_ARN),
            sts_client_factory=_factory(_RaisingStsClient(RuntimeError('unused'))),
        )

        with _capture_loguru() as captured:
            try:
                mechanism.derive(_bearer_scope(token))
                raise AssertionError('derive should have failed closed on bad token')
            except CredentialDerivationError as exc:
                message = str(exc)

        combined_logs = '\n'.join(captured)
        assert token not in message
        assert token not in combined_logs
