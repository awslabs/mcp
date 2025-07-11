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

"""Function to list the SCRAM secrets associated with an MSK cluster.

Maps to AWS CLI command: aws kafka list-scram-secrets.
"""


def list_scram_secrets(cluster_arn, client, max_results=None, next_token=None):
    """Returns a list of the SCRAM secrets associated with an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.
        max_results (int, optional): The maximum number of results to return in the response
        next_token (str, optional): The paginated results marker. When the result is truncated,
                                   this value is provided to get the next set of results

    Returns:
        dict: Result containing the list of SCRAM secret ARNs and next token if applicable
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_cluster_info.'
        )

    # Build the request parameters
    params = {'ClusterArn': cluster_arn}

    # Add optional parameters if provided
    if max_results:
        params['MaxResults'] = max_results

    if next_token:
        params['NextToken'] = next_token

    response = client.list_scram_secrets(**params)

    return response
