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

"""AWS Secrets Manager MCP Server implementation."""

import json
import sys
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from .consts import (
    AWS_PROFILE,
    DEFAULT_MAX_RESULTS,
    DEFAULT_REGION,
    ERROR_MESSAGES,
    FASTMCP_LOG_LEVEL,
    SECRETS_MANAGER_INSTRUCTIONS,
    SUCCESS_MESSAGES,
)
from .models import (
    CreateSecretRequest,
    ListSecretsResponse,
    RandomPasswordConfig,
    ResourcePolicy,
    RotationConfiguration,
    SecretListItem,
    SecretMetadata,
    SecretValue,
    SecretsManagerResponse,
    Tag,
    UpdateSecretRequest,
)


# Configure logging
logger.remove()
logger.add(sys.stderr, level=FASTMCP_LOG_LEVEL)

# Initialize MCP server
mcp = FastMCP(
    'AWS-Secrets-Manager-MCP',
    instructions=SECRETS_MANAGER_INSTRUCTIONS,
    dependencies=[
        'pydantic',
        'boto3',
        'botocore',
        'loguru',
    ],
)

# Global AWS clients
_secrets_client: Optional[Any] = None


def extract_field_value(value: Any, default: Any = None) -> Any:
    """Extract actual value from Field object or return the value as-is."""
    from pydantic.fields import FieldInfo
    
    if isinstance(value, FieldInfo):
        return value.default if value.default is not ... else default
    return value


def get_secrets_client(region: Optional[str] = None) -> Any:
    """Get or create AWS Secrets Manager client."""
    global _secrets_client
    
    if _secrets_client is None or (region and region != DEFAULT_REGION):
        try:
            session = boto3.Session(profile_name=AWS_PROFILE) if AWS_PROFILE else boto3.Session()
            _secrets_client = session.client('secretsmanager', region_name=region or DEFAULT_REGION)
            logger.info(f'Created Secrets Manager client for region: {region or DEFAULT_REGION}')
        except NoCredentialsError:
            logger.error('No AWS credentials found')
            raise
        except Exception as e:
            logger.error(f'Error creating Secrets Manager client: {str(e)}')
            raise
    
    return _secrets_client


def handle_aws_error(error: ClientError, operation: str) -> SecretsManagerResponse:
    """Handle AWS client errors and return appropriate response."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    logger.error(f'AWS error in {operation}: {error_code} - {error_message}')
    
    # Map common AWS errors to user-friendly messages
    if error_code == 'ResourceNotFoundException':
        message = f'Secret not found during {operation}'
    elif error_code == 'InvalidParameterException':
        message = f'Invalid parameter provided for {operation}: {error_message}'
    elif error_code == 'AccessDeniedException':
        message = f'Access denied for {operation}. Check IAM permissions.'
    elif error_code == 'EncryptionFailure':
        message = f'Encryption/decryption failed for {operation}. Check KMS permissions.'
    elif error_code == 'InvalidRequestException':
        message = f'Invalid request for {operation}: {error_message}'
    elif error_code == 'LimitExceededException':
        message = f'AWS service limit exceeded for {operation}'
    elif error_code == 'ResourceExistsException':
        message = f'Resource already exists for {operation}'
    else:
        message = f'AWS error in {operation}: {error_code} - {error_message}'
    
    return SecretsManagerResponse(
        success=False,
        message=message,
        data={'error_code': error_code, 'aws_message': error_message}
    )


@mcp.tool(name='create-secret')
async def create_secret(
    ctx: Context,
    name: str = Field(..., description='Name of the secret to create'),
    secret_value: Union[str, Dict[str, Any]] = Field(
        ..., 
        description='Secret value as string or JSON object'
    ),
    description: Optional[str] = Field(
        None, 
        description='Description of the secret'
    ),
    kms_key_id: Optional[str] = Field(
        None, 
        description='KMS key ID for encryption (optional)'
    ),
    tags: Optional[List[Dict[str, str]]] = Field(
        None, 
        description='Tags to associate with the secret as list of {"Key": "key", "Value": "value"} objects'
    ),
    region: Optional[str] = Field(
        None, 
        description='AWS region (defaults to configured region)'
    ),
) -> SecretsManagerResponse:
    """Create a new secret in AWS Secrets Manager.
    
    This tool creates a new secret with the specified name and value. The secret value
    can be a simple string or a JSON object for structured data like database credentials.
    
    Examples:
    - Simple API key: create_secret(name="prod/api-key", secret_value="abc123")
    - Database credentials: create_secret(name="prod/db/mysql", secret_value={"username": "admin", "password": "secret123"})
    """
    try:
        # Extract actual parameter values from Field objects
        name = extract_field_value(name)
        secret_value = extract_field_value(secret_value)
        description = extract_field_value(description, None)
        kms_key_id = extract_field_value(kms_key_id, None)
        tags = extract_field_value(tags, None)
        region = extract_field_value(region, None)
        
        # Validate and prepare request
        if isinstance(secret_value, dict):
            secret_string = json.dumps(secret_value)
        else:
            secret_string = str(secret_value)
        
        request = CreateSecretRequest(
            name=name,
            secret_value=secret_value,
            description=description,
            kms_key_id=kms_key_id,
            tags=[Tag(key=tag['Key'], value=tag['Value']) for tag in (tags or [])]
        )
        
        client = get_secrets_client(region)
        
        # Prepare API call parameters
        params = {
            'Name': request.name,
            'SecretString': secret_string,
        }
        
        if request.description:
            params['Description'] = request.description
        
        if request.kms_key_id:
            params['KmsKeyId'] = request.kms_key_id
        
        if request.tags:
            params['Tags'] = [{'Key': tag.key, 'Value': tag.value} for tag in request.tags]
        
        # Create the secret
        response = client.create_secret(**params)
        
        logger.info(f'Successfully created secret: {name}')
        
        return SecretsManagerResponse(
            success=True,
            message=SUCCESS_MESSAGES['secret_created'].format(name),
            data={
                'arn': response['ARN'],
                'name': response['Name'],
                'version_id': response['VersionId']
            }
        )
        
    except ClientError as e:
        return handle_aws_error(e, 'create_secret')
    except Exception as e:
        error_message = f'Error creating secret: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return SecretsManagerResponse(success=False, message=error_message)


def main():
    """Main entry point for the AWS Secrets Manager MCP server."""
    logger.info('Starting AWS Secrets Manager MCP server')
    
    # Validate AWS credentials
    try:
        get_secrets_client()
        logger.info('AWS credentials validated successfully')
    except NoCredentialsError:
        error_message = ERROR_MESSAGES['no_credentials']
        logger.error(error_message)
        raise ValueError(error_message)
    except Exception as e:
        error_message = f'Error validating AWS credentials: {str(e)}'
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
