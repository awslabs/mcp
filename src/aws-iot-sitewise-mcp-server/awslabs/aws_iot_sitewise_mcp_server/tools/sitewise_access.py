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

"""AWS IoT SiteWise Access Policies and Configuration Management Tools."""

from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from pydantic import Field
from typing import Any, Dict, Optional


@tool_metadata(readonly=True)
def describe_default_encryption_configuration(
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Retrieve information about the default encryption configuration for your AWS account.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing default encryption configuration
    """
    try:
        client = create_sitewise_client(region)

        response = client.describe_default_encryption_configuration()

        return {
            'success': True,
            'encryption_type': response['encryptionType'],
            'kms_key_id': response.get('kmsKeyId', ''),
            'configuration_status': response['configurationStatus'],
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def put_default_encryption_configuration(
    encryption_type: str = Field(
        ...,
        description='The type of encryption used for the encryption configuration (SITEWISE_DEFAULT_ENCRYPTION, KMS_BASED_ENCRYPTION)',
    ),
    region: str = Field('us-east-1', description='AWS region'),
    kms_key_id: Optional[str] = Field(
        None, description='The Key ID of the customer managed key used for KMS encryption'
    ),
) -> Dict[str, Any]:
    """Set the default encryption configuration for your AWS account.

    Args:
        encryption_type: The type of encryption used for the encryption \
            configuration (SITEWISE_DEFAULT_ENCRYPTION, KMS_BASED_ENCRYPTION)
        region: AWS region (default: us-east-1)
        kms_key_id: The Key ID of the customer managed key used for KMS \
            encryption

    Returns:
        Dictionary containing encryption configuration response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'encryptionType': encryption_type}
        if kms_key_id:
            params['kmsKeyId'] = kms_key_id

        response = client.put_default_encryption_configuration(**params)

        return {
            'success': True,
            'encryption_type': response['encryptionType'],
            'kms_key_id': response.get('kmsKeyId', ''),
            'configuration_status': response['configurationStatus'],
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def describe_logging_options(
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Retrieve the current AWS IoT SiteWise logging options.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing logging options
    """
    try:
        client = create_sitewise_client(region)

        response = client.describe_logging_options()

        return {'success': True, 'logging_options': response['loggingOptions']}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def put_logging_options(
    logging_options: Dict[str, Any] = Field(
        ..., description='Logging configuration with level (INFO, ERROR, OFF) and optional roleArn'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Set logging options for AWS IoT SiteWise.

    Args:
        logging_options: The logging options to set
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing logging options response
    """
    try:
        client = create_sitewise_client(region)

        client.put_logging_options(loggingOptions=logging_options)
        return {'success': True, 'message': 'Logging options updated successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def describe_storage_configuration(
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Retrieve information about the storage configuration for your AWS account.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing storage configuration
    """
    try:
        client = create_sitewise_client(region)

        response = client.describe_storage_configuration()

        return {
            'success': True,
            'storage_type': response['storageType'],
            'multi_layer_storage': response.get('multiLayerStorage', {}),
            'disassociated_data_storage': response.get('disassociatedDataStorage', 'ENABLED'),
            'retention_period': response.get('retentionPeriod', {}),
            'configuration_status': response['configurationStatus'],
            'last_update_date': (
                response.get('lastUpdateDate', '').isoformat()
                if response.get('lastUpdateDate')
                else ''
            ),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def put_storage_configuration(
    storage_type: str = Field(
        ..., description='The storage type (SITEWISE_DEFAULT_STORAGE, MULTI_LAYER_STORAGE)'
    ),
    region: str = Field('us-east-1', description='AWS region'),
    multi_layer_storage: Optional[Dict[str, Any]] = Field(
        None, description='Multi-layer storage configuration details'
    ),
    disassociated_data_storage: str = Field(
        'ENABLED', description='Disassociated data storage setting (ENABLED, DISABLED)'
    ),
    retention_period: Optional[Dict[str, Any]] = Field(
        None, description='Data retention period configuration'
    ),
    warm_tier: str = Field('ENABLED', description='Warm tier setting (ENABLED, DISABLED)'),
    warm_tier_retention_period: Optional[Dict[str, Any]] = Field(
        None, description='Warm tier retention period configuration'
    ),
) -> Dict[str, Any]:
    """Configure storage settings for AWS IoT SiteWise.

    Args:
        storage_type: The storage tier that you specified for your data (
            SITEWISE_DEFAULT_STORAGE, MULTI_LAYER_STORAGE)
        region: AWS region (default: us-east-1)
        multi_layer_storage: Identifies a storage destination
        disassociated_data_storage: Contains the storage configuration for \
            time series data that isn't associated with asset properties
        retention_period: How many days your data is kept in the hot tier
        warm_tier: A service managed storage tier optimized for analytical \
            queries (ENABLED, DISABLED)
        warm_tier_retention_period: Set this period to specify how long your \
            data is stored in the warm tier

    Returns:
        Dictionary containing storage configuration response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'storageType': storage_type,
            'disassociatedDataStorage': disassociated_data_storage,
            'warmTier': warm_tier,
        }

        if multi_layer_storage:
            params['multiLayerStorage'] = multi_layer_storage
        if retention_period:
            params['retentionPeriod'] = retention_period
        if warm_tier_retention_period:
            params['warmTierRetentionPeriod'] = warm_tier_retention_period

        response = client.put_storage_configuration(**params)

        return {
            'success': True,
            'storage_type': response['storageType'],
            'multi_layer_storage': response.get('multiLayerStorage', {}),
            'disassociated_data_storage': response.get('disassociatedDataStorage', 'ENABLED'),
            'retention_period': response.get('retentionPeriod', {}),
            'configuration_status': response['configurationStatus'],
            'warm_tier': response.get('warmTier', 'ENABLED'),
            'warm_tier_retention_period': response.get('warmTierRetentionPeriod', {}),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


# Create MCP tools

describe_default_encryption_configuration_tool = Tool.from_function(
    fn=describe_default_encryption_configuration,
    name='describe_default_encryption_config',
    description=(
        'Retrieve information about the default encryption configuration for AWS IoT SiteWise.'
    ),
)

put_default_encryption_configuration_tool = Tool.from_function(
    fn=put_default_encryption_configuration,
    name='put_default_encryption_configuration',
    description='Set the default encryption configuration for AWS IoT \
        SiteWise.',
)

describe_logging_options_tool = Tool.from_function(
    fn=describe_logging_options,
    name='describe_logging_options',
    description='Retrieve the current AWS IoT SiteWise logging options.',
)

put_logging_options_tool = Tool.from_function(
    fn=put_logging_options,
    name='put_logging_options',
    description='Set logging options for AWS IoT SiteWise.',
)

describe_storage_configuration_tool = Tool.from_function(
    fn=describe_storage_configuration,
    name='describe_storage_configuration',
    description=('Retrieve information about the storage configuration for AWS IoT SiteWise.'),
)

put_storage_configuration_tool = Tool.from_function(
    fn=put_storage_configuration,
    name='put_storage_configuration',
    description=(
        'Configure storage settings for AWS IoT SiteWise including '
        'multi-layer storage and retention policies.'
    ),
)
