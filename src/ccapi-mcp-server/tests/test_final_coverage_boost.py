"""Final coverage boost tests."""

import pytest
from unittest.mock import patch, MagicMock
import json
from awslabs.ccapi_mcp_server.errors import ClientError


class TestFinalCoverageBoost:
    """Final tests to reach 94% coverage."""

    def test_server_main_function_coverage(self):
        """Test main function paths."""
        import sys
        from awslabs.ccapi_mcp_server.server import main
        
        original_argv = sys.argv
        try:
            sys.argv = ['server.py', '--readonly']
            with patch('awslabs.ccapi_mcp_server.server.get_aws_profile_info') as mock_profile:
                with patch('awslabs.ccapi_mcp_server.server.mcp.run'):
                    mock_profile.return_value = {
                        'profile': 'test',
                        'account_id': '123',
                        'region': 'us-east-1'
                    }
                    main()
        finally:
            sys.argv = original_argv

    @pytest.mark.asyncio
    async def test_server_generate_infrastructure_code_paths(self):
        """Test generate_infrastructure_code paths."""
        from awslabs.ccapi_mcp_server.server import generate_infrastructure_code
        
        with pytest.raises(ClientError):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'credentials_valid': False}
            )

    def test_infrastructure_generator_edge_cases(self):
        """Test infrastructure generator edge cases."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code
        import asyncio
        
        # Test with no properties for create
        with pytest.raises(ClientError):
            asyncio.run(generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                properties={}
            ))

    def test_schema_manager_edge_cases(self):
        """Test schema manager edge cases."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager
        import asyncio
        
        sm = schema_manager()
        
        # Test with invalid resource type
        with pytest.raises(ClientError):
            asyncio.run(sm.get_schema(''))

    @pytest.mark.asyncio 
    async def test_server_tools_edge_cases(self):
        """Test server tools edge cases."""
        from awslabs.ccapi_mcp_server.server import (
            get_resource_schema_information,
            list_resources,
            get_resource
        )
        
        # Test empty resource types
        with pytest.raises(ClientError):
            await get_resource_schema_information(resource_type='')
            
        with pytest.raises(ClientError):
            await list_resources(resource_type='')
            
        with pytest.raises(ClientError):
            await get_resource(resource_type='', identifier='test')

    def test_cloud_control_utils_edge_cases(self):
        """Test cloud control utils edge cases."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags
        
        # Test with empty properties
        result = add_default_tags({}, {})
        assert result == {}
        
        # Test with None properties
        result = add_default_tags(None, {})
        assert result == {}

    def test_context_coverage(self):
        """Test context module."""
        from awslabs.ccapi_mcp_server.context import Context
        
        Context.initialize(True)
        assert Context.readonly_mode() is True
        
        Context.initialize(False)
        assert Context.readonly_mode() is False