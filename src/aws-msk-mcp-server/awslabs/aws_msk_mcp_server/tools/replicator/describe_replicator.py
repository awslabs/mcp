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

"""Function to retrieve information about an MSK replicator.

Maps to AWS CLI command: aws kafka describe-replicator.
"""


def describe_replicator(replicator_arn, client):
    """Returns information about an MSK replicator.

    Args:
        replicator_arn (str): The ARN of the replicator to describe
        client (boto3.client): Boto3 client for Kafka. Must be provided.

    Returns:
        dict: Replicator information containing:
            - ReplicatorInfo (dict): Detailed information about the replicator including:
                - ReplicatorArn (str): The ARN of the replicator
                - ReplicatorName (str): The name of the replicator
                - KafkaClusters (list): Information about the source and target Kafka clusters
                - ReplicationInfoList (list): Information about the topics being replicated
                - ServiceExecutionRoleArn (str): The ARN of the IAM role used by the replicator
                - ReplicatorState (str): The state of the replicator
                - CreationTime (datetime): The time when the replicator was created
                - CurrentVersion (str): The current version of the replicator
                - Tags (dict, optional): Tags attached to the replicator
    """
    if client is None:
        raise ValueError('Client must be provided.')

    response = client.describe_replicator(ReplicatorArn=replicator_arn)

    return response
