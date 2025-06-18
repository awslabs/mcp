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
"""Function to update an MSK cluster's configuration.

Maps to AWS CLI command: aws kafka update-cluster-configuration.
"""


def update_cluster_configuration(
    cluster_arn, configuration_arn, configuration_revision, current_version, client
):
    """Updates an MSK cluster's configuration.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        configuration_arn (str): The Amazon Resource Name (ARN) of the configuration to use
        configuration_revision (int): The revision of the configuration to use
        current_version (str): The version of the cluster to update from
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Result of the update operation containing ClusterArn and ClusterOperationArn
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    configuration_info = {'Arn': configuration_arn, 'Revision': configuration_revision}

    response = client.update_cluster_configuration(
        ClusterArn=cluster_arn,
        CurrentVersion=current_version,
        ConfigurationInfo=configuration_info,
    )

    return response
