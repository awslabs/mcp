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

"""Function to list topics in an MSK cluster.

Maps to AWS MSK API: GET /clusters/{clusterArn}/topics.
"""

from typing import Any, Optional


def list_topics(
    cluster_arn: str,
    client,
    topic_name_filter: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
):
    """Returns all topics in an MSK cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to list topics for
        client (boto3.client): Boto3 client for Kafka. Must be provided by list_topics_tool.
        topic_name_filter (str, optional): Returns topics starting with given name
        max_results (int, optional): Maximum number of results to return (default maximum 100 per API call)
        next_token (str, optional): Token for pagination

    Returns:
        dict: Response containing topics information:
            - topics (list): List of topic objects with:
                - partitionCount (int): Number of partitions in the topic
                - replicationFactor (int): Replication factor for the topic
                - topicName (str): Name of the topic
                - outOfSyncReplicaCount (int): Number of out-of-sync replicas
                - topicArn (str): ARN of the topic
            - nextToken (str, optional): Token for next page if there are more results
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from list_topics_tool.'
        )

    # Build parameters for the API call
    params: dict[str, Any] = {'ClusterArn': cluster_arn}

    if topic_name_filter is not None:
        params['TopicNameFilter'] = topic_name_filter

    if max_results is not None:
        params['MaxResults'] = max_results

    if next_token is not None:
        params['NextToken'] = next_token

    # Make the API call using the new MSK Topics API
    response = client.list_topics(**params)

    return response
