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

from awslabs.ccapi_mcp_server.errors import ClientError
from typing import Any, Dict

# Resource types that use non-standard tag properties
RESOURCE_TAG_PROPERTY_MAP = {
    'AWS::EFS::FileSystem': 'FileSystemTags',
    'AWS::EFS::AccessPoint': 'Tags',  # EFS Access Points use Tags
    'AWS::CloudFormation::Stack': 'Tags',
    'AWS::ECR::Repository': 'Tags',
    'AWS::RDS::DBInstance': 'Tags',
    'AWS::S3::Bucket': 'Tags',
    'AWS::EC2::Instance': 'Tags',
    'AWS::ECS::Cluster': 'Tags',
    'AWS::ECS::TaskDefinition': 'Tags',
    'AWS::ECS::Service': 'Tags',
    'AWS::SecretsManager::Secret': 'Tags',
    'AWS::ElasticLoadBalancingV2::LoadBalancer': 'Tags',
    'AWS::ElasticLoadBalancingV2::TargetGroup': 'Tags',
    # Add more resource types as they are discovered to have different tag properties
    # Default fallback is 'Tags' for most AWS resources
}


def add_default_tags(properties: Dict, schema: Dict, resource_type: str = None) -> Dict:
    """
    Add default MCP server tags to resource properties using the correct tag property name.
    
    This function automatically adds management tags for tracking resources created by the MCP server.
    It handles different AWS resource types that use different tag property names (e.g., EFS uses
    'FileSystemTags' instead of the standard 'Tags').
    
    Args:
        properties: The resource properties dictionary
        schema: The resource schema (for future validation)
        resource_type: AWS resource type (e.g., 'AWS::EFS::FileSystem', 'AWS::S3::Bucket')
    
    Returns:
        Modified properties dictionary with default tags added using the correct property name
    """
    # Return empty dict when properties is None or empty dict {}
    # This prevents processing invalid/missing resource properties
    if not properties:
        return {}

    properties_with_tags = properties.copy()

    # Determine the correct tag property name for this resource type
    tag_property = RESOURCE_TAG_PROPERTY_MAP.get(resource_type, 'Tags')

    # Always try to add tags - don't check schema since it can be unreliable
    # Ensure tag property array exists
    if tag_property not in properties_with_tags:
        properties_with_tags[tag_property] = []

    tags = properties_with_tags[tag_property]
    # Add default tags if they don't exist
    managed_by_exists = any(tag.get('Key') == 'MANAGED_BY' for tag in tags if isinstance(tag, dict))
    source_exists = any(tag.get('Key') == 'MCP_SERVER_SOURCE_CODE' for tag in tags if isinstance(tag, dict))
    version_exists = any(tag.get('Key') == 'MCP_SERVER_VERSION' for tag in tags if isinstance(tag, dict))

    if not managed_by_exists:
        tags.append({'Key': 'MANAGED_BY', 'Value': 'CCAPI-MCP-SERVER'})
    if not source_exists:
        tags.append(
            {
                'Key': 'MCP_SERVER_SOURCE_CODE',
                'Value': 'https://github.com/awslabs/mcp/tree/main/src/ccapi-mcp-server',
            }
        )
    if not version_exists:
        from awslabs.ccapi_mcp_server import __version__

        tags.append({'Key': 'MCP_SERVER_VERSION', 'Value': __version__})

    properties_with_tags[tag_property] = tags

    return properties_with_tags


def get_resource_tag_property(resource_type: str) -> str:
    """
    Get the correct tag property name for a given AWS resource type.
    
    Args:
        resource_type: AWS resource type (e.g., 'AWS::EFS::FileSystem')
        
    Returns:
        The tag property name to use ('Tags', 'FileSystemTags', etc.)
    """
    return RESOURCE_TAG_PROPERTY_MAP.get(resource_type, 'Tags')


def add_resource_to_tag_map(resource_type: str, tag_property: str) -> None:
    """
    Add a new resource type to the tag property mapping.
    
    This is useful for extending support to new resource types that use
    non-standard tag properties.
    
    Args:
        resource_type: AWS resource type (e.g., 'AWS::NewService::Resource')  
        tag_property: Tag property name (e.g., 'ResourceTags')
    """
    RESOURCE_TAG_PROPERTY_MAP[resource_type] = tag_property


def validate_patch(patch_document: Any):
    """A best effort check that makes sure that the format of a patch document is valid before sending it to CloudControl."""
    if not isinstance(patch_document, list):
        raise ClientError('Patch document must be a list')

    for patch_op in patch_document:
        if not isinstance(patch_op, dict):
            raise ClientError('Each patch operation must be a dictionary')
        if 'op' not in patch_op:
            raise ClientError("Each patch operation must include an 'op' field")
        if patch_op['op'] not in ['add', 'remove', 'replace', 'move', 'copy', 'test']:
            raise ClientError(
                f"Operation '{patch_op['op']}' is not supported. Must be one of: add, remove, replace, move, copy, test"
            )
        if 'path' not in patch_op:
            raise ClientError("Each patch operation must include a 'path' field")
        # Value is required for add, replace, and test operations
        if patch_op['op'] in ['add', 'replace', 'test'] and 'value' not in patch_op:
            raise ClientError(f"The '{patch_op['op']}' operation requires a 'value' field")
        # From is required for move and copy operations
        if patch_op['op'] in ['move', 'copy'] and 'from' not in patch_op:
            raise ClientError(f"The '{patch_op['op']}' operation requires a 'from' field")


def progress_event(response_event, hooks_events) -> Dict[str, Any]:
    """Map a CloudControl API response to a standard output format for the MCP."""
    response = {
        'status': response_event['OperationStatus'],
        'resource_type': response_event['TypeName'],
        'is_complete': response_event['OperationStatus'] == 'SUCCESS'
        or response_event['OperationStatus'] == 'FAILED',
        'request_token': response_event['RequestToken'],
    }

    if response_event.get('Identifier', None):
        response['identifier'] = response_event['Identifier']
    if response_event.get('ResourceModel', None):
        response['resource_info'] = response_event['ResourceModel']
    if response_event.get('ErrorCode', None):
        response['error_code'] = response_event['ErrorCode']
    if response_event.get('EventTime', None):
        response['event_time'] = response_event['EventTime']
    if response_event.get('RetryAfter', None):
        response['retry_after'] = response_event['RetryAfter']

    # CloudControl returns a list of hooks events which may also contain a message which should
    # take precedent over the status message returned from CloudControl directly
    hooks_status_message = None
    if hooks_events:
        failed_hook_event_messages = (
            hook_event['HookStatusMessage']
            for hook_event in hooks_events
            if hook_event.get('HookStatus', None) == 'HOOK_COMPLETE_FAILED'
            or hook_event.get('HookStatus', None) == 'HOOK_FAILED'
        )
        hooks_status_message = next(failed_hook_event_messages, None)

    if hooks_status_message:
        response['status_message'] = hooks_status_message
    elif response_event.get('StatusMessage', None):
        response['status_message'] = response_event['StatusMessage']

    return response
