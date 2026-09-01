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

"""Inbound SigV4 identity mechanism (Requirement 13.1).

This mechanism derives a per-request
:class:`~awslabs.aws_healthomics_mcp_server.utils.aws_utils.CredentialContext`
from a request that carries an AWS Signature Version 4 ``Authorization`` header.

Trust model
-----------
SigV4 is treated as a first-class inbound mechanism because credential freshness
lives on the client: the caller signs each request with their *own* AWS
credentials. Crucially, SigV4 proves possession of the secret access key without
ever transmitting it, so this server **cannot** recover the caller's secret from
the signature alone.

This mechanism is therefore intended for deployments where a trusted fronting
layer (for example ``mcp-proxy-for-aws``, a reverse proxy, or an API gateway)
sits in front of the server, validates the SigV4 signature, and forwards the
caller's verified short-lived credentials to the server on trusted headers. In
that topology:

* The caller identity (access key id) is parsed from the SigV4 ``Authorization``
  header's ``Credential`` scope and used as the per-caller ``identity_key`` for
  cache partitioning.
* The server-usable credentials (secret access key and, when present, session
  token) are read from the forwarded headers documented below.

When the forwarded credential material required to build a usable session is
absent, :meth:`InboundSigV4.derive` raises
:class:`~awslabs.aws_healthomics_mcp_server.utils.aws_utils.CredentialDerivationError`
rather than partially populating a context. The server never falls back to
process-level credentials for the request.

Forwarded credential headers (set only by a trusted fronting layer):

* ``X-Aho-Forwarded-Secret-Access-Key`` — the caller's secret access key.
* ``X-Aho-Forwarded-Session-Token`` — the caller's session token (optional).
  The standard ``X-Amz-Security-Token`` header is also accepted as a fallback
  source for the session token.

SECURITY: no credential material (access key id, secret access key, session
token, or raw header values) is ever logged by this module.
"""

from awslabs.aws_healthomics_mcp_server.middleware import Scope
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
)
from loguru import logger


# SigV4 authorization scheme prefix (RFC-style scheme token for AWS SigV4).
_SIGV4_SCHEME = 'AWS4-HMAC-SHA256'

# Header names are compared lowercased; ASGI normalizes header names to bytes.
_AUTHORIZATION_HEADER = b'authorization'
_FORWARDED_SECRET_HEADER = b'x-aho-forwarded-secret-access-key'
_FORWARDED_SESSION_TOKEN_HEADER = b'x-aho-forwarded-session-token'
_AMZ_SECURITY_TOKEN_HEADER = b'x-amz-security-token'


def _header_value(scope: Scope, name: bytes) -> str | None:
    """Return the decoded value of the first matching header, or ``None``.

    ASGI ``scope['headers']`` is a list of ``(bytes, bytes)`` tuples with
    lowercased header names. Values are decoded as latin-1 (the HTTP header
    octet encoding) so arbitrary bytes never raise.

    Args:
        scope: The ASGI HTTP connection scope.
        name: The lowercased header name to look up, as bytes.

    Returns:
        str | None: The decoded header value, or ``None`` if not present.
    """
    headers = scope.get('headers') or []
    for raw_name, raw_value in headers:
        if raw_name == name:
            return raw_value.decode('latin-1')
    return None


def _parse_access_key_id(authorization: str) -> str | None:
    """Extract the access key id from a SigV4 ``Authorization`` header value.

    The SigV4 header has the shape::

        AWS4-HMAC-SHA256 Credential=<AKID>/<date>/<region>/<service>/aws4_request,
            SignedHeaders=..., Signature=...

    The access key id is the first element of the ``Credential`` scope.

    Args:
        authorization: The raw ``Authorization`` header value.

    Returns:
        str | None: The parsed access key id, or ``None`` if it cannot be parsed.
    """
    value = authorization.strip()
    if not value.startswith(_SIGV4_SCHEME):
        return None

    # Locate the Credential=<scope> component within the comma-separated params.
    for component in value[len(_SIGV4_SCHEME) :].split(','):
        component = component.strip()
        if component.startswith('Credential='):
            scope_value = component[len('Credential=') :]
            access_key_id = scope_value.split('/', 1)[0].strip()
            return access_key_id or None
    return None


class InboundSigV4:
    """Derive a per-request identity from presented SigV4 credentials.

    Implements the
    :class:`~awslabs.aws_healthomics_mcp_server.middleware.InboundMechanism`
    Protocol for AWS Signature Version 4 signed requests (Requirement 13.1). See
    the module docstring for the trust model and the forwarded-header contract.
    """

    name = 'sigv4'

    def applies(self, scope: Scope) -> bool:
        """Return whether the request carries a SigV4 ``Authorization`` header.

        Detects an inbound SigV4-signed request by inspecting the ASGI scope
        headers for an ``Authorization`` value beginning with the
        ``AWS4-HMAC-SHA256`` scheme.

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            bool: ``True`` if a SigV4 ``Authorization`` header is present.
        """
        authorization = _header_value(scope, _AUTHORIZATION_HEADER)
        if authorization is None:
            return False
        return authorization.strip().startswith(_SIGV4_SCHEME)

    def derive(self, scope: Scope) -> CredentialContext:
        """Derive a :class:`CredentialContext` from the presented SigV4 request.

        Parses the caller's access key id from the SigV4 ``Authorization``
        header's ``Credential`` scope (used as both ``identity_key`` and
        ``access_key_id``), then reads the forwarded secret access key and
        optional session token supplied by a trusted fronting layer.

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            CredentialContext: The per-request identity with ``source='sigv4'``.

        Raises:
            CredentialDerivationError: If the ``Authorization`` header is missing
                or malformed, or if the forwarded secret access key required to
                build a usable session is absent. The context is never partially
                populated.
        """
        authorization = _header_value(scope, _AUTHORIZATION_HEADER)
        if authorization is None:
            raise CredentialDerivationError('SigV4 inbound: missing Authorization header.')

        access_key_id = _parse_access_key_id(authorization)
        if not access_key_id:
            raise CredentialDerivationError(
                'SigV4 inbound: malformed Authorization header; could not parse '
                'the access key id from the Credential scope.'
            )

        secret_access_key = _header_value(scope, _FORWARDED_SECRET_HEADER)
        if not secret_access_key:
            # SigV4 proves possession without transmitting the secret, so a
            # server-usable session cannot be formed unless a trusted fronting
            # layer forwards short-lived credentials. Fail closed.
            raise CredentialDerivationError(
                'SigV4 inbound: no forwarded credential material available to '
                'build a session. This mechanism requires a trusted fronting '
                'layer to forward short-lived credentials.'
            )

        session_token = _header_value(scope, _FORWARDED_SESSION_TOKEN_HEADER) or _header_value(
            scope, _AMZ_SECURITY_TOKEN_HEADER
        )

        logger.debug('SigV4 inbound: derived credential context for a caller identity.')
        return CredentialContext(
            identity_key=access_key_id,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            source='sigv4',
        )
