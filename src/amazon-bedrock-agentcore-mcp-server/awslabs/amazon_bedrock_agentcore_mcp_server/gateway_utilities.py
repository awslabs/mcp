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

"""AgentCore MCP Server - Gateway Management Module utility files.

Contains utility functions for managing gateways, including
- Uploading Smithy models from to S3
- Uploading OpenAPI schemas to S3 with credential configuration.

"""

import boto3
import json
from typing import List, Optional


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def upload_smithy_model(  # pragma: no cover
    smithy_model: dict, smithy_model_name: str, region: str, setup_steps: List[str]
) -> Optional[str]:
    """Take a dict of a smithy model (usually from json) upload to S3.

    Args:
        smithy_model: Dictionary representing the Smithy model JSON
        smithy_model_name: Name of the Smithy model (e.g., s3, dynamodb)
        region: AWS region for S3 bucket
        setup_steps: List to append status messages to

    Returns:
        S3 URI of uploaded Smithy model, or None if failed
    """
    try:  # pragma: no cover
        # Step 1: Search GitHub API for the service directory

        # Step 6: Create S3 bucket name and upload
        bucket_name = f'agentcore-smithy-models-{region}'
        s3_key = f'{smithy_model_name}.json'

        setup_steps.append(f'S3: Uploading to S3: {bucket_name}/{s3_key}')

        s3_client = boto3.client('s3', region_name=region)

        # Create bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            setup_steps.append(f'OK S3 bucket {bucket_name} exists')
        except Exception as e:
            print(f'Could not access S3 bucket: {str(e)}')
            try:
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region},
                    )
                setup_steps.append(f'OK Created S3 bucket {bucket_name}')
            except Exception as bucket_error:
                setup_steps.append(f'X Could not create S3 bucket: {str(bucket_error)}')
                return None

        # Upload the JSON file
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(smithy_model, indent=2),
                ContentType='application/json',
            )
            setup_steps.append('OK Uploaded Smithy model to S3')

            s3_uri = f's3://{bucket_name}/{s3_key}'
            return s3_uri

        except Exception as upload_error:
            setup_steps.append(f'X S3 upload failed: {str(upload_error)}')
            return None

    except Exception as e:
        setup_steps.append(f'X Smithy model workflow failed: {str(e)}')
        return None


async def upload_openapi_schema(  # pragma: no cover
    openapi_spec: dict,
    gateway_name: str,
    region: str,
    setup_steps: List[str],
    api_key: str = '',
    credential_location: str = 'QUERY_PARAMETER',
    credential_parameter_name: str = 'api_key',
) -> Optional[dict]:
    """Upload OpenAPI schema to S3 and create proper credential configuration.

    Args:
        openapi_spec: OpenAPI specification as dictionary
        gateway_name: Gateway name for S3 key
        region: AWS region for S3 bucket
        setup_steps: List to append status messages to
        api_key: API key for authentication
        credential_location: Where to place credentials (QUERY_PARAMETER or HEADER)
        credential_parameter_name: Name of the credential parameter

    Returns:
        Dictionary with S3 URI and credential configuration, or None if failed
    """
    import json

    try:
        # Step 1: Upload OpenAPI schema to S3
        bucket_name = f'agentcore-openapi-schemas-{region}'
        s3_key = f'{gateway_name}-openapi-schema.json'

        setup_steps.append(f'S3: Uploading OpenAPI schema to S3: {bucket_name}/{s3_key}')

        s3_client = boto3.client('s3', region_name=region)

        # Create bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            setup_steps.append(f'OK S3 bucket {bucket_name} exists')
        except Exception as e:
            print(f'Could not access S3 bucket: {str(e)}')
            try:
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region},
                    )
                setup_steps.append(f'OK Created S3 bucket {bucket_name}')
            except Exception as bucket_error:
                setup_steps.append(f'X Could not create S3 bucket: {str(bucket_error)}')
                return None

        # Upload the OpenAPI schema
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(openapi_spec, indent=2),
                ContentType='application/json',
            )
            setup_steps.append('OK Uploaded OpenAPI schema to S3')

            s3_uri = f's3://{bucket_name}/{s3_key}'

            # Step 2: Create credential configuration if API key provided
            credential_config = None
            if api_key:
                setup_steps.append(
                    f'Security: Configuring API key credentials ({credential_location})'
                )

                credential_config = {
                    'credentialProviderType': 'API_KEY',
                    'credentialLocation': credential_location,
                    'credentialParameterName': credential_parameter_name,
                    'credentialValue': api_key,
                }
                setup_steps.append('OK API key credential configuration created')

            return {'s3_uri': s3_uri, 'credential_config': credential_config}

        except Exception as upload_error:
            setup_steps.append(f'X S3 upload failed: {str(upload_error)}')
            return None

    except Exception as e:
        setup_steps.append(f'X OpenAPI schema workflow failed: {str(e)}')
        return None
