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
"""Function to disassociate SCRAM secrets from an MSK cluster.

Maps to AWS CLI command: aws kafka batch-disassociate-scram-secret.
"""


def batch_disassociate_scram_secret(cluster_arn, secret_arns, client):
    """Disassociates SCRAM secrets from an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
        secret_arns (list): A list of secret ARNs to disassociate from the cluster
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Information about the disassociated secrets
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    response = client.batch_disassociate_scram_secret(
        ClusterArn=cluster_arn, SecretArnList=secret_arns
    )

    return response
