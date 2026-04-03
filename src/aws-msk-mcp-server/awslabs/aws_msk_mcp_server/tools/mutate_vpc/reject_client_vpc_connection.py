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
"""Function to reject a client VPC connection for an MSK cluster.

Maps to AWS CLI command: aws kafka reject-client-vpc-connection.
"""


def reject_client_vpc_connection(cluster_arn, vpc_connection_arn, client):
    """Rejects a client VPC connection for an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
        vpc_connection_arn (str): The Amazon Resource Name (ARN) of the VPC connection
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Information about the rejected VPC connection
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    response = client.reject_client_vpc_connection(
        ClusterArn=cluster_arn, VpcConnectionArn=vpc_connection_arn
    )

    return response
