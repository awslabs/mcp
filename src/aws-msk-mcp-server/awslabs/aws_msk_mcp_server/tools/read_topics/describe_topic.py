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

"""Function to describe a specific topic in an MSK cluster.

Maps to AWS MSK API: GET /v1/clusters/{clusterArn}/topics/{topicName}.
"""


def describe_topic(cluster_arn, topic_name, client):
    """Returns details for a topic on an MSK cluster.

    Args:
        cluster_arn (str): The ARN of the cluster containing the topic
        topic_name (str): The name of the topic to describe
        client (boto3.client): Boto3 client for Kafka. Must be provided by describe_topic_tool.

    Returns:
        dict: Response containing topic details:
            - TopicArn (str): The Amazon Resource Name (ARN) of the topic
            - TopicName (str): The Kafka topic name of the topic
            - ReplicationFactor (int): The replication factor of the topic
            - PartitionCount (int): The partition count of the topic
            - Configs (str): Topic configurations encoded as a Base64 string
            - Status (str): The status of the topic (CREATING, UPDATING, DELETING, ACTIVE)
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from describe_topic_tool.'
        )

    # Make the API call using the MSK describe_topic API
    response = client.describe_topic(ClusterArn=cluster_arn, TopicName=topic_name)

    return response
