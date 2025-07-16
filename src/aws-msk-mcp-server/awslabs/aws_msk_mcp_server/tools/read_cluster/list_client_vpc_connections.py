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

"""Function to list client VPC connections for an MSK cluster.

Maps to AWS CLI command: aws kafka list-client-vpc-connections.
"""


def list_client_vpc_connections(cluster_arn, client, max_results=10, next_token=None):
    """Lists the client VPC connections in a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to list client VPC connections for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.
        max_results (int): Maximum number of connections to return
        next_token (str): Token for pagination

    Returns:
        dict: List of client VPC connections
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_cluster_info.'
        )

    # Example implementation
    params = {'ClusterArn': cluster_arn, 'MaxResults': max_results}

    if next_token:
        params['NextToken'] = next_token

    response = client.list_client_vpc_connections(**params)

    return response
