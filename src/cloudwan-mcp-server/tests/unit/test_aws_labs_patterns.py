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

"""Unit tests following AWS Labs MCP server patterns."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from awslabs.cloudwan_mcp_server.config_manager import AWSConfigManager


class TestAWSLabsPatterns:
    """Unit tests following AWS Labs standard patterns."""

    @pytest.mark.unit
    def test_aws_config_manager_initialization(self):
        """Test AWS config manager follows AWS Labs patterns."""
        config_manager = AWSConfigManager()
        
        # AWS Labs standard: config manager should have region and profile handling
        assert hasattr(config_manager, 'region')
        assert hasattr(config_manager, 'profile')
        
    @pytest.mark.unit
    @patch('boto3.client')
    def test_aws_client_creation_patterns(self, mock_boto_client):
        """Test AWS client creation following AWS Labs patterns."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        config_manager = AWSConfigManager()
        client = config_manager.get_aws_client('networkmanager')
        
        # Verify boto3 client was called with proper service
        mock_boto_client.assert_called_once_with('networkmanager', region_name=config_manager.region)
        assert client == mock_client

    @pytest.mark.unit  
    def test_error_response_format_compliance(self):
        """Test error responses follow AWS Labs format standards."""
        from awslabs.cloudwan_mcp_server.utils.response_formatter import format_error_response
        
        error_response = format_error_response("Test error", "TEST_ERROR")
        
        # AWS Labs standard error format
        assert error_response['success'] is False
        assert 'error' in error_response
        assert 'error_code' in error_response
        assert error_response['error'] == "Test error"
        assert error_response['error_code'] == "TEST_ERROR"

    @pytest.mark.unit
    def test_success_response_format_compliance(self):
        """Test success responses follow AWS Labs format standards.""" 
        from awslabs.cloudwan_mcp_server.utils.response_formatter import format_success_response
        
        test_data = {"key": "value"}
        success_response = format_success_response(test_data)
        
        # AWS Labs standard success format
        assert success_response['success'] is True
        assert 'data' in success_response
        assert success_response['data'] == test_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tool_base_class_compliance(self):
        """Test base tool class follows AWS Labs patterns."""
        from awslabs.cloudwan_mcp_server.tools.base import BaseMCPTool
        
        # Test abstract base class behavior
        assert hasattr(BaseMCPTool, 'execute')
        assert hasattr(BaseMCPTool, 'validate_input') 
        assert hasattr(BaseMCPTool, 'format_response')

    @pytest.mark.unit
    def test_input_validation_patterns(self):
        """Test input validation follows AWS Labs patterns."""
        from awslabs.cloudwan_mcp_server.utils.validation import (
            validate_core_network_id, 
            validate_global_network_id,
            validate_ip_address
        )
        
        # Test valid inputs
        assert validate_core_network_id("core-network-1234567890abcdef0") is True
        assert validate_global_network_id("global-network-1234567890abcdef0") is True  
        assert validate_ip_address("10.0.0.1") is True
        
        # Test invalid inputs
        assert validate_core_network_id("invalid-id") is False
        assert validate_global_network_id("") is False
        assert validate_ip_address("999.999.999.999") is False

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_client')
    def test_aws_service_error_handling(self, mock_get_client):
        """Test AWS error handling patterns."""
        from awslabs.cloudwan_mcp_server.tools.core import list_core_networks
        from botocore.exceptions import ClientError
        
        # Mock AWS client that raises service error
        mock_client = Mock()
        mock_client.list_core_networks.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}},
            "ListCoreNetworks"
        )
        mock_get_client.return_value = mock_client
        
        # Test error handling - should return error response, not raise
        async def test_error_handling():
            result = await list_core_networks()
            assert result['success'] is False
            assert 'error' in result
            assert 'AccessDenied' in result['error'] or 'Access denied' in result['error']
            
        asyncio.run(test_error_handling())

    @pytest.mark.unit
    def test_logging_patterns(self):
        """Test logging follows AWS Labs patterns.""" 
        from awslabs.cloudwan_mcp_server.utils.logger import get_logger
        
        logger = get_logger(__name__)
        
        # AWS Labs standard: loguru-based logging
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')

    @pytest.mark.unit
    @pytest.mark.parametrize("tool_name,expected_result", [
        ("list_core_networks", True),
        ("get_global_networks", True), 
        ("trace_network_path", True),
        ("nonexistent_tool", False)
    ])
    def test_tool_availability_parametrized(self, tool_name, expected_result):
        """Test tool availability using parametrized testing (AWS Labs pattern)."""
        from awslabs.cloudwan_mcp_server import server
        
        has_tool = hasattr(server, tool_name)
        assert has_tool == expected_result

    @pytest.mark.unit
    def test_configuration_validation(self):
        """Test configuration validation follows AWS Labs patterns."""
        from awslabs.cloudwan_mcp_server.utils.config import validate_configuration
        
        valid_config = {
            'aws_region': 'us-east-1',
            'log_level': 'INFO'
        }
        
        invalid_config = {
            'log_level': 'INVALID'  # Missing required aws_region
        }
        
        assert validate_configuration(valid_config) is True
        assert validate_configuration(invalid_config) is False

    @pytest.mark.unit 
    @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'})
    def test_environment_variable_handling(self):
        """Test environment variable handling follows AWS Labs patterns."""
        from awslabs.cloudwan_mcp_server.utils.config import get_aws_region
        
        region = get_aws_region()
        assert region == 'us-east-1'

    @pytest.mark.unit
    def test_resource_cleanup_patterns(self):
        """Test resource cleanup follows AWS Labs patterns."""
        from awslabs.cloudwan_mcp_server.utils.aws_config_manager import AWSConfigManager
        
        config_manager = AWSConfigManager()
        
        # Test that cleanup method exists (AWS Labs pattern for resource management)
        assert hasattr(config_manager, 'cleanup') or hasattr(config_manager, '__del__')