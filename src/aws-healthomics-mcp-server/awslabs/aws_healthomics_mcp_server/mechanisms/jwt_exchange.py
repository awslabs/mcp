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

"""Inbound JWT-to-STS exchange mechanism (STS AssumeRole + ABAC session tags).

This module implements :class:`InboundJwtExchange`, the inbound identity mechanism
that exchanges a bearer/JWT token presented on an HTTP request into temporary AWS
credentials by calling AWS STS to assume a per-caller/per-tenant role
(Requirements 13.2-13.4). ABAC session tags identifying the caller are attached to
the assumed-role session so downstream authorization and audit can key on the
caller identity (Requirement 13.3).

Trust model
-----------
This mechanism does **not** verify the JWT signature. It assumes a fronting layer
(for example, an API gateway, application load balancer, or the AgentCore hosting
layer) has already authenticated the token and is responsible for cryptographic
verification, per the platform-glue split called out in the requirements. This
mechanism only *decodes* the token's claims (base64url, no signature check) to
extract a stable caller identifier (the ``sub`` claim by default), then uses the
**server's own** credentials (the default credential chain, never the inbound
token) to call ``sts:AssumeRole``. The assumed role's trust policy is the real
authorization boundary; the ABAC ``caller`` session tag lets that role's policies
(and CloudTrail) scope and attribute actions to the individual caller.

ABAC-tag approach
-----------------
``AssumeRoleWithWebIdentity`` does not accept caller-supplied ``Tags`` directly
(session tags for web identity come from the IdP token's configured tag claims).
To attach ABAC session tags that identify the caller in a portable way, this
mechanism uses ``sts:AssumeRole`` with an explicit ``Tags`` list derived from the
decoded JWT claims (``[{'Key': 'caller', 'Value': <sub>}]``). The server's own
identity must be permitted to ``sts:AssumeRole`` and ``sts:TagSession`` on the
target role.

Security
--------
The bearer token and the derived credentials are **never** logged. STS or token
failures raise :class:`CredentialDerivationError` (an ``InboundAuthError``) without
populating any credential context and without making any other AWS call for the
request (Requirement 13.4, Property 19).
"""

import base64
import binascii
import boto3
import botocore.session
import json
import re
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_JWT_SESSION_DURATION
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RoleResolver,
    StaticRoleResolver,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
    build_user_agent_extra,
)
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from typing import Any


# RoleSessionName must match this pattern (2-64 chars from the documented set).
_SESSION_NAME_ALLOWED = re.compile(r'[^\w+=,.@-]')
_SESSION_NAME_MAX_LEN = 64
_DEFAULT_SESSION_NAME = 'jwt-caller'


def get_sts_client(region: str | None = None) -> Any:
    """Build a fresh AWS STS client using the server's own default credentials.

    The exchange must run with the server's own identity, **never** the inbound
    token, so this constructs a brand-new client from the default credential chain
    (it intentionally does not go through ``get_aws_session``, which resolves the
    per-request inbound context). The standard ``user_agent_extra`` is applied for
    consistency with the rest of the server.

    Args:
        region: Optional AWS region for the STS client. When ``None``, the default
            region resolution of the underlying session is used.

    Returns:
        Any: A configured boto3 STS client.
    """
    botocore_session = botocore.session.Session()
    botocore_session.user_agent_extra = build_user_agent_extra()
    session = boto3.Session(botocore_session=botocore_session, region_name=region)
    return session.client('sts')


def _sanitize_session_name(value: str) -> str:
    """Sanitize a caller identifier into a valid STS ``RoleSessionName``.

    Replaces characters outside the allowed set, trims to the maximum length, and
    falls back to a constant default when nothing usable remains.

    Args:
        value: Raw caller identifier (e.g. the JWT ``sub`` claim).

    Returns:
        str: A non-empty session name of at most 64 valid characters.
    """
    cleaned = _SESSION_NAME_ALLOWED.sub('-', value).strip('-')
    cleaned = cleaned[:_SESSION_NAME_MAX_LEN]
    return cleaned or _DEFAULT_SESSION_NAME


def _decode_jwt_claims(token: str) -> dict[str, Any]:
    """Decode the claims (payload) of a JWT without verifying its signature.

    See the module trust model: signature verification is the responsibility of a
    fronting layer. This only base64url-decodes the payload segment to read claims.

    Args:
        token: The compact-serialized JWT (``header.payload.signature``).

    Returns:
        dict: The decoded claims object.

    Raises:
        CredentialDerivationError: If the token is malformed or its payload is not
            a JSON object. The token value is never included in the error.
    """
    parts = token.split('.')
    if len(parts) < 2:
        raise CredentialDerivationError('Malformed bearer token: not a JWT.')

    payload_segment = parts[1]
    # Restore base64url padding before decoding.
    pad_len = (-len(payload_segment)) % 4
    payload_segment = payload_segment + ('=' * pad_len)

    try:
        decoded = base64.urlsafe_b64decode(payload_segment.encode('ascii'))
        claims = json.loads(decoded)
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise CredentialDerivationError('Malformed bearer token: undecodable claims.') from exc

    if not isinstance(claims, dict):
        raise CredentialDerivationError('Malformed bearer token: claims are not an object.')

    return claims


class InboundJwtExchange:
    """Inbound mechanism that exchanges a bearer/JWT for assumed-role credentials.

    Implements the :class:`~awslabs.aws_healthomics_mcp_server.middleware.InboundMechanism`
    Protocol. :meth:`applies` detects an ``Authorization: Bearer <token>`` header,
    and :meth:`derive` exchanges that token via STS ``AssumeRole`` into a
    per-caller/per-tenant role with ABAC session tags identifying the caller.

    Attributes:
        name: Mechanism identifier (``'jwt'``).
    """

    name = 'jwt'

    def __init__(
        self,
        role_arn: str | None = None,
        session_duration: int = DEFAULT_JWT_SESSION_DURATION,
        region: str | None = None,
        caller_claim: str = 'sub',
        tag_key: str = 'caller',
        sts_client_factory: Any = get_sts_client,
        role_resolver: RoleResolver | None = None,
    ):
        """Initialize the JWT exchange mechanism.

        The mechanism resolves the downstream role per request through a
        :class:`~awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver.RoleResolver`.
        For backward-compatible construction, a bare ``role_arn`` may be supplied
        instead of a resolver; in that case a
        :class:`~awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver.StaticRoleResolver`
        is created that resolves every request to that single ARN (with no
        ``ExternalId``), preserving the original static behavior. Exactly one of
        ``role_resolver`` or ``role_arn`` must be provided; ``role_resolver`` takes
        precedence when both are given.

        Args:
            role_arn: ARN of the per-caller/per-tenant role to assume. Retained for
                backward-compatible construction; when provided without a
                ``role_resolver`` it is wrapped in a ``StaticRoleResolver``.
            session_duration: ``DurationSeconds`` for the assumed-role session
                (default :data:`DEFAULT_JWT_SESSION_DURATION`).
            region: Optional region for the STS client.
            caller_claim: JWT claim used as the stable caller identifier and ABAC
                tag value (default ``'sub'``).
            tag_key: ABAC session tag key identifying the caller (default
                ``'caller'``).
            sts_client_factory: Callable returning a fresh STS client. Injectable
                for testing; defaults to :func:`get_sts_client`.
            role_resolver: Resolver mapping decoded token claims to a
                :class:`RoleTarget` (role ARN + optional ``ExternalId``). When
                omitted, a ``StaticRoleResolver`` is built from ``role_arn``.

        Raises:
            ValueError: If neither ``role_resolver`` nor ``role_arn`` is provided.
        """
        if role_resolver is None:
            if role_arn is None:
                raise ValueError(
                    'InboundJwtExchange requires either a role_resolver or a role_arn.'
                )
            role_resolver = StaticRoleResolver(role_arn)

        self.role_arn = role_arn
        self.role_resolver = role_resolver
        self.session_duration = session_duration
        self.region = region
        self.caller_claim = caller_claim
        self.tag_key = tag_key
        self._sts_client_factory = sts_client_factory

    def _extract_bearer_token(self, scope: dict) -> str | None:
        """Extract the bearer token from the ASGI scope ``Authorization`` header.

        Args:
            scope: The ASGI HTTP connection scope. ``scope['headers']`` is a list of
                ``(name, value)`` byte tuples.

        Returns:
            str | None: The token string when an ``Authorization: Bearer <token>``
            header is present, otherwise ``None``.
        """
        for name, value in scope.get('headers', []):
            if name.lower() == b'authorization':
                try:
                    decoded = value.decode('latin-1')
                except (UnicodeDecodeError, AttributeError):
                    return None
                if decoded.startswith('Bearer '):
                    token = decoded[len('Bearer ') :].strip()
                    return token or None
        return None

    def applies(self, scope: dict) -> bool:
        """Return whether the request carries an ``Authorization: Bearer`` token.

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            bool: ``True`` if a non-empty bearer token is present.
        """
        return self._extract_bearer_token(scope) is not None

    def derive(self, scope: dict) -> CredentialContext:
        """Exchange the bearer/JWT token into a :class:`CredentialContext` via STS.

        Decodes the token claims (no signature verification; see the module trust
        model), extracts the caller identifier, and calls ``sts:AssumeRole`` on the
        configured role with an ABAC session tag identifying the caller. On any
        token or STS failure, raises :class:`CredentialDerivationError` without
        populating a context and without making any other AWS call (Requirement
        13.4, Property 19).

        Args:
            scope: The ASGI HTTP connection scope.

        Returns:
            CredentialContext: The per-request identity (``source='jwt'``).

        Raises:
            CredentialDerivationError: If the token is missing/invalid, the caller
                claim is absent or empty, role resolution fails, a non-static
                resolver supplies no ExternalId, or the STS assume-role call fails.
                In every case no ``CredentialContext`` is populated and no further
                AWS call is made (Requirements 7.4, 8.1, 8.2, 8.4).
        """
        token = self._extract_bearer_token(scope)
        if token is None:
            raise CredentialDerivationError('No bearer token present on the request.')

        claims = _decode_jwt_claims(token)
        caller = claims.get(self.caller_claim)
        if not isinstance(caller, str) or not caller:
            raise CredentialDerivationError(
                f'Bearer token is missing a usable "{self.caller_claim}" claim.'
            )

        # Resolve the downstream target (role ARN + optional ExternalId) from the
        # provider-controlled resolver, never from a token claim. Resolvers fail
        # closed by raising CredentialDerivationError; that error propagates
        # unchanged here, so a resolution failure denies the request before any
        # STS client is built or AWS call is made (Requirements 8.1, 8.4).
        target = self.role_resolver.resolve(claims)

        # Confused-deputy protection (Requirement 7.4): every resolver other than
        # the static single-role resolver MUST supply a non-empty ExternalId. The
        # StaticRoleResolver legitimately returns external_id=None (its role is
        # fixed provider configuration, not a cross-account customer role), so it
        # is the only exemption. Fail closed BEFORE building the STS client so no
        # assume_role call is made when the ExternalId is absent.
        has_external_id = isinstance(target.external_id, str) and bool(target.external_id)
        if not has_external_id and not isinstance(self.role_resolver, StaticRoleResolver):
            raise CredentialDerivationError(
                'Resolved role target is missing a required ExternalId.'
            )

        # Build a fresh STS client using the server's own credentials (never the
        # inbound token). No AWS call has been made yet.
        sts_client = self._sts_client_factory(self.region)

        assume_role_kwargs: dict[str, Any] = {
            'RoleArn': target.role_arn,
            'RoleSessionName': _sanitize_session_name(caller),
            'DurationSeconds': self.session_duration,
            'Tags': [{'Key': self.tag_key, 'Value': caller}],
        }
        # Include ExternalId only when the resolved target supplies a non-empty
        # value; otherwise omit the parameter entirely (static single-role case).
        if has_external_id:
            assume_role_kwargs['ExternalId'] = target.external_id

        try:
            response = sts_client.assume_role(**assume_role_kwargs)
        except (ClientError, BotoCoreError) as exc:
            # No context is populated and no other AWS call is made for this
            # request. Never log the token or any credential material.
            logger.warning(
                'JWT-to-STS exchange failed for inbound request: {}', type(exc).__name__
            )
            raise CredentialDerivationError('STS assume-role failed for JWT exchange.') from exc

        credentials = response['Credentials']
        return CredentialContext(
            identity_key=caller,
            access_key_id=credentials['AccessKeyId'],
            secret_access_key=credentials['SecretAccessKey'],
            session_token=credentials['SessionToken'],
            source='jwt',
        )
