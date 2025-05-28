"""Base authentication provider interface."""

import abc
import httpx
from typing import Any, Dict, Optional


class AuthProvider(abc.ABC):
    """Abstract base class for authentication providers.

    Authentication providers handle different authentication methods for APIs.
    Implementing classes must provide methods for setting up authentication
    for HTTP requests.
    """

    @abc.abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for HTTP requests.

        Returns:
            Dict[str, str]: Headers to include in HTTP requests

        """
        pass

    @abc.abstractmethod
    def get_auth_params(self) -> Dict[str, str]:
        """Get authentication query parameters for HTTP requests.

        Returns:
            Dict[str, str]: Query parameters to include in HTTP requests

        """
        pass

    @abc.abstractmethod
    def get_auth_cookies(self) -> Dict[str, str]:
        """Get authentication cookies for HTTP requests.

        Returns:
            Dict[str, str]: Cookies to include in HTTP requests

        """
        pass

    @abc.abstractmethod
    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Get authentication object for HTTPX.

        Returns:
            Optional[httpx.Auth]: Authentication object for HTTPX client or None

        """
        pass

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Check if the authentication provider is properly configured.

        Returns:
            bool: True if configured, False otherwise

        """
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Get the name of the authentication provider.

        Returns:
            str: Name of the authentication provider

        """
        pass


class NullAuthProvider(AuthProvider):
    """No-op authentication provider.

    This provider is used when authentication is disabled or not configured.
    """

    def __init__(self, config: Any = None):
        """Initialize with optional configuration.

        Args:
            config: Optional configuration object (ignored by this provider)

        """
        # Config is ignored by this provider
        pass

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for HTTP requests.

        Returns:
            Dict[str, str]: Empty dict as no authentication is provided

        """
        return {}

    def get_auth_params(self) -> Dict[str, str]:
        """Get authentication query parameters for HTTP requests.

        Returns:
            Dict[str, str]: Empty dict as no authentication is provided

        """
        return {}

    def get_auth_cookies(self) -> Dict[str, str]:
        """Get authentication cookies for HTTP requests.

        Returns:
            Dict[str, str]: Empty dict as no authentication is provided

        """
        return {}

    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Get authentication object for HTTPX.

        Returns:
            Optional[httpx.Auth]: None as no authentication is provided

        """
        return None

    def is_configured(self) -> bool:
        """Check if the authentication provider is properly configured.

        Returns:
            bool: Always True as null provider requires no configuration

        """
        return True

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider.

        Returns:
            str: Name of the authentication provider

        """
        return 'none'
