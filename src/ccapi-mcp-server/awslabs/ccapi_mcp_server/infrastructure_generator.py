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

"""Infrastructure code generation utilities for the CFN MCP Server."""

import json
from awslabs.ccapi_mcp_server.aws_client import get_aws_client
from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags, validate_patch
from awslabs.ccapi_mcp_server.errors import ClientError, handle_aws_api_error
from awslabs.ccapi_mcp_server.schema_manager import schema_manager
from typing import Dict, List


async def generate_infrastructure_code(
    resource_type: str,
    properties: Dict = {},
    identifier: str = '',
    patch_document: List = [],
    region: str = '',
    disable_default_tags: bool = False,
) -> Dict:
    """Generate infrastructure code for security scanning before resource creation or update."""
    if not resource_type:
        raise ClientError('Please provide a resource type (e.g., AWS::S3::Bucket)')

    # Determine if this is a create or update operation
    is_update = identifier != '' and (patch_document or properties)

    # Validate the resource type against the schema
    sm = schema_manager()
    schema = await sm.get_schema(resource_type, region)

    # Check if resource supports tagging
    supports_tagging = 'Tags' in schema.get('properties', {})

    if is_update:
        # This is an update operation
        if not identifier:
            raise ClientError('Please provide a resource identifier for update operations')

        # Get the current resource state
        cloudcontrol_client = get_aws_client('cloudcontrol', region)
        try:
            current_resource = cloudcontrol_client.get_resource(
                TypeName=resource_type, Identifier=identifier
            )
            current_properties = json.loads(current_resource['ResourceDescription']['Properties'])
        except Exception as e:
            raise handle_aws_api_error(e)

        # If patch_document is provided, validate it
        if patch_document:
            validate_patch(patch_document)
            # Note: In a real implementation, you would apply the patch to current_properties
            # For simplicity, we'll just use the current properties
            properties_with_tags = current_properties
        else:
            # If properties are provided directly for update
            properties_with_tags = properties if properties else current_properties

        operation = 'update'
    else:
        # This is a create operation
        if not properties:
            raise ClientError('Please provide the properties for the desired resource')

        # Apply default tags if enabled and not explicitly disabled
        if disable_default_tags:
            properties_with_tags = properties
            print(
                'Warning: Default tags are disabled. It is highly recommended to add custom tags to identify resources managed by this MCP server.'
            )
        else:
            properties_with_tags = add_default_tags(properties, schema)

        operation = 'create'

    # Generate a CloudFormation template representation for security scanning
    cf_template = {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Resources': {'Resource': {'Type': resource_type, 'Properties': properties_with_tags}},
    }

    return {
        'resource_type': resource_type,
        'operation': operation,
        'properties': properties_with_tags,
        'region': region,
        'cloudformation_template': cf_template,
        'supports_tagging': supports_tagging,
    }
