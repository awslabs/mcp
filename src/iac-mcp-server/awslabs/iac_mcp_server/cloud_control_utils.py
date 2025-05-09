# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

from awslabs.iac_mcp_server.errors import ClientError


def validate_patch(patch_document: list):
    """A best effort check that makes sure that the format of a patch document is valid before sending it to CloudControl."""
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


def progress_event(response_event) -> dict[str, str]:
    """Map a CloudControl API response to a standard output format for the MCP."""
    response = {
        'status': response_event['OperationStatus'],
        'resource_type': response_event['TypeName'],
        'is_complete': response_event['OperationStatus'] == 'SUCCESS',
        'request_token': response_event['RequestToken'],
    }

    if response_event.get('Identifier', None):
        response['identifer'] = response_event['Identifier']
    if response_event.get('StatusMessage', None):
        response['status_message'] = response_event['StatusMessage']
    if response_event.get('ResourceModel', None):
        response['resource_info'] = response_event['ResourceModel']
    if response_event.get('ErrorCode', None):
        response['error_code'] = response_event['ErrorCode']
    if response_event.get('EventTime', None):
        response['event_time'] = response_event['EventTime']
    if response_event.get('RetryAfter', None):
        response['retry_after'] = response_event['RetryAfter']

    return response
