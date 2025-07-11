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
"""Function to update the EBS storage associated with MSK brokers.

Maps to AWS CLI command: aws kafka update-broker-storage.
"""


def update_broker_storage(cluster_arn, current_version, target_broker_ebs_volume_info, client):
    """Updates the EBS storage associated with MSK brokers.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        current_version (str): The version of cluster to update from
        target_broker_ebs_volume_info (list): List of dictionaries describing the target volume size and broker IDs
            Example: [
                {
                    "KafkaBrokerNodeId": "ALL",
                    "VolumeSizeGB": 1100,
                    "ProvisionedThroughput": {
                        "Enabled": True,
                        "VolumeThroughput": 250
                    }
                }
            ]
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Result of the update operation containing ClusterArn and ClusterOperationArn
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    response = client.update_broker_storage(
        ClusterArn=cluster_arn,
        CurrentVersion=current_version,
        TargetBrokerEBSVolumeInfo=target_broker_ebs_volume_info,
    )

    return response
