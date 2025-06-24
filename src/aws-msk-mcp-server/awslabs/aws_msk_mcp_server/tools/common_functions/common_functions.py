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
#
# Common functions that may be shared amongst tools
def check_mcp_generated_tag(resource_arn: str, client) -> bool:
    """Check if a resource has the "MCP Generated" tag.

    Args:
        resource_arn (str): The Amazon Resource Name (ARN) of the resource to check
        client (boto3.client): Boto3 client for Kafka

    Returns:
        bool: True if the resource has the "MCP Generated" tag, False otherwise

    Raises:
        ValueError: If the client is not provided
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    response = client.list_tags_for_resource(ResourceArn=resource_arn)
    tags = response.get('Tags', {})

    # Make the comparison case-insensitive by converting to lowercase
    tag_value = tags.get('MCP Generated')
    return tag_value is not None and tag_value.lower() == 'true'


def get_cluster_name(cluster_identifier: str) -> str:
    """Extract or validate the cluster name from either an ARN or direct cluster name.

    Args:
        cluster_identifier: Either:
            - ARN string in format "arn:aws:kafka:region:account:cluster/cluster-name/uuid"
            - Direct cluster name

    Returns:
        The cluster name

    Raises:
        ValueError: If the ARN format is invalid when an ARN is provided
    """
    if cluster_identifier.startswith('arn:aws:kafka:'):
        try:
            # Handle ARN format
            parts = cluster_identifier.split('/')
            if len(parts) < 3:
                raise ValueError('Invalid MSK cluster ARN format')
            return parts[-2]
        except (IndexError, AttributeError) as e:
            raise ValueError(f'Invalid MSK cluster ARN format: {str(e)}')
    else:
        # Handle direct cluster name
        return cluster_identifier
