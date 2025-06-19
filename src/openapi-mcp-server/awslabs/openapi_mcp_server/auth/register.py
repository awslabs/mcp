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
"""Register authentication providers."""

import os
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.auth.auth_factory import register_auth_provider


def register_auth_providers() -> None:
    """Register authentication providers based on configuration.

    This function registers only the authentication provider that is specified
    by the AUTH_TYPE environment variable or command-line argument.
    If no auth type is specified, it registers all available providers.
    """
    # Get the auth type from environment variable
    auth_type = os.environ.get('AUTH_TYPE', '').lower()

    # If no auth type is specified in the environment, register all providers
    if not auth_type:
        logger.debug('No auth type specified in environment, registering all providers')
        register_all_providers()
    else:
        # Register only the specified provider
        register_provider_by_type(auth_type)


def register_provider_by_type(auth_type: str) -> None:
    """Register a specific authentication provider by type.

    Args:
        auth_type: The type of authentication provider to register

    """
    if auth_type == 'bearer':
        from awslabs.openapi_mcp_server.auth.bearer_auth import BearerAuthProvider

        register_auth_provider('bearer', BearerAuthProvider)
        logger.info('Registered Bearer authentication provider')
    elif auth_type == 'basic':
        from awslabs.openapi_mcp_server.auth.basic_auth import BasicAuthProvider

        register_auth_provider('basic', BasicAuthProvider)
        logger.info('Registered Basic authentication provider')
    elif auth_type == 'api_key':
        from awslabs.openapi_mcp_server.auth.api_key_auth import ApiKeyAuthProvider

        register_auth_provider('api_key', ApiKeyAuthProvider)
        logger.info('Registered Api_Key authentication provider')
    elif auth_type == 'cognito':
        from awslabs.openapi_mcp_server.auth.cognito_auth import CognitoAuthProvider

        register_auth_provider('cognito', CognitoAuthProvider)
        logger.info('Registered Cognito authentication provider')
    else:
        logger.warning(f'Unknown auth type: {auth_type}, registering all providers')
        register_all_providers()


def register_all_providers() -> None:
    """Register all available authentication providers."""
    # Import all provider classes
    from awslabs.openapi_mcp_server.auth.api_key_auth import ApiKeyAuthProvider
    from awslabs.openapi_mcp_server.auth.basic_auth import BasicAuthProvider
    from awslabs.openapi_mcp_server.auth.bearer_auth import BearerAuthProvider

    # Register the standard providers
    register_auth_provider('bearer', BearerAuthProvider)
    logger.info('Registered Bearer authentication provider')

    register_auth_provider('basic', BasicAuthProvider)
    logger.info('Registered Basic authentication provider')

    register_auth_provider('api_key', ApiKeyAuthProvider)
    logger.info('Registered Api_Key authentication provider')

    # Only register Cognito if it's available
    try:
        from awslabs.openapi_mcp_server.auth.cognito_auth import CognitoAuthProvider

        register_auth_provider('cognito', CognitoAuthProvider)
        logger.info('Registered Cognito authentication provider')
    except ImportError:
        logger.debug('Cognito authentication provider not available')


# Don't register providers automatically when this module is imported
# This will be done explicitly in server.py
