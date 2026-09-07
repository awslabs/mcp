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

"""AWS utility functions for the HealthOmics MCP server."""

import base64
import boto3
import botocore.session
import contextvars
import io
import os
import zipfile
from awslabs.aws_healthomics_mcp_server import __version__
from awslabs.aws_healthomics_mcp_server.consts import (
    AGENT_ENV,
    DEFAULT_OMICS_SERVICE_NAME,
    DEFAULT_REGION,
)
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from loguru import logger
from typing import Any, Callable, Dict, Optional, Protocol, cast


def get_region() -> str:
    """Get the AWS region from environment variable or default.

    Returns:
        str: AWS region name
    """
    return os.environ.get('AWS_REGION', DEFAULT_REGION)


def get_omics_service_name() -> str:
    """Get the HealthOmics service name from environment variable or default.

    Returns:
        str: HealthOmics service name
    """
    service_name = os.environ.get('HEALTHOMICS_SERVICE_NAME', DEFAULT_OMICS_SERVICE_NAME)

    # Check if service name is empty or only whitespace
    if not service_name or not service_name.strip():
        logger.warning(
            'HEALTHOMICS_SERVICE_NAME environment variable is empty or contains only whitespace. '
            f'Using default service name: {DEFAULT_OMICS_SERVICE_NAME}'
        )
        return DEFAULT_OMICS_SERVICE_NAME

    return service_name.strip()


def get_omics_endpoint_url() -> str | None:
    """Get the HealthOmics service endpoint URL from environment variable.

    Returns:
        str | None: HealthOmics endpoint URL if valid, None otherwise
    """
    endpoint_url = os.environ.get('HEALTHOMICS_ENDPOINT_URL')

    # If environment variable is not set, return None (no warning needed)
    if endpoint_url is None:
        return None

    endpoint_url = endpoint_url.strip()

    # Check if endpoint URL is empty or only whitespace
    if not endpoint_url:
        logger.warning(
            'HEALTHOMICS_ENDPOINT_URL environment variable is empty or contains only whitespace. '
            'Using default endpoint.'
        )
        return None

    # Validate that endpoint URL starts with http:// or https://
    if not (endpoint_url.startswith('http://') or endpoint_url.startswith('https://')):
        logger.warning(
            f'HEALTHOMICS_ENDPOINT_URL environment variable "{endpoint_url}" must begin with '
            'http:// or https://. Using default endpoint.'
        )
        return None

    return endpoint_url


def get_agent_value() -> str | None:
    """Get the agent identifier from the AGENT environment variable.

    Reads the value, strips whitespace, sanitizes by removing characters
    not permitted in HTTP header values (outside visible ASCII 0x20-0x7E),
    and returns None if the result is empty.

    Returns:
        str | None: The sanitized agent value if valid, None otherwise.
    """
    raw = os.environ.get(AGENT_ENV)
    if raw is None:
        return None

    stripped = raw.strip()
    if not stripped:
        return None

    sanitized = ''.join(c for c in stripped if 0x20 <= ord(c) <= 0x7E)

    if not sanitized:
        logger.warning(
            f'{AGENT_ENV} environment variable value became empty after sanitization. '
            'Treating as unset.'
        )
        return None

    return sanitized


def build_user_agent_extra() -> str:
    """Build the ``user_agent_extra`` string applied to every boto3 session.

    Produces the server identifier and, when the ``AGENT`` environment variable is
    set to a non-empty sanitized value, appends the lowercased ``agent/<value>``
    suffix. This is the single source of truth for the user-agent string so that
    every session-construction path (the default resolver and request-scoped
    credential contexts) applies an identical value.

    Returns:
        str: The ``user_agent_extra`` string.
    """
    user_agent_extra = f'md/awslabs#mcp#aws-healthomics-mcp-server#{__version__}'

    agent_value = get_agent_value()
    if agent_value:
        user_agent_extra += f' agent/{agent_value.lower()}'

    return user_agent_extra


def get_aws_session(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> boto3.Session:
    """Get an AWS session with the centralized region configuration.

    Args:
        region_name: Optional region override. If not specified, falls back to
            AWS_REGION environment variable or default region.
        profile_name: Optional AWS profile override. If not specified, falls back to
            the default credential chain.

    Returns:
        boto3.Session: Configured AWS session

    Raises:
        ImportError: If boto3 is not available
    """
    # Delegate session construction to the active credential resolver (the seam).
    # Absent region/profile are passed through unchanged so the resolver applies
    # its own defaults (e.g. get_region() and the default credential chain).
    return get_active_resolver().resolve(
        CredentialRequest(region=region_name, profile=profile_name)
    )


@dataclass(frozen=True)
class CredentialRequest:
    """Inputs to credential resolution.

    Both fields are optional; resolvers apply their own defaults (e.g. the default
    credential chain when ``profile`` is absent and ``get_region()`` when ``region``
    is absent).

    Attributes:
        region: Optional AWS region override.
        profile: Optional AWS profile name override.
    """

    region: str | None = None
    profile: str | None = None


class CredentialResolver(Protocol):
    """Seam: produce a configured ``boto3.Session`` for a resolution request."""

    def resolve(self, request: CredentialRequest) -> boto3.Session:
        """Resolve a request into a configured ``boto3.Session``.

        Args:
            request: The credential resolution inputs (region/profile).

        Returns:
            boto3.Session: Configured AWS session.
        """
        ...


class DefaultCredentialResolver:
    """Phase 1 resolver that reproduces today's ``get_aws_session()`` behavior exactly.

    Selects the default credential chain vs a named profile, resolves the region from
    the request or ``get_region()``, and applies the identical ``user_agent_extra``
    string (including the sanitized ``AGENT`` suffix). The existing Pydantic
    ``FieldInfo`` defensive coercion (mapping non-``str``/non-``None`` values to
    ``None``) is preserved so direct calls with unresolved ``FieldInfo`` defaults
    behave as before.
    """

    def resolve(self, request: CredentialRequest) -> boto3.Session:
        """Resolve a request into a configured ``boto3.Session``.

        Args:
            request: The credential resolution inputs (region/profile).

        Returns:
            boto3.Session: Configured AWS session.
        """
        region_name = request.region
        profile_name = request.profile

        # Handle FieldInfo objects from Pydantic (FastMCP compatibility)
        if not isinstance(region_name, (str, type(None))):
            region_name = None
        if not isinstance(profile_name, (str, type(None))):
            profile_name = None

        botocore_session = botocore.session.Session()
        botocore_session.user_agent_extra = build_user_agent_extra()

        kwargs: dict[str, Any] = {
            'region_name': region_name or get_region(),
            'botocore_session': botocore_session,
        }
        if profile_name:
            kwargs['profile_name'] = profile_name

        return boto3.Session(**kwargs)


class RequestScopedCredentialResolver:
    """Phase 2 resolver that derives credentials from the active ``CredentialContext``.

    Reads the per-request :class:`CredentialContext` from the ``contextvars`` accessor
    on every call and builds a fresh ``boto3.Session`` from that context's explicit
    credentials. ``request.profile`` is ignored entirely for identity selection; the
    region comes from ``request.region`` when present, otherwise ``get_region()``.

    Per-request credential freshness guarantees (Requirement 12):

    - **Freshness (12.1).** Each :meth:`resolve` call re-reads the active context and
      builds a brand-new session via :meth:`CredentialContext.build_session`; no
      process-level cached session is ever reused.
    - **No cross-identity reuse (12.2).** The resolver holds no instance, class, or
      module state that could carry a prior request's credentials or session into a
      new request. Identity is read fresh from the request-scoped contextvar on every
      call, so a new inbound identity always derives its own session. ``__slots__`` is
      empty to make this stateless guarantee airtight: no per-instance attribute (and
      therefore no cached session/credentials) can be attached to a resolver.
    - **Discard on completion (12.3).** The resolver itself retains nothing after a
      call returns; the per-request context is set and torn down by the identity
      middleware via :func:`set_credential_context` / :func:`reset_credential_context`.
    - **No fallback on failure (12.4 / 8.6).** If no context is present, raises
      :class:`NoRequestIdentityError` with **no fallback** to another context or to
      :class:`DefaultCredentialResolver`. Mechanism-level derivation failures surface
      as :class:`CredentialDerivationError`; in neither case does the resolver fall
      back to process-level or previously derived credentials.
    """

    # Empty slots: the resolver is intentionally stateless with respect to
    # credentials and sessions. Disallowing instance attributes guarantees no
    # session or credential material can be cached on a resolver instance across
    # requests (Requirements 12.1, 12.2).
    __slots__ = ()

    def resolve(self, request: CredentialRequest) -> boto3.Session:
        """Resolve a request into a configured ``boto3.Session``.

        Args:
            request: The credential resolution inputs. ``region`` is honored when
                present; ``profile`` is ignored for identity selection.

        Returns:
            boto3.Session: Session built from the active context's credentials.

        Raises:
            NoRequestIdentityError: If no request-scoped ``CredentialContext`` is
                present for the current execution context.
        """
        ctx = get_credential_context()
        if ctx is None:
            raise NoRequestIdentityError(
                'No request identity was resolved for this request; refusing to '
                'fall back to another credential context or the default credential '
                'chain.'
            )

        region_name = request.region

        # Handle FieldInfo objects from Pydantic (FastMCP compatibility). A non-str,
        # non-None region (e.g. an unresolved FieldInfo default) is coerced to None
        # before the request.region-or-default decision. request.profile is ignored
        # for identity, so no coercion is needed for it.
        if not isinstance(region_name, (str, type(None))):
            region_name = None

        region = region_name or get_region()
        # request.profile is intentionally IGNORED for identity (Requirement 10.1).
        return ctx.build_session(region=region)


_active_resolver: CredentialResolver = DefaultCredentialResolver()


def get_active_resolver() -> CredentialResolver:
    """Return the currently active credential resolver.

    Returns:
        CredentialResolver: The resolver used to produce ``boto3.Session`` instances.
    """
    return _active_resolver


def set_active_resolver(resolver: CredentialResolver) -> None:
    """Set the active credential resolver.

    Args:
        resolver: The resolver to install as the active credential resolver.
    """
    global _active_resolver
    _active_resolver = resolver


# ---------------------------------------------------------------------------
# Phase 2: per-request credential context, contextvar accessors, and exceptions.
#
# These primitives support request-scoped, multi-tenant credential resolution.
# They are introduced additively and are not referenced on any single-tenant
# (Phase 1) code path. CredentialContext carries the per-request identity used to
# build a fresh boto3.Session for each inbound request.
#
# SECURITY: credential material (access key id, secret access key, session token)
# MUST NEVER be logged. The secret-bearing fields are excluded from the generated
# dataclass repr via field(repr=False), and __repr__ is overridden to redact, so
# that accidental logging or string interpolation cannot leak secrets.
# ---------------------------------------------------------------------------


class InboundAuthError(Exception):
    """Base error for inbound authentication failures in multi-tenant mode.

    Raised when an inbound request cannot be authenticated/authorized. The
    identity middleware translates this into a rejection (e.g. HTTP 401) without
    dispatching a tool or calling any AWS service.
    """


class NoRequestIdentityError(InboundAuthError):
    """Raised when no request-scoped ``CredentialContext`` is present.

    Indicates that a tool executed in multi-tenant mode without an active
    credential context (no inbound identity was resolved for the request). The
    resolver raises this rather than falling back to another context or to the
    default credential chain (Requirement 8.6).
    """


class CredentialDerivationError(InboundAuthError):
    """Raised when deriving credentials for an inbound request fails.

    Indicates that an enabled inbound mechanism failed to derive a usable
    ``CredentialContext`` (e.g. an STS exchange failure). No AWS service is called
    for the request and no fallback to process-level or previously derived
    credentials occurs (Requirement 12.4).
    """


@dataclass(frozen=True)
class CredentialContext:
    """Per-request identity used to build AWS sessions in multi-tenant mode.

    Carries the credentials derived for a single inbound request along with a
    stable ``identity_key`` used for per-identity cache keying. Instances are
    immutable and are stored in a ``contextvars.ContextVar`` so concurrent
    requests never observe each other's context.

    SECURITY: ``access_key_id``, ``secret_access_key``, and ``session_token`` are
    credential material and MUST NEVER be logged. They are excluded from the
    dataclass repr (``repr=False``) and ``__repr__`` is overridden to redact them.

    Attributes:
        identity_key: Stable identity hash used for per-identity cache keying.
        access_key_id: AWS access key id (secret; never logged).
        secret_access_key: AWS secret access key (secret; never logged).
        session_token: Optional AWS session token (secret; never logged).
        source: Mechanism that produced the context ('sigv4' | 'jwt' | 'explicit').
    """

    identity_key: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)
    session_token: str | None = field(repr=False)
    source: str

    def build_session(self, region: str) -> boto3.Session:
        """Build a fresh ``boto3.Session`` from this context's explicit credentials.

        Constructs a session using the context's explicit credentials and the
        given region, applying the same ``user_agent_extra`` string used by the
        default resolver (including the sanitized ``AGENT`` suffix). A new session
        is created on every call; no process-level session is reused.

        Args:
            region: AWS region to configure on the session.

        Returns:
            boto3.Session: Session configured with this context's credentials.
        """
        botocore_session = botocore.session.Session()
        botocore_session.user_agent_extra = build_user_agent_extra()

        return boto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            aws_session_token=self.session_token,
            region_name=region,
            botocore_session=botocore_session,
        )

    def __repr__(self) -> str:
        """Return a redacted repr that never exposes credential material.

        Returns:
            str: Repr exposing only ``identity_key`` and ``source``; secret fields
            are shown as ``'***'`` so accidental logging cannot leak secrets.
        """
        return (
            f'CredentialContext(identity_key={self.identity_key!r}, '
            "access_key_id='***', secret_access_key='***', session_token='***', "
            f'source={self.source!r})'
        )


_credential_context: contextvars.ContextVar[CredentialContext | None] = contextvars.ContextVar(
    'credential_context', default=None
)


def get_credential_context() -> CredentialContext | None:
    """Return the credential context for the current request, if any.

    Returns:
        CredentialContext | None: The active context, or ``None`` when no inbound
        identity has been set for the current execution context.
    """
    return _credential_context.get()


def set_credential_context(
    context: CredentialContext,
) -> contextvars.Token[CredentialContext | None]:
    """Set the credential context for the current request.

    Intended for use by the identity middleware to populate the per-request
    context before any tool executes. The returned token must be passed to
    :func:`reset_credential_context` on completion to discard the context.

    Args:
        context: The credential context to install for the current request.

    Returns:
        contextvars.Token: Token used to restore the previous context value.
    """
    return _credential_context.set(context)


def reset_credential_context(token: contextvars.Token[CredentialContext | None]) -> None:
    """Reset the credential context using a token from :func:`set_credential_context`.

    Restores the contextvar to its previous value so the request's credential
    context is not available to any subsequent request (Requirement 12.3).

    Args:
        token: The token returned by :func:`set_credential_context`.
    """
    _credential_context.reset(token)


def create_zip_file(files: Dict[str, str]) -> bytes:
    """Create a ZIP file in memory from a dictionary of files.

    Args:
        files: Dictionary mapping filenames to file contents

    Returns:
        bytes: ZIP file content as bytes
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.read()


def encode_to_base64(data: bytes) -> str:
    """Encode bytes to base64 string.

    Args:
        data: Bytes to encode

    Returns:
        str: Base64-encoded string
    """
    return base64.b64encode(data).decode('utf-8')


def decode_from_base64(data: str) -> bytes:
    """Decode base64 string to bytes.

    Args:
        data: Base64-encoded string

    Returns:
        bytes: Decoded bytes
    """
    return base64.b64decode(data)


def create_aws_client(
    service_name: str,
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Generic AWS client factory for any service.

    Args:
        service_name: Name of the AWS service (e.g., 'omics', 'logs', 's3')
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured AWS service client

    Raises:
        Exception: If client creation fails
    """
    session = get_aws_session(region_name=region_name, profile_name=profile_name)
    try:
        return session.client(service_name)
    except Exception as e:
        logger.error(
            f'Failed to create {service_name} client in region {region_name or get_region()}: {str(e)}'
        )
        raise


def get_omics_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS HealthOmics client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured HealthOmics client

    Raises:
        Exception: If client creation fails
    """
    session = get_aws_session(region_name=region_name, profile_name=profile_name)
    service_name = get_omics_service_name()
    endpoint_url = get_omics_endpoint_url()

    try:
        if endpoint_url:
            return session.client(service_name, endpoint_url=endpoint_url)
        else:
            return session.client(service_name)
    except Exception as e:
        logger.error(
            f'Failed to create {service_name} client in region {region_name or get_region()}: {str(e)}'
        )
        raise


def get_logs_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS CloudWatch Logs client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured CloudWatch Logs client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('logs', region_name=region_name, profile_name=profile_name)


def get_codeconnections_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS CodeConnections client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured CodeConnections client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('codeconnections', region_name=region_name, profile_name=profile_name)


def get_ecr_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS ECR client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured ECR client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('ecr', region_name=region_name, profile_name=profile_name)


def get_codebuild_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS CodeBuild client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured CodeBuild client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('codebuild', region_name=region_name, profile_name=profile_name)


def get_iam_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS IAM client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured IAM client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('iam', region_name=region_name, profile_name=profile_name)


def get_account_id(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> str:
    """Get the current AWS account ID.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        str: AWS account ID

    Raises:
        Exception: If unable to retrieve account ID
    """
    try:
        session = get_aws_session(region_name=region_name, profile_name=profile_name)
        sts_client = session.client('sts')
        response = sts_client.get_caller_identity()
        return response['Account']
    except Exception as e:
        logger.error(f'Failed to get AWS account ID: {str(e)}')
        raise


def _derive_partition(session: boto3.Session) -> str:
    """Derive the AWS partition from a session's caller identity ARN.

    Builds an STS client from the given session, calls ``get_caller_identity``,
    and parses the partition out of the returned ARN
    (``arn:partition:sts::account-id:assumed-role/...``). Used by both the
    single-tenant and multi-tenant partition resolution paths.

    Args:
        session: The ``boto3.Session`` whose credentials identify the caller.

    Returns:
        str: AWS partition (e.g., 'aws', 'aws-cn', 'aws-us-gov').

    Raises:
        Exception: If the caller identity cannot be retrieved or the partition
            cannot be parsed. The error is logged and re-raised; no cached value
            for any other context is served (Requirement 11.4).
    """
    try:
        sts_client = session.client('sts')
        response = sts_client.get_caller_identity()
        # Extract partition from the ARN: arn:partition:sts::account-id:assumed-role/...
        arn = response['Arn']
        partition = arn.split(':')[1]
        logger.debug(f'Detected AWS partition: {partition}')
        return partition
    except Exception as e:
        logger.error(f'Failed to get AWS partition: {str(e)}')
        raise


# Per-context partition cache for multi-tenant mode, keyed by
# (CredentialContext.identity_key, region). Embedding identity_key in the key
# guarantees a partition derived for one identity is never served to a request
# resolving to a different identity (Requirements 11.2, 11.3).
#
# The cache is bounded to avoid unbounded memory growth on a long-running
# multi-tenant endpoint that serves a large or unbounded number of distinct
# caller identities. When the bound is exceeded the oldest entry is evicted
# (insertion-order FIFO). Eviction only affects a cold cache miss for the evicted
# identity (a re-derivation), never correctness: the key always embeds
# identity_key, so an evicted-and-refilled entry is still that identity's own
# partition. Partition values are tiny and stable per (identity, region), so a
# modest bound comfortably covers realistic concurrency.
_MAX_PARTITION_CACHE_ENTRIES = 4096
_partition_cache: 'OrderedDict[tuple[str, str], str]' = OrderedDict()


@lru_cache
def _default_get_partition(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> str:
    """Resolve the AWS partition for single-tenant mode (process-wide cached).

    Preserves today's behavior: a process-wide ``@lru_cache`` keyed by
    ``(region_name, profile_name)`` (Property 17). Sessions are produced via the
    active (default) resolver through :func:`get_aws_session`.

    Args:
        region_name: Optional region override.
        profile_name: Optional AWS profile override.

    Returns:
        str: AWS partition (e.g., 'aws', 'aws-cn', 'aws-us-gov').

    Raises:
        Exception: If a session cannot be built or the partition cannot be
            resolved.
    """
    try:
        session = get_aws_session(region_name=region_name, profile_name=profile_name)
    except Exception as e:
        logger.error(f'Failed to get AWS partition: {str(e)}')
        raise
    return _derive_partition(session)


class _PartitionResolver(Protocol):
    """Callable protocol for :func:`get_partition` exposing ``cache_clear``.

    ``get_partition`` is a plain function with a ``cache_clear`` attribute
    attached (preserving the historical ``get_partition.cache_clear()`` API).
    Typing the public name against this Protocol makes the ``cache_clear``
    attribute visible to static type checkers at every call site.
    """

    def __call__(
        self,
        region_name: Optional[str] = ...,
        profile_name: Optional[str] = ...,
    ) -> str:
        """Resolve the current AWS partition."""
        ...

    # Declared as a callable attribute (not a method) so the runtime attribute
    # assignment below type-checks cleanly and call sites see ``cache_clear``.
    cache_clear: Callable[[], None]


def _get_partition(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> str:
    """Get the current AWS partition.

    In single-tenant mode (the default resolver is active), preserves today's
    process-wide ``@lru_cache`` behavior keyed by ``(region, profile)``
    (Property 17).

    In multi-tenant mode (a :class:`RequestScopedCredentialResolver` is active),
    resolves the partition using the credentials of the active
    :class:`CredentialContext` and caches the result keyed by
    ``(identity_key, region)`` so a value derived for one identity is never
    served to a request with a different identity (Requirements 11.1, 11.2,
    11.3). A missing context raises :class:`NoRequestIdentityError`, and a
    resolution failure raises without serving another context's cached value
    (Requirement 11.4).

    Args:
        region_name: Optional region override.
        profile_name: Optional AWS profile override (ignored in multi-tenant
            mode, where identity comes from the active context).

    Returns:
        str: AWS partition (e.g., 'aws', 'aws-cn', 'aws-us-gov').

    Raises:
        NoRequestIdentityError: In multi-tenant mode when no credential context
            is present for the current request.
        Exception: If the partition cannot be resolved.
    """
    resolver = get_active_resolver()
    if isinstance(resolver, RequestScopedCredentialResolver):
        ctx = get_credential_context()
        if ctx is None:
            raise NoRequestIdentityError(
                'No request identity was resolved for this request; refusing to '
                'serve a partition value cached for a different credential context.'
            )
        key = (ctx.identity_key, region_name or get_region())
        cached = _partition_cache.get(key)
        if cached is not None:
            # Refresh recency so frequently-used identities are retained under the
            # FIFO/LRU bound.
            _partition_cache.move_to_end(key)
            return cached
        # profile is intentionally ignored; identity comes from the active context.
        session = resolver.resolve(CredentialRequest(region=region_name, profile=None))
        partition = _derive_partition(session)
        _partition_cache[key] = partition
        # Bound the cache to avoid unbounded growth across many caller identities.
        # Evicting the oldest entry never affects correctness (keys embed
        # identity_key); at worst the evicted identity re-derives on its next call.
        while len(_partition_cache) > _MAX_PARTITION_CACHE_ENTRIES:
            _partition_cache.popitem(last=False)
        return partition

    # Single-tenant: preserve today's process-wide cached behavior.
    return _default_get_partition(region_name, profile_name)


def _clear_partition_caches() -> None:
    """Clear both the single-tenant lru cache and the per-context partition cache.

    Exposed as ``get_partition.cache_clear`` to preserve the public
    ``get_partition.cache_clear()`` API used by existing callers and tests, while
    also resetting the multi-tenant per-context cache so state fully resets.
    """
    _default_get_partition.cache_clear()
    _partition_cache.clear()


# Preserve the historical ``get_partition.cache_clear()`` API. The single-tenant
# path is still backed by an lru cache; this shim also clears the per-context
# cache so a single call fully resets partition resolution state. The public name
# is typed against ``_PartitionResolver`` so the ``cache_clear`` attribute is
# visible to static type checkers at every call site.
get_partition: _PartitionResolver = cast(_PartitionResolver, _get_partition)
get_partition.cache_clear = _clear_partition_caches
