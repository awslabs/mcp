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

"""Function to describe partitions of a specific topic in an MSK cluster.

Maps to AWS MSK API: describe_topic_partitions.
"""

from typing import Any, Optional


def describe_topic_partitions(
    cluster_arn: str,
    topic_name: str,
    client,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
):
    """Returns partition information for a topic on an MSK cluster.

    Args:
        cluster_arn (str): The ARN of the cluster containing the topic
        topic_name (str): The name of the topic to describe partitions for
        client (boto3.client): Boto3 client for Kafka. Must be provided by describe_topic_partitions_tool.
        max_results (int, optional): Maximum number of partitions to return
        next_token (str, optional): Token for pagination

    Returns:
        dict: Response containing partition information:
            - Partitions (list): List of partition objects containing:
                - Partition (int): The partition ID
                - Leader (int): The leader broker ID for the partition
                - Replicas (list): List of replica broker IDs for the partition
                - Isr (list): List of in-sync replica broker IDs for the partition
            - NextToken (str, optional): Token for next page if there are more results
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from describe_topic_partitions_tool.'
        )

    # Build parameters for the API call
    params: dict[str, Any] = {'ClusterArn': cluster_arn, 'TopicName': topic_name}

    if max_results is not None:
        params['MaxResults'] = max_results

    if next_token is not None:
        params['NextToken'] = next_token

    # Make the API call using the MSK describe_topic_partitions API
    response = client.describe_topic_partitions(**params)

    return response
