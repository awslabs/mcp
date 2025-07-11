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

"""Function to retrieve metadata about an MSK cluster.

Maps to AWS CLI command: aws kafka describe-cluster-v2.
"""


def describe_cluster(cluster_arn, client):
    """Returns metadata about an MSK cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to describe
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Cluster metadata
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_cluster_info.'
        )

    # Example implementation
    response = client.describe_cluster_v2(ClusterArn=cluster_arn)

    return response
