"""Connection management for Memcached MCP Server."""

import os
import ssl
from pymemcache.client.base import Client
from pymemcache.client.retrying import RetryingClient
from pymemcache.exceptions import MemcacheError
from typing import Any, Dict, Optional


class MemcachedConnectionManager:
    """Manages connection to Memcached."""

    _client: Optional[RetryingClient] = None

    @classmethod
    def get_connection(cls) -> RetryingClient:
        """Get or create a Memcached client connection.

        Returns:
            RetryingClient: A Memcached client with retry capabilities
        """
        if cls._client is None:
            # Get configuration from environment
            host = os.getenv('MEMCACHED_HOST', '127.0.0.1')
            port = int(os.getenv('MEMCACHED_PORT', '11211'))
            timeout = float(os.getenv('MEMCACHED_TIMEOUT', '1'))
            connect_timeout = float(os.getenv('MEMCACHED_CONNECT_TIMEOUT', '5'))
            retry_timeout = float(os.getenv('MEMCACHED_RETRY_TIMEOUT', '1'))
            max_retries = int(os.getenv('MEMCACHED_MAX_RETRIES', '3'))

            # SSL/TLS configuration
            use_tls = os.getenv('MEMCACHED_USE_TLS', 'false').lower() == 'true'
            tls_cert_path = os.getenv('MEMCACHED_TLS_CERT_PATH')
            tls_key_path = os.getenv('MEMCACHED_TLS_KEY_PATH')
            tls_ca_cert_path = os.getenv('MEMCACHED_TLS_CA_CERT_PATH')
            tls_verify = os.getenv('MEMCACHED_TLS_VERIFY', 'true').lower() == 'true'

            # Configure TLS context if enabled
            tls_context = None
            if use_tls:
                tls_context = ssl.create_default_context(
                    cafile=tls_ca_cert_path if tls_ca_cert_path else None
                )
                if not tls_verify:
                    tls_context.check_hostname = False
                    tls_context.verify_mode = ssl.CERT_NONE
                if tls_cert_path and tls_key_path:
                    tls_context.load_cert_chain(tls_cert_path, tls_key_path)

            # Create base client
            client_kwargs: Dict[str, Any] = {
                'server': (host, port),
                'timeout': timeout,
                'connect_timeout': connect_timeout,
                'no_delay': True,  # Disable Nagle's algorithm
            }
            if tls_context:
                client_kwargs['tls_context'] = tls_context

            base_client = Client(**client_kwargs)

            # Wrap with retry capabilities
            cls._client = RetryingClient(
                base_client,
                attempts=max_retries,
                retry_delay=retry_timeout,
                retry_for=[MemcacheError],
            )

        return cls._client

    @classmethod
    def close_connection(cls) -> None:
        """Close the Memcached client connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
