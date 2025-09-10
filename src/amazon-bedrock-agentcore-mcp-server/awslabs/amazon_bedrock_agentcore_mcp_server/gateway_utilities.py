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
- Finding and uploading Smithy models from GitHub to S3
- Discovering available Smithy models from GitHub
- Uploading OpenAPI schemas to S3 with credential configuration.

"""

import boto3
import json
import requests
from typing import Dict, List, Optional


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def find_and_upload_smithy_model(  # pragma: no cover
    smithy_model: str, region: str, setup_steps: List[str]
) -> Optional[str]:
    """Find Smithy model in GitHub AWS API models repo, download it, upload to S3.

    Args:
        smithy_model: The AWS service name (e.g., 'lambda', 'dynamodb')
        region: AWS region for S3 bucket
        setup_steps: List to append status messages to

    Returns:
        S3 URI of uploaded Smithy model, or None if failed
    """
    try:  # pragma: no cover
        # Step 1: Search GitHub API for the service directory
        setup_steps.append(
            f'Network: Searching GitHub API for {smithy_model} service directory...'
        )

        github_api_url = (
            f'https://api.github.com/repos/aws/api-models-aws/contents/models/{smithy_model}'
        )
        response = requests.get(github_api_url)

        if response.status_code != 200:
            setup_steps.append(f"X Service '{smithy_model}' not found in GitHub API models")
            return None

        service_contents = response.json()
        setup_steps.append(f'OK Found {smithy_model} service directory')

        # Step 2: Find the service subdirectory (should be one directory)
        service_dir = None
        for item in service_contents:
            if item['type'] == 'dir' and item['name'] == 'service':
                service_dir = item
                break

        if not service_dir:
            setup_steps.append(f"X No 'service' directory found for {smithy_model}")
            return None

        setup_steps.append('OK Found service directory')

        # Step 3: Get contents of service directory to find version
        service_api_url = service_dir['url']
        response = requests.get(service_api_url)

        if response.status_code != 200:
            setup_steps.append('X Could not access service directory')
            return None

        service_versions = response.json()

        # Find the latest version directory (they're date-formatted)
        version_dir = None
        latest_version = ''

        for item in service_versions:
            if item['type'] == 'dir':
                version_name = item['name']
                if version_name > latest_version:  # String comparison works for YYYY-MM-DD format
                    latest_version = version_name
                    version_dir = item

        if not version_dir:
            setup_steps.append(f'X No version directory found for {smithy_model}')
            return None

        setup_steps.append(f'OK Found latest version: {latest_version}')

        # Step 4: Get contents of version directory to find service.json
        version_api_url = version_dir['url']
        response = requests.get(version_api_url)

        if response.status_code != 200:
            setup_steps.append('X Could not access version directory')
            return None

        version_contents = response.json()

        # Find the smithy model JSON file (usually named {service}-{version}.json)
        service_json_file = None
        expected_filename = f'{smithy_model}-{latest_version}.json'

        for item in version_contents:
            if item['type'] == 'file' and item['name'].endswith('.json'):
                # Try exact match first
                if item['name'] == expected_filename:
                    service_json_file = item
                    break
                # Fall back to any JSON file that contains the service name
                elif smithy_model in item['name'].lower():
                    service_json_file = item
                    break

        if not service_json_file:
            # List all files for debugging
            file_list = [item['name'] for item in version_contents if item['type'] == 'file']
            setup_steps.append(f'X No Smithy JSON file found in {smithy_model}/{latest_version}')
            setup_steps.append(f'Available files: {file_list}')
            return None

        setup_steps.append(f'OK Found Smithy model file: {service_json_file["name"]}')

        # Step 5: Download the service.json file
        download_url = service_json_file['download_url']
        setup_steps.append('Download: Downloading Smithy model JSON...')

        response = requests.get(download_url)
        if response.status_code != 200:
            setup_steps.append('X Could not download service.json')
            return None

        smithy_json = response.json()
        setup_steps.append(f'OK Downloaded Smithy model ({len(response.content)} bytes)')

        # Step 6: Create S3 bucket name and upload
        bucket_name = f'agentcore-smithy-models-{region}'
        s3_key = f'{smithy_model}-{latest_version}-service.json'

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
                Body=json.dumps(smithy_json, indent=2),
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


async def discover_smithy_models() -> Dict[str, List[Dict[str, str]]]:  # pragma: no cover
    """Dynamically discover available AWS Smithy models from GitHub API models repository.

    Returns:
        Dictionary with categorized services or error info
    """
    from collections import defaultdict

    try:
        # Step 1: Get the models directory from GitHub API
        github_api_url = 'https://api.github.com/repos/aws/api-models-aws/contents/models'
        response = requests.get(github_api_url, timeout=10)

        if response.status_code != 200:
            return {
                'errors': [
                    {
                        'message': f'GitHub API request failed: {response.status_code}',
                        'type': 'not200',
                    }
                ]
            }

        models_contents = response.json()

        # Step 2: Extract service names from directory listing
        services = []
        for item in models_contents:
            if item['type'] == 'dir':
                service_name = item['name']
                services.append(service_name)

        # Step 3: Categorize services (basic categorization)
        categories = defaultdict(list)

        # Define service categories based on known patterns
        category_patterns = {
            'Storage': ['s3', 'efs', 'fsx', 'glacier', 'backup'],
            'Database': ['dynamodb', 'rds', 'redshift', 'timestream', 'documentdb', 'neptune'],
            'Compute': ['lambda', 'ec2', 'ecs', 'batch', 'lightsail', 'autoscaling'],
            'Networking': ['vpc', 'route53', 'cloudfront', 'elb', 'apigateway', 'directconnect'],
            'Security': ['iam', 'sts', 'cognito', 'secretsmanager', 'kms', 'acm'],
            'Developer Tools': [
                'codecommit',
                'codebuild',
                'codedeploy',
                'codepipeline',
                'cloudformation',
            ],
            'Monitoring': ['cloudwatch', 'logs', 'xray', 'cloudtrail', 'config'],
            'AI/ML': ['bedrock', 'sagemaker', 'comprehend', 'textract', 'rekognition'],
            'Analytics': ['kinesis', 'glue', 'athena', 'quicksight', 'elasticsearch'],
            'Management': ['organizations', 'support', 'health', 'trustedadvisor'],
        }

        # Categorize each service
        for service in sorted(services):
            categorized = False
            for category, patterns in category_patterns.items():
                if any(pattern in service.lower() for pattern in patterns):
                    categories[category].append(
                        {'name': service, 'description': f'AWS {service} service'}
                    )
                    categorized = True
                    break

            # If not categorized, put in "Other Services"
            if not categorized:
                categories['Other Services'].append(
                    {'name': service, 'description': f'AWS {service} service'}
                )

        return dict(categories)

    except requests.RequestException as e:
        return {
            'errors': [
                {
                    'message': f'Network error accessing GitHub API: {str(e)}',
                    'type': 'RequestException',
                }
            ]
        }
    except Exception as e:
        return {
            'errors': [{'message': f'Failed to discover Smithy models: {str(e)}', 'type': 'Other'}]
        }


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
