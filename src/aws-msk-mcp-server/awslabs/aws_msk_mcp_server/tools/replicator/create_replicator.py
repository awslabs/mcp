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

"""Function to create a new MSK replicator.

Maps to AWS CLI command: aws kafka create-replicator.
"""


def create_replicator(
    replicator_name,
    source_kafka_cluster_arn,
    target_kafka_cluster_arn,
    service_execution_role_arn,
    client,
    kafka_clusters=None,
    replication_info_list=None,
    tags=None,
):
    """Creates a new MSK replicator.

    Args:
        replicator_name (str): The name of the replicator
        source_kafka_cluster_arn (str): The ARN of the source Kafka cluster
        target_kafka_cluster_arn (str): The ARN of the target Kafka cluster
        service_execution_role_arn (str): The ARN of the IAM role used by the replicator
        client (boto3.client): Boto3 client for Kafka. Must be provided.
        kafka_clusters (dict, optional): Configuration details for the source and target clusters
        replication_info_list (list, optional): List of topic configurations to replicate
        tags (dict, optional): Key-value pairs to associate with the replicator

    Returns:
        dict: Result of the replicator creation operation containing:
            - ReplicatorArn (str): The Amazon Resource Name (ARN) of the replicator
            - ReplicatorName (str): The name of the replicator
            - ReplicatorState (str): The state of the replicator (e.g., CREATING)
            - CreationTime (datetime): The time when the replicator was created
            - Tags (dict, optional): Tags attached to the replicator
    """
    if client is None:
        raise ValueError('Client must be provided.')

    # Prepare the request parameters
    request_params = {
        'ReplicatorName': replicator_name,
        'SourceKafkaClusterArn': source_kafka_cluster_arn,
        'TargetKafkaClusterArn': target_kafka_cluster_arn,
        'ServiceExecutionRoleArn': service_execution_role_arn,
    }

    # Add optional parameters if provided
    if kafka_clusters:
        request_params['KafkaClusters'] = kafka_clusters

    if replication_info_list:
        request_params['ReplicationInfoList'] = replication_info_list

    if tags:
        request_params['Tags'] = tags

    # Create the replicator
    response = client.create_replicator(**request_params)

    return response
