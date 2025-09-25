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
"""Tests for the base authentication provider."""

import unittest
from awslabs.openapi_mcp_server.auth.base_auth import BaseAuthProvider
from unittest.mock import MagicMock


class TestBaseAuthProvider(unittest.TestCase):
    """Test cases for the base authentication provider."""

    def test_requires_valid_config_decorator(self):
        """Test that the _requires_valid_config decorator works correctly."""

        # Create a mock subclass of BaseAuthProvider
        class MockAuthProvider(BaseAuthProvider):
            def __init__(self, config, is_valid=True):
                self._config = config
                self._is_valid = is_valid
                self._auth_headers = {}
                self._auth_params = {}
                self._auth_cookies = {}

                # Skip the validation and initialization
                if not is_valid:
                    self._log_validation_error()

            def _validate_config(self):
                return self._is_valid

            def _log_validation_error(self):
                pass

            @property
            def provider_name(self):
                return 'mock'

        # Create a provider with valid config
        valid_provider = MockAuthProvider(MagicMock(), is_valid=True)
        valid_provider._auth_headers = {'Authorization': 'Bearer token'}

        # Create a provider with invalid config
        invalid_provider = MockAuthProvider(MagicMock(), is_valid=False)

        # Test that the valid provider returns headers
        self.assertEqual(valid_provider.get_auth_headers(), {'Authorization': 'Bearer token'})

        # Test that the invalid provider returns empty headers
        self.assertEqual(invalid_provider.get_auth_headers(), {})

    def test_template_method_pattern(self):
        """Test that the template method pattern works correctly."""
        # Create a mock implementation to track method calls
        method_calls = []

        class TemplateTestProvider(BaseAuthProvider):
            def _validate_config(self):
                method_calls.append('_validate_config')
                return True

            def _initialize_auth(self):
                method_calls.append('_initialize_auth')
                self._auth_headers = {'Test': 'Value'}

            def _log_validation_error(self):
                method_calls.append('_log_validation_error')

            @property
            def provider_name(self):
                return 'template_test'

        # Create a provider instance which should trigger the template methods
        config = MagicMock()
        provider = TemplateTestProvider(config)

        # Check that methods were called in the correct order
        self.assertEqual(method_calls, ['_validate_config', '_initialize_auth'])

        # Check that initialization set the headers
        self.assertEqual(provider.get_auth_headers(), {'Test': 'Value'})

    def test_invalid_config_template_method(self):
        """Test that the template method pattern handles invalid config correctly."""
        # Create a mock implementation to track method calls
        method_calls = []

        class InvalidConfigProvider(BaseAuthProvider):
            def _validate_config(self):
                method_calls.append('_validate_config')
                return False

            def _initialize_auth(self):
                method_calls.append('_initialize_auth')

            def _log_validation_error(self):
                method_calls.append('_log_validation_error')

            def _handle_validation_error(self):
                method_calls.append('_handle_validation_error')
                # Call the parent method to ensure coverage
                super()._handle_validation_error()

            @property
            def provider_name(self):
                return 'invalid_config'

        # Create a provider instance which should trigger validation but not initialization
        config = MagicMock()
        provider = InvalidConfigProvider(config)

        # Check that methods were called in the correct order
        # Note: _handle_validation_error is called instead of _log_validation_error directly
        self.assertEqual(method_calls, ['_validate_config', '_handle_validation_error'])

        # Check that is_configured returns False
        self.assertFalse(provider.is_configured())


if __name__ == '__main__':
    unittest.main()
