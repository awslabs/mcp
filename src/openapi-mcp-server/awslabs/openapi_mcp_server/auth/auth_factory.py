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
from awslabs.openapi_mcp_server.auth.auth_provider import AuthProvider, NullAuthProvider
from typing import Any, Dict, Type


# Registry of authentication providers keyed by auth type
_AUTH_PROVIDERS: Dict[str, Type[Any]] = {'none': NullAuthProvider}


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


def get_auth_provider(config: Config) -> AuthProvider:
    """Get an authentication provider based on configuration.

    Args:
        config: The application configuration

    Returns:
        AuthProvider: An authentication provider instance. Falls back to
        ``NullAuthProvider`` if the configured auth type is not registered.

    """
    auth_type = config.auth_type.lower()

    if auth_type not in _AUTH_PROVIDERS:
        logger.warning(f"Unknown authentication type '{auth_type}'. Falling back to 'none'.")
        auth_type = 'none'

    provider = _AUTH_PROVIDERS[auth_type](config)
    logger.info(f'Created authentication provider: {provider.provider_name}')

    if auth_type != 'none' and not provider.is_configured():
        logger.warning(
            f"Authentication provider '{provider.provider_name}' is not properly configured"
        )

    return provider


def is_auth_type_available(auth_type: str) -> bool:
    """Check if an authentication type is registered.

    Args:
        auth_type: The authentication type to check

    Returns:
        bool: True if available, False otherwise

    """
    return auth_type.lower() in _AUTH_PROVIDERS
