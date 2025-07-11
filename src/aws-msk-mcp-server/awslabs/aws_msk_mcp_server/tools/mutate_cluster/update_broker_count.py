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
"""Function to update the broker count for an MSK cluster.

Maps to AWS CLI command: aws kafka update-broker-count.
"""


def update_broker_count(cluster_arn, current_version, target_number_of_broker_nodes, client):
    """Updates the number of broker nodes in a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to update
        current_version (str): The current version of the cluster
        target_number_of_broker_nodes (int): The target number of broker nodes
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Result of the update operation
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    # Example implementation
    response = client.update_broker_count(
        ClusterArn=cluster_arn,
        CurrentVersion=current_version,
        TargetNumberOfBrokerNodes=target_number_of_broker_nodes,
    )

    return response
