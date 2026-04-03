import json
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler import (
    GlueCommonsHandler,
)
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.server.fastmcp import Context
from unittest.mock import Mock, patch


def extract_response_data(response):
    """Helper function to extract data from CallToolResult content."""
    if response.isError:
        return {}
    # Find the JSON content in the response
    for content_item in response.content:
        if content_item.type == 'text':
            try:
                return json.loads(content_item.text)
            except (json.JSONDecodeError, ValueError):
                continue
    return {}


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = Mock()
        mock.get_aws_region.return_value = 'us-east-1'
        mock.get_aws_account_id.return_value = '123456789012'
        mock.prepare_resource_tags.return_value = {'mcp-managed': 'true'}
        mock.is_resource_mcp_managed.return_value = True
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a GlueCommonsHandler instance with write access for testing."""
    mcp = Mock()
    return GlueCommonsHandler(mcp, allow_write=True)


@pytest.fixture
def no_write_handler(mock_aws_helper):
    """Create a GlueCommonsHandler instance without write access for testing."""
    mcp = Mock()
    return GlueCommonsHandler(mcp, allow_write=False)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return Mock(spec=Context)


class TestGlueCommonsHandler:
    """Test class for GlueCommonsHandler functionality."""

    def test_initialization_with_default_params(self, mock_aws_helper):
        """Test handler initialization with default parameters."""
        mcp = Mock()
        handler = GlueCommonsHandler(mcp)

        assert handler.mcp == mcp
        assert handler.allow_write is False
        assert handler.allow_sensitive_data_access is False
        assert handler.glue_client is not None

        # Verify tool registration calls
        assert mcp.tool.call_count == 4
        expected_tools = [
            'manage_aws_glue_usage_profiles',
            'manage_aws_glue_security_configurations',
            'manage_aws_glue_encryption',
            'manage_aws_glue_resource_policies',
        ]
        actual_tools = [call[1]['name'] for call in mcp.tool.call_args_list]
        assert set(actual_tools) == set(expected_tools)

    def test_initialization_with_write_and_sensitive_access(self, mock_aws_helper):
        """Test handler initialization with write and sensitive data access enabled."""
        mcp = Mock()
        handler = GlueCommonsHandler(mcp, allow_write=True, allow_sensitive_data_access=True)

        assert handler.allow_write is True
        assert handler.allow_sensitive_data_access is True
        mock_aws_helper.create_boto3_client.assert_called_with('glue')

    @pytest.mark.asyncio
    async def test_usage_profiles_create_with_complex_configuration(self, handler, mock_context):
        """Test usage profile creation with complex real-world configuration."""
        handler.glue_client.create_usage_profile.return_value = {}

        complex_config = {
            'JobConfiguration': {
                'numberOfWorkers': {'DefaultValue': '10', 'MinValue': '1', 'MaxValue': '100'},
                'workerType': {
                    'DefaultValue': 'G.2X',
                    'AllowedValues': ['G.1X', 'G.2X', 'G.4X', 'G.8X'],
                },
                'timeout': {'DefaultValue': '2880', 'MinValue': '1', 'MaxValue': '10080'},
            },
            'SessionConfiguration': {
                'idleTimeout': {'DefaultValue': '60', 'MinValue': '1', 'MaxValue': '1440'},
                'sessionTimeout': {'DefaultValue': '2880', 'MinValue': '1', 'MaxValue': '10080'},
            },
        }

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='production-etl-profile',
            description='Production ETL jobs with strict resource limits',
            configuration=complex_config,
            tags={'Environment': 'Production', 'Team': 'DataEngineering'},
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('profile_name') == 'production-etl-profile'

        # Verify the create_usage_profile was called with correct merged tags
        call_args = handler.glue_client.create_usage_profile.call_args
        assert call_args[1]['Name'] == 'production-etl-profile'
        assert call_args[1]['Configuration'] == complex_config
        assert 'Environment' in call_args[1]['Tags']
        assert 'mcp-managed' in call_args[1]['Tags']

    @pytest.mark.asyncio
    async def test_security_config_with_comprehensive_encryption(self, handler, mock_context):
        """Test security configuration with comprehensive encryption settings."""
        handler.glue_client.create_security_configuration.return_value = {
            'CreatedTimestamp': datetime.now()
        }

        comprehensive_encryption = {
            'S3Encryption': [
                {
                    'S3EncryptionMode': 'SSE-KMS',
                    'KmsKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
                }
            ],
            'CloudWatchEncryption': {
                'CloudWatchEncryptionMode': 'SSE-KMS',
                'KmsKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/87654321-4321-4321-4321-210987654321',
            },
            'JobBookmarksEncryption': {
                'JobBookmarksEncryptionMode': 'CSE-KMS',
                'KmsKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/11223344-5566-7788-9900-aabbccddeeff',
            },
        }

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='create-security-configuration',
            config_name='comprehensive-encryption-config',
            encryption_configuration=comprehensive_encryption,
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('config_name') == 'comprehensive-encryption-config'
        assert response_data.get('encryption_configuration') == comprehensive_encryption

    @pytest.mark.asyncio
    async def test_encryption_settings_with_all_options(self, handler, mock_context):
        """Test catalog encryption settings with all configuration options."""
        handler.glue_client.put_data_catalog_encryption_settings.return_value = {}

        encryption_at_rest = {
            'CatalogEncryptionMode': 'SSE-KMS',
            'SseAwsKmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/catalog-key-id',
            'CatalogEncryptionServiceRole': 'arn:aws:iam::123456789012:role/GlueCatalogEncryptionServiceRole',
        }

        connection_password_encryption = {
            'ReturnConnectionPasswordEncrypted': True,
            'AwsKmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/connection-key-id',
        }

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            catalog_id='123456789012',
            encryption_at_rest=encryption_at_rest,
            connection_password_encryption=connection_password_encryption,
        )

        assert result.isError is False

        # Verify the API was called with correct parameters
        call_args = handler.glue_client.put_data_catalog_encryption_settings.call_args
        expected_settings = {
            'EncryptionAtRest': encryption_at_rest,
            'ConnectionPasswordEncryption': connection_password_encryption,
        }
        assert call_args[1]['DataCatalogEncryptionSettings'] == expected_settings
        assert call_args[1]['CatalogId'] == '123456789012'

    @pytest.mark.asyncio
    async def test_resource_policy_with_complex_policy_document(self, handler, mock_context):
        """Test resource policy management with complex IAM policy document."""
        handler.glue_client.put_resource_policy.return_value = {
            'PolicyHash': 'complex-policy-hash-12345'
        }

        complex_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'AllowCrossAccountGlueAccess',
                    'Effect': 'Allow',
                    'Principal': {
                        'AWS': [
                            'arn:aws:iam::111122223333:root',
                            'arn:aws:iam::444455556666:user/DataAnalyst',
                        ]
                    },
                    'Action': [
                        'glue:GetDatabase',
                        'glue:GetDatabases',
                        'glue:GetTable',
                        'glue:GetTables',
                        'glue:GetPartition',
                        'glue:GetPartitions',
                    ],
                    'Resource': [
                        'arn:aws:glue:us-east-1:123456789012:catalog',
                        'arn:aws:glue:us-east-1:123456789012:database/*',
                        'arn:aws:glue:us-east-1:123456789012:table/*/*',
                    ],
                    'Condition': {'StringEquals': {'glue:CatalogId': '123456789012'}},
                },
                {
                    'Sid': 'DenyDeleteOperations',
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Action': ['glue:DeleteDatabase', 'glue:DeleteTable', 'glue:DeletePartition'],
                    'Resource': '*',
                },
            ],
        }

        result = await handler.manage_aws_glue_resource_policies(
            mock_context,
            operation='put-resource-policy',
            policy=json.dumps(complex_policy),
            policy_exists_condition='NOT_EXIST',
            enable_hybrid=True,
            resource_arn='arn:aws:glue:us-east-1:123456789012:catalog',
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('policy_hash') == 'complex-policy-hash-12345'

        # Verify API call parameters
        call_args = handler.glue_client.put_resource_policy.call_args
        assert call_args[1]['PolicyInJson'] == json.dumps(complex_policy)
        assert call_args[1]['PolicyExistsCondition'] == 'NOT_EXIST'
        assert call_args[1]['EnableHybrid'] is True
        assert call_args[1]['ResourceArn'] == 'arn:aws:glue:us-east-1:123456789012:catalog'

    @pytest.mark.asyncio
    async def test_concurrent_resource_modification_scenario(self, handler, mock_context):
        """Test handling of concurrent resource modification scenarios."""
        # Simulate concurrent modification by having get return different data than expected
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            # First call returns profile exists, second call (within update) returns different data
            handler.glue_client.get_usage_profile.side_effect = [
                {'Name': 'test-profile', 'Tags': {'mcp-managed': 'true'}},
                {
                    'Name': 'test-profile',
                    'Tags': {'mcp-managed': 'true', 'modified-by': 'other-system'},
                },
            ]
            handler.glue_client.update_usage_profile.return_value = {}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='update-profile',
                profile_name='test-profile',
                configuration={'updated': 'config'},
            )

            # Should still succeed as MCP management is verified
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_boundary_values_and_edge_cases(self, handler, mock_context):
        """Test boundary values and edge cases for various parameters."""
        # Test with empty configuration
        handler.glue_client.create_usage_profile.return_value = {}

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='minimal-profile',
            configuration={},  # Empty but valid configuration
            description='',  # Empty description
            tags={},  # Empty tags
        )

        assert result.isError is False

        # Test with very long profile name (at AWS limits)
        long_profile_name = 'a' * 255  # AWS Glue profile name limit

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name=long_profile_name,
            configuration={'test': 'config'},
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('profile_name') == long_profile_name

    @pytest.mark.asyncio
    async def test_aws_helper_integration_scenarios(self, handler, mock_context):
        """Test various AWS helper integration scenarios."""
        # Test when AWS helper returns None for region/account
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = None
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            handler.glue_client.get_usage_profile.return_value = {'Name': 'test-profile'}
            handler.glue_client.delete_usage_profile.return_value = {}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context, operation='delete-profile', profile_name='test-profile'
            )

            # Should handle None region gracefully (defaults to us-east-1)
            assert result.isError is False
            mock_aws_helper.get_aws_region.assert_called()

    @pytest.mark.asyncio
    async def test_resource_policy_edge_cases(self, handler, mock_context):
        """Test resource policy management edge cases."""
        # Test policy with special characters and escaping
        special_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                    'Action': 'glue:*',
                    'Resource': '*',
                    'Condition': {
                        'StringLike': {'glue:ResourceTag/Environment': ['dev*', 'test*']}
                    },
                }
            ],
        }

        handler.glue_client.put_resource_policy.return_value = {'PolicyHash': 'special-hash'}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='put-resource-policy', policy=json.dumps(special_policy)
        )

        assert result.isError is False

        # Test delete with all optional parameters
        handler.glue_client.delete_resource_policy.return_value = {}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context,
            operation='delete-resource-policy',
            policy_hash='special-hash',
            resource_arn='arn:aws:glue:us-east-1:123456789012:catalog',
        )

        assert result.isError is False

        # Verify delete was called with all parameters
        call_args = handler.glue_client.delete_resource_policy.call_args
        assert call_args[1]['PolicyHashCondition'] == 'special-hash'
        assert call_args[1]['ResourceArn'] == 'arn:aws:glue:us-east-1:123456789012:catalog'

    @pytest.mark.asyncio
    async def test_encryption_settings_edge_cases(self, handler, mock_context):
        """Test encryption settings with various edge cases."""
        # Test with only connection password encryption
        handler.glue_client.put_data_catalog_encryption_settings.return_value = {}

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            connection_password_encryption={'ReturnConnectionPasswordEncrypted': False},
        )

        assert result.isError is False

        # Verify only connection password encryption was set
        call_args = handler.glue_client.put_data_catalog_encryption_settings.call_args
        settings = call_args[1]['DataCatalogEncryptionSettings']
        assert 'ConnectionPasswordEncryption' in settings
        assert 'EncryptionAtRest' not in settings

    @pytest.mark.asyncio
    async def test_security_config_without_timestamps(self, handler, mock_context):
        """Test security configuration handling when timestamps are missing."""
        # Test create without CreatedTimestamp in response
        handler.glue_client.create_security_configuration.return_value = {}

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='create-security-configuration',
            config_name='no-timestamp-config',
            encryption_configuration={'S3Encryption': [{'S3EncryptionMode': 'SSE-S3'}]},
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('creation_time') == ''

        # Test get without CreatedTimeStamp in response
        handler.glue_client.get_security_configuration.return_value = {
            'SecurityConfiguration': {
                'Name': 'no-timestamp-config',
                'EncryptionConfiguration': {'S3Encryption': [{'S3EncryptionMode': 'SSE-S3'}]},
            }
        }

        result = await handler.manage_aws_glue_security(
            mock_context, operation='get-security-configuration', config_name='no-timestamp-config'
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('creation_time') == ''

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
        response_data = extract_response_data(result)
        assert response_data.get('profile_name') == 'test-profile'
        assert response_data.get('operation') == 'create-usage-profile'

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
        response_data = extract_response_data(result)
        assert response_data.get('config_name') == 'test-config'
        assert response_data.get('operation') == 'create-security-configuration'

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
        response_data = extract_response_data(result)
        assert response_data.get('encryption_settings') == {'test': 'settings'}
        assert response_data.get('operation') == 'get-datacatalog-encryption'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_put_success(self, handler, mock_context):
        """Test successful creation of a Glue resource policy."""
        handler.glue_client.put_resource_policy.return_value = {'PolicyHash': 'test-hash'}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='put-resource-policy', policy='{"Version": "2012-10-17"}'
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('policy_hash') == 'test-hash'
        assert response_data.get('operation') == 'put-resource-policy'

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
            response_data = extract_response_data(result)
            assert response_data.get('profile_name') == 'test-profile'
            assert response_data.get('operation') == 'delete-usage-profile'

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
        response_data = extract_response_data(result)
        assert response_data.get('profile_name') == 'test-profile'
        assert response_data.get('operation') == 'get-usage-profile'

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
            response_data = extract_response_data(result)
            assert response_data.get('profile_name') == 'test-profile'
            assert response_data.get('operation') == 'update-usage-profile'

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
        response_data = extract_response_data(result)
        assert response_data.get('config_name') == 'test-config'
        assert response_data.get('operation') == 'delete-security-configuration'

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
        response_data = extract_response_data(result)
        assert response_data.get('config_name') == 'test-config'
        assert response_data.get('operation') == 'get-security-configuration'

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
        response_data = extract_response_data(result)
        assert response_data.get('operation') == 'put-datacatalog-encryption'

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
        response_data = extract_response_data(result)
        assert response_data.get('policy_hash') == 'test-hash'
        assert response_data.get('operation') == 'get-resource-policy'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_resource_policies_delete_success(self, handler, mock_context):
        """Test successful deletion of resource policy."""
        handler.glue_client.delete_resource_policy.return_value = {}

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='delete-resource-policy'
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('operation') == 'delete-resource-policy'

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
        response_data = extract_response_data(result)
        assert response_data.get('policy_hash') == 'test-hash'

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
        response_data = extract_response_data(result)
        assert response_data.get('operation') == 'put-datacatalog-encryption'

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
    async def test_integration_create_update_delete_usage_profile_lifecycle(
        self, handler, mock_context
    ):
        """Integration test: Complete lifecycle of usage profile management."""
        # Step 1: Create profile
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-west-2'
            mock_aws_helper.get_aws_account_id.return_value = '987654321098'
            mock_aws_helper.is_resource_mcp_managed.return_value = True
            mock_aws_helper.prepare_resource_tags.return_value = {
                'mcp-managed': 'true',
                'Environment': 'test',
            }

            handler.glue_client.create_usage_profile.return_value = {}

            # Create profile
            result = await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='create-profile',
                profile_name='integration-test-profile',
                description='Profile for integration testing',
                configuration={
                    'JobConfiguration': {
                        'numberOfWorkers': {
                            'DefaultValue': '5',
                            'MinValue': '1',
                            'MaxValue': '20',
                        },
                        'workerType': {'DefaultValue': 'G.1X', 'AllowedValues': ['G.1X', 'G.2X']},
                    }
                },
                tags={'Project': 'IntegrationTest'},
            )

            assert result.isError is False
            create_data = extract_response_data(result)
            assert create_data.get('profile_name') == 'integration-test-profile'

            # Step 2: Get profile to verify creation
            handler.glue_client.get_usage_profile.return_value = {
                'Name': 'integration-test-profile',
                'Description': 'Profile for integration testing',
                'Configuration': {
                    'JobConfiguration': {
                        'numberOfWorkers': {
                            'DefaultValue': '5',
                            'MinValue': '1',
                            'MaxValue': '20',
                        },
                        'workerType': {'DefaultValue': 'G.1X', 'AllowedValues': ['G.1X', 'G.2X']},
                    }
                },
                'Tags': {'mcp-managed': 'true', 'Project': 'IntegrationTest'},
            }

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context, operation='get-profile', profile_name='integration-test-profile'
            )

            assert result.isError is False
            get_data = extract_response_data(result)
            assert get_data.get('profile_name') == 'integration-test-profile'

            # Step 3: Update profile
            handler.glue_client.update_usage_profile.return_value = {}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='update-profile',
                profile_name='integration-test-profile',
                description='Updated profile for integration testing',
                configuration={
                    'JobConfiguration': {
                        'numberOfWorkers': {
                            'DefaultValue': '10',
                            'MinValue': '1',
                            'MaxValue': '50',
                        },
                        'workerType': {
                            'DefaultValue': 'G.2X',
                            'AllowedValues': ['G.1X', 'G.2X', 'G.4X'],
                        },
                    }
                },
            )

            assert result.isError is False
            update_data = extract_response_data(result)
            assert update_data.get('operation') == 'update-usage-profile'

            # Step 4: Delete profile
            handler.glue_client.delete_usage_profile.return_value = {}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context, operation='delete-profile', profile_name='integration-test-profile'
            )

            assert result.isError is False
            delete_data = extract_response_data(result)
            assert delete_data.get('operation') == 'delete-usage-profile'

    @pytest.mark.asyncio
    async def test_integration_security_config_and_encryption_workflow(
        self, handler, mock_context
    ):
        """Integration test: Security configuration with comprehensive encryption workflow."""
        # Step 1: Create comprehensive security configuration
        handler.glue_client.create_security_configuration.return_value = {
            'CreatedTimestamp': datetime.now()
        }

        security_config = {
            'S3Encryption': [
                {
                    'S3EncryptionMode': 'SSE-KMS',
                    'KmsKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/s3-key',
                }
            ],
            'CloudWatchEncryption': {
                'CloudWatchEncryptionMode': 'SSE-KMS',
                'KmsKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/cw-key',
            },
            'JobBookmarksEncryption': {
                'JobBookmarksEncryptionMode': 'CSE-KMS',
                'KmsKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/bookmark-key',
            },
        }

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='create-security-configuration',
            config_name='integration-security-config',
            encryption_configuration=security_config,
        )

        assert result.isError is False

        # Step 2: Verify security configuration exists
        handler.glue_client.get_security_configuration.return_value = {
            'SecurityConfiguration': {
                'Name': 'integration-security-config',
                'EncryptionConfiguration': security_config,
            },
            'CreatedTimeStamp': datetime.now(),
        }

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='get-security-configuration',
            config_name='integration-security-config',
        )

        assert result.isError is False

        # Step 3: Configure catalog encryption to match security config
        handler.glue_client.put_data_catalog_encryption_settings.return_value = {}

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            encryption_at_rest={
                'CatalogEncryptionMode': 'SSE-KMS',
                'SseAwsKmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/catalog-key',
            },
            connection_password_encryption={
                'ReturnConnectionPasswordEncrypted': True,
                'AwsKmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/connection-key',
            },
        )

        assert result.isError is False

        # Step 4: Verify encryption settings
        handler.glue_client.get_data_catalog_encryption_settings.return_value = {
            'DataCatalogEncryptionSettings': {
                'EncryptionAtRest': {
                    'CatalogEncryptionMode': 'SSE-KMS',
                    'SseAwsKmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/catalog-key',
                },
                'ConnectionPasswordEncryption': {
                    'ReturnConnectionPasswordEncrypted': True,
                    'AwsKmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/connection-key',
                },
            }
        }

        result = await handler.manage_aws_glue_encryption(
            mock_context, operation='get-catalog-encryption-settings'
        )

        assert result.isError is False

        # Step 5: Clean up security configuration
        handler.glue_client.delete_security_configuration.return_value = {}

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='delete-security-configuration',
            config_name='integration-security-config',
        )

        assert result.isError is False

    @pytest.mark.asyncio
    async def test_edge_case_malformed_json_in_resource_policy(self, handler, mock_context):
        """Test edge case: Malformed JSON in resource policy."""
        # Test with malformed JSON (missing closing brace)
        malformed_json = '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow"'

        # The handler should pass through the malformed JSON to AWS, which will return an error
        error_response = {
            'Error': {'Code': 'MalformedPolicyDocument', 'Message': 'Invalid policy document'}
        }
        handler.glue_client.put_resource_policy.side_effect = ClientError(
            error_response, 'PutResourcePolicy'
        )

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='put-resource-policy', policy=malformed_json
        )

        assert result.isError is True
        assert 'Invalid policy document' in result.content[0].text

    @pytest.mark.asyncio
    async def test_edge_case_unicode_and_special_characters(self, handler, mock_context):
        """Test edge case: Unicode and special characters in names and descriptions."""
        # Test with Unicode characters
        unicode_profile_name = 'test-profile-ñäme-测试-🔒'
        unicode_description = 'Description with émojis 🚀 and spëcial chars ñoñó'

        handler.glue_client.create_usage_profile.return_value = {}

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name=unicode_profile_name,
            description=unicode_description,
            configuration={'test': 'config'},
            tags={'Unicode': 'tëst-välue-测试'},
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('profile_name') == unicode_profile_name

    @pytest.mark.asyncio
    async def test_edge_case_extremely_large_configurations(self, handler, mock_context):
        """Test edge case: Extremely large configuration objects."""
        # Create a large configuration to test size limits
        large_config = {
            'JobConfiguration': {
                f'setting_{i}': {
                    'DefaultValue': f'value_{i}',
                    'MinValue': '1',
                    'MaxValue': '1000',
                    'Description': f'Large configuration setting number {i} with detailed description',
                }
                for i in range(100)  # 100 configuration entries
            }
        }

        handler.glue_client.create_usage_profile.return_value = {}

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='large-config-profile',
            configuration=large_config,
        )

        assert result.isError is False

    @pytest.mark.asyncio
    async def test_edge_case_null_and_empty_values_handling(self, handler, mock_context):
        """Test edge case: Handling of null and empty values in responses."""
        # Test when AWS returns null/empty values in response fields
        handler.glue_client.get_usage_profile.return_value = {
            'Name': 'test-profile',
            'Description': None,  # Null description
            'Configuration': {},  # Empty configuration
            'Tags': None,  # Null tags
        }

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context, operation='get-profile', profile_name='test-profile'
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('profile_name') == 'test-profile'

        # Test resource policy with null values
        handler.glue_client.get_resource_policy.return_value = {
            'PolicyHash': None,
            'PolicyInJson': None,
            'CreateTime': None,
            'UpdateTime': None,
        }

        result = await handler.manage_aws_glue_resource_policies(
            mock_context, operation='get-resource-policy'
        )

        assert result.isError is False
        response_data = extract_response_data(result)
        assert response_data.get('policy_hash') is None

    @pytest.mark.asyncio
    async def test_concurrent_operations_simulation(self, handler, mock_context):
        """Test simulation of concurrent operations on the same resource."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            # Simulate concurrent modification error
            error_response = {
                'Error': {
                    'Code': 'ConcurrentModificationException',
                    'Message': 'Resource being modified',
                }
            }
            handler.glue_client.update_usage_profile.side_effect = ClientError(
                error_response, 'UpdateUsageProfile'
            )
            handler.glue_client.get_usage_profile.return_value = {'Name': 'concurrent-profile'}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context,
                operation='update-profile',
                profile_name='concurrent-profile',
                configuration={'test': 'config'},
            )

            assert result.isError is True
            assert 'Resource being modified' in result.content[0].text

    @pytest.mark.asyncio
    async def test_aws_service_limits_and_quotas(self, handler, mock_context):
        """Test AWS service limits and quota-related errors."""
        # Test usage profile creation with quota exceeded
        error_response = {
            'Error': {'Code': 'LimitExceededException', 'Message': 'Too many usage profiles'}
        }
        handler.glue_client.create_usage_profile.side_effect = ClientError(
            error_response, 'CreateUsageProfile'
        )

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='quota-test-profile',
            configuration={'test': 'config'},
        )

        assert result.isError is True
        assert 'Too many usage profiles' in result.content[0].text

        # Test security configuration with resource limit
        error_response = {
            'Error': {
                'Code': 'ResourceNumberLimitExceededException',
                'Message': 'Security config limit exceeded',
            }
        }
        handler.glue_client.create_security_configuration.side_effect = ClientError(
            error_response, 'CreateSecurityConfiguration'
        )

        result = await handler.manage_aws_glue_security(
            mock_context,
            operation='create-security-configuration',
            config_name='quota-security-config',
            encryption_configuration={'test': 'config'},
        )

        assert result.isError is True
        assert 'Security config limit exceeded' in result.content[0].text

    @pytest.mark.asyncio
    async def test_cross_region_resource_management(self, handler, mock_context):
        """Test cross-region resource management scenarios."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler.AwsHelper'
        ) as mock_aws_helper:
            # Test with different regions
            mock_aws_helper.get_aws_region.return_value = 'eu-west-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            handler.glue_client.get_usage_profile.return_value = {'Name': 'cross-region-profile'}
            handler.glue_client.delete_usage_profile.return_value = {}

            result = await handler.manage_aws_glue_usage_profiles(
                mock_context, operation='delete-profile', profile_name='cross-region-profile'
            )

            assert result.isError is False
            # Verify the correct region was used in ARN construction
            mock_aws_helper.is_resource_mcp_managed.assert_called()

    @pytest.mark.asyncio
    async def test_permission_denied_scenarios(self, handler, mock_context):
        """Test various permission denied scenarios."""
        # Test insufficient permissions for usage profile operations
        error_response = {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'User not authorized'}
        }
        handler.glue_client.create_usage_profile.side_effect = ClientError(
            error_response, 'CreateUsageProfile'
        )

        result = await handler.manage_aws_glue_usage_profiles(
            mock_context,
            operation='create-profile',
            profile_name='permission-test-profile',
            configuration={'test': 'config'},
        )

        assert result.isError is True
        assert 'User not authorized' in result.content[0].text

        # Test KMS key permission issues for encryption
        error_response = {
            'Error': {'Code': 'KMSKeyNotAccessibleException', 'Message': 'KMS key not accessible'}
        }
        handler.glue_client.put_data_catalog_encryption_settings.side_effect = ClientError(
            error_response, 'PutDataCatalogEncryptionSettings'
        )

        result = await handler.manage_aws_glue_encryption(
            mock_context,
            operation='put-catalog-encryption-settings',
            encryption_at_rest={
                'CatalogEncryptionMode': 'SSE-KMS',
                'SseAwsKmsKeyId': 'invalid-key',
            },
        )

        assert result.isError is True
        assert 'KMS key not accessible' in result.content[0].text

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
