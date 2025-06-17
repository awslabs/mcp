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
"""Tests for authentication provider factory caching."""

import unittest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_factory import (
    _PROVIDER_CACHE,
    clear_provider_cache,
    get_auth_provider,
)


class TestAuthFactoryCaching(unittest.TestCase):
    """Test cases for authentication provider factory caching."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the cache before each test
        clear_provider_cache()

        # Create a mock config
        self.config = Config()
        self.config.auth_type = 'none'

    def test_provider_caching(self):
        """Test that providers are cached and reused."""
        # Get a provider
        provider1 = get_auth_provider(self.config)

        # Get another provider with the same config
        provider2 = get_auth_provider(self.config)

        # They should be the same instance
        self.assertIs(provider1, provider2)

    def test_different_configs_different_instances(self):
        """Test that different configs result in different provider instances."""
        # Get a provider with one config
        provider1 = get_auth_provider(self.config)

        # Create a different config
        config2 = Config()
        config2.auth_type = 'none'
        config2.auth_token = 'test_token'  # Different from first config

        # Get a provider with the different config
        provider2 = get_auth_provider(config2)

        # They should be different instances
        self.assertIsNot(provider1, provider2)

    def test_cache_clearing(self):
        """Test that clearing the cache works."""
        # Get a provider
        provider1 = get_auth_provider(self.config)

        # Clear the cache
        clear_provider_cache()

        # Get another provider with the same config
        provider2 = get_auth_provider(self.config)

        # They should be different instances
        self.assertIsNot(provider1, provider2)

    def test_cache_hit_count(self):
        """Test that the cache is hit the expected number of times."""
        # Clear the cache to start fresh
        clear_provider_cache()

        # Get the initial cache size
        initial_cache_size = len(_PROVIDER_CACHE)

        # Get a provider multiple times with the same config
        provider1 = get_auth_provider(self.config)
        provider2 = get_auth_provider(self.config)
        provider3 = get_auth_provider(self.config)

        # The cache should only have one entry
        self.assertEqual(len(_PROVIDER_CACHE), initial_cache_size + 1)

        # All providers should be the same instance
        self.assertIs(provider1, provider2)
        self.assertIs(provider2, provider3)

        # Change the config
        self.config.auth_token = 'new_token'

        # Get a provider with the new config
        provider4 = get_auth_provider(self.config)

        # The cache should now have two entries
        self.assertEqual(len(_PROVIDER_CACHE), initial_cache_size + 2)

        # The new provider should be different
        self.assertIsNot(provider1, provider4)


if __name__ == '__main__':
    unittest.main()
