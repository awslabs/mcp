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

"""CloudWatch Application Signals MCP Server - AWS client initialization.

Supports two modes:
1. Default mode: Module-level singleton clients using AWS_PROFILE or the default credential chain.
2. Custom mode: Per-request clients via a pluggable factory, allowing consumers to override
   credentials and region. Set via set_client_factory() and set_region_override().

Both the region override and the client factory use ``contextvars.ContextVar`` so
that each async request/coroutine gets its own isolated copy — no cross-request
race conditions.
"""

import boto3
import contextvars
import os
from . import __version__
from botocore.config import Config
from contextlib import contextmanager
from loguru import logger
from typing import Any, Callable, Dict, Optional, cast


# Default AWS region from environment variable
_DEFAULT_REGION = os.environ.get('AWS_REGION', 'us-east-1')
logger.debug(f'Default AWS region: {_DEFAULT_REGION}')

# Backward-compatible export (static, does not reflect overrides)
AWS_REGION = _DEFAULT_REGION

# ---------------------------------------------------------------------------
# Region override — per-request via contextvars so concurrent async
# requests never interfere with each other.
# ---------------------------------------------------------------------------

_region_override_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    '_region_override', default=None
)


def set_region_override(region: str) -> None:
    """Override the AWS region for the current async context.

    Requires a custom client factory to be set first (via ``set_client_factory``),
    because the default singleton clients are pre-built with the default region
    and would not honour this override.

    Raises:
        RuntimeError: If no custom client factory has been registered.
    """
    if _client_factory_var.get() is None:
        raise RuntimeError(
            'set_region_override() requires a custom client factory. '
            'Call set_client_factory() first.'
        )
    _region_override_var.set(region)
    logger.info(f'Region override set: {region}')


def clear_region_override() -> None:
    """Clear the region override for the current async context."""
    _region_override_var.set(None)


@contextmanager
def region_override(region: str):
    """Context manager that sets and automatically clears a region override."""
    token = _region_override_var.set(region)
    try:
        yield
    finally:
        _region_override_var.reset(token)


def get_region() -> str:
    """Get the active AWS region for the current async context.

    Returns the override region if set, otherwise the default from AWS_REGION env var.
    """
    override = _region_override_var.get()
    return override if override is not None else _DEFAULT_REGION


def _default_boto3_config() -> Config:
    """Create the default botocore Config with user agent suffix."""
    mcp_source = os.environ.get('MCP_RUN_FROM')
    user_agent_suffix = f'/{mcp_source}' if mcp_source else ''
    return Config(
        user_agent_extra=f'awslabs.cloudwatch-applicationsignals-mcp-server/{__version__}{user_agent_suffix}'
    )


def _get_endpoint_overrides() -> Dict[str, Optional[str]]:
    """Get endpoint URL overrides from environment variables."""
    return {
        'application-signals': os.environ.get('MCP_APPLICATIONSIGNALS_ENDPOINT'),
        'logs': os.environ.get('MCP_LOGS_ENDPOINT'),
        'cloudwatch': os.environ.get('MCP_CLOUDWATCH_ENDPOINT'),
        'xray': os.environ.get('MCP_XRAY_ENDPOINT'),
        'synthetics': os.environ.get('MCP_SYNTHETICS_ENDPOINT'),
    }


# ---------------------------------------------------------------------------
# Client factory hook — per-request via contextvars so concurrent async
# requests never interfere with each other.
# ---------------------------------------------------------------------------

_client_factory_var: contextvars.ContextVar[Optional[Callable[[str], Any]]] = (
    contextvars.ContextVar('_client_factory', default=None)
)


def set_client_factory(factory: Callable[[str], Any]) -> None:
    """Set a custom client factory for the current async context.

    The factory receives a service name (e.g. 'logs', 'cloudwatch') and must
    return a boto3 client for that service. Use this to inject custom credentials
    or configuration when consuming this package.

    Args:
        factory: A callable(service_name: str) -> boto3.client
    """
    _client_factory_var.set(factory)
    logger.info('Custom client factory registered')


def clear_client_factory() -> None:
    """Clear the custom client factory for the current async context.

    Also clears any region override since it is only meaningful with a custom factory.
    """
    _client_factory_var.set(None)
    _region_override_var.set(None)


def get_client(service_name: str) -> Any:
    """Get a boto3 client for the given service.

    Delegates to the custom factory if one is set for the current async context,
    otherwise returns the module-level singleton client initialized from the
    default credential chain.

    Args:
        service_name: AWS service name (e.g. 'logs', 'application-signals', 'cloudwatch')

    Returns:
        A boto3 client for the specified service.

    Raises:
        KeyError: If *service_name* is not a recognised service and no custom factory is set.
    """
    factory = _client_factory_var.get()
    if factory is not None:
        logger.debug(f'get_client({service_name}): using custom factory')
        return factory(service_name)

    # Fall back to module-level singletons
    logger.debug(f'get_client({service_name}): using default singleton (local creds)')
    if service_name not in _singleton_clients:
        raise KeyError(
            f"Unknown service '{service_name}'. "
            f'Available services: {sorted(_singleton_clients.keys())}'
        )
    return _singleton_clients[service_name]


# ---------------------------------------------------------------------------
# Module-level singleton clients (local/CLI mode)
# ---------------------------------------------------------------------------


def _initialize_aws_clients() -> Dict[str, Any]:
    """Initialize AWS clients with proper configuration."""
    config = _default_boto3_config()
    endpoints = _get_endpoint_overrides()

    for svc, url in endpoints.items():
        if url:
            logger.debug(f'Using {svc} endpoint override: {url}')

    if aws_profile := os.environ.get('AWS_PROFILE'):
        logger.debug(f'Using AWS profile: {aws_profile}')
        session = boto3.Session(profile_name=aws_profile, region_name=_DEFAULT_REGION)
        create = cast(Callable[..., Any], session.client)
    else:
        create = cast(Callable[..., Any], boto3.client)

    def _make(service_name: str, **extra_kwargs) -> Any:
        kwargs = {'region_name': _DEFAULT_REGION, 'config': config}
        endpoint = endpoints.get(service_name)
        if endpoint:
            kwargs['endpoint_url'] = endpoint
        kwargs.update(extra_kwargs)
        return create(service_name, **kwargs)

    clients = {
        'logs': _make('logs'),
        'application-signals': _make('application-signals'),
        'cloudwatch': _make('cloudwatch'),
        'xray': _make('xray'),
        'synthetics': _make('synthetics'),
        's3': _make('s3'),
        'iam': _make('iam'),
        'lambda': _make('lambda'),
        'sts': _make('sts'),
    }

    logger.debug('AWS clients initialized successfully')
    return clients


try:
    _singleton_clients = _initialize_aws_clients()
except Exception as e:
    logger.error(f'Failed to initialize AWS clients: {str(e)}')
    raise


# ---------------------------------------------------------------------------
# Backward-compatible module-level exports
# ---------------------------------------------------------------------------

logs_client = _singleton_clients['logs']
applicationsignals_client = _singleton_clients['application-signals']
cloudwatch_client = _singleton_clients['cloudwatch']
xray_client = _singleton_clients['xray']
synthetics_client = _singleton_clients['synthetics']
s3_client = _singleton_clients['s3']
iam_client = _singleton_clients['iam']
lambda_client = _singleton_clients['lambda']
sts_client = _singleton_clients['sts']
