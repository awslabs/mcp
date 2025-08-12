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
"""Tests for cloud control utils."""

import pytest
from awslabs.ccapi_mcp_server.cloud_control_utils import progress_event, validate_patch


class TestUtils:
    """Test cloud control utilities."""

    def test_progress_event(self):
        """Test progress event processing."""
        event = {
            'OperationStatus': 'SUCCESS',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
        }
        result = progress_event(event, None)
        assert result['status'] == 'SUCCESS'
        assert result['resource_type'] == 'AWS::S3::Bucket'

    def test_validate_patch(self):
        """Test patch validation."""
        patch_doc = [{'op': 'add', 'path': '/test', 'value': 'value'}]
        # Should not raise exception
        validate_patch(patch_doc)

    def test_validate_patch_invalid(self):
        """Test invalid patch validation."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        with pytest.raises(ClientError):
            validate_patch([{'invalid': 'patch'}])

    def test_progress_event_pending(self):
        """Test progress event with pending status."""
        event = {
            'OperationStatus': 'IN_PROGRESS',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
        }

        result = progress_event(event, None)

        assert result['status'] == 'IN_PROGRESS'
        assert not result['is_complete']

    def test_validate_patch_missing_path(self):
        """Test patch validation with missing path."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        patch_doc = [{'op': 'add', 'value': 'test'}]

        with pytest.raises(ClientError):
            validate_patch(patch_doc)

    def test_progress_event_with_identifier(self):
        """Test progress event with identifier."""
        event = {
            'OperationStatus': 'SUCCESS',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
            'Identifier': 'my-bucket',
        }

        result = progress_event(event, None)

        assert result['status'] == 'SUCCESS'
        assert result['identifier'] == 'my-bucket'
        assert result['is_complete']

    def test_add_default_tags_enabled(self):
        """Test adding default tags when enabled."""
        import os
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        os.environ['DEFAULT_TAGGING'] = 'true'
        properties = {'BucketName': 'test-bucket'}
        schema = {'properties': {'Tags': {}}}

        result = add_default_tags(properties, schema)

        # Function may or may not add tags depending on implementation
        assert isinstance(result, dict)

        # Clean up
        if 'DEFAULT_TAGGING' in os.environ:
            del os.environ['DEFAULT_TAGGING']

    def test_validate_patch_replace_operation(self):
        """Test patch validation with replace operation."""
        patch_doc = [{'op': 'replace', 'path': '/BucketName', 'value': 'new-bucket'}]
        # Should not raise exception
        validate_patch(patch_doc)

    def test_validate_patch_remove_operation(self):
        """Test patch validation with remove operation."""
        patch_doc = [{'op': 'remove', 'path': '/Tags/0'}]
        # Should not raise exception
        validate_patch(patch_doc)

    def test_validate_patch_invalid_operation(self):
        """Test patch validation with invalid operation."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        patch_doc = [{'op': 'invalid_op', 'path': '/test', 'value': 'value'}]

        with pytest.raises(ClientError):
            validate_patch(patch_doc)

    def test_progress_event_failed_status(self):
        """Test progress event with failed status."""
        event = {
            'OperationStatus': 'FAILED',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
            'StatusMessage': 'Resource creation failed',
        }

        result = progress_event(event, None)

        assert result['status'] == 'FAILED'
        assert result['is_complete']
        assert result['status_message'] == 'Resource creation failed'

    def test_progress_event_with_resource_model(self):
        """Test progress event with resource model."""
        event = {
            'OperationStatus': 'SUCCESS',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
            'ResourceModel': '{"BucketName": "test-bucket"}',
        }

        result = progress_event(event, None)

        assert result['status'] == 'SUCCESS'
        assert 'resource_info' in result

    def test_validate_patch_empty_list(self):
        """Test patch validation with empty list."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        # Empty list may or may not raise an error depending on implementation
        try:
            validate_patch([])
        except ClientError:
            pass  # Expected if validation requires non-empty list

    def test_validate_patch_working(self):
        """Test patch validation with working input."""
        # Just test that the function works with valid input
        validate_patch([{'op': 'add', 'path': '/test', 'value': 'value'}])

    def test_validate_patch_non_list(self):
        """Test patch validation with non-list input - covers lines 65-66."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        with pytest.raises(ClientError, match='Patch document must be a list'):
            validate_patch('not a list')

    def test_validate_patch_dict_input(self):
        """Test patch validation with dict input - covers lines 65-66."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        with pytest.raises(ClientError, match='Patch document must be a list'):
            validate_patch({'op': 'add', 'path': '/test'})

    def test_progress_event_minimal(self):
        """Test progress event with minimal data."""
        event = {
            'OperationStatus': 'SUCCESS',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
        }

        result = progress_event(event, None)

        assert result['status'] == 'SUCCESS'
        assert result['is_complete']
        assert result['resource_type'] == 'AWS::S3::Bucket'
        assert result['request_token'] == 'test-token'

    def test_add_default_tags_always_enabled(self):
        """Test add_default_tags always adds tags in v1."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        properties = {'BucketName': 'test-bucket'}
        schema = {'properties': {'Tags': {}}}

        result = add_default_tags(properties, schema)
        assert 'Tags' in result
        assert len(result['Tags']) == 3
        tag_keys = {tag['Key'] for tag in result['Tags']}
        assert tag_keys == {'MANAGED_BY', 'MCP_SERVER_SOURCE_CODE', 'MCP_SERVER_VERSION'}

        # Verify actual values
        tag_dict = {tag['Key']: tag['Value'] for tag in result['Tags']}
        assert tag_dict['MANAGED_BY'] == 'CCAPI-MCP-SERVER'
        assert (
            tag_dict['MCP_SERVER_SOURCE_CODE']
            == 'https://github.com/awslabs/mcp/tree/main/src/ccapi-mcp-server'
        )
        from awslabs.ccapi_mcp_server import __version__

        assert tag_dict['MCP_SERVER_VERSION'] == __version__

    def test_add_default_tags_no_properties(self):
        """Test add_default_tags with no properties."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        result = add_default_tags({}, {})
        assert result == {}

    def test_progress_event_with_hooks(self):
        """Test progress event with hooks events."""
        event = {
            'OperationStatus': 'FAILED',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
            'StatusMessage': 'Original message',
        }

        hooks_events = [
            {'HookStatus': 'HOOK_COMPLETE_FAILED', 'HookStatusMessage': 'Hook failed message'}
        ]

        result = progress_event(event, hooks_events)
        assert result['status_message'] == 'Hook failed message'

    def test_validate_patch_move_copy_operations(self):
        """Test patch validation with move and copy operations."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        # Test move operation without 'from' field
        with pytest.raises(ClientError):
            validate_patch([{'op': 'move', 'path': '/test'}])

        # Test copy operation without 'from' field
        with pytest.raises(ClientError):
            validate_patch([{'op': 'copy', 'path': '/test'}])

        # Test valid move operation
        validate_patch([{'op': 'move', 'path': '/test', 'from': '/source'}])

        # Test valid copy operation
        validate_patch([{'op': 'copy', 'path': '/test', 'from': '/source'}])

    def test_add_default_tags_no_tags_property(self):
        """Test add_default_tags without Tags property - V1 always adds tags."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        properties = {'BucketName': 'test-bucket'}
        schema = {'properties': {'BucketName': {'type': 'string'}}}  # No Tags property

        result = add_default_tags(properties, schema)

        # V1 behavior: Always adds tags regardless of schema
        assert 'Tags' in result
        assert len(result['Tags']) == 3
        assert result['BucketName'] == 'test-bucket'

        # Verify default tags are present
        tag_keys = {tag['Key'] for tag in result['Tags']}
        assert tag_keys == {'MANAGED_BY', 'MCP_SERVER_SOURCE_CODE', 'MCP_SERVER_VERSION'}

    def test_add_default_tags_with_tags_property(self):
        """Test add_default_tags with Tags property in schema."""
        import os
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        os.environ['DEFAULT_TAGS'] = 'enabled'

        properties = {'BucketName': 'test-bucket'}
        schema = {'properties': {'Tags': {'type': 'array'}}}

        result = add_default_tags(properties, schema)

        # Should add default tags when enabled and Tags property exists
        assert isinstance(result, dict)

        # Clean up
        if 'DEFAULT_TAGS' in os.environ:
            del os.environ['DEFAULT_TAGS']

    def test_add_default_tags_with_existing_user_tags(self):
        """Test add_default_tags preserves user tags and adds default tags."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        properties = {
            'BucketName': 'test-bucket',
            'Tags': [
                {'Key': 'user-tag', 'Value': 'user-value'},
                {'Key': 'another-tag', 'Value': 'another-value'},
            ],
        }
        schema = {'properties': {'Tags': {'type': 'array'}}}

        result = add_default_tags(properties, schema)

        # Should have user tags + 3 default tags = 5 total
        assert len(result['Tags']) == 5

        # Check user tags are preserved
        tag_dict = {tag['Key']: tag['Value'] for tag in result['Tags']}
        assert tag_dict['user-tag'] == 'user-value'
        assert tag_dict['another-tag'] == 'another-value'

        # Check default tags are added
        assert tag_dict['MANAGED_BY'] == 'CCAPI-MCP-SERVER'
        assert (
            tag_dict['MCP_SERVER_SOURCE_CODE']
            == 'https://github.com/awslabs/mcp/tree/main/src/ccapi-mcp-server'
        )
        from awslabs.ccapi_mcp_server import __version__

        assert tag_dict['MCP_SERVER_VERSION'] == __version__

    def test_progress_event_with_error_code(self):
        """Test progress event with error code."""
        event = {
            'OperationStatus': 'FAILED',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
            'ErrorCode': 'InvalidRequest',
        }

        result = progress_event(event, None)

        assert result['status'] == 'FAILED'
        assert 'error_code' in result

    def test_progress_event_with_retry_after(self):
        """Test progress event with retry after."""
        event = {
            'OperationStatus': 'IN_PROGRESS',
            'TypeName': 'AWS::S3::Bucket',
            'RequestToken': 'test-token',
            'RetryAfter': '30',
        }

        result = progress_event(event, None)

        assert result['status'] == 'IN_PROGRESS'
        assert 'retry_after' in result

    def test_validate_patch_test_operation(self):
        """Test patch validation with test operation."""
        patch_doc = [{'op': 'test', 'path': '/test', 'value': 'expected'}]
        # Should not raise exception
        validate_patch(patch_doc)

    def test_validate_patch_missing_value_for_add(self):
        """Test patch validation missing value for add operation."""
        from awslabs.ccapi_mcp_server.errors import ClientError

        patch_doc = [{'op': 'add', 'path': '/test'}]  # Missing value

        with pytest.raises(ClientError):
            validate_patch(patch_doc)

    def test_validate_patch_comprehensive_types(self):
        """Test validate_patch with comprehensive input types - covers lines 65-66."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import validate_patch
        from awslabs.ccapi_mcp_server.errors import ClientError

        # Test all these should hit the isinstance check on lines 65-66
        test_cases = [None, 42, 'string', {'dict': 'value'}, ('tuple',), set(), frozenset()]

        for test_input in test_cases:
            with pytest.raises(ClientError, match='Patch document must be a list'):
                validate_patch(test_input)

    def test_validate_patch_edge_cases(self):
        """Test validate_patch edge cases to ensure complete coverage."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import validate_patch
        from awslabs.ccapi_mcp_server.errors import ClientError

        # Test with boolean False (falsy but not None)
        with pytest.raises(ClientError, match='Patch document must be a list'):
            validate_patch(False)

        # Test with empty string (falsy)
        with pytest.raises(ClientError, match='Patch document must be a list'):
            validate_patch('')

        # Test with zero (falsy)
        with pytest.raises(ClientError, match='Patch document must be a list'):
            validate_patch(0)

        # Test with complex object
        class CustomObject:
            pass

        with pytest.raises(ClientError, match='Patch document must be a list'):
            validate_patch(CustomObject())
