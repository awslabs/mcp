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

"""Role resolution abstraction for the inbound ``jwt`` mechanism.

This module introduces the seam that maps a request's decoded token claims to
the downstream role the server must assume, so a single ``jwt`` endpoint can act
in many customers' accounts.

Core abstractions:

- :class:`RoleTarget` -- the resolved downstream target for a request: a role
  ARN plus an optional ``ExternalId``.
- :class:`RoleResolver` -- the :class:`~typing.Protocol` consumed by
  ``InboundJwtExchange`` that maps decoded token claims to a
  :class:`RoleTarget`.

Two concrete resolvers are implemented here:

- :class:`StaticRoleResolver` -- returns a single provider-configured role ARN
  (from ``MCP_JWT_ROLE_ARN``) with no ``ExternalId``, for every request. This is
  the backward-compatible single-role behavior.
- :class:`RegistryRoleResolver` -- looks up the authenticated identity in a
  provider-controlled :class:`RegistrySource` (a file-based JSON map,
  :class:`FileRegistrySource`, or a DynamoDB table, :class:`DynamoDbRegistrySource`,
  selected from ``MCP_JWT_ROLE_REGISTRY`` by :func:`parse_registry_source`) and
  returns that identity's role ARN and per-customer ``ExternalId`` for
  cross-account assumption.

Regardless of implementation, resolution is always driven by provider-controlled
configuration or a provider-controlled registry -- never by an unvalidated token
claim -- and the resulting mapping is the enforced cross-tenant boundary
(Requirement 5.1).

SECURITY: Resolvers MUST fail closed. When a role target cannot be resolved for
a request, a resolver raises
:class:`~awslabs.aws_healthomics_mcp_server.utils.aws_utils.CredentialDerivationError`
and returns no target, so the server never falls back to unintended credentials.
Resolvers MUST NOT log claim contents or any bearer-token / credential material;
only non-secret facts (such as the exception type) may ever surface in logs.
"""

import boto3
import botocore.session
import json
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialDerivationError as CredentialDerivationError,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    build_user_agent_extra,
)
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, NamedTuple, Protocol, runtime_checkable
from urllib.parse import urlparse


# URI schemes recognized in an ``MCP_JWT_ROLE_REGISTRY`` value; each selects
# exactly one registry source backend.
_FILE_SCHEME = 'file'
_DYNAMODB_SCHEME = 'dynamodb'

# Startup error message for an ``MCP_JWT_ROLE_REGISTRY`` value that names neither a
# supported ``file://`` map nor a ``dynamodb://`` table. The value itself is
# provider-controlled configuration (not secret) and is safe to echo so operators
# can correct it.
ERROR_UNSUPPORTED_REGISTRY_SOURCE = (
    "Unsupported MCP_JWT_ROLE_REGISTRY value '{}'. Expected a file-based JSON map "
    "('file:///path/map.json') or a DynamoDB table ('dynamodb://table-name')."
)

# Default caller claim used to identify the authenticated caller within the decoded
# token claims. Mirrors ``InboundJwtExchange``'s default so the same identity keys
# both the assume-role session tag and the registry lookup.
_DEFAULT_CALLER_CLAIM = 'sub'

# Registry_Record field names.
_RECORD_ROLE_ARN = 'role_arn'
_RECORD_EXTERNAL_ID = 'external_id'
_RECORD_ENABLED = 'enabled'

# Attribute name of the DynamoDB partition key that holds the Authenticated_Identity.
# The identity is the table's partition key (see design "Data Models"); the default
# is overridable per deployment so the table schema is not forced to a fixed name.
_DEFAULT_PARTITION_KEY = 'identity'

# Maximum length of an ``sts:ExternalId`` accepted by AWS STS (Requirement 7.1).
# A resolved External_Id must be a non-empty string no longer than this.
_MAX_EXTERNAL_ID_LEN = 1224


class RoleTarget(NamedTuple):
    """The resolved downstream target for a request.

    Attributes:
        role_arn: The ARN of the role the server assumes for the request. This
            value always originates from provider-controlled configuration or a
            provider-controlled registry, never from a token claim.
        external_id: The per-customer ``sts:ExternalId`` guarding the assume, or
            ``None`` when no ``ExternalId`` applies (for example the static
            single-role configuration). When present it is passed unmodified on
            the ``sts:AssumeRole`` call; the server never generates, derives, or
            rotates it.
    """

    role_arn: str
    external_id: str | None


@runtime_checkable
class RoleResolver(Protocol):
    """Maps decoded token claims to a :class:`RoleTarget` for a request.

    Implementations resolve the target from an authoritative, provider-controlled
    source (a configured ARN or a registry). The claims are used only to identify
    the authenticated caller; the target role ARN is never taken from a claim.
    """

    def resolve(self, claims: dict) -> RoleTarget:
        """Resolve the :class:`RoleTarget` for the given decoded token claims.

        Args:
            claims: The decoded (already signature-verified upstream) token
                claims for the request. Used only to identify the authenticated
                caller; the claim contents MUST NOT be logged.

        Returns:
            The :class:`RoleTarget` mapped to the request's authenticated
            identity.

        Raises:
            CredentialDerivationError: If a role target cannot be resolved for
                the request. Implementations fail closed and return no target;
                no claim or token material is included in the error.
        """
        ...


class StaticRoleResolver:
    """Resolves every request to a single, statically configured role ARN.

    This resolver reproduces the current static ``MCP_JWT_ROLE_ARN`` behavior and
    is the default when only ``MCP_JWT_ROLE_ARN`` is configured (backward
    compatible). It returns the configured role ARN with no ``ExternalId`` for
    every request, regardless of the decoded token claims, so the assumed role is
    determined solely by provider-controlled configuration and never by a token
    claim (Requirement 5.2).
    """

    def __init__(self, role_arn: str) -> None:
        """Initialize the resolver with the statically configured role ARN.

        Args:
            role_arn: The provider-configured ``MCP_JWT_ROLE_ARN`` value that
                every request resolves to.
        """
        self._role_arn = role_arn

    def resolve(self, claims: dict) -> RoleTarget:
        """Return the configured role ARN with no ``ExternalId``.

        The claims are ignored: the target is fixed by provider-controlled
        configuration, so the same :class:`RoleTarget` is returned for every
        request (Requirement 2.2).

        Args:
            claims: The decoded token claims for the request. Ignored by this
                resolver; the claim contents MUST NOT be logged.

        Returns:
            A :class:`RoleTarget` whose ``role_arn`` is the configured value and
            whose ``external_id`` is ``None``.
        """
        return RoleTarget(role_arn=self._role_arn, external_id=None)


class RegistrySourceError(Exception):
    """Raised when a registry source cannot be read or queried.

    This is an internal signal from a :class:`RegistrySource` backend that its
    underlying store (a JSON file or a DynamoDB table) could not be read or
    parsed. :class:`RegistryRoleResolver` catches this and re-raises a
    :class:`~awslabs.aws_healthomics_mcp_server.utils.aws_utils.CredentialDerivationError`
    so the request fails closed (Requirement 3.7). Backends MUST NOT include any
    claim, token, or credential material in the message; only non-secret facts
    (such as the failing store's identifier) may appear.
    """


@runtime_checkable
class RegistrySource(Protocol):
    """A provider-controlled source of Registry_Records keyed on the identity.

    A ``RegistryRoleResolver`` reads records from exactly one source backend --
    either a file-based JSON map or a DynamoDB table -- selected from the
    ``MCP_JWT_ROLE_REGISTRY`` value (Requirement 3.2). Each backend exposes the
    same lookup shape so the resolver's record handling is backend-agnostic.
    """

    def get_record(self, identity: str) -> dict | None:
        """Return the raw Registry_Record for ``identity``, or ``None`` if absent.

        Args:
            identity: The Authenticated_Identity (the extracted caller-claim
                value) used as the lookup key. MUST NOT be logged.

        Returns:
            The record ``{role_arn, external_id, account_id?, enabled?}`` mapped to
            ``identity``, or ``None`` when no record exists for it. Validation of
            the record's contents is the resolver's responsibility.

        Raises:
            RegistrySourceError: If the underlying store cannot be read, queried,
                or parsed. No claim, token, or credential material is included.
        """
        ...


class FileRegistrySource:
    """Registry source backed by a JSON map on the local filesystem.

    Selected by a ``file:///path/map.json`` ``MCP_JWT_ROLE_REGISTRY`` value. The
    file holds a single JSON object mapping each Authenticated_Identity to a
    Registry_Record ``{role_arn, external_id, account_id?, enabled?}``. This
    backend is intended for small deployments and local testing; the DynamoDB
    backend is recommended for production.

    The map is re-read on every lookup so that onboarding/offboarding edits to the
    file take effect without restarting the server, and so a read failure fails
    the individual request closed (Requirement 3.7) rather than at startup.
    """

    def __init__(self, path: str) -> None:
        """Initialize the file-backed source.

        Args:
            path: Filesystem path to the JSON map, parsed from the ``file://`` URI
                in ``MCP_JWT_ROLE_REGISTRY``.
        """
        self._path = path

    def get_record(self, identity: str) -> dict | None:
        """Load the JSON map and return the record mapped to ``identity``.

        Args:
            identity: The Authenticated_Identity used as the lookup key. MUST NOT
                be logged.

        Returns:
            The Registry_Record for ``identity``, or ``None`` when the map has no
            entry for it.

        Raises:
            RegistrySourceError: If the file cannot be read, does not contain a
                JSON object, or the matching entry is not a JSON object. The
                identity and record contents are never included in the message.
        """
        try:
            with open(self._path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            # Report only the store path (provider-controlled, non-secret) and the
            # exception type; never the identity or any record contents.
            raise RegistrySourceError(
                f'Unable to read registry map at {self._path!r}: {type(exc).__name__}.'
            ) from exc

        if not isinstance(data, dict):
            raise RegistrySourceError(f'Registry map at {self._path!r} is not a JSON object.')

        record = data.get(identity)
        if record is None:
            return None
        if not isinstance(record, dict):
            raise RegistrySourceError(f'Registry record in {self._path!r} is not a JSON object.')
        return record


def get_dynamodb_client(region: str | None = None) -> Any:
    """Build a fresh AWS DynamoDB client using the server's own default credentials.

    The registry lookup must run with the server's own identity, **never** the
    inbound token, so this constructs a brand-new client from the default
    credential chain (it intentionally does not go through ``get_aws_session``,
    which resolves the per-request inbound context). The standard
    ``user_agent_extra`` is applied for consistency with the rest of the server.
    This mirrors ``jwt_exchange.get_sts_client`` so both server-credential paths
    are built the same way.

    Args:
        region: Optional AWS region for the DynamoDB client. When ``None``, the
            default region resolution of the underlying session is used.

    Returns:
        Any: A configured boto3 DynamoDB client.
    """
    botocore_session = botocore.session.Session()
    botocore_session.user_agent_extra = build_user_agent_extra()
    session = boto3.Session(botocore_session=botocore_session, region_name=region)
    return session.client('dynamodb')


class DynamoDbRegistrySource:
    """Registry source backed by a DynamoDB table keyed on the identity.

    Selected by a ``dynamodb://table-name`` ``MCP_JWT_ROLE_REGISTRY`` value. The
    identity is the table's partition key and the item holds the Registry_Record
    fields ``{role_arn, external_id, account_id?, enabled?}``.

    Each lookup uses a fresh boto3 DynamoDB client built from the server's **own**
    default credentials (never the inbound token), so onboarding/offboarding edits
    take effect without restarting the server and a query failure fails the
    individual request closed (Requirement 3.7) rather than at startup.
    """

    def __init__(
        self,
        table_name: str,
        region: str | None = None,
        partition_key: str = _DEFAULT_PARTITION_KEY,
        client_factory: Any = get_dynamodb_client,
    ) -> None:
        """Initialize the DynamoDB-backed source.

        Args:
            table_name: Name of the DynamoDB table, parsed from the
                ``dynamodb://`` URI in ``MCP_JWT_ROLE_REGISTRY``.
            region: Optional AWS region for the DynamoDB client. When ``None``, the
                default region resolution of the underlying session is used.
            partition_key: Attribute name of the table's partition key that holds
                the Authenticated_Identity. Defaults to ``'identity'``.
            client_factory: Callable returning a fresh DynamoDB client built from
                the server's own credentials. Injectable for testing; defaults to
                :func:`get_dynamodb_client`.
        """
        self.table_name = table_name
        self._region = region
        self._partition_key = partition_key
        self._client_factory = client_factory

    def get_record(self, identity: str) -> dict | None:
        """Query the table for the record mapped to ``identity``.

        Builds a fresh DynamoDB client from the server's own credentials (never the
        inbound token), reads the item whose partition key equals ``identity``, and
        deserializes the DynamoDB attribute values into plain Python values matching
        what ``RegistryRoleResolver`` expects. Field validation is the resolver's
        responsibility.

        Args:
            identity: The Authenticated_Identity partition key. MUST NOT be logged.

        Returns:
            The Registry_Record ``{role_arn, external_id, account_id?, enabled?}``
            mapped to ``identity`` with plain Python values, or ``None`` when the
            table has no item for it.

        Raises:
            RegistrySourceError: If the table cannot be read or queried. Only the
                (provider-controlled, non-secret) table name and the exception type
                are surfaced; the identity and record contents are never included.
        """
        client = self._client_factory(self._region)
        try:
            response = client.get_item(
                TableName=self.table_name,
                Key={self._partition_key: {'S': identity}},
            )
        except (ClientError, BotoCoreError) as exc:
            # Report only the table name (provider-controlled, non-secret) and the
            # exception type; never the identity or any record contents.
            raise RegistrySourceError(
                f'Unable to query registry table {self.table_name!r}: {type(exc).__name__}.'
            ) from exc

        item = response.get('Item')
        if item is None:
            return None

        # Deserialize DynamoDB attribute values (e.g. ``{'S': 'arn'}``) into plain
        # Python values (e.g. ``'arn'``) so the returned dict matches the shape the
        # resolver validates.
        deserializer = TypeDeserializer()
        return {key: deserializer.deserialize(value) for key, value in item.items()}


def parse_registry_source(registry_value: str) -> RegistrySource:
    """Select the registry source backend named by an ``MCP_JWT_ROLE_REGISTRY`` value.

    The value names exactly one backend by URI scheme (Requirement 3.2):

    - ``file:///path/map.json`` selects a :class:`FileRegistrySource`, and
    - ``dynamodb://table-name`` selects a :class:`DynamoDbRegistrySource`.

    Args:
        registry_value: The provider-controlled ``MCP_JWT_ROLE_REGISTRY`` value.

    Returns:
        The :class:`RegistrySource` backend for the given value.

    Raises:
        ValueError: If the value is empty or names an unsupported scheme. The
            value is provider-controlled configuration (not secret) and is echoed
            so operators can correct it.
    """
    value = (registry_value or '').strip()
    parsed = urlparse(value)
    scheme = parsed.scheme.lower()

    if scheme == _FILE_SCHEME:
        # A well-formed file URI is ``file:///abs/path`` (empty netloc) or
        # ``file://localhost/abs/path``. The path segment carries the filesystem
        # path; anything else (e.g. ``file://relative``) is rejected.
        if parsed.netloc not in ('', 'localhost'):
            raise ValueError(ERROR_UNSUPPORTED_REGISTRY_SOURCE.format(value))
        path = parsed.path
        if not path:
            raise ValueError(ERROR_UNSUPPORTED_REGISTRY_SOURCE.format(value))
        return FileRegistrySource(path)

    if scheme == _DYNAMODB_SCHEME:
        # The table name is the URI authority (``dynamodb://table-name``).
        table_name = parsed.netloc
        if not table_name:
            raise ValueError(ERROR_UNSUPPORTED_REGISTRY_SOURCE.format(value))
        return DynamoDbRegistrySource(table_name)

    raise ValueError(ERROR_UNSUPPORTED_REGISTRY_SOURCE.format(value))


class RegistryRoleResolver:
    """Resolves each request to the role mapped to its Authenticated_Identity.

    This resolver satisfies the :class:`RoleResolver` Protocol and backs the
    multi-tenant ``MCP_JWT_ROLE_REGISTRY`` configuration. It extracts the
    authenticated caller identity from the decoded token claims (the configured
    caller claim, ``sub`` by default) and looks up the matching Registry_Record in
    a provider-controlled :class:`RegistrySource`. The role ARN and ``ExternalId``
    always originate from that provider-controlled record, never from a token claim
    (Requirement 5.2).

    SECURITY: The resolver fails closed (Requirements 3.4-3.7, 8.1). It raises
    :class:`CredentialDerivationError` -- and returns no target -- when the caller
    identity is missing, no record exists, the record is disabled, the record is
    missing its ``role_arn`` or ``external_id``, the ``external_id`` is not a
    non-empty string of at most 1224 characters, or the source cannot be read or
    queried. The ``external_id`` is used unmodified; the server never generates,
    derives, or rotates it (Requirement 7.3). Claim, token, and credential material
    is never logged, and never appears in the raised error (Requirement 9).
    """

    def __init__(
        self,
        source: RegistrySource,
        caller_claim: str = _DEFAULT_CALLER_CLAIM,
    ) -> None:
        """Initialize the registry-backed resolver.

        Args:
            source: The provider-controlled :class:`RegistrySource` (a file-based
                JSON map or a DynamoDB table) that records are read from.
            caller_claim: The token claim naming the authenticated caller, used as
                the registry lookup key. Defaults to ``'sub'`` to match
                ``InboundJwtExchange``.
        """
        self._source = source
        self._caller_claim = caller_claim

    @classmethod
    def from_registry_value(
        cls,
        registry_value: str,
        caller_claim: str = _DEFAULT_CALLER_CLAIM,
    ) -> 'RegistryRoleResolver':
        """Build a resolver from an ``MCP_JWT_ROLE_REGISTRY`` value.

        Selects the source backend named by ``registry_value`` via
        :func:`parse_registry_source`, then wraps it in a
        :class:`RegistryRoleResolver`.

        Args:
            registry_value: The provider-controlled ``MCP_JWT_ROLE_REGISTRY`` value
                (``file:///path/map.json`` or ``dynamodb://table-name``).
            caller_claim: The token claim naming the authenticated caller. Defaults
                to ``'sub'``.

        Returns:
            A resolver reading from the selected source backend.

        Raises:
            ValueError: If ``registry_value`` is empty or names an unsupported
                scheme (raised by :func:`parse_registry_source`).
        """
        return cls(parse_registry_source(registry_value), caller_claim=caller_claim)

    def resolve(self, claims: dict) -> RoleTarget:
        """Resolve the :class:`RoleTarget` mapped to the request's caller identity.

        Extracts the caller identity from the configured caller claim, looks up its
        Registry_Record in the source, and applies the fail-closed rules
        (Requirements 3.3-3.7, 7.1, 7.3). The claim contents, the identity, and any
        record contents are never logged and never included in the raised error.

        Args:
            claims: The decoded token claims for the request. Used only to identify
                the authenticated caller; the claim contents MUST NOT be logged.

        Returns:
            The :class:`RoleTarget` (``role_arn`` and non-empty ``external_id``)
            from the enabled record mapped to the caller identity.

        Raises:
            CredentialDerivationError: If the caller claim is missing or empty, no
                record exists, the record is disabled, the record is missing its
                ``role_arn`` or ``external_id``, the ``external_id`` is not a
                non-empty string of at most 1224 characters, or the source cannot
                be read or queried. The resolver fails closed and returns no target.
        """
        identity = claims.get(self._caller_claim)
        if not isinstance(identity, str) or not identity:
            # Requirement 1.8 / 8.3: no usable caller identity, so fail closed
            # before touching the source. The claim value is never echoed.
            raise CredentialDerivationError(
                f'Decoded token claims are missing a usable "{self._caller_claim}" claim.'
            )

        try:
            record = self._source.get_record(identity)
        except RegistrySourceError as exc:
            # Requirement 3.7: source read/query failure fails the request closed.
            # Only the (non-secret) source message and exception type are surfaced.
            raise CredentialDerivationError(
                f'Registry source could not be read for role resolution: {type(exc).__name__}.'
            ) from exc

        if record is None:
            # Requirement 3.4: no record mapped to this identity -> fail closed.
            raise CredentialDerivationError('No registry record for the authenticated identity.')

        # Requirement 3.5: an ``enabled`` indicator that is present and not truthy
        # (for example ``false``) denies access; an absent indicator means enabled.
        if _RECORD_ENABLED in record and not record[_RECORD_ENABLED]:
            raise CredentialDerivationError(
                'Registry record for the authenticated identity is disabled.'
            )

        role_arn = record.get(_RECORD_ROLE_ARN)
        if not isinstance(role_arn, str) or not role_arn:
            # Requirement 3.6: a record missing its role ARN -> fail closed.
            raise CredentialDerivationError('Registry record is missing a role ARN.')

        external_id = record.get(_RECORD_EXTERNAL_ID)
        if not isinstance(external_id, str) or not external_id:
            # Requirement 3.6: a record missing its ExternalId -> fail closed.
            raise CredentialDerivationError('Registry record is missing an ExternalId.')
        if len(external_id) > _MAX_EXTERNAL_ID_LEN:
            # Requirement 7.1: the ExternalId must be at most 1224 characters.
            raise CredentialDerivationError('Registry record ExternalId is too long.')

        # Requirement 7.3: use the record's ExternalId unmodified; never generate,
        # derive, or rotate it.
        return RoleTarget(role_arn=role_arn, external_id=external_id)
