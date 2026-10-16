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

"""Server transport and network configuration parsing (Phase 1).

This module reads transport/network configuration from command-line flags and
environment variables, applying the precedence rule that a non-empty CLI flag
value wins over the matching environment variable. It also normalizes the
transport mode against the supported set and validates the network bind host
and port for network transports.

Host/port validation is only enforced for network transports
(``streamable-http`` / ``sse``). When the transport is ``stdio`` the host, port,
and path are ignored: the resolved configuration uses the network defaults so
that arbitrary bind values never affect stdio runtime behavior.
"""

import argparse
import ipaddress
import os
import re
from awslabs.aws_healthomics_mcp_server import consts
from dataclasses import dataclass
from typing import Optional, Sequence


# RFC 1123 host label: 1-63 chars of letters/digits/hyphens, not starting or
# ending with a hyphen.
_HOSTNAME_LABEL_RE = re.compile(r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$')

# Minimum and maximum valid TCP port numbers (inclusive).
_MIN_PORT = 1
_MAX_PORT = 65535

# Maximum length of a syntactically valid hostname (RFC 1123).
_MAX_HOSTNAME_LENGTH = 253


class TransportConfigError(Exception):
    """Raised when server transport/network configuration is invalid at startup."""


class UnsupportedTransportError(TransportConfigError):
    """Raised when an unsupported transport mode is supplied."""


@dataclass(frozen=True)
class ServerConfig:
    """Resolved server configuration for transport and network binding.

    Attributes:
        transport: One of the supported transport modes
            (``stdio``, ``streamable-http``, ``sse``).
        host: Network bind address. Format validation is performed in a later task.
        port: Network bind port. Range validation is performed in a later task.
        path: Request path served for network transports.
        multi_tenant: Whether request-scoped multi-tenant credential resolution is
            enabled (Phase 2). Defaults to disabled (single-tenant mode).
        inbound_mechanisms: The enabled inbound identity mechanisms (Phase 2), a
            subset of ``{'sigv4', 'jwt', 'explicit'}`` ordered by
            :data:`consts.INBOUND_PRECEDENCE`. Empty when none are selected.
        jwt_session_duration: Session duration (in seconds) applied to the inbound
            JWT-to-STS AssumeRole exchange. Defaults to
            :data:`consts.DEFAULT_JWT_SESSION_DURATION` when unset and is always an
            integer within the inclusive range
            ``consts.JWT_SESSION_DURATION_MIN..consts.JWT_SESSION_DURATION_MAX``.
        jwt_role_arn: The static role ARN used to select the ``StaticRoleResolver``
            for the inbound ``jwt`` mechanism, or ``None`` when unset. Mutually
            exclusive with :attr:`jwt_role_registry`; at most one of the two is
            ever non-``None`` on a resolved configuration.
        jwt_role_registry: The registry source (for example
            ``file:///path/map.json`` or ``dynamodb://table-name``) used to select
            the ``RegistryRoleResolver`` for the inbound ``jwt`` mechanism, or
            ``None`` when unset. Mutually exclusive with :attr:`jwt_role_arn`.
    """

    transport: str
    host: str
    port: int
    path: str
    multi_tenant: bool = False
    inbound_mechanisms: tuple[str, ...] = ()
    jwt_session_duration: int = consts.DEFAULT_JWT_SESSION_DURATION
    jwt_role_arn: Optional[str] = None
    jwt_role_registry: Optional[str] = None


def _resolve(cli_value: Optional[str], env_var: str) -> Optional[str]:
    """Resolve a configuration value with CLI-over-environment precedence.

    A command-line value wins when it is supplied and not empty/whitespace-only;
    otherwise the matching environment variable value is used (which may itself
    be ``None`` when unset).

    Args:
        cli_value: The raw value from the command-line flag, or ``None`` when absent.
        env_var: The name of the environment variable to fall back to.

    Returns:
        The resolved raw value, or ``None`` when neither source supplies one.
    """
    if cli_value is not None and cli_value.strip() != '':
        return cli_value
    return os.environ.get(env_var)


def normalize_transport(raw: Optional[str]) -> str:
    """Normalize a raw transport value to a supported transport mode.

    Surrounding whitespace is trimmed and the result is matched case-sensitively
    against the supported transport modes. An absent, empty, or whitespace-only
    value normalizes to the default ``stdio`` transport.

    Args:
        raw: The raw transport value from CLI or environment, or ``None``.

    Returns:
        A supported transport mode string.

    Raises:
        UnsupportedTransportError: If a non-empty value does not match a
            supported transport mode.
    """
    if raw is None:
        return consts.DEFAULT_TRANSPORT

    trimmed = raw.strip()
    if trimmed == '':
        return consts.DEFAULT_TRANSPORT

    if trimmed not in consts.SUPPORTED_TRANSPORTS:
        raise UnsupportedTransportError(
            consts.ERROR_UNSUPPORTED_TRANSPORT.format(
                trimmed, ', '.join(consts.SUPPORTED_TRANSPORTS)
            )
        )

    return trimmed


def is_loopback(host: str) -> bool:
    """Classify whether a host is an IP loopback literal.

    Returns ``True`` only when ``host`` is an IP address literal that is in the
    IPv4 ``127.0.0.0/8`` range or is the IPv6 loopback address ``::1``. Non-IP
    hostnames (e.g. ``localhost``) and any non-loopback IP literal return
    ``False``.

    Args:
        host: The host string to classify.

    Returns:
        ``True`` if ``host`` is a loopback IP literal, otherwise ``False``.
    """
    try:
        address = ipaddress.ip_address(host.strip())
    except ValueError:
        return False

    if isinstance(address, ipaddress.IPv4Address):
        return address in ipaddress.IPv4Network('127.0.0.0/8')

    return address == ipaddress.IPv6Address('::1')


def _is_valid_hostname(host: str) -> bool:
    """Return whether a string is a syntactically valid hostname (RFC 1123).

    The hostname must be at most 253 characters and consist of dot-separated
    labels, each 1-63 characters of letters, digits, or hyphens, and not start
    or end with a hyphen. A single trailing dot (the root label) is permitted.
    """
    if not host or len(host) > _MAX_HOSTNAME_LENGTH:
        return False

    candidate = host[:-1] if host.endswith('.') else host
    if candidate == '':
        return False

    return all(_HOSTNAME_LABEL_RE.match(label) for label in candidate.split('.'))


def _is_valid_host(host: str) -> bool:
    """Return whether a string is a valid IPv4/IPv6 address or hostname."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return _is_valid_hostname(host)


def _validate_host(raw: Optional[str]) -> str:
    """Resolve and validate a network bind host, applying the default when absent.

    Args:
        raw: The raw host value from CLI or environment, or ``None``.

    Returns:
        The validated host string (the default loopback host when absent).

    Raises:
        TransportConfigError: If a supplied value is not a valid IPv4 address,
            IPv6 address, or syntactically valid hostname. The server does not
            bind in this case.
    """
    if raw is None or raw.strip() == '':
        return consts.DEFAULT_HTTP_HOST

    trimmed = raw.strip()
    if not _is_valid_host(trimmed):
        raise TransportConfigError(consts.ERROR_INVALID_HOST.format(raw))
    return trimmed


def _parse_port(raw: Optional[str]) -> int:
    """Convert a raw port value to an integer in ``1..65535``, applying the default.

    An absent or whitespace-only value yields the default port. Otherwise the
    value must parse as an integer within the inclusive range ``1..65535``.

    Args:
        raw: The raw port value from CLI or environment, or ``None``.

    Returns:
        The validated port as an integer.

    Raises:
        TransportConfigError: If a supplied value is not an integer or falls
            outside the range ``1..65535``. The server does not bind in this case.
    """
    if raw is None or raw.strip() == '':
        return consts.DEFAULT_HTTP_PORT

    trimmed = raw.strip()
    try:
        port = int(trimmed)
    except ValueError as exc:
        raise TransportConfigError(consts.ERROR_INVALID_PORT.format(raw)) from exc

    if port < _MIN_PORT or port > _MAX_PORT:
        raise TransportConfigError(consts.ERROR_INVALID_PORT.format(raw))

    return port


def _parse_jwt_session_duration(raw: Optional[str]) -> int:
    """Convert a raw JWT session-duration value to a validated integer of seconds.

    An absent or whitespace-only value yields
    :data:`consts.DEFAULT_JWT_SESSION_DURATION`. Otherwise the value must parse as
    an integer within the inclusive range
    ``consts.JWT_SESSION_DURATION_MIN..consts.JWT_SESSION_DURATION_MAX``.

    Args:
        raw: The raw session-duration value from CLI or environment, or ``None``.

    Returns:
        The validated session duration in seconds.

    Raises:
        TransportConfigError: If a supplied value is not an integer or falls
            outside the accepted range. The error message identifies the rejected
            value and the accepted range, and the server does not start in this
            case.
    """
    if raw is None or raw.strip() == '':
        return consts.DEFAULT_JWT_SESSION_DURATION

    trimmed = raw.strip()
    try:
        duration = int(trimmed)
    except ValueError as exc:
        raise TransportConfigError(
            consts.ERROR_INVALID_JWT_SESSION_DURATION.format(
                raw, consts.JWT_SESSION_DURATION_MIN, consts.JWT_SESSION_DURATION_MAX
            )
        ) from exc

    if duration < consts.JWT_SESSION_DURATION_MIN or duration > consts.JWT_SESSION_DURATION_MAX:
        raise TransportConfigError(
            consts.ERROR_INVALID_JWT_SESSION_DURATION.format(
                raw, consts.JWT_SESSION_DURATION_MIN, consts.JWT_SESSION_DURATION_MAX
            )
        )

    return duration


def _resolve_role_resolution_sources(
    raw_role_arn: Optional[str], raw_role_registry: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """Select the single active JWT role-resolution source, rejecting conflicts.

    The two sources ``MCP_JWT_ROLE_ARN`` (static resolver) and
    ``MCP_JWT_ROLE_REGISTRY`` (registry resolver) are mutually exclusive. Each raw
    value is normalized by trimming surrounding whitespace; an absent, empty, or
    whitespace-only value is treated as unset (``None``). When exactly one source
    is set, that source's normalized value is returned and the other is ``None``.
    When neither is set, both are ``None`` and JWT-based role resolution is left
    disabled. When both are set, the configuration is rejected so the server exits
    without starting a transport.

    Args:
        raw_role_arn: The raw static role ARN value from CLI or environment, or
            ``None`` when absent.
        raw_role_registry: The raw registry source value from CLI or environment,
            or ``None`` when absent.

    Returns:
        A ``(role_arn, role_registry)`` tuple in which at most one element is a
        non-empty string and the other is ``None``.

    Raises:
        TransportConfigError: If both role-resolution sources are set. The error
            message names both conflicting sources and the server does not start.
    """
    role_arn = (
        raw_role_arn.strip() if raw_role_arn is not None and raw_role_arn.strip() != '' else None
    )
    role_registry = (
        raw_role_registry.strip()
        if raw_role_registry is not None and raw_role_registry.strip() != ''
        else None
    )

    if role_arn is not None and role_registry is not None:
        raise TransportConfigError(
            consts.ERROR_CONFLICTING_ROLE_RESOLUTION_SOURCES.format(
                consts.MCP_JWT_ROLE_ARN_ENV, consts.MCP_JWT_ROLE_REGISTRY_ENV
            )
        )

    return role_arn, role_registry


# Recognized boolean values for the multi-tenant flag/env var. Parsing is
# case-insensitive and trims surrounding whitespace before matching.
_MULTI_TENANT_ENABLE_VALUES = ('true', '1', 'yes', 'on', 'enabled')
_MULTI_TENANT_DISABLE_VALUES = ('false', '0', 'no', 'off', 'disabled')


def _parse_multi_tenant(raw: Optional[str]) -> bool:
    """Parse a raw multi-tenant configuration value into a boolean.

    The value is matched case-insensitively after trimming surrounding
    whitespace. Absent, empty, or whitespace-only values, as well as the
    recognized disable values, yield ``False`` (single-tenant mode). The
    recognized enable values yield ``True``.

    Args:
        raw: The raw value from CLI or environment, or ``None`` when absent.

    Returns:
        ``True`` when multi-tenant mode is enabled, ``False`` otherwise.

    Raises:
        TransportConfigError: If a supplied value is neither a recognized enable
            nor disable value. The server does not start in this case.
    """
    if raw is None:
        return False

    trimmed = raw.strip().lower()
    if trimmed == '':
        return False
    if trimmed in _MULTI_TENANT_ENABLE_VALUES:
        return True
    if trimmed in _MULTI_TENANT_DISABLE_VALUES:
        return False

    accepted = ', '.join(_MULTI_TENANT_ENABLE_VALUES + _MULTI_TENANT_DISABLE_VALUES)
    raise TransportConfigError(consts.ERROR_INVALID_MULTI_TENANT_VALUE.format(raw, accepted))


def _parse_inbound_mechanisms(raw: Optional[str]) -> tuple[str, ...]:
    """Parse a raw inbound-auth value into an ordered tuple of mechanisms.

    The value is a comma-separated list selecting a subset of
    :data:`consts.INBOUND_MECHANISMS` (for example ``'sigv4,jwt'``). Tokens are
    trimmed and matched case-insensitively; empty tokens are ignored. The result
    is de-duplicated and ordered deterministically by
    :data:`consts.INBOUND_PRECEDENCE`. An absent or empty value yields an empty
    tuple.

    Args:
        raw: The raw value from CLI or environment, or ``None`` when absent.

    Returns:
        A tuple of the selected mechanisms ordered by ``INBOUND_PRECEDENCE``.

    Raises:
        TransportConfigError: If any token is not a recognized inbound mechanism.
            The server does not start in this case.
    """
    if raw is None or raw.strip() == '':
        return ()

    selected: set[str] = set()
    for token in raw.split(','):
        mechanism = token.strip().lower()
        if mechanism == '':
            continue
        if mechanism not in consts.INBOUND_MECHANISMS:
            accepted = ', '.join(consts.INBOUND_MECHANISMS)
            raise TransportConfigError(
                consts.ERROR_INVALID_INBOUND_AUTH.format(token.strip(), accepted)
            )
        selected.add(mechanism)

    return tuple(mechanism for mechanism in consts.INBOUND_PRECEDENCE if mechanism in selected)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for transport and network configuration flags."""
    parser = argparse.ArgumentParser(
        prog='aws-healthomics-mcp-server',
        description='AWS HealthOmics MCP Server',
        add_help=True,
    )
    parser.add_argument(
        '--transport',
        dest='transport',
        default=None,
        help=(
            'Transport mode: one of '
            f'{", ".join(consts.SUPPORTED_TRANSPORTS)} '
            f'(default: {consts.DEFAULT_TRANSPORT}). '
            f'Overrides the {consts.MCP_TRANSPORT_ENV} environment variable.'
        ),
    )
    parser.add_argument(
        '--host',
        dest='host',
        default=None,
        help=(
            'Network bind address for HTTP-based transports '
            f'(default: {consts.DEFAULT_HTTP_HOST}). '
            f'Overrides the {consts.MCP_HOST_ENV} environment variable.'
        ),
    )
    parser.add_argument(
        '--port',
        dest='port',
        default=None,
        help=(
            'Network bind port for HTTP-based transports '
            f'(default: {consts.DEFAULT_HTTP_PORT}). '
            f'Overrides the {consts.MCP_PORT_ENV} environment variable.'
        ),
    )
    parser.add_argument(
        '--path',
        dest='path',
        default=None,
        help=(
            'Request path served for HTTP-based transports '
            f'(default: {consts.DEFAULT_HTTP_PATH}). '
            f'Overrides the {consts.MCP_PATH_ENV} environment variable.'
        ),
    )
    parser.add_argument(
        '--multi-tenant',
        dest='multi_tenant',
        default=None,
        help=(
            'Enable request-scoped multi-tenant credential resolution. Accepts '
            f'enable values ({", ".join(_MULTI_TENANT_ENABLE_VALUES)}) or disable '
            f'values ({", ".join(_MULTI_TENANT_DISABLE_VALUES)}); case-insensitive '
            '(default: disabled). Requires a network transport (streamable-http '
            f'or sse). Overrides the {consts.MCP_MULTI_TENANT_ENV} environment '
            'variable.'
        ),
    )
    parser.add_argument(
        '--inbound-auth',
        dest='inbound_auth',
        default=None,
        help=(
            'Comma-separated subset of inbound identity mechanisms to enable '
            f'({", ".join(consts.INBOUND_MECHANISMS)}), for example "sigv4,jwt". '
            f'Overrides the {consts.MCP_INBOUND_AUTH_ENV} environment variable.'
        ),
    )
    parser.add_argument(
        '--jwt-session-duration',
        dest='jwt_session_duration',
        default=None,
        help=(
            'Session duration in seconds for the inbound JWT-to-STS AssumeRole '
            f'exchange. Must be an integer within the inclusive range '
            f'{consts.JWT_SESSION_DURATION_MIN} to {consts.JWT_SESSION_DURATION_MAX} '
            f'(default: {consts.DEFAULT_JWT_SESSION_DURATION}). Overrides the '
            f'{consts.MCP_JWT_SESSION_DURATION_ENV} environment variable.'
        ),
    )
    parser.add_argument(
        '--jwt-role-arn',
        dest='jwt_role_arn',
        default=None,
        help=(
            'Static IAM role ARN assumed by the inbound JWT-to-STS exchange, '
            'selecting the static role resolver. Mutually exclusive with '
            f'--jwt-role-registry. Overrides the {consts.MCP_JWT_ROLE_ARN_ENV} '
            'environment variable.'
        ),
    )
    parser.add_argument(
        '--jwt-role-registry',
        dest='jwt_role_registry',
        default=None,
        help=(
            'Registry source for per-request role/ExternalId resolution (for '
            'example "file:///path/map.json" or "dynamodb://table-name"), '
            'selecting the registry role resolver. Mutually exclusive with '
            f'--jwt-role-arn. Overrides the {consts.MCP_JWT_ROLE_REGISTRY_ENV} '
            'environment variable.'
        ),
    )
    return parser


def parse_config(argv: Optional[Sequence[str]] = None) -> ServerConfig:
    """Parse and resolve server configuration from CLI flags and environment.

    Each value is resolved with CLI-over-environment precedence and the transport
    mode is normalized against the supported set.

    Args:
        argv: Optional argument vector (excluding the program name). When ``None``,
            ``sys.argv`` is used by argparse.

    Returns:
        A fully populated, frozen :class:`ServerConfig`.

    Raises:
        UnsupportedTransportError: If an unsupported transport value is supplied.
        TransportConfigError: If the supplied multi-tenant value is unrecognized,
            an inbound-auth token is not a recognized mechanism, the supplied JWT
            session duration is not an integer or falls outside the inclusive range
            ``consts.JWT_SESSION_DURATION_MIN..consts.JWT_SESSION_DURATION_MAX``,
            both JWT role-resolution sources (``MCP_JWT_ROLE_ARN`` and
            ``MCP_JWT_ROLE_REGISTRY``) are configured, multi-tenant mode is enabled
            together with the ``stdio`` transport, or, for a network transport, the
            supplied host is not a valid IPv4/IPv6 address or hostname or the
            supplied port is not an integer in ``1..65535``.
    """
    parser = _build_parser()
    args, _unknown = parser.parse_known_args(argv)

    raw_transport = _resolve(args.transport, consts.MCP_TRANSPORT_ENV)
    raw_host = _resolve(args.host, consts.MCP_HOST_ENV)
    raw_port = _resolve(args.port, consts.MCP_PORT_ENV)
    raw_path = _resolve(args.path, consts.MCP_PATH_ENV)
    raw_multi_tenant = _resolve(args.multi_tenant, consts.MCP_MULTI_TENANT_ENV)
    raw_inbound_auth = _resolve(args.inbound_auth, consts.MCP_INBOUND_AUTH_ENV)
    raw_jwt_session_duration = _resolve(
        args.jwt_session_duration, consts.MCP_JWT_SESSION_DURATION_ENV
    )
    raw_jwt_role_arn = _resolve(args.jwt_role_arn, consts.MCP_JWT_ROLE_ARN_ENV)
    raw_jwt_role_registry = _resolve(args.jwt_role_registry, consts.MCP_JWT_ROLE_REGISTRY_ENV)

    transport = normalize_transport(raw_transport)
    multi_tenant = _parse_multi_tenant(raw_multi_tenant)
    inbound_mechanisms = _parse_inbound_mechanisms(raw_inbound_auth)
    jwt_session_duration = _parse_jwt_session_duration(raw_jwt_session_duration)
    jwt_role_arn, jwt_role_registry = _resolve_role_resolution_sources(
        raw_jwt_role_arn, raw_jwt_role_registry
    )

    # Multi-tenant mode requires a network transport. Reject the stdio + multi-tenant
    # combination before any transport starts so the server exits without serving.
    if multi_tenant and transport not in consts.NETWORK_TRANSPORTS:
        raise TransportConfigError(consts.ERROR_MULTI_TENANT_REQUIRES_NETWORK)

    # Host/port/path only apply to network transports. For stdio they are
    # ignored entirely: the resolved configuration uses network defaults so that
    # arbitrary (even invalid) bind values never affect stdio runtime behavior
    # and never raise a configuration error.
    if transport not in consts.NETWORK_TRANSPORTS:
        return ServerConfig(
            transport=transport,
            host=consts.DEFAULT_HTTP_HOST,
            port=consts.DEFAULT_HTTP_PORT,
            path=consts.DEFAULT_HTTP_PATH,
            multi_tenant=multi_tenant,
            inbound_mechanisms=inbound_mechanisms,
            jwt_session_duration=jwt_session_duration,
            jwt_role_arn=jwt_role_arn,
            jwt_role_registry=jwt_role_registry,
        )

    host = _validate_host(raw_host)
    port = _parse_port(raw_port)
    path = (
        raw_path if raw_path is not None and raw_path.strip() != '' else consts.DEFAULT_HTTP_PATH
    )

    return ServerConfig(
        transport=transport,
        host=host,
        port=port,
        path=path,
        multi_tenant=multi_tenant,
        inbound_mechanisms=inbound_mechanisms,
        jwt_session_duration=jwt_session_duration,
        jwt_role_arn=jwt_role_arn,
        jwt_role_registry=jwt_role_registry,
    )
