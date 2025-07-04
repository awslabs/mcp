"""Tests for the common module of amazon-sns-sqs-mcp-server."""

from awslabs.amazon_sns_sqs_mcp_server.common import (
    MCP_SERVER_VERSION_TAG,
    validate_mcp_server_version_tag,
)


class TestCommonUtils:
    """Test common utilities."""

    def test_validate_mcp_server_version_tag_with_tag(self):
        """Test validate_mcp_server_version_tag with tag present."""
        # Test with tag present
        tags = {MCP_SERVER_VERSION_TAG: '1.0.0'}
        result, message = validate_mcp_server_version_tag(tags)
        assert result is True
        assert message == ''

    def test_validate_mcp_server_version_tag_without_tag(self):
        """Test validate_mcp_server_version_tag with tag missing."""
        # Test with tag missing
        tags = {'some_other_tag': 'value'}
        result, message = validate_mcp_server_version_tag(tags)
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'

    def test_validate_mcp_server_version_tag_empty_tags(self):
        """Test validate_mcp_server_version_tag with empty tags."""
        # Test with empty tags
        tags = {}
        result, message = validate_mcp_server_version_tag(tags)
        assert result is False
