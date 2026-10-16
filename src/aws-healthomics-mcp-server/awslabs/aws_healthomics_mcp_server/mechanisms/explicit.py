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

"""Inbound explicit-credentials identity mechanism (Requirement 13.5).

This mechanism reads short-lived AWS credentials supplied directly in request
headers and builds a per-request
:class:`~awslabs.aws_healthomics_mcp_server.utils.aws_utils.CredentialContext`
from them, with no server-side exchange.

Header names (matched case-insensitively):

- ``X-Aws-Access-Key-Id`` (required)
- ``X-Aws-Secret-Access-Key`` (required)
- ``X-Aws-Session-Token`` (optional, but expected for short-lived credentials)

SECURITY: These headers carry live AWS credential material. This mechanism
therefore requires a *trusted transport*: it must only be enabled behind a
fronting layer / TLS that the operator controls, and the supplied credentials
MUST be short-lived (e.g. STS session credentials with a session token). The
credential header *values* are NEVER logged by this module — only header
presence and the non-secret ``identity_key`` (the access key id) ever surface in
logs. Treat the access key id as a low-sensitivity identifier; the secret access
key and session token must never be emitted anywhere.
"""

from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
)


# Canonical (lowercased) header names. ASGI delivers header names lowercased, but
# we normalize defensively so matching is case-insensitive regardless of source.
_ACCESS_KEY_ID_HEADER = 'x-aws-access-key-id'
_SECRET_ACCESS_KEY_HEADER = 'x-aws-secret-access-key'  # pragma: allowlist secret
_SESSION_TOKEN_HEADER = 'x-aws-session-token'


def _read_headers(scope: dict) -> dict[str, str]:
    """Extract headers from an ASGI scope into a lowercased name->value mapping.

    ``scope['headers']`` is a list of ``(bytes, bytes)`` tuples. Names are
    lowercased so lookups are case-insensitive. Values are decoded as latin-1
    (the HTTP header byte encoding) and stripped of surrounding whitespace. If a
    header appears more than once, the last occurrence wins.

    Args:
        scope: The ASGI HTTP connection scope.

    Returns:
        dict[str, str]: Mapping of lowercased header name to stripped value.
    """
    headers: dict[str, str] = {}
    for raw_name, raw_value in scope.get('headers', []):
        try:
            name = raw_name.decode('latin-1').strip().lower()
            value = raw_value.decode('latin-1').strip()
        except (AttributeError, UnicodeDecodeError):
            # Skip malformed header entries rather than failing the whole request
            # here; derive() applies the authoritative presence checks.
            continue
        headers[name] = value
    return headers


class InboundExplicitCredentials:
    """Derive a request identity from explicit AWS credentials in request headers.

    Implements the
    :class:`~awslabs.aws_healthomics_mcp_server.middleware.InboundMechanism`
    protocol. :meth:`applies` returns ``True`` when both the access-key-id and
    secret-access-key headers are present (and non-empty); :meth:`derive` builds a
    :class:`CredentialContext` directly from those headers.

    SECURITY: requires a trusted transport and short-lived credentials. The
    credential header values are never logged (see module docstring).
    """

    name = 'explicit'

    def applies(self, scope: dict) -> bool:
        """Return whether explicit short-lived AWS credentials are present.

        Detects the explicit-credentials headers in the request. Returns ``True``
        only when both the access-key-id and secret-access-key headers are present
        with non-empty values; the session-token header is optional.

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            bool: ``True`` if this mechanism can derive an identity from the request.
        """
        headers = _read_headers(scope)
        return bool(headers.get(_ACCESS_KEY_ID_HEADER) and headers.get(_SECRET_ACCESS_KEY_HEADER))

    def derive(self, scope: dict) -> CredentialContext:
        """Build a :class:`CredentialContext` from the explicit-credential headers.

        Reads the access key id, secret access key, and optional session token from
        the request headers and constructs a context with ``source='explicit'`` and
        ``identity_key`` set to the access key id (a stable per-credential identity
        used for cache keying). Defensively re-validates that the required headers
        are present and non-empty even though :meth:`applies` should have gated this
        call; the context is never partially populated.

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            CredentialContext: The per-request identity built from the headers.

        Raises:
            CredentialDerivationError: If the required access-key-id or
                secret-access-key header is missing or empty.
        """
        headers = _read_headers(scope)
        access_key_id = headers.get(_ACCESS_KEY_ID_HEADER)
        secret_access_key = headers.get(_SECRET_ACCESS_KEY_HEADER)
        session_token = headers.get(_SESSION_TOKEN_HEADER) or None

        # Defensive: never partially populate. Do not include header values in the
        # error message — only the (non-secret) fact that they were absent.
        if not access_key_id or not secret_access_key:
            raise CredentialDerivationError(
                'Explicit-credentials mechanism requires both the '
                f'{_ACCESS_KEY_ID_HEADER!r} and {_SECRET_ACCESS_KEY_HEADER!r} '
                'request headers to be present and non-empty.'
            )

        return CredentialContext(
            identity_key=access_key_id,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            source='explicit',
        )
