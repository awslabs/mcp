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

"""Function to list revisions of an MSK configuration.

Maps to AWS CLI command: aws kafka list-configuration-revisions.
"""


def list_configuration_revisions(arn, client, next_token, max_results=10):
    """Returns a list of all revisions of an MSK configuration.

    Args:
        arn (str): The Amazon Resource Name (ARN) of the configuration
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_configuration_info.
        max_results (int): The maximum number of results to return in the response
        next_token (str): The paginated results marker

    Returns:
        dict: List of configuration revisions
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_configuration_info.'
        )

    params = {'Arn': arn}

    if max_results:
        params['MaxResults'] = max_results

    if next_token:
        params['NextToken'] = next_token

    response = client.list_configuration_revisions(**params)

    return response
