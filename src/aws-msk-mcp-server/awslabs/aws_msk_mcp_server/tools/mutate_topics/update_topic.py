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

"""Function to update the configuration of a topic in an MSK cluster.

Maps to AWS MSK API: update_topic.
"""

from typing import Any, Optional


def update_topic(
    cluster_arn: str,
    topic_name: str,
    client,
    configs: Optional[str] = None,
    partition_count: Optional[int] = None,
):
    """Updates the configuration of the specified topic.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        topic_name (str): The name of the topic to update configuration for
        client (boto3.client): Boto3 client for Kafka. Must be provided by update_topic_tool.
        configs (str, optional): The new topic configurations encoded as a Base64 string
        partition_count (int, optional): The new total number of partitions for the topic

    Returns:
        dict: Response containing topic update result:
            - TopicArn (str): The Amazon Resource Name (ARN) of the topic
            - TopicName (str): The name of the topic whose configuration was updated
            - Status (str): The status of the topic update (CREATING, UPDATING, DELETING, ACTIVE)
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from update_topic_tool.'
        )

    # Build parameters for the API call
    params: dict[str, Any] = {
        'ClusterArn': cluster_arn,
        'TopicName': topic_name,
    }

    # Add optional parameters if provided
    if configs is not None:
        params['Configs'] = configs

    if partition_count is not None:
        params['PartitionCount'] = partition_count

    # Make the API call using the MSK update_topic API
    response = client.update_topic(**params)

    return response
