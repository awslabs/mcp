import pytest
from awslabs.dataprocessing_mcp_server.handlers.glue.glue_commons_handler import GlueCommonsHandler
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import Mock, patch


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server instance for testing."""
    mcp = Mock()
    mcp.tool = Mock(return_value=lambda x: x)
    return mcp


@pytest.fixture
def mock_context():
    """Create a mock context for testing."""
    return Mock()


@pytest.fixture
def handler(mock_mcp):
    """Create a GlueCommonsHandler instance with write access for testing."""
    with patch(
        'awslabs.dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_aws_helper.create_boto3_client.return_value = Mock()
        handler = GlueCommonsHandler(mock_mcp, allow_write=True)
        return handler


@pytest.fixture
def no_write_handler(mock_mcp):
    """Create a GlueCommonsHandler instance without write access for testing."""
    with patch(
        'awslabs.dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_aws_helper.create_boto3_client.return_value = Mock()
        handler = GlueCommonsHandler(mock_mcp, allow_write=False)
        return handler


class TestGlueCommonsHandler:
    """Test class for GlueCommonsHandler functionality."""

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_create_success(self, handler, mock_context):
        """Test successful creation of a Glue usage profile."""
        handler.glue_client.create_usage_profile.return_value = {}

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='test-profile',
            configuration={'test': 'config'},
            description='test description',
            tags={'tag1': 'value1'},
        )

        assert result.isError is False
        assert result.profile_name == 'test-profile'
        assert result.operation == 'create'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_create_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that creating a usage profile fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='test-profile',
            configuration={'test': 'config'},
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_create_success(self, handler, mock_context):
        """Test successful creation of a Glue security configuration."""
        handler.glue_client.create_security_configuration.return_value = {
            'CreatedTimestamp': datetime.now()
        }

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='create-security-configuration',
            config_name='test-config',
            encryption_configuration={'test': 'config'},
        )

        assert result.isError is False
        assert result.config_name == 'test-config'
        assert result.operation == 'create'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_get_not_found(self, handler, mock_context):
        """Test handling of EntityNotFoundException when getting a security configuration."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        handler.glue_client.get_security_configuration.side_effect = ClientError(
            error_response, 'GetSecurityConfiguration'
        )

        result = await handler.manage_aws_glue_security(
            mock_context, operation='get-security-configuration', config_name='test-config'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_get_success(self, handler, mock_context):
        """Test successful retrieval of Glue data catalog encryption settings."""
        handler.glue_client.get_data_catalog_encryption_settings.return_value = {
            'DataCatalogEncryptionSettings': {'test': 'settings'}
        }

        result = await handler.manage_aws_glue_encryption(
            mock_context, operation='get-catalog-encryption-settings'
        )

        assert result.isError is False
        assert result.encryption_settings == {'test': 'settings'}

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_put_success(self, handler, mock_context):
        """Test successful creation of a Glue resource policy."""
        handler.glue_client.put_resource_policy.return_value = {'PolicyHash': 'test-hash'}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='put-resource-policy', policy='{"Version": "2012-10-17"}'
        )

        assert result.isError is False
        assert result.policy_hash == 'test-hash'
        assert result.operation == 'put'

    @pytest.mark.asyncio
    async def test_invalid_operations(self, handler, mock_context):
        """Test handling of invalid operations for various Glue management functions."""
        # Test invalid operation for usage profiles
        result = await handler.manage_aws_glue_usage_profiles(
            mock_context, operation='invalid-operation', profile_name='test'
        )
        assert result.isError is True

        # Test invalid operation for security configurations
        result = await handler.manage_aws_glue_security(
            mock_context, operation='invalid-operation', config_name='test'
        )
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_error_handling(self, handler, mock_context):
        """Test error handling when Glue API calls raise exceptions."""
        handler.glue_client.get_usage_profile.side_effect = Exception('Test error')

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context, operation='get-profile', profile_name='test'
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text
