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

"""Infrastructure generation implementation for CCAPI MCP server."""

import datetime
import uuid
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.impl.utils.validation import validate_workflow_token
from awslabs.ccapi_mcp_server.infrastructure_generator import (
    generate_infrastructure_code as generate_infrastructure_code_impl,
)
from awslabs.ccapi_mcp_server.models.models import GenerateInfrastructureCodeRequest


async def generate_infrastructure_code_impl_wrapper(
    request: GenerateInfrastructureCodeRequest, workflow_store: dict
) -> dict:
    """Generate infrastructure code before resource creation or update implementation."""
    # Validate credentials token
    cred_data = validate_workflow_token(request.credentials_token, 'credentials', workflow_store)
    aws_session_data = cred_data['data']
    if not aws_session_data.get('credentials_valid'):
        raise ClientError('Invalid AWS credentials')

    # V1: Always add required MCP server identification tags
    # Inform user about default tags and ask if they want additional ones

    # Generate infrastructure code using the existing implementation
    result = await generate_infrastructure_code_impl(
        resource_type=request.resource_type,
        properties=request.properties,
        identifier=request.identifier,
        patch_document=request.patch_document,
        region=request.region or aws_session_data.get('region') or 'us-east-1',
    )

    # Generate a generated code token that enforces using the exact properties and template
    generated_code_token = f'generated_code_{str(uuid.uuid4())}'

    # Store structured workflow data including both properties and CloudFormation template
    workflow_store[generated_code_token] = {
        'type': 'generated_code',
        'data': {
            'properties': result['properties'],
            'cloudformation_template': result.get('cloudformation_template', result['properties']),
        },
        'parent_token': request.credentials_token,
        'timestamp': datetime.datetime.now().isoformat(),
    }

    # Keep credentials token for later use in create_resource()

    return {
        'generated_code_token': generated_code_token,
        'message': 'Infrastructure code generated successfully. Use generated_code_token with both explain() and run_checkov().',
        'next_step': 'Use explain() and run_checkov() with generated_code_token, then create_resource() with explained_token.',
        **result,  # Include all infrastructure code data for display
    }
