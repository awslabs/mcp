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

"""Function to list all MSK replicators in an account.

Maps to AWS CLI command: aws kafka list-replicators.
"""


def list_replicators(client, max_results=None, next_token=None):
    """Returns a list of all MSK replicators in this account.

    Args:
        client (boto3.client): Boto3 client for Kafka. Must be provided.
        max_results (int, optional): Maximum number of replicators to return
        next_token (str, optional): Token for pagination

    Returns:
        dict: List of replicators containing:
            - ReplicatorInfoList (list): List of replicator information objects, each containing:
                - ReplicatorArn (str): The ARN of the replicator
                - ReplicatorName (str): The name of the replicator
                - ReplicatorState (str): The state of the replicator
                - CreationTime (datetime): The time when the replicator was created
            - NextToken (str, optional): Token for pagination
    """
    if client is None:
        raise ValueError('Client must be provided.')

    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params['MaxResults'] = max_results

    if next_token:
        request_params['NextToken'] = next_token

    # List the replicators
    response = client.list_replicators(**request_params)

    return response
