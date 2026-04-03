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

"""Function to describe a cluster operation for an MSK cluster.

Maps to AWS CLI command: aws kafka describe-cluster-operation-v2.
"""


def describe_cluster_operation(cluster_operation_arn, client):
    """Returns information about a cluster operation.

    Args:
        cluster_operation_arn (str): The Amazon Resource Name (ARN) of the cluster operation
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Information about the cluster operation
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_cluster_info.'
        )

    response = client.describe_cluster_operation_v2(ClusterOperationArn=cluster_operation_arn)

    return response
