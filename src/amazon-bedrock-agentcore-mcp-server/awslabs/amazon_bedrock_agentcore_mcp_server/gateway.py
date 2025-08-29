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

"""AgentCore MCP Server - Gateway Management Module.

Contains gateway creation, configuration, deletion, and MCP testing tools.

MCP TOOLS IMPLEMENTED:
• agent_gateway - Consolidated gateway management (setup, create, delete, list)
• manage_credentials - API key credential provider management

"""

import boto3
import json
import os
import requests
import time
from .utils import RUNTIME_AVAILABLE, SDK_AVAILABLE
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from pydantic import Field
from typing import Dict, List, Literal, Optional


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def _find_and_upload_smithy_model(
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
    import json

    try:
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


async def _discover_smithy_models() -> Dict[str, List[Dict[str, str]]]:
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


async def _upload_openapi_schema(
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


# ============================================================================
# GATEWAY MANAGEMENT TOOLS
# ============================================================================


def register_gateway_tools(mcp: FastMCP):
    """Register gateway management tools."""

    @mcp.tool()
    async def agent_gateway(
        action: Literal[
            'setup',
            'create',
            'targets',
            'cognito',
            'list',
            'delete',
            'auth',
            'test',
            'list_tools',
            'search_tools',
            'invoke_tool',
            'discover',
            'safe_examples',
        ] = Field(default='setup', description='Gateway action'),
        gateway_name: str = Field(default='', description='Gateway name'),
        target_type: Literal['lambda', 'openApiSchema', 'smithyModel'] = Field(
            default='lambda', description='Target type'
        ),
        smithy_model: str = Field(
            default='', description="AWS Smithy model name (e.g., 's3', 'dynamodb')"
        ),
        openapi_spec: Optional[dict] = Field(
            default=None, description='OpenAPI specification as dict'
        ),
        target_name: str = Field(default='', description='Custom target name'),
        target_payload: Optional[dict] = Field(
            default=None, description='Target configuration payload'
        ),
        role_arn: str = Field(default='', description='IAM role ARN for targets'),
        enable_semantic_search: bool = Field(
            default=True, description='Enable semantic search for tools'
        ),
        credentials: Optional[dict] = Field(
            default=None, description='Authentication credentials'
        ),
        credential_location: str = Field(
            default='QUERY_PARAMETER', description='Where to include credentials'
        ),
        credential_parameter_name: str = Field(
            default='api_key', description='Parameter name for credentials'
        ),
        api_key: str = Field(default='', description='API key for authentication'),
        region: str = Field(default='us-east-1', description='AWS region'),
        query: str = Field(default='', description='Search query for tools'),
        tool_name: str = Field(default='', description='Tool name to invoke'),
        tool_arguments: Optional[dict] = Field(
            default=None, description='Arguments for tool invocation'
        ),
    ) -> str:
        """Gateway: CONSOLIDATED AGENT GATEWAY MANAGEMENT.

        Single tool for ALL gateway operations with complete workflow automation.

        Actions:
        - setup: Complete gateway setup workflow (cognito + gateway + targets)
        - test: Test gateway with MCP client functionality (list/search/invoke tools)
        - list_tools: List available tools from gateway via MCP protocol
        - search_tools: Semantic search for tools through gateway
        - invoke_tool: Invoke specific tools through gateway
        - safe_examples: Show validated patterns for any Smithy model (prevents multiple creation)
        - discover: Discover AWS service models for Smithy targets
        - create: Create new gateway only
        - targets: Manage gateway targets (lambda, openapi, smithy)
        - cognito: Setup Cognito OAuth authorization
        - list: List existing gateways and targets
        - delete: Delete gateway resources
        - auth: Get authentication tokens
        """
        if not SDK_AVAILABLE:
            return """X AgentCore SDK Not Available

To use gateway functionality:
1. Install: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`
2. Configure AWS credentials: `aws configure`
3. Retry gateway operations

Alternative: Use AWS Console for gateway management"""

        try:
            import boto3

            # Action: list - List all existing gateways
            if action == 'list':
                try:
                    client = boto3.client('bedrock-agentcore-control', region_name=region)

                    # List all gateways - using correct service and method
                    gateways_response = client.list_gateways()
                    gateways = gateways_response.get('items', [])

                    if not gateways:
                        return f"""# Gateway: No Gateways Found

Region: {region}

## Getting Started:
Create your first gateway:
```python
agent_gateway(action="setup", gateway_name="my-gateway", smithy_model="dynamodb")
```

## Available Smithy Models:
Use `agent_gateway(action="discover")` to see all AWS services available for gateway integration.

## AWS Console:
[Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
"""

                    # Format results
                    result_parts = []
                    result_parts.append('# Gateway: Gateway Resources Found')
                    result_parts.append('                    ')
                    result_parts.append(f'Region: {region}')
                    result_parts.append(f'Total Gateways: {len(gateways)}')
                    result_parts.append('')

                    # List each gateway with management options
                    for gateway in gateways:
                        gateway_name = gateway.get('name', 'unknown')
                        gateway_id = gateway.get('gatewayId', 'unknown')
                        status = gateway.get('status', 'unknown')
                        created_time = gateway.get('createdAt', 'unknown')

                        result_parts.append(f'{gateway_name}:')
                        result_parts.append(f'- ID: `{gateway_id}`')
                        result_parts.append(f'- Status: {status}')
                        result_parts.append(f'- Created: {created_time}')
                        result_parts.append(
                            f'- Delete: `agent_gateway(action="delete", gateway_name="{gateway_name}")`'
                        )

                    result_parts.append('')
                    result_parts.append('## Gateway Operations:')
                    result_parts.append(
                        '- Delete Gateway: `agent_gateway(action="delete", gateway_name="GATEWAY_NAME")` ! Permanent'
                    )
                    result_parts.append(
                        '- Test Gateway: `agent_gateway(action="test", gateway_name="GATEWAY_NAME")`'
                    )
                    result_parts.append('')
                    result_parts.append('## AWS Console Links:')
                    result_parts.append(
                        f'- [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)'
                    )
                    result_parts.append(
                        f'- [Cognito Console](https://console.aws.amazon.com/cognito/v2/home?region={region})'
                    )

                    return '\n'.join(result_parts)

                except Exception as e:
                    return f"""X Gateway List Error: {str(e)}

Region: {region}

Possible Causes:
- AWS credentials not configured
- Insufficient permissions
- AgentCore service not available in region

Troubleshooting:
1. Check credentials: `aws sts get-caller-identity`
2. Verify region: AgentCore available in us-east-1, us-west-2
3. Check permissions: bedrock-agentcore-control:ListGateways"""

            # Action: delete - Delete gateway with robust target cleanup
            elif action == 'delete':
                if not gateway_name:
                    return 'X Error: gateway_name is required for delete action'

                try:
                    client = boto3.client('bedrock-agentcore-control', region_name=region)

                    # Get gateway ID from name
                    gateways = client.list_gateways()['items']
                    gateway_id = None
                    for gw in gateways:
                        if gw.get('name') == gateway_name:
                            gateway_id = gw.get('gatewayId')
                            break

                    if not gateway_id:
                        return f"X Gateway Not Found: No gateway named '{gateway_name}'"

                    deletion_steps = []

                    # Step 1: List all targets first
                    targets = []
                    try:
                        targets_response = client.list_gateway_targets(
                            gatewayIdentifier=gateway_id
                        )
                        targets = targets_response.get('items', [])
                        deletion_steps.append(
                            f'List: Listed gateway targets: {len(targets)} found'
                        )
                    except Exception as targets_error:
                        deletion_steps.append(f'X Could not list targets: {str(targets_error)}')
                        # Continue anyway - maybe there are no targets

                    # Step 2: Delete all targets if any exist - ENHANCED LOGIC WITH THROTTLING PROTECTION
                    if targets:
                        deletion_steps.append(f'Target: Deleting {len(targets)} targets...')

                        # Delete targets one by one with throttling protection
                        remaining_target_ids = [
                            t.get('targetId') for t in targets if t.get('targetId')
                        ]
                        max_deletion_attempts = 5

                        for attempt in range(max_deletion_attempts):
                            deletion_steps.append(
                                f'Retry: Deletion attempt {attempt + 1}/{max_deletion_attempts}'
                            )

                            # Track which targets were successfully deleted in this attempt
                            successfully_deleted = []

                            for target_id in remaining_target_ids:
                                target_name = next(
                                    (
                                        t.get('name', 'unknown')
                                        for t in targets
                                        if t.get('targetId') == target_id
                                    ),
                                    'unknown',
                                )

                                try:
                                    deletion_steps.append(
                                        f'Delete: Deleting target: {target_name} ({target_id})'
                                    )
                                    client.delete_gateway_target(
                                        gatewayIdentifier=gateway_id, targetId=target_id
                                    )
                                    deletion_steps.append(
                                        f'OK Successfully deleted target: {target_name}'
                                    )
                                    successfully_deleted.append(target_id)

                                    # Add small delay between deletions to avoid throttling
                                    time.sleep(2)

                                except Exception as target_error:
                                    error_msg = str(target_error).lower()
                                    if 'throttling' in error_msg or 'rate' in error_msg:
                                        deletion_steps.append(
                                            f'Throttling: Throttling detected for {target_name}, will retry after delay'
                                        )
                                        # Wait longer for throttling
                                        time.sleep(10)
                                    elif 'not found' in error_msg or 'does not exist' in error_msg:
                                        deletion_steps.append(
                                            f'OK Target {target_name} already deleted'
                                        )
                                        successfully_deleted.append(target_id)
                                    else:
                                        deletion_steps.append(
                                            f'X Failed to delete target {target_name}: {str(target_error)}'
                                        )

                            # Remove successfully deleted targets from remaining list
                            remaining_target_ids = [
                                tid
                                for tid in remaining_target_ids
                                if tid not in successfully_deleted
                            ]

                            if not remaining_target_ids:
                                deletion_steps.append('OK All targets successfully deleted')
                                break

                            # If we still have targets remaining, wait before next attempt
                            if attempt < max_deletion_attempts - 1:
                                wait_time = min(
                                    30, (attempt + 1) * 10
                                )  # Exponential backoff, max 30s
                                deletion_steps.append(
                                    f'Wait: {len(remaining_target_ids)} targets remaining. Waiting {wait_time} seconds before retry...'
                                )
                                time.sleep(wait_time)

                                # Double-check which targets still exist
                                try:
                                    verify_response = client.list_gateway_targets(
                                        gatewayIdentifier=gateway_id
                                    )
                                    current_targets = verify_response.get('items', [])
                                    current_target_ids = [
                                        t.get('targetId')
                                        for t in current_targets
                                        if t.get('targetId')
                                    ]

                                    # Only retry targets that actually still exist
                                    remaining_target_ids = [
                                        tid
                                        for tid in remaining_target_ids
                                        if tid in current_target_ids
                                    ]

                                    if not remaining_target_ids:
                                        deletion_steps.append(
                                            'OK All targets confirmed deleted via verification'
                                        )
                                        break

                                    deletion_steps.append(
                                        f'List: Verified {len(remaining_target_ids)} targets still exist'
                                    )

                                except Exception as verify_error:
                                    deletion_steps.append(
                                        f'! Could not verify remaining targets: {str(verify_error)}'
                                    )

                        # Final check - if targets still remain after all attempts
                        if remaining_target_ids:
                            # Get final list of what actually still exists
                            try:
                                final_verify_response = client.list_gateway_targets(
                                    gatewayIdentifier=gateway_id
                                )
                                final_remaining_targets = final_verify_response.get('items', [])
                                final_remaining_ids = [
                                    t.get('targetId')
                                    for t in final_remaining_targets
                                    if t.get('targetId')
                                ]

                                if not final_remaining_ids:
                                    deletion_steps.append(
                                        'OK Final verification: All targets successfully deleted'
                                    )
                                else:
                                    # Return detailed error for manual intervention
                                    deletion_steps.append(
                                        f'X {len(final_remaining_ids)} targets could not be deleted after {max_deletion_attempts} attempts'
                                    )

                                    return f"""X Gateway Deletion Failed - Targets Still Exist

Gateway: `{gateway_name}` ({gateway_id})
Issue: {len(final_remaining_ids)} targets could not be deleted after {max_deletion_attempts} attempts with throttling protection

## Deletion Steps Attempted:
{chr(10).join(f'- {step}' for step in deletion_steps)}

## Remaining Targets:
{chr(10).join(f'- {t.get("name", "unknown")} (ID: `{t.get("targetId", "no-id")}`)' for t in final_remaining_targets)}

## This indicates a persistent AWS issue. Try:
1. Wait 10-15 minutes for AWS to fully process deletions
2. Use AWS Console to manually delete targets
3. Contact AWS Support if targets cannot be deleted manually

AWS Console: [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)"""

                            except Exception as final_verify_error:
                                deletion_steps.append(
                                    f'X Could not perform final verification: {str(final_verify_error)}'
                                )
                                return f"""X Gateway Deletion Failed - Cannot Verify Final State

Gateway: `{gateway_name}` ({gateway_id})
Issue: Cannot verify target deletion status after {max_deletion_attempts} attempts

## Deletion Steps Attempted:
{chr(10).join(f'- {step}' for step in deletion_steps)}

Verification Error: {str(final_verify_error)}

Manual Action Required: Use AWS Console to check and complete deletion"""
                    else:
                        deletion_steps.append('Info: No targets to delete')

                    # Step 3: Delete the gateway itself with retry logic
                    gateway_deletion_attempts = 3
                    # gateway_deleted = False

                    for gateway_attempt in range(gateway_deletion_attempts):
                        try:
                            deletion_steps.append(
                                f'Delete: Attempting to delete gateway: {gateway_name} (attempt {gateway_attempt + 1}/{gateway_deletion_attempts})'
                            )
                            client.delete_gateway(gatewayIdentifier=gateway_id)
                            deletion_steps.append('Gateway deletion successful')
                            # gateway_deleted = True

                            break

                        except Exception as delete_error:
                            error_msg = str(delete_error).lower()

                            if 'throttling' in error_msg or 'rate' in error_msg:
                                deletion_steps.append(
                                    'Throttling: Gateway deletion throttled, waiting before retry...'
                                )
                                if gateway_attempt < gateway_deletion_attempts - 1:
                                    wait_time = (gateway_attempt + 1) * 15  # 15, 30 seconds
                                    time.sleep(wait_time)
                                    continue
                            elif 'targets associated' in error_msg:
                                deletion_steps.append(
                                    'X Gateway still has associated targets - this should not happen after target cleanup'
                                )
                                # Wait a bit longer and try once more
                                if gateway_attempt < gateway_deletion_attempts - 1:
                                    deletion_steps.append(
                                        'Wait: Waiting 30 seconds for AWS to fully process target deletions...'
                                    )
                                    time.sleep(30)
                                    continue

                            deletion_steps.append(
                                f'X Gateway deletion attempt {gateway_attempt + 1} failed: {str(delete_error)}'
                            )

                            if gateway_attempt == gateway_deletion_attempts - 1:
                                # Final attempt failed
                                return f"""X Gateway Deletion Failed

Gateway: `{gateway_name}` ({gateway_id})
Region: {region}

## Deletion Steps Attempted:
{chr(10).join(f'- {step}' for step in deletion_steps)}

Final Error: {str(delete_error)}

Possible Causes:
- AWS service temporary issues
- Network connectivity problems
- Insufficient permissions for gateway deletion
- Targets may still be processing deletion

Troubleshooting:
1. Wait 10-15 minutes and retry: AWS may need more time to process target deletions
2. Check AWS Console: [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
3. Verify permissions: Ensure your AWS role has `bedrock-agentcore-control:DeleteGateway` permission
4. Retry deletion: `agent_gateway(action="delete", gateway_name="{gateway_name}")`

If problem persists, this may be an AWS service issue."""

                    # Success case - gateway was deleted
                    return f"""# OK Gateway Deleted Successfully

## Deleted Gateway:
- Name: `{gateway_name}`
- ID: `{gateway_id}`
- Status: Deleted
- Region: {region}

## Deletion Steps:
{chr(10).join(f'- {step}' for step in deletion_steps)}

## ! Important Notes:
- Deletion is permanent and cannot be undone
- All gateway targets have been automatically deleted
- Any agents using this gateway will lose access to tools
- Cognito resources may still exist - check Cognito console if cleanup needed
- IAM roles may still exist - check IAM console if cleanup needed

## Next Steps:
- Update any agents that were using this gateway
- Remove gateway references from agent code
- Create new gateway if needed: `agent_gateway(action="setup", gateway_name="new_name")`

## AWS Console Links:
- [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
- [Cognito Console](https://console.aws.amazon.com/cognito/v2/home?region={region})
- [IAM Console](https://console.aws.amazon.com/iam/home?region={region}#/roles)

Gateway `{gateway_name}` has been completely removed from your AWS account."""

                except Exception as e:
                    return f"""X Gateway Deletion Error: {str(e)}

Gateway: `{gateway_name}`
Region: {region}

Possible Causes:
- Gateway doesn't exist or was already deleted
- AWS credentials not configured
- Network connectivity issues
- Insufficient permissions

Check Status: `agent_gateway(action="list")` to see available gateways"""

            # Action: discover - Dynamically discover available AWS services for Smithy models
            elif action == 'discover':
                try:
                    # Get live data from GitHub API
                    discovered_services = await _discover_smithy_models()

                    # Check for errors
                    if 'error' in discovered_services:
                        return f"""X Service Discovery Failed

Error: {discovered_services['error']}

## Fallback - Common Services:
Use these well-known AWS services while discovery is unavailable:

Popular Services: `dynamodb`, `s3`, `lambda`, `ec2`, `iam`, `sts`
Storage: `s3`, `efs`, `fsx`
Database: `dynamodb`, `rds`, `redshift`
Compute: `lambda`, `ec2`, `ecs`
Security: `iam`, `sts`, `cognito-idp`

## Manual Check:
Visit: https://github.com/aws/api-models-aws/tree/main/models

## Usage:
```python
agent_gateway(action="setup", gateway_name="my-gateway", smithy_model="dynamodb")
```"""

                    # Format the discovered services
                    result_parts = []
                    result_parts.append('# Search: AWS Service Discovery - Live Results')
                    result_parts.append('')
                    result_parts.append('Network: Source: GitHub AWS API Models Repository (Live)')
                    result_parts.append(
                        f'Target: Total Services Found: {sum(len(services) for services in discovered_services.values())}'
                    )
                    result_parts.append('')

                    # Add each category
                    for category, services in discovered_services.items():
                        if services:  # Only show categories with services
                            result_parts.append(f'### {category} ({len(services)} services):')
                            for service in services:
                                result_parts.append(
                                    f'- {service["name"]} - {service["description"]}'
                                )
                            result_parts.append('')

                    # Add usage examples
                    result_parts.append('## Usage Examples:')
                    result_parts.append('')

                    # Find popular services for examples
                    all_services = []
                    for services in discovered_services.values():
                        all_services.extend([s['name'] for s in services])

                    popular = ['dynamodb', 's3', 'lambda', 'ec2', 'iam']
                    available_popular = [s for s in popular if s in all_services]

                    if available_popular:
                        for service in available_popular[:3]:  # Show top 3
                            result_parts.append(f'### Create {service.upper()} Gateway:')
                            result_parts.append('```python')
                            result_parts.append('agent_gateway(')
                            result_parts.append('    action="setup",')
                            result_parts.append(f'    gateway_name="my-{service}-gateway",')
                            result_parts.append(f'    smithy_model="{service}"')
                            result_parts.append(')')
                            result_parts.append('```')
                            result_parts.append('')

                    # Add OpenAPI example
                    result_parts.append('### Create OpenAPI Gateway:')
                    result_parts.append('```python')
                    result_parts.append('agent_gateway(')
                    result_parts.append('    action="setup",')
                    result_parts.append('    gateway_name="my-api-gateway",')
                    result_parts.append('    openapi_spec=your_openapi_spec,')
                    result_parts.append('    api_key="your-api-key"')  # pragma: allowlist secret
                    result_parts.append(')')
                    result_parts.append('```')
                    result_parts.append('')

                    result_parts.append('## Model Names:')
                    result_parts.append('- Use exact names from the list above')
                    result_parts.append('- Names are case-sensitive (use lowercase)')
                    result_parts.append("- Some services use hyphens (e.g., 'cognito-idp')")
                    result_parts.append('')

                    result_parts.append('## Next Steps:')
                    result_parts.append('```python')
                    result_parts.append('# Choose any service from above and create gateway')
                    result_parts.append(
                        'agent_gateway(action="setup", gateway_name="my-gateway", smithy_model="SERVICE_NAME")'
                    )
                    result_parts.append('```')
                    result_parts.append('')
                    result_parts.append(
                        'OK All services shown are verified to exist in the AWS API models repository!'
                    )

                    return '\n'.join(result_parts)

                except Exception as e:
                    return f"""X Discovery Error: {str(e)}

## Fallback - Manual List:
While discovery is unavailable, use these verified services:

Most Popular: `dynamodb`, `s3`, `lambda`, `ec2`, `iam`
Storage: `s3`, `efs`, `fsx`, `glacier`
Database: `dynamodb`, `rds`, `redshift`, `timestream-query`
Compute: `lambda`, `ec2`, `ecs`, `batch`
Security: `iam`, `sts`, `cognito-idp`, `secretsmanager`
Networking: `vpc`, `route53`, `apigateway`
Monitoring: `cloudwatch`, `logs`, `xray`

## Manual Discovery:
Visit: https://github.com/aws/api-models-aws/tree/main/models

## Usage:
```python
agent_gateway(action="setup", gateway_name="my-gateway", smithy_model="dynamodb")
```"""

            # Action: setup - Complete gateway setup workflow (the comprehensive approach)
            elif action == 'setup':
                if not gateway_name:
                    return """X Error: gateway_name is required for setup action

Example:
```python
agent_gateway(action="setup", gateway_name="my-gateway", smithy_model="dynamodb")
```"""

                if not RUNTIME_AVAILABLE:
                    return """X Starter Toolkit Not Available

To use complete gateway setup:
1. Install: `uv add bedrock-agentcore-starter-toolkit`
2. Configure AWS credentials
3. Retry setup

Alternative: Use individual actions (create, targets, cognito)"""

                try:
                    # Use the starter toolkit GatewayClient for complete setup
                    from bedrock_agentcore_starter_toolkit.operations.gateway.client import (
                        GatewayClient,
                    )

                    setup_steps = []
                    setup_results = {}

                    # Initialize GatewayClient object
                    client = GatewayClient(region_name=region)
                    setup_steps.append('OK GatewayClient initialized')

                    # Step 1: Create Cognito OAuth authorizer
                    setup_steps.append('Security: Step 1: Setting up Cognito OAuth...')
                    cognito_result = None
                    try:
                        cognito_result = client.create_oauth_authorizer_with_cognito(gateway_name)
                        setup_results['cognito'] = cognito_result
                        setup_steps.append('OK Cognito OAuth setup complete')

                        # Store cognito info for later use
                        client_info = cognito_result.get('client_info', {})
                        if client_info:
                            # Save configuration for token generation
                            config_dir = os.path.expanduser('~/.agentcore_gateways')
                            os.makedirs(config_dir, exist_ok=True)
                            config_file = os.path.join(config_dir, f'{gateway_name}.json')

                            gateway_config = {
                                'gateway_name': gateway_name,
                                'region': region,
                                'cognito_client_info': client_info,
                                'created_at': str(time.time()),
                            }

                            with open(config_file, 'w') as f:
                                json.dump(gateway_config, f, indent=2, default=str)

                            setup_steps.append(f'Config: Configuration saved: {config_file}')

                    except Exception as cognito_error:
                        setup_steps.append(f'X Cognito setup failed: {str(cognito_error)}')
                        # Continue with gateway creation anyway

                    # Step 2: Create gateway
                    setup_steps.append('Gateway: Step 2: Creating gateway...')

                    try:
                        # Create gateway using GatewayClient with proper parameters
                        gateway_result = client.create_mcp_gateway(
                            name=gateway_name,
                            role_arn=None,  # Let it auto-create
                            authorizer_config=cognito_result.get('authorizer_config')
                            if cognito_result
                            else None,
                            enable_semantic_search=enable_semantic_search,
                        )
                        setup_results['gateway'] = gateway_result
                        setup_steps.append('OK Gateway creation complete')

                    except Exception as gateway_error:
                        setup_steps.append(f'X Gateway creation failed: {str(gateway_error)}')
                        return f"""X Gateway Setup Failed

## Setup Steps Attempted:
{chr(10).join(f'- {step}' for step in setup_steps)}

Gateway Creation Error: {str(gateway_error)}

Troubleshooting:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify permissions for bedrock-agentcore-control
3. Try individual setup steps manually
4. Check AWS Console for partial resources"""

                    # Step 3: Add targets if specified
                    if smithy_model or openapi_spec:
                        setup_steps.append('Target: Step 3: Adding targets...')

                        try:
                            if smithy_model:
                                # Complete Smithy model workflow:
                                # 1. Search GitHub API models repo
                                # 2. Download JSON model
                                # 3. Upload to S3
                                # 4. Create target with S3 URI

                                setup_steps.append(
                                    f'Search: Searching for {smithy_model} Smithy model in GitHub...'
                                )

                                try:
                                    # Search for the Smithy model in AWS API models repository
                                    smithy_s3_uri = await _find_and_upload_smithy_model(
                                        smithy_model, region, setup_steps
                                    )

                                    if not smithy_s3_uri:
                                        raise Exception(
                                            f'Could not find or upload Smithy model for {smithy_model}'
                                        )

                                    setup_steps.append(
                                        f'OK Smithy model uploaded to: {smithy_s3_uri}'
                                    )

                                    # Create proper smithy model configuration with S3 URI
                                    smithy_target_config = {'s3': {'uri': smithy_s3_uri}}

                                    setup_steps.append(
                                        'Target: Creating Smithy target with S3 URI...'
                                    )

                                    target_result = client.create_mcp_gateway_target(
                                        gateway=gateway_result,
                                        name=target_name or f'{smithy_model}-target',
                                        target_type='smithyModel',
                                        target_payload=smithy_target_config,
                                    )

                                except Exception as smithy_error:
                                    setup_steps.append(
                                        f'X Smithy model setup failed: {str(smithy_error)}'
                                    )
                                    # Continue without target - gateway still created
                                    return f"""! Gateway Created with Warnings

## Setup Steps:
{chr(10).join(f'- {step}' for step in setup_steps)}

Gateway `{gateway_name}` was created but Smithy target setup failed.

Error: {str(smithy_error)}

Manual Steps to Add Target:
1. Download Smithy model from: https://github.com/aws/api-models-aws/tree/main/models/{smithy_model}
2. Upload to S3 bucket
3. Use AWS Console to add target with S3 URI

Gateway URL: Check AWS Console for connection details"""
                                setup_results['target'] = target_result
                                setup_steps.append(
                                    f"OK Smithy target '{smithy_model}' added successfully"
                                )

                            elif openapi_spec:
                                # Complete OpenAPI workflow:
                                # 1. Upload OpenAPI schema to S3
                                # 2. Configure API key credentials if provided
                                # 3. Create target with S3 URI and credentials

                                setup_steps.append(
                                    f'Document: Processing OpenAPI schema for {gateway_name}...'
                                )

                                try:
                                    # Upload OpenAPI schema and configure credentials
                                    openapi_result = await _upload_openapi_schema(
                                        openapi_spec=openapi_spec,
                                        gateway_name=gateway_name,
                                        region=region,
                                        setup_steps=setup_steps,
                                        api_key=api_key,
                                        credential_location=credential_location,
                                        credential_parameter_name=credential_parameter_name,
                                    )

                                    if not openapi_result:
                                        raise Exception(
                                            'Could not upload OpenAPI schema or configure credentials'
                                        )

                                    setup_steps.append(
                                        f'OK OpenAPI schema uploaded to: {openapi_result["s3_uri"]}'
                                    )

                                    # Create proper OpenAPI target configuration
                                    openapi_target_config = {
                                        's3': {'uri': openapi_result['s3_uri']}
                                    }

                                    # Prepare credentials configuration
                                    credentials_config = []
                                    if openapi_result['credential_config']:
                                        credentials_config.append(
                                            openapi_result['credential_config']
                                        )
                                        setup_steps.append(
                                            'Security: API key credentials configured'
                                        )

                                    setup_steps.append(
                                        'Target: Creating OpenAPI target with S3 URI...'
                                    )

                                    target_result = client.create_mcp_gateway_target(
                                        gateway=gateway_result,
                                        name=target_name or 'openapi-target',
                                        target_type='openApiSchema',
                                        target_payload=openapi_target_config,
                                        credentials=credentials_config
                                        if credentials_config
                                        else None,
                                    )

                                except Exception as openapi_error:
                                    setup_steps.append(
                                        f'X OpenAPI target setup failed: {str(openapi_error)}'
                                    )
                                    # Continue without target - gateway still created
                                    return f"""! Gateway Created with Warnings

## Setup Steps:
{chr(10).join(f'- {step}' for step in setup_steps)}

Gateway `{gateway_name}` was created but OpenAPI target setup failed.

Error: {str(openapi_error)}

Manual Steps to Add Target:
1. Upload OpenAPI schema to S3 bucket
2. Configure API key credentials if needed
3. Use AWS Console to add target with S3 URI

Gateway URL: Check AWS Console for connection details"""

                                setup_results['target'] = target_result
                                setup_steps.append('OK OpenAPI target added successfully')

                        except Exception as target_error:
                            setup_steps.append(f'X Target setup failed: {str(target_error)}')
                            # Gateway still created, just note the target failure

                    # Step 4: Generate access token
                    setup_steps.append('Security: Step 4: Generating access token...')

                    try:
                        if cognito_result and 'client_info' in cognito_result:
                            access_token = client.get_access_token_for_cognito(
                                cognito_result['client_info']
                            )
                        else:
                            setup_steps.append(
                                '! Cannot generate access token: Cognito setup failed'
                            )
                            access_token = None
                        setup_results['access_token'] = access_token
                        setup_steps.append('OK Access token generated successfully')
                    except Exception as token_error:
                        setup_steps.append(f'! Token generation failed: {str(token_error)}')
                        # Continue without token for now

                    # Step 5: Wait for gateway to be ready
                    setup_steps.append('Wait: Step 5: Waiting for gateway to be ready...')

                    max_wait_time = 120  # 2 minutes
                    wait_start = time.time()

                    while time.time() - wait_start < max_wait_time:
                        try:
                            # Use the existing client's boto3 client for status checks
                            gateway_status = client.client.get_gateway(
                                gatewayIdentifier=gateway_result['gateway']['gatewayId']
                            )

                            status = gateway_status.get('status', 'UNKNOWN')
                            setup_steps.append(f'Status: Gateway status: {status}')

                            if status == 'READY':
                                setup_steps.append('OK Gateway is ready!')
                                break
                            elif 'FAILED' in status:
                                setup_steps.append(f'X Gateway setup failed with status: {status}')
                                break

                            time.sleep(10)

                        except Exception as status_error:
                            setup_steps.append(f'! Status check failed: {str(status_error)}')
                            break
                    else:
                        setup_steps.append(
                            'Time: Gateway still initializing - may take a few more minutes'
                        )

                    # Generate success response
                    return f"""# Gateway: Gateway Setup Complete!

## Setup Steps:
{chr(10).join(f'- {step}' for step in setup_steps)}

## Gateway Information:
- Name: `{gateway_name}`
- Region: `{region}`
- Semantic Search: {'Enabled' if enable_semantic_search else 'Disabled'}
{f'- Smithy Model: `{smithy_model}`' if smithy_model else ''}
{'- Targets: OpenAPI specification added' if openapi_spec else ''}

## Next Steps:

### 1. Get Access Token:
```python
get_oauth_access_token(method="gateway_client", gateway_name="{gateway_name}")
```

### 2. Test Gateway:
```python
agent_gateway(action="test", gateway_name="{gateway_name}")
```

### 3. List Available Tools:
```python
agent_gateway(action="list_tools", gateway_name="{gateway_name}")
```

## AWS Console:
- [Gateway Management](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
- [Cognito OAuth](https://console.aws.amazon.com/cognito/v2/home?region={region})

Your gateway is ready for MCP client connections! Success!"""

                except Exception as e:
                    return f"""X Gateway Setup Error: {str(e)}

Gateway Name: `{gateway_name}`
Region: {region}

Troubleshooting:
1. Check bedrock-agentcore-starter-toolkit installation
2. Verify AWS credentials and permissions
3. Try individual setup actions for debugging
4. Check AWS Console for partial resources"""

            # Action: test - Test gateway with MCP functionality
            elif action == 'test':
                if not gateway_name:
                    return 'X Error: gateway_name is required for test action'

                return f"""# Test: Gateway MCP Testing

## Gateway: `{gateway_name}`

## Testing Steps:

### 1. Get Access Token:
```python
get_oauth_access_token(method="gateway_client", gateway_name="{gateway_name}")
```

### 2. List Available Tools:
```python
agent_gateway(action="list_tools", gateway_name="{gateway_name}")
```

### 3. Search Tools (if semantic search enabled):
```python
agent_gateway(action="search_tools", gateway_name="{gateway_name}", query="database operations")
```

### 4. Invoke Specific Tool:
```python
agent_gateway(
    action="invoke_tool",
    gateway_name="{gateway_name}",
    tool_name="DescribeTable",
    tool_arguments={{"TableName": "MyTable"}}
)
```

## MCP Client Example:
```python
from mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# Get gateway URL from AWS Console
gateway_url = "https://gateway-id.bedrock-agentcore.{region}.amazonaws.com/mcp"

# Get access token first
access_token = "YOUR_ACCESS_TOKEN"

client = MCPClient(
    lambda: streamablehttp_client(
        gateway_url,
        headers={{"Authorization": f"Bearer {{access_token}}"}}
    )
)

with client:
    # List tools
    tools = client.list_tools_sync()
    print([tool.tool_name for tool in tools])

    # Invoke tool
    result = client.call_tool_sync("DescribeTable", {{"TableName": "MyTable"}})
    print(result)
```

## Manual Testing:
```bash
# Get gateway endpoint from AWS Console first
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
     https://gateway-id.bedrock-agentcore.{region}.amazonaws.com/mcp/tools
```

Complete these steps to fully test your gateway's MCP functionality."""

            # Action: list_tools - List available tools from gateway via MCP protocol
            elif action == 'list_tools':
                if not gateway_name:
                    return 'X Error: gateway_name is required for list_tools action'

                try:
                    # Load gateway configuration
                    config_dir = Path.home() / '.agentcore_gateways'
                    config_file = config_dir / f'{gateway_name}.json'

                    if not config_file.exists():
                        return f"""X Gateway Configuration Not Found

Gateway: `{gateway_name}`
Expected Config: `{config_file}`

Solutions:
1. Check gateway name: `agent_gateway(action="list")`
2. Recreate configuration: `agent_gateway(action="setup", gateway_name="{gateway_name}")`"""

                    with open(config_file, 'r') as f:
                        config = json.load(f)

                    # Get access token
                    from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

                    gateway_client = GatewayClient(region_name=region)
                    client_info = config.get('client_info') or config.get('cognito_client_info')
                    access_token = gateway_client.get_access_token_for_cognito(client_info)

                    # Get gateway details using boto3 API directly
                    try:
                        boto3_client = boto3.client(
                            'bedrock-agentcore-control', region_name=region
                        )

                        # First try with gateway name
                        try:
                            response = boto3_client.get_gateway(gatewayIdentifier=gateway_name)
                            gateway_url = response['gatewayUrl']
                        except Exception:
                            # Try to find gateway ID using list_gateways, then use get_gateway
                            gateway_id = None
                            paginator = boto3_client.get_paginator('list_gateways')
                            for page in paginator.paginate():
                                for gateway in page.get('items', []):
                                    if gateway.get('name') == gateway_name:
                                        gateway_id = gateway.get('gatewayId')
                                        break
                                if gateway_id:
                                    break

                            if gateway_id:
                                response = boto3_client.get_gateway(gatewayIdentifier=gateway_id)
                                gateway_url = response['gatewayUrl']
                            else:
                                raise Exception(f"Gateway '{gateway_name}' not found")

                    except Exception as e:
                        return f"""X Failed to get gateway details: {str(e)}

Gateway: `{gateway_name}`
Region: {region}

Possible Solutions:
1. Check gateway exists: `agent_gateway(action="list")`
2. Verify AWS permissions for bedrock-agentcore:GetGateway
3. Ensure gateway name is correct"""

                    # Use MCP client to list tools (following working Strands example)
                    from mcp.client.streamable_http import streamablehttp_client
                    from strands.tools.mcp.mcp_client import MCPClient

                    def create_streamable_http_transport(mcp_url: str, access_token: str):
                        return streamablehttp_client(
                            mcp_url, headers={'Authorization': f'Bearer {access_token}'}
                        )

                    def get_full_tools_list(client):
                        more_tools = True
                        tools = []
                        pagination_token = None
                        while more_tools:
                            tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
                            tools.extend(tmp_tools)
                            if tmp_tools.pagination_token is None:
                                more_tools = False
                            else:
                                more_tools = True
                                pagination_token = tmp_tools.pagination_token
                        return tools

                    # Create MCP client and get tools
                    mcp_client = MCPClient(
                        lambda: create_streamable_http_transport(gateway_url, access_token)
                    )

                    with mcp_client:
                        tools = get_full_tools_list(mcp_client)
                        tool_names = [tool.tool_name for tool in tools]

                        tool_details = []
                        for tool in tools:
                            tool_details.append(
                                {
                                    'name': tool.tool_name,
                                    'description': getattr(
                                        tool, 'description', 'No description available'
                                    ),
                                    'input_schema': getattr(tool, 'input_schema', {}),
                                }
                            )

                    return f"""# Tools: Gateway Tools List

## Gateway: `{gateway_name}`
Total Tools: {len(tools)}
Gateway URL: `{gateway_url}`

## Available Tools:
{chr(10).join([f'- {tool["name"]}: {tool["description"]}' for tool in tool_details])}

## Tool Names Only:
```
{tool_names}
```

## Usage Example:
```python
# Invoke a tool
agent_gateway(
    action="invoke_tool",
    gateway_name="{gateway_name}",
    tool_name="ListTables",  # Example DynamoDB tool
    tool_arguments={{}}
)
```

OK Gateway is ready for MCP tool invocation!"""

                except Exception as e:
                    return f"""X Failed to List Tools: {str(e)}

Gateway: `{gateway_name}`
Region: {region}

Possible Solutions:
1. Check gateway exists: `agent_gateway(action="list")`
2. Verify AWS credentials
3. Ensure gateway is in READY state
4. Get new access token if expired"""

            # Action: search_tools - Semantic search for tools through gateway
            elif action == 'search_tools':
                if not gateway_name:
                    return 'X Error: gateway_name is required for search_tools action'
                if not query:
                    return 'X Error: query is required for search_tools action'

                try:
                    # Use the built-in semantic search tool directly
                    # Load gateway configuration for proper tool invocation
                    config_dir = Path.home() / '.agentcore_gateways'
                    config_file = config_dir / f'{gateway_name}.json'

                    if not config_file.exists():
                        return f"""X Gateway Configuration Not Found

Gateway: `{gateway_name}`
Expected Config: `{config_file}`

Solutions:
1. Check gateway name: `agent_gateway(action="list")`
2. Recreate configuration: `agent_gateway(action="setup", gateway_name="{gateway_name}")`"""

                    with open(config_file, 'r') as f:
                        config = json.load(f)

                    # Get access token
                    from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

                    gateway_client = GatewayClient(region_name=region)
                    client_info = config.get('client_info') or config.get('cognito_client_info')
                    access_token = gateway_client.get_access_token_for_cognito(client_info)

                    # Get gateway details
                    boto3_client = boto3.client('bedrock-agentcore-control', region_name=region)
                    gateway_id = None
                    paginator = boto3_client.get_paginator('list_gateways')
                    for page in paginator.paginate():
                        for gateway in page.get('items', []):
                            if gateway.get('name') == gateway_name:
                                gateway_id = gateway.get('gatewayId')
                                break
                        if gateway_id:
                            break

                    if not gateway_id:
                        return f"X Gateway '{gateway_name}' not found"

                    response = boto3_client.get_gateway(gatewayIdentifier=gateway_id)
                    gateway_url = response['gatewayUrl']

                    # Use MCP client to invoke the search tool
                    from mcp.client.streamable_http import streamablehttp_client
                    from strands.tools.mcp.mcp_client import MCPClient

                    def create_transport(mcp_url: str, token: str):
                        return streamablehttp_client(
                            mcp_url, headers={'Authorization': f'Bearer {token}'}
                        )

                    mcp_client = MCPClient(lambda: create_transport(gateway_url, access_token))

                    with mcp_client:
                        result = mcp_client.call_tool_sync(
                            tool_use_id=f'search-{gateway_name}-{int(time.time())}',
                            name='x_amz_bedrock_agentcore_search',
                            arguments={'query': query},
                        )

                    # Parse the structured content from the result
                    tools_data = []
                    if (
                        hasattr(result, 'get')
                        and result.get('structuredContent')
                        and result.get('structuredContent', {}).get('tools')
                    ):
                        # Direct access to structured content
                        tools_data = result.get('structuredContent', {}).get('tools', [])
                    elif 'structuredContent' in str(result):
                        # Try to extract from string representation
                        import re

                        tool_matches = re.findall(r'dynamodb-target___\w+', str(result))
                        tools_data = [
                            {'name': tool, 'description': 'Found via semantic search'}
                            for tool in set(tool_matches)
                        ]

                    # Format the results
                    if tools_data:
                        matching_tools = []
                        for tool in tools_data:
                            name = tool.get('name', 'Unknown')
                            desc = tool.get('description', 'No description available')
                            # Truncate long descriptions
                            if len(desc) > 200:
                                desc = desc[:200] + '...'
                            matching_tools.append(f'- {name}: {desc}')
                    else:
                        matching_tools = ['No tools found matching your search query.']

                    return f"""# Search: Gateway Semantic Search Results

## Gateway: `{gateway_name}`
Search Query: `{query}`
Matches Found: {len(tools_data)}
Search Method: Built-in semantic search (x_amz_bedrock_agentcore_search)

## Matching Tools:
{chr(10).join(matching_tools)}

## Usage Example:
```python
# Invoke a matching tool
agent_gateway(
    action="invoke_tool",
    gateway_name="{gateway_name}",
    tool_name="TOOL_NAME_FROM_RESULTS",
    tool_arguments={{"key": "value"}}
)
```

Note: This uses the gateway's built-in semantic search for highly accurate, context-aware results"""

                except Exception as e:
                    return f"""X Search Failed: {str(e)}

Gateway: `{gateway_name}`
Query: `{query}`

Try: `agent_gateway(action="list_tools", gateway_name="{gateway_name}")` first"""

            # Action: invoke_tool - Invoke specific tools through gateway
            elif action == 'invoke_tool':
                if not gateway_name:
                    return 'X Error: gateway_name is required for invoke_tool action'
                if not tool_name:
                    return 'X Error: tool_name is required for invoke_tool action'

                try:
                    # Load gateway configuration
                    config_dir = Path.home() / '.agentcore_gateways'
                    config_file = config_dir / f'{gateway_name}.json'

                    if not config_file.exists():
                        return f"""X Gateway Configuration Not Found

Gateway: `{gateway_name}`
Expected Config: `{config_file}`

Solutions:
1. Check gateway name: `agent_gateway(action="list")`
2. Recreate configuration: `agent_gateway(action="setup", gateway_name="{gateway_name}")`"""

                    with open(config_file, 'r') as f:
                        config = json.load(f)

                    # Get access token
                    from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

                    gateway_client = GatewayClient(region_name=region)
                    client_info = config.get('client_info') or config.get('cognito_client_info')
                    access_token = gateway_client.get_access_token_for_cognito(client_info)

                    # Get gateway details using boto3 API directly
                    try:
                        boto3_client = boto3.client(
                            'bedrock-agentcore-control', region_name=region
                        )

                        # First try with gateway name
                        try:
                            response = boto3_client.get_gateway(gatewayIdentifier=gateway_name)
                            gateway_url = response['gatewayUrl']
                        except Exception:
                            # Try to find gateway ID using list_gateways, then use get_gateway
                            gateway_id = None
                            paginator = boto3_client.get_paginator('list_gateways')
                            for page in paginator.paginate():
                                for gateway in page.get('items', []):
                                    if gateway.get('name') == gateway_name:
                                        gateway_id = gateway.get('gatewayId')
                                        break
                                if gateway_id:
                                    break

                            if gateway_id:
                                response = boto3_client.get_gateway(gatewayIdentifier=gateway_id)
                                gateway_url = response['gatewayUrl']
                            else:
                                raise Exception(f"Gateway '{gateway_name}' not found")

                    except Exception as e:
                        return f"""X Failed to get gateway details: {str(e)}

Gateway: `{gateway_name}`
Region: {region}

Possible Solutions:
1. Check gateway exists: `agent_gateway(action="list")`
2. Verify AWS permissions for bedrock-agentcore:GetGateway
3. Ensure gateway name is correct"""

                    # Use MCP client to invoke tool (following working Strands example)
                    from mcp.client.streamable_http import streamablehttp_client
                    from strands.tools.mcp.mcp_client import MCPClient

                    def create_streamable_http_transport(mcp_url: str, access_token: str):
                        return streamablehttp_client(
                            mcp_url, headers={'Authorization': f'Bearer {access_token}'}
                        )

                    # Create MCP client and invoke tool
                    mcp_client = MCPClient(
                        lambda: create_streamable_http_transport(gateway_url, access_token)
                    )

                    with mcp_client:
                        args = tool_arguments or {}
                        # Use the correct AgentCore format for call_tool_sync
                        result = mcp_client.call_tool_sync(
                            tool_use_id=f'gateway-{gateway_name}-{tool_name}-{int(time.time())}',
                            name=tool_name,
                            arguments=args,
                        )

                    # Format the result nicely
                    result_content = (
                        result.get('content') if hasattr(result, 'get') else str(result)
                    )

                    return f"""# Tool: Tool Invocation Result

## Gateway: `{gateway_name}`
Tool: `{tool_name}`
Arguments: `{args}`

## Result:
```json
{json.dumps(result_content, indent=2) if isinstance(result_content, (dict, list)) else result_content}
```

## Status: OK Success

## Next Steps:
- Try other tools: `agent_gateway(action="list_tools", gateway_name="{gateway_name}")`
- Search tools: `agent_gateway(action="search_tools", gateway_name="{gateway_name}", query="your_query")`"""

                except Exception as e:
                    return f"""X Tool Invocation Failed: {str(e)}

Gateway: `{gateway_name}`
Tool: `{tool_name}`
Arguments: `{tool_arguments or {}}`

Possible Solutions:
1. Check tool exists: `agent_gateway(action="list_tools", gateway_name="{gateway_name}")`
2. Verify tool arguments match expected schema
3. Ensure gateway is accessible and credentials are valid
4. Check tool name spelling and case sensitivity"""

            # For other actions, return appropriate not-implemented messages
            else:
                return f"""# WIP: Action '{action}' Implementation

This action is available but requires additional implementation.

## Currently Available Actions:
- setup: Complete gateway setup with Cognito + targets
- list: List all existing gateways
- delete: Delete gateway and all targets (enhanced with retry logic)
- discover: Show available AWS Smithy models
- test: Show testing instructions
- list_tools: List gateway tools via MCP protocol OK
- search_tools: Semantic search for tools OK
- invoke_tool: Invoke specific tools OK

## Coming Soon:
- create: Create gateway only
- targets: Manage individual targets
- cognito: Manage OAuth settings
- auth: Get authentication info

For now, use `action="setup"` for complete gateway creation or `action="list"` to manage existing gateways."""

        except ImportError as e:
            return f"""X Required Dependencies Missing

Error: {str(e)}

To use gateway functionality:
1. Install AWS SDK: `uv add boto3`
2. Install AgentCore: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`
3. Configure AWS: `aws configure`

Alternative: Use AWS Console for gateway management"""

        except Exception as e:
            return f"""X Gateway Operation Error: {str(e)}

Action: {action}
Gateway: {gateway_name or 'Not specified'}
Region: {region}

Troubleshooting:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify permissions for bedrock-agentcore-control
3. Check gateway exists: `agent_gateway(action="list")`
4. Try individual actions for debugging"""
