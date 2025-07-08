import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler import (
    GlueCommonsHandler,
)
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
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_aws_helper.create_boto3_client.return_value = Mock()
        handler = GlueCommonsHandler(mock_mcp, allow_write=True)
        return handler


@pytest.fixture
def no_write_handler(mock_mcp):
    """Create a GlueCommonsHandler instance without write access for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
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

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_delete_success(self, handler, mock_context):
        """Test successful deletion of a Glue usage profile."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            handler.glue_client.get_usage_profile.return_value = {'Name': 'test-profile'}
            handler.glue_client.delete_usage_profile.return_value = {}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context, operation='delete-profile', profile_name='test-profile'
            )

            assert result.isError is False
            assert result.profile_name == 'test-profile'
            assert result.operation == 'delete'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_delete_not_found(self, handler, mock_context):
        """Test deletion of a non-existent usage profile."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        handler.glue_client.get_usage_profile.side_effect = ClientError(
            error_response, 'GetUsageProfile'
        )

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context, operation='delete-profile', profile_name='test-profile'
        )

        assert result.isError is True
        assert 'not found' in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_delete_not_mcp_managed(
        self, handler, mock_context
    ):
        """Test deletion of a usage profile not managed by MCP."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = False

            handler.glue_client.get_usage_profile.return_value = {'Name': 'test-profile'}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context, operation='delete-profile', profile_name='test-profile'
            )

            assert result.isError is True
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_get_success(self, handler, mock_context):
        """Test successful retrieval of a usage profile."""
        handler.glue_client.get_usage_profile.return_value = {
            'Name': 'test-profile',
            'Configuration': {'test': 'config'},
        }

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context, operation='get-profile', profile_name='test-profile'
        )

        assert result.isError is False
        assert result.profile_name == 'test-profile'
        assert result.operation == 'get'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_update_success(self, handler, mock_context):
        """Test successful update of a usage profile."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            handler.glue_client.get_usage_profile.return_value = {'Name': 'test-profile'}
            handler.glue_client.update_usage_profile.return_value = {}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='update-profile',
                profile_name='test-profile',
                configuration={'test': 'updated-config'},
            )

            assert result.isError is False
            assert result.profile_name == 'test-profile'
            assert result.operation == 'update'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_create_missing_config(
        self, handler, mock_context
    ):
        """Test creation of usage profile without configuration raises ValueError."""
        with pytest.raises(ValueError, match='configuration is required'):
            await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='create-profile',
                profile_name='test-profile',
                configuration=None,
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_update_missing_config(
        self, handler, mock_context
    ):
        """Test update of usage profile without configuration raises ValueError."""
        with pytest.raises(ValueError, match='configuration is required'):
            await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='update-profile',
                profile_name='test-profile',
                configuration=None,
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_update_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that updating a usage profile fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='update-profile',
            profile_name='test-profile',
            configuration={'test': 'config'},
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_delete_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that deleting a usage profile fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_usage_profiles(
            mock_context, operation='delete-profile', profile_name='test-profile'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_delete_success(self, handler, mock_context):
        """Test successful deletion of a security configuration."""
        handler.glue_client.get_security_configuration.return_value = {
            'SecurityConfiguration': {'Name': 'test-config'}
        }
        handler.glue_client.delete_security_configuration.return_value = {}

        result = await handler.manage_aws_glue_security(
            mock_context, operation='delete-security-configuration', config_name='test-config'
        )

        assert result.isError is False
        assert result.config_name == 'test-config'
        assert result.operation == 'delete'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_delete_not_found(self, handler, mock_context):
        """Test deletion of a non-existent security configuration."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        handler.glue_client.get_security_configuration.side_effect = ClientError(
            error_response, 'GetSecurityConfiguration'
        )

        result = await handler.manage_aws_glue_security(
            mock_context, operation='delete-security-configuration', config_name='test-config'
        )

        assert result.isError is True
        assert 'not found' in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_get_success(self, handler, mock_context):
        """Test successful retrieval of a security configuration."""
        handler.glue_client.get_security_configuration.return_value = {
            'SecurityConfiguration': {
                'Name': 'test-config',
                'EncryptionConfiguration': {'test': 'encryption'},
            },
            'CreatedTimeStamp': datetime.now(),
        }

        result = await handler.manage_aws_glue_security(
            mock_context, operation='get-security-configuration', config_name='test-config'
        )

        assert result.isError is False
        assert result.config_name == 'test-config'
        assert result.operation == 'get'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_create_missing_config(self, handler, mock_context):
        """Test creation of security configuration without encryption_configuration raises ValueError."""
        with pytest.raises(ValueError, match='encryption_configuration is required'):
            await handler.manage_aws_glue_security(
                mock_context,
                operation='create-security-configuration',
                config_name='test-config',
                encryption_configuration=None,
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_create_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that creating a security configuration fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_security(
            mock_context,
            operation='create-security-configuration',
            config_name='test-config',
            encryption_configuration={'test': 'config'},
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_delete_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that deleting a security configuration fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_security(
            mock_context, operation='delete-security-configuration', config_name='test-config'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_delete_other_error(self, handler, mock_context):
        """Test deletion of security configuration with other ClientError."""
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        handler.glue_client.get_security_configuration.side_effect = ClientError(
            error_response, 'GetSecurityConfiguration'
        )

        result = await handler.manage_aws_glue_security(
            mock_context, operation='delete-security-configuration', config_name='test-config'
        )
        assert result.isError is True
        assert 'Access denied' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_put_success(self, handler, mock_context):
        """Test successful update of data catalog encryption settings."""
        handler.glue_client.put_data_catalog_encryption_settings.return_value = {}

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            encryption_at_rest={'test': 'encryption'},
        )

        assert result.isError is False
        assert result.operation == 'put'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_put_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that updating encryption settings fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_encryption(
            mock_context, operation='put-catalog-encryption-settings'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_put_missing_settings(self, handler, mock_context):
        """Test update of encryption settings without any encryption config raises ValueError."""
        with pytest.raises(
            ValueError,
            match='Either encryption_at_rest or connection_password_encryption is required',
        ):
            await handler.manage_aws_glue_encryption(
                mock_context,
                operation='put-catalog-encryption-settings',
                encryption_at_rest=None,
                connection_password_encryption=None,
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_get_with_catalog_id(self, handler, mock_context):
        """Test retrieval of encryption settings with catalog ID."""
        handler.glue_client.get_data_catalog_encryption_settings.return_value = {
            'DataCatalogEncryptionSettings': {'test': 'settings'}
        }

        result = await handler.manage_aws_glue_encryption(
            mock_context, operation='get-catalog-encryption-settings', catalog_id='123456789012'
        )

        assert result.isError is False
        handler.glue_client.get_data_catalog_encryption_settings.assert_called_with(
            CatalogId='123456789012'
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_put_with_catalog_id(self, handler, mock_context):
        """Test update of encryption settings with catalog ID."""
        handler.glue_client.put_data_catalog_encryption_settings.return_value = {}

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            catalog_id='123456789012',
            encryption_at_rest={'test': 'encryption'},
        )

        assert result.isError is False

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_invalid_operation(self, handler, mock_context):
        """Test invalid operation for encryption management."""
        result = await handler.manage_aws_glue_encryption(
            mock_context, operation='invalid-operation'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_get_success(self, handler, mock_context):
        """Test successful retrieval of resource policy."""
        handler.glue_client.get_resource_policy.return_value = {
            'PolicyHash': 'test-hash',
            'PolicyInJson': '{"Version": "2012-10-17"}',
            'CreateTime': datetime.now(),
            'UpdateTime': datetime.now(),
        }

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='get-resource-policy'
        )

        assert result.isError is False
        assert result.policy_hash == 'test-hash'
        assert result.operation == 'get'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_delete_success(self, handler, mock_context):
        """Test successful deletion of resource policy."""
        handler.glue_client.delete_resource_policy.return_value = {}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='delete-resource-policy'
        )

        assert result.isError is False
        assert result.operation == 'delete'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_get_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that getting resource policy works without write access."""
        no_write_handler.glue_client.get_resource_policy.return_value = {
            'PolicyHash': 'test-hash',
            'PolicyInJson': '{"Version": "2012-10-17"}',
        }

        result = await no_write_handler.manage_aws_glue_resource_policies(
            mock_context, operation='get-resource-policy'
        )

        assert result.isError is False

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_put_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that putting resource policy fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_resource_policies(
            mock_context, operation='put-resource-policy', policy='{"Version": "2012-10-17"}'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_delete_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that deleting resource policy fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_resource_policies(
            mock_context, operation='delete-resource-policy'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_put_missing_policy(
        self, handler, mock_context
    ):
        """Test update of resource policy without policy raises ValueError."""
        with pytest.raises(ValueError, match='policy is required'):
            await handler.manage_aws_glue_resource_policies(
                mock_context, operation='put-resource-policy', policy=None
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_invalid_operation(
        self, handler, mock_context
    ):
        """Test invalid operation for resource policy management."""
        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='invalid-operation'
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_with_all_params(self, handler, mock_context):
        """Test resource policy management with all optional parameters."""
        handler.glue_client.put_resource_policy.return_value = {'PolicyHash': 'test-hash'}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context,
            operation='put-resource-policy',
            policy='{"Version": "2012-10-17"}',
            policy_hash='existing-hash',
            policy_exists_condition='MUST_EXIST',
            enable_hybrid=True,
            resource_arn='arn:aws:glue:us-east-1:123456789012:catalog',
        )

        assert result.isError is False
        assert result.policy_hash == 'test-hash'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_update_not_mcp_managed(
        self, handler, mock_context
    ):
        """Test update of a usage profile not managed by MCP."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = False

            handler.glue_client.get_usage_profile.return_value = {'Name': 'test-profile'}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='update-profile',
                profile_name='test-profile',
                configuration={'test': 'config'},
            )

            assert result.isError is True
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_update_not_found(self, handler, mock_context):
        """Test update of a non-existent usage profile."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        handler.glue_client.get_usage_profile.side_effect = ClientError(
            error_response, 'GetUsageProfile'
        )

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='update-profile',
            profile_name='test-profile',
            configuration={'test': 'config'},
        )

        assert result.isError is True
        assert 'not found' in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_delete_other_error(self, handler, mock_context):
        """Test deletion of usage profile with other ClientError."""
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        handler.glue_client.get_usage_profile.side_effect = ClientError(
            error_response, 'GetUsageProfile'
        )

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context, operation='delete-profile', profile_name='test-profile'
        )

        assert result.isError is True
        assert 'Access denied' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_update_other_error(self, handler, mock_context):
        """Test update of usage profile with other ClientError."""
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        handler.glue_client.get_usage_profile.side_effect = ClientError(
            error_response, 'GetUsageProfile'
        )

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='update-profile',
            profile_name='test-profile',
            configuration={'test': 'config'},
        )

        assert result.isError is True
        assert 'Access denied' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_put_with_both_settings(self, handler, mock_context):
        """Test update of encryption settings with both encryption types."""
        handler.glue_client.put_data_catalog_encryption_settings.return_value = {}

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            encryption_at_rest={'test': 'encryption'},
            connection_password_encryption={'test': 'password_encryption'},
        )

        assert result.isError is False
        assert result.operation == 'put'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_get_error(self, handler, mock_context):
        """Test error handling for get catalog encryption settings."""
        handler.glue_client.get_data_catalog_encryption_settings.side_effect = Exception(
            'Test error'
        )

        result = await handler.manage_aws_glue_encryption(
            mock_context, operation='get-catalog-encryption-settings'
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_put_error(self, handler, mock_context):
        """Test error handling for put catalog encryption settings."""
        handler.glue_client.put_data_catalog_encryption_settings.side_effect = Exception(
            'Test error'
        )

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            encryption_at_rest={'test': 'encryption'},
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_get_error(self, handler, mock_context):
        """Test error handling for get resource policy."""
        handler.glue_client.get_resource_policy.side_effect = Exception('Test error')

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='get-resource-policy'
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_put_error(self, handler, mock_context):
        """Test error handling for put resource policy."""
        handler.glue_client.put_resource_policy.side_effect = Exception('Test error')

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='put-resource-policy', policy='{"Version": "2012-10-17"}'
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_delete_error(self, handler, mock_context):
        """Test error handling for delete resource policy."""
        handler.glue_client.delete_resource_policy.side_effect = Exception('Test error')

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='delete-resource-policy'
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_create_error(self, handler, mock_context):
        """Test error handling for create security configuration."""
        handler.glue_client.create_security_configuration.side_effect = Exception('Test error')

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='create-security-configuration',
            config_name='test-config',
            encryption_configuration={'test': 'config'},
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_create_error(self, handler, mock_context):
        """Test error handling for create usage profile."""
        handler.glue_client.create_usage_profile.side_effect = Exception('Test error')

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='test-profile',
            configuration={'test': 'config'},
            tags=None,
        )

        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_get_with_resource_arn(
        self, handler, mock_context
    ):
        """Test get resource policy with resource ARN."""
        handler.glue_client.get_resource_policy.return_value = {
            'PolicyHash': 'test-hash',
            'PolicyInJson': '{"Version": "2012-10-17"}',
        }

        result = await handler.manage_aws_glue_resource_policies(
            mock_context,
            operation='get-resource-policy',
            resource_arn='arn:aws:glue:region:account:catalog',
        )

        assert result.isError is False
        handler.glue_client.get_resource_policy.assert_called_with(
            ResourceArn='arn:aws:glue:region:account:catalog'
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_delete_with_policy_hash(
        self, handler, mock_context
    ):
        """Test delete resource policy with policy hash condition."""
        handler.glue_client.delete_resource_policy.return_value = {}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context,
            operation='delete-resource-policy',
            policy_hash='test-hash',
            resource_arn=None,
        )

        assert result.isError is False
        handler.glue_client.delete_resource_policy.assert_called_with(
            PolicyHashCondition='test-hash'
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_security_get_with_client_error(self, handler, mock_context):
        """Test get security configuration with client error."""
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        handler.glue_client.get_security_configuration.side_effect = ClientError(
            error_response, 'GetSecurityConfiguration'
        )

        result = await handler.manage_aws_glue_security(
            mock_context, operation='get-security-configuration', config_name='test-config'
        )

        assert result.isError is True
        assert 'Invalid input' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_usage_profiles_get_with_client_error(
        self, handler, mock_context
    ):
        """Test get usage profile with client error."""
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        handler.glue_client.get_usage_profile.side_effect = ClientError(
            error_response, 'GetUsageProfile'
        )

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context, operation='get-profile', profile_name='test-profile'
        )

        assert result.isError is True
        assert 'Invalid input' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_encryption_put_with_client_error(self, handler, mock_context):
        """Test put catalog encryption settings with client error."""
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        handler.glue_client.put_data_catalog_encryption_settings.side_effect = ClientError(
            error_response, 'PutDataCatalogEncryptionSettings'
        )

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            encryption_at_rest={'test': 'encryption'},
        )

        assert result.isError is True
        assert 'Invalid input' in result.content[0].text
