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

"""GlueCommonsHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.models.glue_models import (
    CreateSecurityConfigurationResponse,
    CreateUsageProfileResponse,
    DeleteResourcePolicyResponse,
    DeleteSecurityConfigurationResponse,
    DeleteUsageProfileResponse,
    GetDataCatalogEncryptionSettingsResponse,
    GetResourcePolicyResponse,
    GetSecurityConfigurationResponse,
    GetUsageProfileResponse,
    PutDataCatalogEncryptionSettingsResponse,
    PutResourcePolicyResponse,
    UpdateUsageProfileResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, Optional, Union


class GlueCommonsHandler:
    """Handler for Amazon Glue common operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Glue Commons handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client('glue')

        # Register tools
        self.mcp.tool(name='manage_aws_glue_usage_profiles')(self.manage_aws_glue_usage_profiles)
        self.mcp.tool(name='manage_aws_glue_security_configurations')(
            self.manage_aws_glue_security
        )
        self.mcp.tool(name='manage_aws_glue_encryption')(self.manage_aws_glue_encryption)
        self.mcp.tool(name='manage_aws_glue_resource_policies')(
            self.manage_aws_glue_resource_policies
        )

    async def manage_aws_glue_usage_profiles(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-profile, delete-profile, get-profile, update-profile. Choose "get-profile" for read-only operations when write access is disabled.',
        ),
        profile_name: str = Field(
            ...,
            description='Name of the usage profile.',
        ),
        description: Optional[str] = Field(
            None,
            description='Description of the usage profile (for create-profile and update-profile operations).',
        ),
        configuration: Optional[Dict[str, Any]] = Field(
            None,
            description='Configuration object specifying job and session values for the profile (required for create-profile and update-profile operations).',
        ),
        tags: Optional[Dict[str, str]] = Field(
            None,
            description='Tags to apply to the usage profile (for create-profile operation).',
        ),
    ) -> Union[
        CreateUsageProfileResponse,
        DeleteUsageProfileResponse,
        GetUsageProfileResponse,
        UpdateUsageProfileResponse,
    ]:
        """Manage AWS Glue Usage Profiles for resource allocation and cost management.

        This tool allows you to create, retrieve, update, and delete AWS Glue Usage Profiles, which define
        resource allocation and cost management settings for Glue jobs and interactive sessions.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-profile, delete-profile, and update-profile operations
        - Appropriate AWS permissions for Glue Usage Profile operations

        ## Operations
        - **create-profile**: Create a new usage profile with specified resource allocations
        - **delete-profile**: Delete an existing usage profile
        - **get-profile**: Retrieve detailed information about a specific usage profile
        - **update-profile**: Update an existing usage profile's configuration

        ## Example
        ```json
        {
          "operation": "create-profile",
          "profile_name": "my-standard-profile",
          "description": "Standard resource allocation for ETL jobs",
          "configuration": {
              "JobConfiguration": {
                "numberOfWorkers": {
                  "DefaultValue": "10",
                  "MinValue": "1",
                  "MaxValue": "10"
                },
                "workerType": {
                  "DefaultValue": "G.2X",
                  "AllowedValues": [
                    "G.2X",
                    "G.4X",
                    "G.8X"
                  ]
                },
            }
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            profile_name: Name of the usage profile
            description: Description of the usage profile
            configuration: Configuration object specifying job and session values
            tags: Tags to apply to the usage profile

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation != 'get-profile':
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'create-profile':
                    return CreateUsageProfileResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        profile_name='',
                        operation='create',
                    )
                elif operation == 'delete-profile':
                    return DeleteUsageProfileResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        profile_name='',
                        operation='delete',
                    )
                elif operation == 'update-profile':
                    return UpdateUsageProfileResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        profile_name='',
                        operation='update',
                    )

            if operation == 'create-profile':
                if configuration is None:
                    raise ValueError('configuration is required for create-profile operation')

                # Prepare create request parameters
                params = {'Name': profile_name, 'Configuration': configuration}

                if description:
                    params['Description'] = description

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags('GlueUsageProfile')

                # Merge user-provided tags with MCP tags
                if tags:
                    merged_tags = tags.copy()
                    merged_tags.update(resource_tags)
                    params['Tags'] = merged_tags
                else:
                    params['Tags'] = resource_tags

                # Create the usage profile
                response = self.glue_client.create_usage_profile(**params)

                return CreateUsageProfileResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created usage profile {profile_name}',
                        )
                    ],
                    profile_name=profile_name,
                    operation='create',
                )

            elif operation == 'delete-profile':
                # First get the profile to check if it's managed by MCP
                try:
                    response = self.glue_client.get_usage_profile(Name=profile_name)

                    # Construct the ARN for the usage profile
                    region = AwsHelper.get_aws_region() or 'us-east-1'
                    account_id = AwsHelper.get_aws_account_id()
                    profile_arn = f'arn:aws:glue:{region}:{account_id}:usageProfile/{profile_name}'

                    # Check if the profile is managed by MCP
                    tags = response.get('Tags', {})
                    if not AwsHelper.is_resource_mcp_managed(self.glue_client, profile_arn, {}):
                        error_message = f'Cannot delete usage profile {profile_name} - it is not managed by the MCP server (missing required tags)'
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteUsageProfileResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            profile_name=profile_name,
                            operation='delete',
                        )
                except ClientError as e:
                    if e.response['Error']['Code'] == 'EntityNotFoundException':
                        error_message = f'Usage profile {profile_name} not found'
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteUsageProfileResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            profile_name=profile_name,
                            operation='delete',
                        )
                    else:
                        raise e

                # Delete the usage profile if it's managed by MCP
                self.glue_client.delete_usage_profile(Name=profile_name)

                return DeleteUsageProfileResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully deleted usage profile {profile_name}',
                        )
                    ],
                    profile_name=profile_name,
                    operation='delete',
                )

            elif operation == 'get-profile':
                # Get the usage profile
                response = self.glue_client.get_usage_profile(Name=profile_name)

                return GetUsageProfileResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved usage profile {profile_name}',
                        )
                    ],
                    profile_name=response.get('Name', profile_name),
                    profile_details=response,
                    operation='get',
                )

            elif operation == 'update-profile':
                if configuration is None:
                    raise ValueError('configuration is required for update-profile operation')

                # First get the profile to check if it's managed by MCP
                try:
                    response = self.glue_client.get_usage_profile(Name=profile_name)

                    # Construct the ARN for the usage profile
                    region = AwsHelper.get_aws_region() or 'us-east-1'
                    account_id = AwsHelper.get_aws_account_id()
                    profile_arn = f'arn:aws:glue:{region}:{account_id}:usageProfile/{profile_name}'

                    # Check if the profile is managed by MCP
                    tags = response.get('Tags', {})
                    if not AwsHelper.is_resource_mcp_managed(self.glue_client, profile_arn, {}):
                        error_message = f'Cannot update usage profile {profile_name} - it is not managed by the MCP server (missing required tags)'
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return UpdateUsageProfileResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            profile_name=profile_name,
                            operation='update',
                        )
                except ClientError as e:
                    if e.response['Error']['Code'] == 'EntityNotFoundException':
                        error_message = f'Usage profile {profile_name} not found'
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return UpdateUsageProfileResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            profile_name=profile_name,
                            operation='update',
                        )
                    else:
                        raise e

                # Prepare update request parameters
                params = {'Name': profile_name, 'Configuration': configuration}

                if description:
                    params['Description'] = description

                # Update the usage profile
                response = self.glue_client.update_usage_profile(**params)

                return UpdateUsageProfileResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated usage profile {profile_name}',
                        )
                    ],
                    profile_name=profile_name,
                    operation='update',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-profile, delete-profile, get-profile, update-profile'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetUsageProfileResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    profile_name=profile_name,
                    profile_details={},
                    operation='get',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_usage_profiles: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetUsageProfileResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                profile_name=profile_name,
                profile_details={},
                operation='get',
            )

    async def manage_aws_glue_security(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-security-configuration, delete-security-configuration, get-security-configuration. Choose "get-security-configuration" for read-only operations when write access is disabled.',
        ),
        config_name: str = Field(
            ...,
            description='Name of the security configuration.',
        ),
        encryption_configuration: Optional[Dict[str, Any]] = Field(
            None,
            description='Encryption configuration for create-security-configuration operation, containing settings for S3, CloudWatch, and job bookmarks encryption.',
        ),
    ) -> Union[
        CreateSecurityConfigurationResponse,
        DeleteSecurityConfigurationResponse,
        GetSecurityConfigurationResponse,
    ]:
        """Manage AWS Glue Security Configurations for data encryption.

        This tool allows you to create, retrieve, and delete AWS Glue Security Configurations, which define
        encryption settings for Glue jobs, crawlers, and development endpoints.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-security-configuration and delete-security-configuration operations
        - Appropriate AWS permissions for Glue Security Configuration operations

        ## Operations
        - **create-security-configuration**: Create a new security configuration with encryption settings
        - **delete-security-configuration**: Delete an existing security configuration
        - **get-security-configuration**: Retrieve detailed information about a specific security configuration

        ## Example
        ```json
        {
          "operation": "create-security-configuration",
          "config_name": "my-encryption-config",
          "encryption_configuration": {
            "S3Encryption": [
              {
                "S3EncryptionMode": "SSE-KMS",
                "KmsKeyArn": "arn:aws:kms:region:account-id:key/key-id"
              }
            ],
            "CloudWatchEncryption": {
              "CloudWatchEncryptionMode": "DISABLED"
            },
            "JobBookmarksEncryption": {
              "JobBookmarksEncryptionMode": "CSE-KMS",
              "KmsKeyArn": "arn:aws:kms:region:account-id:key/key-id"
            }
          }
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            config_name: Name of the security configuration
            encryption_configuration: Encryption configuration for create-security-configuration operation

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation != 'get-security-configuration':
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'create-security-configuration':
                    return CreateSecurityConfigurationResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        config_name='',
                        creation_time='',
                        encryption_configuration={},
                        operation='create',
                    )
                elif operation == 'delete-security-configuration':
                    return DeleteSecurityConfigurationResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        config_name='',
                        operation='delete',
                    )

            if operation == 'create-security-configuration':
                if encryption_configuration is None:
                    raise ValueError(
                        'encryption_configuration is required for create-security-configuration operation'
                    )

                # Create the security configuration
                response = self.glue_client.create_security_configuration(
                    Name=config_name, EncryptionConfiguration=encryption_configuration
                )

                return CreateSecurityConfigurationResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created security configuration {config_name}',
                        )
                    ],
                    config_name=config_name,
                    creation_time=(
                        response.get('CreatedTimestamp', '').isoformat()
                        if response.get('CreatedTimestamp')
                        else ''
                    ),
                    encryption_configuration=encryption_configuration or {},
                    operation='create',
                )

            elif operation == 'delete-security-configuration':
                # First check if the security configuration exists
                try:
                    # Get the security configuration
                    self.glue_client.get_security_configuration(Name=config_name)

                    # Note: Security configurations don't support tags in AWS Glue API
                    # so we can't verify if it's managed by MCP

                except ClientError as e:
                    if e.response['Error']['Code'] == 'EntityNotFoundException':
                        error_message = f'Security configuration {config_name} not found'
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteSecurityConfigurationResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            config_name=config_name,
                            operation='delete',
                        )
                    else:
                        raise e

                # Delete the security configuration
                self.glue_client.delete_security_configuration(Name=config_name)

                return DeleteSecurityConfigurationResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully deleted security configuration {config_name}',
                        )
                    ],
                    config_name=config_name,
                    operation='delete',
                )

            elif operation == 'get-security-configuration':
                # Get the security configuration
                response = self.glue_client.get_security_configuration(Name=config_name)

                security_config = response.get('SecurityConfiguration', {})

                return GetSecurityConfigurationResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved security configuration {config_name}',
                        )
                    ],
                    config_name=security_config.get('Name', config_name),
                    config_details=security_config,
                    creation_time=(
                        response.get('CreatedTimeStamp', '').isoformat()
                        if response.get('CreatedTimeStamp')
                        else ''
                    ),
                    encryption_configuration=security_config.get('EncryptionConfiguration', {}),
                    operation='get',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-security-configuration, delete-security-configuration, get-security-configuration'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetSecurityConfigurationResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    config_name=config_name,
                    config_details={},
                    creation_time='',
                    encryption_configuration={},
                    operation='get',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_security: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetSecurityConfigurationResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                config_name=config_name,
                config_details={},
                creation_time='',
                encryption_configuration={},
                operation='get',
            )

    async def manage_aws_glue_encryption(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: get-catalog-encryption-settings, put-catalog-encryption-settings. Choose "get-catalog-encryption-settings" for read-only operations when write access is disabled.',
        ),
        catalog_id: Optional[str] = Field(
            None,
            description="ID of the Data Catalog to retrieve or update encryption settings for (defaults to caller's AWS account ID).",
        ),
        encryption_at_rest: Optional[Dict[str, Any]] = Field(
            None,
            description='Encryption-at-rest configuration for the Data Catalog (for put-catalog-encryption-settings operation).',
        ),
        connection_password_encryption: Optional[Dict[str, Any]] = Field(
            None,
            description='Connection password encryption configuration for the Data Catalog (for put-catalog-encryption-settings operation).',
        ),
    ) -> Union[
        GetDataCatalogEncryptionSettingsResponse,
        PutDataCatalogEncryptionSettingsResponse,
    ]:
        """Manage AWS Glue Data Catalog Encryption Settings for data protection.

        This tool allows you to retrieve and update AWS Glue Data Catalog Encryption Settings, which control
        how metadata and connection passwords are encrypted in the Data Catalog.

        ## Requirements
        - The server must be run with the `--allow-write` flag for put-catalog-encryption-settings operation
        - Appropriate AWS permissions for Glue Data Catalog Encryption operations

        ## Operations
        - **get-catalog-encryption-settings**: Retrieve the current encryption settings for the Data Catalog
        - **put-catalog-encryption-settings**: Update the encryption settings for the Data Catalog

        ## Example
        ```json
        {
          "operation": "put-catalog-encryption-settings",
          "encryption_at_rest": {
            "CatalogEncryptionMode": "SSE-KMS",
            "SseAwsKmsKeyId": "arn:aws:kms:region:account-id:key/key-id"
          },
          "connection_password_encryption": {
            "ReturnConnectionPasswordEncrypted": true,
            "AwsKmsKeyId": "arn:aws:kms:region:account-id:key/key-id"
          }
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            catalog_id: ID of the Data Catalog (optional, defaults to the caller's AWS account ID)
            encryption_at_rest: Encryption-at-rest configuration for the Data Catalog
            connection_password_encryption: Connection password encryption configuration

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation != 'get-catalog-encryption-settings':
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                return PutDataCatalogEncryptionSettingsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    operation='put',
                )

            if operation == 'get-catalog-encryption-settings':
                # Prepare parameters
                params = {}
                if catalog_id:
                    params['CatalogId'] = catalog_id

                # Get the catalog encryption settings
                response = self.glue_client.get_data_catalog_encryption_settings(**params)

                return GetDataCatalogEncryptionSettingsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully retrieved Data Catalog encryption settings',
                        )
                    ],
                    encryption_settings=response.get('DataCatalogEncryptionSettings', {}),
                    operation='get',
                )

            elif operation == 'put-catalog-encryption-settings':
                # Prepare encryption settings
                encryption_settings = {}
                if encryption_at_rest:
                    encryption_settings['EncryptionAtRest'] = encryption_at_rest
                if connection_password_encryption:
                    encryption_settings['ConnectionPasswordEncryption'] = (
                        connection_password_encryption
                    )

                if not encryption_settings:
                    raise ValueError(
                        'Either encryption_at_rest or connection_password_encryption is required for put-catalog-encryption-settings operation'
                    )

                # Prepare parameters
                params: Dict[str, Any] = {'DataCatalogEncryptionSettings': encryption_settings}
                if catalog_id:
                    params['CatalogId'] = catalog_id

                # Update the catalog encryption settings
                self.glue_client.put_data_catalog_encryption_settings(**params)

                return PutDataCatalogEncryptionSettingsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully updated Data Catalog encryption settings',
                        )
                    ],
                    operation='put',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: get-catalog-encryption-settings, put-catalog-encryption-settings'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetDataCatalogEncryptionSettingsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    encryption_settings={},
                    operation='get',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_encryption: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetDataCatalogEncryptionSettingsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                encryption_settings={},
                operation='get',
            )

    async def manage_aws_glue_resource_policies(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: get-resource-policy, put-resource-policy, delete-resource-policy. Choose "get-resource-policy" for read-only operations when write access is disabled.',
        ),
        policy: Optional[str] = Field(
            None,
            description='Resource policy document for put-resource-policy operation.',
        ),
        policy_hash: Optional[str] = Field(
            None,
            description='Hash of the policy to update or delete.',
        ),
        policy_exists_condition: Optional[str] = Field(
            None,
            description='Condition under which to update or delete the policy (MUST_EXIST or NOT_EXIST).',
        ),
        enable_hybrid: Optional[bool] = Field(
            None,
            description='Whether to enable hybrid access policy for put-resource-policy operation.',
        ),
        resource_arn: Optional[str] = Field(
            None,
            description='ARN of the Glue resource for the resource policy (optional).',
        ),
    ) -> Union[
        GetResourcePolicyResponse,
        PutResourcePolicyResponse,
        DeleteResourcePolicyResponse,
    ]:
        r"""Manage AWS Glue Resource Policies for access control.

        This tool allows you to retrieve, create, update, and delete AWS Glue Resource Policies, which
        control access to Glue resources through IAM policy documents.

        ## Requirements
        - The server must be run with the `--allow-write` flag for put-resource-policy and delete-resource-policy operations
        - Appropriate AWS permissions for Glue Resource Policy operations

        ## Operations
        - **get-resource-policy**: Retrieve the current resource policy
        - **put-resource-policy**: Create or update the resource policy
        - **delete-resource-policy**: Delete the resource policy

        ## Example
        ```json
        {
          "operation": "put-resource-policy",
          "policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789…
          "policy_exists_condition": "NOT_EXIST",
          "enable_hybrid": true
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            policy: Resource policy document for put-resource-policy operation
            policy_hash: Hash of the policy to update or delete
            policy_exists_condition: Condition under which to update or delete the policy
            enable_hybrid: Whether to enable hybrid access policy for put-resource-policy operation
            resource_arn: ARN of the Glue resource for the resource policy

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation != 'get-resource-policy':
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'put-resource-policy':
                    return PutResourcePolicyResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        policy_hash=None,
                        operation='put',
                    )
                elif operation == 'delete-resource-policy':
                    return DeleteResourcePolicyResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        operation='delete',
                    )

            if operation == 'get-resource-policy':
                # Prepare parameters
                params = {}
                if resource_arn:
                    params['ResourceArn'] = resource_arn

                # Get the resource policy
                response = self.glue_client.get_resource_policy(**params)

                return GetResourcePolicyResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully retrieved resource policy',
                        )
                    ],
                    policy_hash=response.get('PolicyHash'),
                    policy_in_json=response.get('PolicyInJson'),
                    create_time=(
                        response.get('CreateTime', '').isoformat()
                        if response.get('CreateTime')
                        else None
                    ),
                    update_time=(
                        response.get('UpdateTime', '').isoformat()
                        if response.get('UpdateTime')
                        else None
                    ),
                    operation='get',
                )

            elif operation == 'put-resource-policy':
                if policy is None:
                    raise ValueError('policy is required for put-resource-policy operation')

                # Prepare parameters
                params: Dict[str, Any] = {'PolicyInJson': policy}
                if policy_hash:
                    params['PolicyHashCondition'] = policy_hash
                if policy_exists_condition:
                    params['PolicyExistsCondition'] = policy_exists_condition
                if enable_hybrid is not None:
                    params['EnableHybrid'] = enable_hybrid
                if resource_arn:
                    params['ResourceArn'] = resource_arn

                # Update the resource policy
                response = self.glue_client.put_resource_policy(**params)

                return PutResourcePolicyResponse(
                    isError=False,
                    content=[
                        TextContent(type='text', text='Successfully updated resource policy')
                    ],
                    policy_hash=response.get('PolicyHash'),
                    operation='put',
                )

            elif operation == 'delete-resource-policy':
                # Prepare parameters
                params = {}
                if policy_hash:
                    params['PolicyHashCondition'] = policy_hash
                if resource_arn:
                    params['ResourceArn'] = resource_arn

                # Delete the resource policy
                self.glue_client.delete_resource_policy(**params)

                return DeleteResourcePolicyResponse(
                    isError=False,
                    content=[
                        TextContent(type='text', text='Successfully deleted resource policy')
                    ],
                    operation='delete',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: get-resource-policy, put-resource-policy, delete-resource-policy'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetResourcePolicyResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    policy_hash=None,
                    policy_in_json=None,
                    create_time=None,
                    update_time=None,
                    operation='get',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_resource_policies: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetResourcePolicyResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                policy_hash=None,
                policy_in_json=None,
                create_time=None,
                update_time=None,
                operation='get',
            )
