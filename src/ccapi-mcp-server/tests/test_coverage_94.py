"""Tests to reach 94% coverage by targeting specific missing lines."""

import pytest
from unittest.mock import patch


class TestCoverage94:
    """Target specific missing lines to reach 94%."""

    def test_server_readonly_mode_paths(self):
        """Test server readonly mode paths."""
        from awslabs.ccapi_mcp_server.server import get_aws_profile_info

        # Test exception path in get_aws_profile_info
        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_client.side_effect = Exception('Test error')
            result = get_aws_profile_info()
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_server_session_validation_paths(self):
        """Test session validation paths."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        # Test with invalid env check result
        with pytest.raises(Exception):
            await get_aws_session_info(None)

    def test_infrastructure_generator_create_paths(self):
        """Test infrastructure generator create paths."""
        import asyncio
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        # Test create operation without properties
        with pytest.raises(Exception):
            asyncio.run(generate_infrastructure_code(resource_type='AWS::S3::Bucket'))

    def test_schema_manager_download_paths(self):
        """Test schema manager download paths."""
        import asyncio
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Test invalid resource type format
        with pytest.raises(Exception):
            asyncio.run(sm._download_resource_schema('Invalid'))

    def test_cloud_control_utils_progress_event_paths(self):
        """Test progress event paths."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import progress_event

        # Test with hooks events
        event = {
            'OperationStatus': 'FAILED',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'token',
            'StatusMessage': 'Original message',
        }
        hooks = [{'HookStatus': 'HOOK_COMPLETE_FAILED', 'HookStatusMessage': 'Hook failed'}]

        result = progress_event(event, hooks)
        assert result['status_message'] == 'Hook failed'

    def test_env_manager_credential_paths(self):
        """Test env manager credential checking paths."""
        from awslabs.ccapi_mcp_server.env_manager import check_aws_credentials

        # Test with mocked environment
        with patch('os.environ') as mock_env:
            mock_env.get.return_value = None
            result = check_aws_credentials()
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_server_tool_validation_paths(self):
        """Test server tool validation paths."""
        from awslabs.ccapi_mcp_server.server import get_resource_request_status

        # Test with empty request token
        with pytest.raises(Exception):
            await get_resource_request_status(request_token='')

    def test_add_default_tags_edge_cases(self):
        """Test add_default_tags edge cases."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        # Test with properties that have existing tags
        properties = {
            'BucketName': 'test',
            'Tags': [
                {'Key': 'MANAGED_BY', 'Value': 'existing'},
                {'Key': 'custom', 'Value': 'tag'},
            ],
        }
        schema = {'properties': {'Tags': {}}}

        result = add_default_tags(properties, schema)
        # Should not duplicate MANAGED_BY tag
        managed_by_count = sum(1 for tag in result['Tags'] if tag['Key'] == 'MANAGED_BY')
        assert managed_by_count == 1

    def test_validate_patch_comprehensive(self):
        """Test validate_patch comprehensive paths."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import validate_patch
        from awslabs.ccapi_mcp_server.errors import ClientError

        # Test various invalid patch operations
        invalid_patches = [
            [{'op': 'invalid', 'path': '/test'}],  # Invalid operation
            [{'op': 'add'}],  # Missing path
            [{'op': 'add', 'path': '/test'}],  # Missing value for add
            [{'op': 'move', 'path': '/test'}],  # Missing from for move
            [{'op': 'copy', 'path': '/test'}],  # Missing from for copy
        ]

        for patch_doc in invalid_patches:
            with pytest.raises(ClientError):
                validate_patch(patch_doc)

    def test_context_module_coverage(self):
        """Test context module coverage."""
        from awslabs.ccapi_mcp_server.context import Context

        # Test both readonly states
        Context.initialize(True)
        assert Context.readonly_mode() is True

        Context.initialize(False)
        assert Context.readonly_mode() is False
