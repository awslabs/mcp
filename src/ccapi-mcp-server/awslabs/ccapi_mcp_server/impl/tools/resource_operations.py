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

"""Resource operations implementation for CCAPI MCP server."""

import json
from awslabs.ccapi_mcp_server.aws_client import get_aws_client
from awslabs.ccapi_mcp_server.cloud_control_utils import progress_event, validate_patch
from awslabs.ccapi_mcp_server.context import Context
from awslabs.ccapi_mcp_server.errors import ClientError, handle_aws_api_error
from awslabs.ccapi_mcp_server.impl.utils.validation import (
    cleanup_workflow_tokens,
    ensure_region_string,
    validate_identifier,
    validate_resource_type,
    validate_workflow_token,
)
from awslabs.ccapi_mcp_server.models.models import (
    CreateResourceRequest,
    DeleteResourceRequest,
    GetResourceRequest,
    UpdateResourceRequest,
)
from os import environ


def check_readonly_mode(aws_session_data: dict) -> None:
    """Check if server is in read-only mode and raise error if so."""
    if Context.readonly_mode() or aws_session_data.get('readonly_mode', False):
        raise ClientError('Server is in read-only mode')


def check_security_scanning() -> tuple[bool, str | None]:
    """Check if security scanning is enabled and return warning if disabled."""
    security_scanning_enabled = environ.get('SECURITY_SCANNING', 'enabled').lower() == 'enabled'
    security_warning = None

    if not security_scanning_enabled:
        security_warning = '⚠️ SECURITY SCANNING IS DISABLED. This MCP server is configured with SECURITY_SCANNING=disabled, which means resources will be created/updated WITHOUT automated security validation. For security best practices, consider enabling SECURITY_SCANNING in your MCP configuration or ensure other security scanning tools are in place.'

    return security_scanning_enabled, security_warning


def _validate_token_chain(
    explained_token: str, security_scan_token: str, workflow_store: dict
) -> None:
    """Validate that tokens are from the same workflow chain."""
    if not explained_token or explained_token not in workflow_store:
        raise ClientError('Invalid explained_token')

    if not security_scan_token or security_scan_token not in workflow_store:
        raise ClientError('Invalid security_scan_token')

    # Security scan token must be created after explain token in same workflow
    explained_data = workflow_store[explained_token]
    security_data = workflow_store[security_scan_token]

    # For now, just ensure both tokens exist and are valid types
    if explained_data.get('type') != 'explained_properties':
        raise ClientError('Invalid explained_token type')

    if security_data.get('type') != 'security_scan':
        raise ClientError('Invalid security_scan_token type')

    # Set the parent relationship (security scan derives from explained token)
    workflow_store[security_scan_token]['parent_token'] = explained_token


async def create_resource_impl(request: CreateResourceRequest, workflow_store: dict) -> dict:
    """Create an AWS resource implementation."""
    validate_resource_type(request.resource_type)

    # Check if security scanning is enabled
    security_scanning_enabled, security_warning = check_security_scanning()

    # Validate security scan token if security scanning is enabled
    if security_scanning_enabled:
        if not request.security_scan_token:
            raise ClientError(
                'Security scanning is enabled but no security_scan_token provided: run run_checkov() first and get user approval via approve_security_findings()'
            )

        # Validate token chain
        _validate_token_chain(request.explained_token, request.security_scan_token, workflow_store)
    elif not security_scanning_enabled and not request.skip_security_check:
        raise ClientError(
            'Security scanning is disabled. You must set skip_security_check=True to proceed without security validation.'
        )

    # Validate credentials token
    cred_data = validate_workflow_token(request.credentials_token, 'credentials', workflow_store)
    aws_session_data = cred_data['data']
    if not aws_session_data.get('credentials_valid'):
        raise ClientError('Invalid AWS credentials')

    # Read-only mode check
    check_readonly_mode(aws_session_data)

    # CRITICAL SECURITY: Get properties from validated explained token only
    workflow_data = validate_workflow_token(
        request.explained_token, 'explained_properties', workflow_store
    )

    # Use ONLY the properties that were explained - no manual override possible
    properties = workflow_data['data']['properties']

    # Ensure region is a string, not a FieldInfo object
    region_str = ensure_region_string(request.region) or 'us-east-1'
    cloudcontrol_client = get_aws_client('cloudcontrol', region_str)
    try:
        response = cloudcontrol_client.create_resource(
            TypeName=request.resource_type, DesiredState=json.dumps(properties)
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    # Clean up consumed tokens after successful operation
    cleanup_workflow_tokens(
        workflow_store,
        request.explained_token,
        request.credentials_token,
        request.security_scan_token or '',
    )

    result = progress_event(response['ProgressEvent'], None)
    if security_warning:
        result['security_warning'] = security_warning
    return result


async def update_resource_impl(request: UpdateResourceRequest, workflow_store: dict) -> dict:
    """Update an AWS resource implementation."""
    validate_resource_type(request.resource_type)
    validate_identifier(request.identifier)

    if not request.patch_document:
        raise ClientError('Please provide a patch document for the update')

    # Validate credentials token
    cred_data = validate_workflow_token(request.credentials_token, 'credentials', workflow_store)
    aws_session_data = cred_data['data']
    if not aws_session_data.get('credentials_valid'):
        raise ClientError('Invalid AWS credentials')

    # Check read-only mode
    try:
        check_readonly_mode(aws_session_data)
    except ClientError:
        raise ClientError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Check if security scanning is enabled
    security_scanning_enabled, security_warning = check_security_scanning()

    # Validate security scan token if security scanning is enabled
    if security_scanning_enabled and not request.security_scan_token:
        raise ClientError('Security scan token required (run run_checkov() first)')

    # CRITICAL SECURITY: Validate explained token (already validated in token chain if security enabled)
    if not security_scanning_enabled or request.skip_security_check:
        validate_workflow_token(request.explained_token, 'explained_properties', workflow_store)
    else:
        # Token already validated in chain
        pass

    validate_patch(request.patch_document)
    # Ensure region is a string, not a FieldInfo object
    region_str = ensure_region_string(request.region) or 'us-east-1'
    cloudcontrol_client = get_aws_client('cloudcontrol', region_str)

    # Convert patch document to JSON string for the API
    patch_document_str = json.dumps(request.patch_document)

    # Update the resource
    try:
        response = cloudcontrol_client.update_resource(
            TypeName=request.resource_type,
            Identifier=request.identifier,
            PatchDocument=patch_document_str,
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    # Clean up consumed tokens after successful operation
    cleanup_workflow_tokens(
        workflow_store,
        request.explained_token,
        request.credentials_token,
        request.security_scan_token or '',
    )

    result = progress_event(response['ProgressEvent'], None)
    if security_warning:
        result['security_warning'] = security_warning
    return result


async def delete_resource_impl(request: DeleteResourceRequest, workflow_store: dict) -> dict:
    """Delete an AWS resource implementation."""
    validate_resource_type(request.resource_type)
    validate_identifier(request.identifier)

    if not request.confirmed:
        raise ClientError(
            'Please confirm the deletion by setting confirmed=True to proceed with resource deletion.'
        )

    # CRITICAL SECURITY: Validate explained token to ensure deletion was explained
    workflow_data = validate_workflow_token(
        request.explained_token, 'explained_delete', workflow_store
    )

    if workflow_data.get('operation') != 'delete':
        raise ClientError('Invalid explained token: token was not generated for delete operation')

    # Validate credentials token
    cred_data = validate_workflow_token(request.credentials_token, 'credentials', workflow_store)
    aws_session_data = cred_data['data']
    if not aws_session_data.get('credentials_valid'):
        raise ClientError('Invalid AWS credentials')

    # Check read-only mode
    try:
        check_readonly_mode(aws_session_data)
    except ClientError:
        raise ClientError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    cloudcontrol_client = get_aws_client('cloudcontrol', request.region or 'us-east-1')
    try:
        response = cloudcontrol_client.delete_resource(
            TypeName=request.resource_type, Identifier=request.identifier
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    # Clean up consumed tokens after successful operation
    cleanup_workflow_tokens(workflow_store, request.explained_token, request.credentials_token)

    return progress_event(response['ProgressEvent'], None)


async def get_resource_impl(
    request: GetResourceRequest, workflow_store: dict | None = None
) -> dict:
    """Get details of a specific AWS resource implementation."""
    validate_resource_type(request.resource_type)
    validate_identifier(request.identifier)

    cloudcontrol = get_aws_client('cloudcontrol', request.region or 'us-east-1')
    try:
        result = cloudcontrol.get_resource(
            TypeName=request.resource_type, Identifier=request.identifier
        )
        properties_str = result['ResourceDescription']['Properties']
        properties = (
            json.loads(properties_str) if isinstance(properties_str, str) else properties_str
        )

        resource_info = {
            'identifier': result['ResourceDescription']['Identifier'],
            'properties': properties,
        }

        # Add security analysis if requested
        if request.analyze_security and workflow_store is not None:
            # Import here to avoid circular imports
            from awslabs.ccapi_mcp_server.impl.tools.explanation import explain_impl
            from awslabs.ccapi_mcp_server.impl.tools.security_scanning import run_checkov_impl
            from awslabs.ccapi_mcp_server.impl.tools.session_management import (
                check_environment_variables_impl,
                get_aws_session_info_impl,
            )

            env_token = None
            creds_token = None
            gen_token = None
            explained_token = None
            security_scan_token = None
            try:
                # Get credentials token first
                env_check = await check_environment_variables_impl(workflow_store)
                env_token = env_check['environment_token']
                session_info = await get_aws_session_info_impl(env_token, workflow_store)
                creds_token = session_info['credentials_token']

                # Use existing security analysis workflow
                from awslabs.ccapi_mcp_server.impl.tools.infrastructure_generation import (
                    generate_infrastructure_code_impl_wrapper,
                )
                from awslabs.ccapi_mcp_server.models.models import (
                    GenerateInfrastructureCodeRequest,
                )

                gen_request = GenerateInfrastructureCodeRequest(
                    resource_type=request.resource_type,
                    properties=properties or {},
                    credentials_token=creds_token or '',
                    region=request.region,
                )
                generated_code = await generate_infrastructure_code_impl_wrapper(
                    gen_request, workflow_store
                )
                gen_token = generated_code['generated_code_token']

                from awslabs.ccapi_mcp_server.models.models import ExplainRequest

                explain_request = ExplainRequest(
                    generated_code_token=gen_token or '', content=None
                )
                explained = await explain_impl(explain_request, workflow_store)
                explained_token = explained['explained_token']

                from awslabs.ccapi_mcp_server.models.models import RunCheckovRequest

                checkov_request = RunCheckovRequest(explained_token=explained_token)
                security_scan = await run_checkov_impl(checkov_request, workflow_store)
                security_scan_token = security_scan.get('security_scan_token')
                resource_info['security_analysis'] = security_scan
            except Exception as e:
                resource_info['security_analysis'] = {
                    'error': f'Security analysis failed: {str(e)}'
                }
            finally:
                # Clean up security analysis tokens that aren't auto-consumed
                # gen_token is consumed by explain(), so only clean remaining tokens
                if workflow_store is not None:
                    cleanup_workflow_tokens(
                        workflow_store,
                        env_token or '',
                        creds_token or '',
                        explained_token or '',
                        security_scan_token or '',
                    )

        return resource_info
    except Exception as e:
        raise handle_aws_api_error(e)


async def get_resource_request_status_impl(request_token: str, region: str | None = None) -> dict:
    """Get the status of a long running operation implementation."""
    if not request_token:
        raise ClientError('Please provide a request token to track the request')

    cloudcontrol_client = get_aws_client('cloudcontrol', region or 'us-east-1')
    try:
        response = cloudcontrol_client.get_resource_request_status(
            RequestToken=request_token,
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    return progress_event(response['ProgressEvent'], response.get('HooksProgressEvent', None))
