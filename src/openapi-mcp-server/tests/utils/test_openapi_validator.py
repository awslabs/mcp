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
"""Tests for the OpenAPI validator module."""

from awslabs.openapi_mcp_server.utils.openapi_validator import (
    validate_openapi_spec,
)
from unittest.mock import MagicMock, patch


class TestOpenAPIValidator:
    """Test cases for OpenAPI validator functions."""

    def test_validate_openapi_spec_valid(self):
        """Test validation of a valid OpenAPI spec."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        assert validate_openapi_spec(spec) is True

    def test_validate_openapi_spec_missing_openapi(self):
        """Test validation with missing openapi field."""
        spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        assert validate_openapi_spec(spec) is False

    def test_validate_openapi_spec_missing_info(self):
        """Test validation with missing info field."""
        spec = {
            'openapi': '3.0.0',
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        assert validate_openapi_spec(spec) is False

    def test_validate_openapi_spec_missing_paths(self):
        """Test validation with missing paths field."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
        }
        assert validate_openapi_spec(spec) is False

    def test_validate_openapi_spec_unsupported_version(self):
        """Test validation with unsupported OpenAPI version."""
        spec = {
            'openapi': '2.0.0',  # Unsupported version
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        # Should still pass basic validation but log a warning
        assert validate_openapi_spec(spec) is True

    def test_validate_openapi_spec_with_openapi_core(self):
        """Test validation using openapi-core if available."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Mock the create_spec method
            mock_create_spec = MagicMock()
            mock_openapi_core.create_spec = mock_create_spec

            assert validate_openapi_spec(spec) is True
            mock_create_spec.assert_called_once_with(spec)

    def test_validate_openapi_spec_with_openapi_core_exception(self):
        """Test validation when openapi-core raises an exception."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Mock the create_spec method to raise an exception
            mock_create_spec = MagicMock(side_effect=Exception('Test exception'))
            mock_openapi_core.create_spec = mock_create_spec

            # Should still return True as we already passed basic validation
            assert validate_openapi_spec(spec) is True

    def test_validate_openapi_spec_with_openapi_spec_class(self):
        """Test validation using OpenAPISpec class if available."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Remove create_spec attribute
            if hasattr(mock_openapi_core, 'create_spec'):
                del mock_openapi_core.create_spec

            # Remove Spec attribute
            if hasattr(mock_openapi_core, 'Spec'):
                del mock_openapi_core.Spec

            # Mock the OpenAPISpec class with create method
            mock_openapi_spec_class = MagicMock()
            mock_create = MagicMock()
            mock_openapi_spec_class.create = mock_create
            mock_openapi_core.OpenAPISpec = mock_openapi_spec_class

            assert validate_openapi_spec(spec) is True

            # The validation function should have called OpenAPISpec.create
            mock_create.assert_called_once_with(spec)

    def test_validate_openapi_spec_with_spec_class(self):
        """Test validation using Spec class if available."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Remove create_spec attribute
            del mock_openapi_core.create_spec

            # Remove OpenAPISpec attribute
            if hasattr(mock_openapi_core, 'OpenAPISpec'):
                del mock_openapi_core.OpenAPISpec

            # Mock the Spec class
            mock_spec = MagicMock()
            mock_spec.create = MagicMock()
            mock_openapi_core.Spec = mock_spec

            assert validate_openapi_spec(spec) is True
            mock_spec.create.assert_called_once_with(spec)

    def test_validate_openapi_spec_with_unsupported_openapi_core(self):
        """Test validation with unsupported openapi-core version."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Remove all supported attributes
            if hasattr(mock_openapi_core, 'create_spec'):
                del mock_openapi_core.create_spec
            if hasattr(mock_openapi_core, 'OpenAPISpec'):
                del mock_openapi_core.OpenAPISpec
            if hasattr(mock_openapi_core, 'Spec'):
                del mock_openapi_core.Spec

            # Should still pass validation
            assert validate_openapi_spec(spec) is True
