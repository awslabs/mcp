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

"""Function to list topics of an MSK cluster.

Maps to AWS CLI command: aws kafka list-topics.
"""


def list_topics(cluster_arn, client, max_results=10, next_token=None):
    """Returns a list of topics in the cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to list topics for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_topic_info.
        max_results (int): Maximum number of topics to return
        next_token (str): Token for pagination

    Returns:
        dict: List of topics
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_topic_info.'
        )

    params = {'ClusterArn': cluster_arn, 'MaxResults': max_results}

    if next_token:
        params['NextToken'] = next_token

    response = client.list_topics(**params)

    return response
