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
"""Authentication provider factory."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_protocol import AuthProviderProtocol
from awslabs.openapi_mcp_server.auth.auth_provider import NullAuthProvider
from typing import Any, Dict, Type


# Registry of authentication providers
_AUTH_PROVIDERS: Dict[str, Type[Any]] = {'none': NullAuthProvider}

# Cache for provider instances
_PROVIDER_CACHE: Dict[int, AuthProviderProtocol] = {}


def register_auth_provider(auth_type: str, provider_class: Type[Any]) -> None:
    """Register an authentication provider.

    Args:
        auth_type: The authentication type identifier
        provider_class: The provider class to register

    Raises:
        ValueError: If auth_type is already registered

    """
    auth_type = auth_type.lower()
    if auth_type in _AUTH_PROVIDERS:
        raise ValueError(f"Authentication provider for type '{auth_type}' already registered")

    _AUTH_PROVIDERS[auth_type] = provider_class
    logger.debug(
        f"Registered authentication provider for type '{auth_type}': {provider_class.__name__}"
    )


def _get_provider_instance(
    auth_type: str, config_hash: int, config: Config
) -> AuthProviderProtocol:
    """Get a cached provider instance or create a new one.

    Args:
        auth_type: The authentication type
        config_hash: Hash of the configuration to differentiate instances
        config: The configuration object

    Returns:
        AuthProviderProtocol: The authentication provider instance

    """
    # Check if we have a cached instance
    if config_hash in _PROVIDER_CACHE:
        logger.debug(f'Using cached authentication provider for {auth_type}')
        return _PROVIDER_CACHE[config_hash]

    # Create a new instance
    provider_class = _AUTH_PROVIDERS[auth_type]
    provider = provider_class(config)

    # Cache the instance
    _PROVIDER_CACHE[config_hash] = provider

    logger.debug(f'Created new authentication provider: {provider.provider_name}')
    return provider


def get_auth_provider(config: Config) -> AuthProviderProtocol:
    """Get an authentication provider based on configuration.

    Args:
        config: The application configuration

    Returns:
        AuthProviderProtocol: An authentication provider instance

    Notes:
        If the specified auth_type is not registered, falls back to NullAuthProvider
        Uses caching to avoid creating duplicate provider instances

    """
    auth_type = config.auth_type.lower()

    if auth_type not in _AUTH_PROVIDERS:
        logger.warning(f"Unknown authentication type '{auth_type}'. Falling back to 'none'.")
        auth_type = 'none'

    # Create a hash of the relevant config parts for caching
    config_hash = hash(
        (
            auth_type,
            getattr(config, 'auth_token', None),
            getattr(config, 'auth_username', None),
            getattr(config, 'auth_password', None),
            getattr(config, 'auth_api_key', None),
            getattr(config, 'auth_api_key_name', None),
            getattr(config, 'auth_api_key_in', None),
        )
    )

    # Get or create provider instance
    provider = _get_provider_instance(auth_type, config_hash, config)

    logger.info(f'Created authentication provider: {provider.provider_name}')

    if not provider.is_configured() and auth_type != 'none':
        logger.warning(
            f"Authentication provider '{provider.provider_name}' is not properly configured"
        )

    return provider


def is_auth_type_available(auth_type: str) -> bool:
    """Check if an authentication type is available.

    Args:
        auth_type: The authentication type to check

    Returns:
        bool: True if available, False otherwise

    """
    return auth_type.lower() in _AUTH_PROVIDERS


def clear_provider_cache() -> None:
    """Clear the provider instance cache.

    This is useful for testing or when configuration changes.
    """
    _PROVIDER_CACHE.clear()
    logger.debug('Authentication provider cache cleared')
