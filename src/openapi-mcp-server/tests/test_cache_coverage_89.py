"""Tests to achieve 89% coverage by targeting specific uncovered lines in cache_provider.py."""

import pytest
import time
from awslabs.openapi_mcp_server.utils.cache_provider import (
    CachetoolsProvider,
    InMemoryCacheProvider,
    create_cache_provider,
)
from unittest.mock import patch


class TestCacheCoverage89:
    """Tests to achieve 89% coverage."""

    def test_in_memory_cache_cleanup_with_expired_entries(self):
        """Test cache cleanup with expired entries."""
        cache = InMemoryCacheProvider(ttl_seconds=1)

        # Add some entries
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Wait for entries to expire
        time.sleep(1.1)

        # Add a fresh entry
        cache.set('key3', 'value3')

        # Mock logger to capture debug message
        with patch('awslabs.openapi_mcp_server.utils.cache_provider.logger') as mock_logger:
            # Trigger cleanup
            expired_count = cache.cleanup()

            # Should have removed 2 expired entries
            assert expired_count == 2

            # Verify debug message was logged
            mock_logger.debug.assert_called_with('Cache cleanup: removed 2 expired entries')

            # Verify only the fresh entry remains
            assert cache.get('key3') == 'value3'
            assert cache.get('key1') is None
            assert cache.get('key2') is None

    def test_cachetools_provider_invalidate_existing_key(self):
        """Test invalidating an existing key in cachetools provider."""
        # Skip if cachetools is not available
        try:
            cache = CachetoolsProvider(ttl_seconds=60)
        except Exception:
            pytest.skip('cachetools not available')

        # Add an entry
        cache.set('test_key', 'test_value')

        # Mock logger to capture debug message
        with patch('awslabs.openapi_mcp_server.utils.cache_provider.logger') as mock_logger:
            # Invalidate the key
            result = cache.invalidate('test_key')

            # Should return True
            assert result is True

            # Verify debug message was logged
            mock_logger.debug.assert_called_with('Cache invalidated: test_key')

            # Verify key is gone
            assert cache.get('test_key') is None

    def test_cachetools_provider_invalidate_nonexistent_key(self):
        """Test invalidating a non-existent key in cachetools provider."""
        # Skip if cachetools is not available
        try:
            cache = CachetoolsProvider(ttl_seconds=60)
        except Exception:
            pytest.skip('cachetools not available')

        # Try to invalidate a non-existent key
        result = cache.invalidate('nonexistent_key')

        # Should return False
        assert result is False

    def test_cachetools_provider_clear(self):
        """Test clearing all entries from cachetools provider."""
        # Skip if cachetools is not available
        try:
            cache = CachetoolsProvider(ttl_seconds=60)
        except Exception:
            pytest.skip('cachetools not available')

        # Add some entries
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')

        # Mock logger to capture debug message
        with patch('awslabs.openapi_mcp_server.utils.cache_provider.logger') as mock_logger:
            # Clear the cache
            cache.clear()

            # Verify debug message was logged
            mock_logger.debug.assert_called_with('Cache cleared (3 entries removed)')

            # Verify all entries are gone
            assert cache.get('key1') is None
            assert cache.get('key2') is None
            assert cache.get('key3') is None

    def test_create_cache_provider_cachetools_exception_fallback(self):
        """Test fallback to in-memory provider when cachetools fails."""
        # Mock cachetools to be available but raise an exception
        with patch('awslabs.openapi_mcp_server.utils.cache_provider.USE_CACHETOOLS', True):
            with patch(
                'awslabs.openapi_mcp_server.utils.cache_provider.CACHETOOLS_AVAILABLE', True
            ):
                with patch(
                    'awslabs.openapi_mcp_server.utils.cache_provider.CachetoolsProvider'
                ) as mock_cachetools:
                    mock_cachetools.side_effect = Exception('Cachetools initialization failed')

                    # Mock logger to capture error and info messages
                    with patch(
                        'awslabs.openapi_mcp_server.utils.cache_provider.logger'
                    ) as mock_logger:
                        # Get cache provider - should fall back to in-memory
                        provider = create_cache_provider(ttl_seconds=60)

                        # Should be InMemoryCacheProvider
                        assert isinstance(provider, InMemoryCacheProvider)

                        # Verify error and info messages were logged
                        mock_logger.error.assert_called_with(
                            'Failed to create cachetools cache provider: Cachetools initialization failed'
                        )
                        mock_logger.info.assert_called_with(
                            'Falling back to in-memory cache provider'
                        )
