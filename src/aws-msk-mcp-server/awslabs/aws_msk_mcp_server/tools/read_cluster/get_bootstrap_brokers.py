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

"""Function to retrieve bootstrap brokers for an MSK cluster.

Maps to AWS CLI command: aws kafka get-bootstrap-brokers.
"""


def get_bootstrap_brokers(cluster_arn, client):
    """Returns connection information for the broker nodes in a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to get bootstrap brokers for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Connection information for the broker nodes
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_cluster_info.'
        )

    # Example implementation
    response = client.get_bootstrap_brokers(ClusterArn=cluster_arn)

    return response
