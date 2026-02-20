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

"""Function to create a topic in an MSK cluster.

Maps to AWS MSK API: create_topic.
"""

from typing import Optional


def create_topic(
    cluster_arn: str,
    topic_name: str,
    partition_count: int,
    replication_factor: int,
    client,
    configs: Optional[str] = None,
):
    """Creates a topic in the specified MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        topic_name (str): The name of the topic to create
        partition_count (int): The number of partitions for the topic
        replication_factor (int): The replication factor for the topic
        client (boto3.client): Boto3 client for Kafka. Must be provided by create_topic_tool.
        configs (str, optional): Topic configurations encoded as a Base64 string

    Returns:
        dict: Response containing topic creation result:
            - TopicArn (str): The Amazon Resource Name (ARN) of the topic
            - TopicName (str): The name of the topic that was created
            - Status (str): The status of the topic creation (CREATING, UPDATING, DELETING, ACTIVE)
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from create_topic_tool.'
        )

    # Build parameters for the API call
    params = {
        'ClusterArn': cluster_arn,
        'TopicName': topic_name,
        'PartitionCount': partition_count,
        'ReplicationFactor': replication_factor,
    }

    # Add optional configs parameter if provided
    if configs is not None:
        params['Configs'] = configs

    # Make the API call using the MSK create_topic API
    response = client.create_topic(**params)

    return response
