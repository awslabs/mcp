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

"""Function to delete a topic in an MSK cluster.

Maps to AWS MSK API: delete_topic.
"""


def delete_topic(cluster_arn, topic_name, client, confirm_delete=None):
    """Deletes a topic in the specified MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        topic_name (str): The name of the topic to delete
        client (boto3.client): Boto3 client for Kafka. Must be provided by delete_topic_tool.
        confirm_delete (str, optional): Must be exactly "DELETE" to confirm the destructive operation

    Returns:
        dict: Response containing topic deletion result:
            - TopicArn (str): The Amazon Resource Name (ARN) of the topic
            - TopicName (str): The name of the topic that was deleted
            - Status (str): The status of the topic deletion (CREATING, UPDATING, DELETING, ACTIVE)
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from delete_topic_tool.'
        )

    # Safety check: require explicit confirmation
    if confirm_delete != 'DELETE':
        raise ValueError(
            f"Safety confirmation required: To delete topic '{topic_name}', you must set "
            f"confirm_delete parameter to exactly 'DELETE' (case-sensitive). "
            f'This is a destructive operation that will permanently delete the topic and all its data. '
            f"Current confirm_delete value: '{confirm_delete}'"
        )

    # Additional safety: prevent deletion of topics with system-like names
    system_prefixes = ['__amazon', '__consumer']
    if any(topic_name.startswith(prefix) for prefix in system_prefixes):
        raise ValueError(
            f"Cannot delete topic '{topic_name}': Topics starting with system prefixes "
            f'{system_prefixes} are protected from deletion for safety.'
        )

    # Make the API call using the MSK delete_topic API
    response = client.delete_topic(ClusterArn=cluster_arn, TopicName=topic_name)

    return response
