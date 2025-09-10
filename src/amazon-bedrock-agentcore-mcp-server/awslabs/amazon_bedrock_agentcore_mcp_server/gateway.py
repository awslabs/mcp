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

import json
import os
import time
from .gateway_return_stmts import (
    return_gateway_delete_overall_error,
    return_gateway_deleted_ok,
    return_gateway_deletion_error,
    return_gateway_deletion_error_2,
    return_gateway_list,
    return_gateway_not_implemented,
    return_gateway_operation_error,
    return_gateway_search_results,
    return_gateway_testing,
    return_gateway_tool_invoke_ok,
    return_list_gateway_error,
    return_no_gateways_found,
    return_sdk_not_available,
    return_smithy_gateway_creation_ok,
)
from .gateway_utilities import (
    upload_openapi_schema,
    upload_smithy_model,
)
from .utils import RUNTIME_AVAILABLE, SDK_AVAILABLE, MCPtoolError
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from pydantic import Field
from strands.tools.mcp.mcp_client import MCPClient
from typing import Literal, Optional


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
        smithy_model: Optional[dict] = Field(
            default=None, description='Smithy model to use as dict'
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
        - create: Create new gateway only
        - targets: Manage gateway targets (lambda, openapi, smithy)
        - cognito: Setup Cognito OAuth authorization
        - list: List existing gateways and targets
        - delete: Delete gateway resources
        - auth: Get authentication tokens
        """
        if not SDK_AVAILABLE:
            return return_sdk_not_available

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
                        raise MCPtoolError(return_no_gateways_found.format(region=region))

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
                    raise MCPtoolError(
                        return_list_gateway_error.format(error_message=str(e), region=region)
                    )

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

                                    return return_gateway_deletion_error.format(
                                        gateway_name=gateway_name,
                                        gateway_id=gateway_id,
                                        deletion_steps_formatted='\n'.join(
                                            f'- {step}' for step in deletion_steps
                                        ),
                                        remaining_targets_count=len(final_remaining_ids),
                                        remaining_targets_formatted='\n'.join(
                                            f'- {t.get("name", "unknown")} (ID: `{t.get("targetId", "no-id")}`)'
                                            for t in final_remaining_targets
                                        ),
                                        max_deletion_attempts=max_deletion_attempts,
                                        region=region,
                                    )

                            except Exception as final_verify_error:
                                deletion_steps.append(
                                    f'X Could not perform final verification: {str(final_verify_error)}'
                                )
                                raise MCPtoolError(f"""X Gateway Deletion Failed - Cannot Verify Final State

Gateway: `{gateway_name}` ({gateway_id})
Issue: Cannot verify target deletion status after {max_deletion_attempts} attempts

## Deletion Steps Attempted:
{chr(10).join(f'- {step}' for step in deletion_steps)}

Verification Error: {str(final_verify_error)}

Manual Action Required: Use AWS Console to check and complete deletion""")

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
                                raise MCPtoolError(
                                    return_gateway_deletion_error_2.format(
                                        gateway_name=gateway_name,
                                        gateway_id=gateway_id,
                                        region=region,
                                        deletion_steps_formatted='\n'.join(
                                            f'- {step}' for step in deletion_steps
                                        ),
                                        delete_error_message=str(delete_error),
                                    )
                                )

                    # Success case - gateway was deleted
                    return return_gateway_deleted_ok.format(
                        gateway_name=gateway_name,
                        region=region,
                        deletion_steps_formatted='\n'.join(f'- {step}' for step in deletion_steps),
                        gateway_id=gateway_id,
                    )

                except Exception as e:
                    raise MCPtoolError(
                        return_gateway_delete_overall_error.format(
                            error_message=str(e), region=region, gateway_name=gateway_name
                        )
                    )

            # Action: setup - Complete gateway setup workflow (the comprehensive approach)
            elif action == 'setup':  # pragma: no cover
                if not gateway_name:
                    return """X Error: gateway_name is required for setup action

Example:
```python
agent_gateway(action="setup", gateway_name="my-gateway", ...)
```"""

                if not RUNTIME_AVAILABLE:
                    raise MCPtoolError("""X Starter Toolkit Not Available

To use complete gateway setup:
1. Install: `uv add bedrock-agentcore-starter-toolkit`
2. Configure AWS credentials
3. Retry setup

Alternative: Use individual actions (create, targets, cognito)""")

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
                        raise MCPtoolError(f"""X Gateway Setup Failed

## Setup Steps Attempted:
{chr(10).join(f'- {step}' for step in setup_steps)}

Gateway Creation Error: {str(gateway_error)}

Troubleshooting:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify permissions for bedrock-agentcore-control
3. Try individual setup steps manually
4. Check AWS Console for partial resources""")

                    # Step 3: Add targets if specified
                    if smithy_model or openapi_spec:
                        setup_steps.append('Target: Step 3: Adding targets...')

                        try:
                            if smithy_model:
                                # 2. Upload to S3
                                # 2. Create target with S3 URI

                                setup_steps.append(
                                    f'Search: Using the provided smithy model -  {smithy_model} ...'
                                )

                                try:
                                    # Search for the Smithy model in AWS API models repository
                                    smithy_s3_uri = await upload_smithy_model(
                                        smithy_model, gateway_name + '_smithy', region, setup_steps
                                    )

                                    if not smithy_s3_uri:
                                        raise Exception(
                                            f'Could not  upload Smithy model for {smithy_model}'
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
1. Download Smithy model (maybe in json format)
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
                                    openapi_result = await upload_openapi_schema(
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
                    return return_smithy_gateway_creation_ok.format(
                        setup_steps_formatted='\n'.join(f'- {step}' for step in setup_steps),
                        gateway_name=gateway_name,
                        region=region,
                        semantic_search_status='Enabled' if enable_semantic_search else 'Disabled',
                        smithy_model_line=f'- Smithy Model: `{smithy_model}`'
                        if smithy_model
                        else '',
                        openapi_spec_line='- Targets: OpenAPI specification added'
                        if openapi_spec
                        else '',
                    )
                except Exception as e:
                    raise MCPtoolError(f"""X Gateway Setup Error: {str(e)}

Gateway Name: `{gateway_name}`
Region: {region}

Troubleshooting:
1. Check bedrock-agentcore-starter-toolkit installation
2. Verify AWS credentials and permissions
3. Try individual setup actions for debugging
4. Check AWS Console for partial resources""")

            # Action: test - Test gateway with MCP functionality
            elif action == 'test':  # pragma: no cover
                if not gateway_name:
                    return 'X Error: gateway_name is required for test action'

                return return_gateway_testing.format(gateway_name=gateway_name, region=region)

            # Action: list_tools - List available tools from gateway via MCP protocol
            elif action == 'list_tools':  # pragma: no cover
                if not gateway_name:
                    raise ValueError('X Error: gateway_name is required for list_tools action')

                try:
                    # Load gateway configuration
                    config_dir = Path.home() / '.agentcore_gateways'
                    config_file = config_dir / f'{gateway_name}.json'

                    if not config_file.exists():
                        raise MCPtoolError(f"""X Gateway Configuration Not Found

Gateway: `{gateway_name}`
Expected Config: `{config_file}`

Solutions:
1. Check gateway name: `agent_gateway(action="list")`
2. Recreate configuration: `agent_gateway(action="setup", gateway_name="{gateway_name}")`""")

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
                        raise MCPtoolError(f"""X Failed to get gateway details: {str(e)}

Gateway: `{gateway_name}`
Region: {region}

Possible Solutions:
1. Check gateway exists: `agent_gateway(action="list")`
2. Verify AWS permissions for bedrock-agentcore:GetGateway
3. Ensure gateway name is correct""")

                    # Use MCP client to list tools

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

                    return return_gateway_list.format(
                        gateway_name=gateway_name,
                        region=region,
                        tools=tools,
                        gateway_url=gateway_url,
                        tool_names=tool_names,
                    )

                except Exception as e:
                    raise MCPtoolError(f"""X Failed to List Tools: {str(e)}

Gateway: `{gateway_name}`
Region: {region}

Possible Solutions:
1. Check gateway exists: `agent_gateway(action="list")`
2. Verify AWS credentials
3. Ensure gateway is in READY state
4. Get new access token if expired""")

            # Action: search_tools - Semantic search for tools through gateway
            elif action == 'search_tools':  # pragma: no cover
                if not gateway_name:
                    raise ValueError('X Error: gateway_name is required for search_tools action')
                if not query:
                    raise ValueError('X Error: query is required for search_tools action')

                try:
                    # Use the built-in semantic search tool directly
                    # Load gateway configuration for proper tool invocation
                    config_dir = Path.home() / '.agentcore_gateways'
                    config_file = config_dir / f'{gateway_name}.json'

                    if not config_file.exists():
                        raise MCPtoolError(f"""X Gateway Configuration Not Found

Gateway: `{gateway_name}`
Expected Config: `{config_file}`

Solutions:
1. Check gateway name: `agent_gateway(action="list")`
2. Recreate configuration: `agent_gateway(action="setup", gateway_name="{gateway_name}")`""")

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
                        raise ValueError(f"X Gateway '{gateway_name}' not found")

                    response = boto3_client.get_gateway(gatewayIdentifier=gateway_id)
                    gateway_url = response['gatewayUrl']

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

                        tool_matches = re.findall(r'\w+-target___\w+', str(result))
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

                    return return_gateway_search_results.format(
                        gateway_name=gateway_name,
                        query=query,
                        tools_data=tools_data,
                        matching_tools=matching_tools,
                        region=region,
                    )

                except Exception as e:
                    raise MCPtoolError(f"""X Search Failed: {str(e)}

Gateway: `{gateway_name}`
Query: `{query}`

Try: `agent_gateway(action="list_tools", gateway_name="{gateway_name}")` first""")

            # Action: invoke_tool - Invoke specific tools through gateway
            elif action == 'invoke_tool':  # pragma: no cover
                if not gateway_name:
                    return 'X Error: gateway_name is required for invoke_tool action'
                if not tool_name:
                    return 'X Error: tool_name is required for invoke_tool action'

                try:
                    # Load gateway configuration
                    config_dir = Path.home() / '.agentcore_gateways'
                    config_file = config_dir / f'{gateway_name}.json'

                    if not config_file.exists():
                        raise MCPtoolError(f"""X Gateway Configuration Not Found

Gateway: `{gateway_name}`
Expected Config: `{config_file}`

Solutions:
1. Check gateway name: `agent_gateway(action="list")`
2. Recreate configuration: `agent_gateway(action="setup", gateway_name="{gateway_name}")`""")

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
                        raise MCPtoolError(f"""X Failed to get gateway details: {str(e)}

Gateway: `{gateway_name}`
Region: {region}

Possible Solutions:
1. Check gateway exists: `agent_gateway(action="list")`
2. Verify AWS permissions for bedrock-agentcore:GetGateway
3. Ensure gateway name is correct""")

                    # Use MCP client to invoke tool (following working Strands example)

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

                    return return_gateway_tool_invoke_ok.format(
                        gateway_name=gateway_name,
                        tool_name=tool_name,
                        args=args,
                        result_content=result_content,
                    )

                except Exception as e:
                    raise MCPtoolError(f"""X Tool Invocation Failed: {str(e)}

Gateway: `{gateway_name}`
Tool: `{tool_name}`
Arguments: `{tool_arguments or {}}`

Possible Solutions:
1. Check tool exists: `agent_gateway(action="list_tools", gateway_name="{gateway_name}")`
2. Verify tool arguments match expected schema
3. Ensure gateway is accessible and credentials are valid
4. Check tool name spelling and case sensitivity""")

            # For other actions, return appropriate not-implemented messages
            else:
                return return_gateway_not_implemented.format(action=action)

        except ImportError as e:
            raise ImportError(f"""X Required Dependencies Missing Error: {str(e)}""")

        except Exception as e:
            raise MCPtoolError(
                return_gateway_operation_error.format(
                    action=action,
                    gateway_name_formatted=gateway_name or 'Not specified',
                    region=region,
                    error_message=str(e),
                )
            )
