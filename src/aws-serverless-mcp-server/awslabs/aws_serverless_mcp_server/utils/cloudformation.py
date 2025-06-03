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
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from loguru import logger
from typing import Any, Dict, Optional


async def get_stack_info(stack_name: str, region: Optional[str] = None) -> Dict[str, Any]:
    """Get information about a CloudFormation stack.

    Args:
        stack_name: Name of the CloudFormation stack
        region: AWS region

    Returns:
        Dict: Stack information including status, outputs, etc.
    """
    # Initialize CloudFormation client
    cf_client = get_aws_client('cloudformation', region)

    try:
        # Get stack information
        response = cf_client.describe_stacks(StackName=stack_name)

        if not response or 'Stacks' not in response or not response['Stacks']:
            return {'status': 'NOT_FOUND', 'message': f'Stack {stack_name} not found'}

        stack = response['Stacks'][0]

        # Extract outputs
        outputs = {}
        if 'Outputs' in stack:
            for output in stack['Outputs']:
                outputs[output['OutputKey']] = output['OutputValue']

        # Return stack information
        return {
            'status': stack['StackStatus'],
            'statusReason': stack.get('StackStatusReason'),
            'lastUpdatedTime': stack.get('LastUpdatedTime').isoformat(),
            'creationTime': stack.get('CreationTime').isoformat(),
            'outputs': outputs,
        }
    except cf_client.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            return {'status': 'NOT_FOUND', 'message': f'Stack {stack_name} not found'}
        logger.error(f'Error getting CloudFormation stack info: {str(e)}')
        raise
    except Exception as e:
        logger.error(f'Error getting CloudFormation stack info: {str(e)}')
        raise


def map_cloudformation_status(cf_status: str) -> str:
    """Map CloudFormation status to a simplified status.

    Args:
        cf_status: CloudFormation stack status

    Returns:
        str: Simplified status
    """
    if cf_status == 'CREATE_COMPLETE' or cf_status == 'UPDATE_COMPLETE':
        return 'DEPLOYED'
    elif cf_status == 'DELETE_COMPLETE':
        return 'DELETED'
    elif cf_status.endswith('_FAILED'):
        return 'FAILED'
    elif cf_status.endswith('_IN_PROGRESS'):
        return 'IN_PROGRESS'
    elif cf_status == 'NOT_FOUND':
        return 'NOT_FOUND'
    else:
        return 'UNKNOWN'
