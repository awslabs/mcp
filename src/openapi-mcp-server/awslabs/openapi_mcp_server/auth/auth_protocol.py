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
"""Authentication provider protocols and type definitions."""

import httpx
from awslabs.openapi_mcp_server.api.config import Config
from typing import Dict, Optional, Protocol, TypeVar, runtime_checkable


@runtime_checkable
class AuthProviderProtocol(Protocol):
    """Protocol defining the interface for authentication providers.

    This protocol allows for better type checking and removes the need for casting.
    """

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider."""
        ...

    def is_configured(self) -> bool:
        """Check if the authentication provider is properly configured."""
        ...

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for HTTP requests."""
        ...

    def get_auth_params(self) -> Dict[str, str]:
        """Get authentication query parameters for HTTP requests."""
        ...

    def get_auth_cookies(self) -> Dict[str, str]:
        """Get authentication cookies for HTTP requests."""
        ...

    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Get authentication object for HTTPX."""
        ...


# Type variable for auth provider classes that can be instantiated with a Config
T = TypeVar('T', bound=AuthProviderProtocol)


class AuthProviderFactory(Protocol):
    """Protocol for auth provider factory functions."""

    def __call__(self, config: Config) -> AuthProviderProtocol:
        """Create an authentication provider instance."""
        ...
