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
from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags
from awslabs.ccapi_mcp_server.errors import ClientError, handle_aws_api_error
from awslabs.ccapi_mcp_server.schema_manager import schema_manager
from typing import Dict, List


async def generate_infrastructure_code(
    resource_type: str,
    properties: Dict = {},
    identifier: str = '',
    patch_document: List = [],
    region: str = '',
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

    # Fallback: Known AWS resources that support tagging even if schema doesn't show it
    if not supports_tagging and resource_type in [
        'AWS::S3::Bucket',
        'AWS::EC2::Instance',
        'AWS::RDS::DBInstance',
    ]:
        supports_tagging = True
        print(
            f"Schema for {resource_type} doesn't show Tags property, but we know it supports tagging"
        )

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

        # Apply patch document or merge properties
        if patch_document:
            # Apply patch operations to current properties
            import copy

            update_properties = copy.deepcopy(current_properties)
            for patch_op in patch_document:
                if patch_op['op'] == 'add' and patch_op['path'] in ['/Tags', '/Tags/-']:
                    # For Tags, merge with existing tags instead of replacing
                    existing_tags = update_properties.get('Tags', [])
                    if patch_op['path'] == '/Tags/-':
                        # Append single tag to array
                        new_tag = patch_op['value']
                        if isinstance(new_tag, dict) and 'Key' in new_tag and 'Value' in new_tag:
                            existing_tags.append(new_tag)
                            update_properties['Tags'] = existing_tags
                    else:
                        # Replace/merge entire tags array
                        new_tags = patch_op['value'] if isinstance(patch_op['value'], list) else []
                        # Combine tags (new tags will override existing ones with same key)
                        tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                        for tag in new_tags:
                            tag_dict[tag['Key']] = tag['Value']
                        update_properties['Tags'] = [
                            {'Key': k, 'Value': v} for k, v in tag_dict.items()
                        ]
                elif patch_op['op'] == 'replace' and patch_op['path'] == '/Tags':
                    # Replace tags completely
                    update_properties['Tags'] = patch_op['value']
                # Add other patch operations as needed
        elif properties:
            # Start with current properties and merge user properties
            update_properties = current_properties.copy()
            for key, value in properties.items():
                if key == 'Tags':
                    # Merge tags instead of replacing
                    existing_tags = update_properties.get('Tags', [])
                    new_tags = value if isinstance(value, list) else []
                    tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    for tag in new_tags:
                        tag_dict[tag['Key']] = tag['Value']
                    update_properties['Tags'] = [
                        {'Key': k, 'Value': v} for k, v in tag_dict.items()
                    ]
                else:
                    update_properties[key] = value
        else:
            update_properties = current_properties

        # V1: Always add required MCP server identification tags for updates too
        properties_with_tags = add_default_tags(update_properties, schema)

        operation = 'update'
    else:
        # This is a create operation
        if not properties:
            raise ClientError('Please provide the properties for the desired resource')

        # V1: Always add required MCP server identification tags
        properties_with_tags = add_default_tags(properties, schema)

        operation = 'create'

    # Generate a CloudFormation template representation for security scanning
    cf_template = {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Resources': {'Resource': {'Type': resource_type, 'Properties': properties_with_tags}},
    }

    # For updates, also generate the proper patch document with default tags
    patch_document_with_tags = None
    if is_update and 'Tags' in properties_with_tags:
        patch_document_with_tags = [
            {'op': 'replace', 'path': '/Tags', 'value': properties_with_tags['Tags']}
        ]

    result = {
        'resource_type': resource_type,
        'operation': operation,
        'properties': properties_with_tags,  # Show user exactly what will be created
        'region': region,
        'cloudformation_template': cf_template,
        'supports_tagging': supports_tagging,
    }

    if patch_document_with_tags:
        result['recommended_patch_document'] = patch_document_with_tags

    return result
