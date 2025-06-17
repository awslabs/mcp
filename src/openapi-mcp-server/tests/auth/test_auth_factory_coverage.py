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

"""Tests to cover specific uncovered lines in auth_factory.py."""

import pytest
from awslabs.openapi_mcp_server.auth.auth_factory import (
    clear_provider_cache,
    get_auth_provider,
    is_auth_type_available,
    register_auth_provider,
)
from unittest.mock import Mock


class TestAuthFactoryCoverage:
    """Test cases to cover specific uncovered lines in AuthFactory."""

    def test_get_auth_provider_unsupported_type(self):
        """Test get_auth_provider with unsupported auth type - it falls back to 'none'."""
        config = Mock()
        config.auth_type = 'unsupported_auth_type_12345'

        # This actually falls back to 'none' instead of raising ValueError
        provider = get_auth_provider(config)
        assert provider is not None

    def test_get_auth_provider_none_type(self):
        """Test get_auth_provider with None auth type."""
        config = Mock()
        config.auth_type = None

        # This should raise AttributeError when trying to call .lower() on None
        with pytest.raises(AttributeError):
            get_auth_provider(config)

    def test_register_auth_provider_functionality(self):
        """Test register_auth_provider function."""

        class TestProvider:
            pass

        # Test registering a new provider
        register_auth_provider('test_provider', TestProvider)

        # Test that it's now available
        assert is_auth_type_available('test_provider')

    def test_is_auth_type_available_edge_cases(self):
        """Test is_auth_type_available with various inputs."""
        # Test with None - this will raise AttributeError
        with pytest.raises(AttributeError):
            is_auth_type_available(None)

        # Test with empty string
        assert not is_auth_type_available('')

        # Test with non-existent type
        assert not is_auth_type_available('non_existent_type_xyz')

    def test_clear_provider_cache_functionality(self):
        """Test clear_provider_cache function."""
        # This should execute without error
        clear_provider_cache()

        # Test multiple calls
        clear_provider_cache()
        clear_provider_cache()

    def test_get_auth_provider_with_valid_none_type(self):
        """Test get_auth_provider with 'none' auth type."""
        config = Mock()
        config.auth_type = 'none'

        # This should work and return a NullAuthProvider
        provider = get_auth_provider(config)
        assert provider is not None
