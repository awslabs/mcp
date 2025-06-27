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
"""Function to add tags to an MSK resource.

Maps to AWS CLI command: aws kafka tag-resource.
"""


def tag_resource(resource_arn, tags, client):
    """Adds tags to an MSK resource.

    Args:
        resource_arn (str): The Amazon Resource Name (ARN) of the resource
        tags (dict): A map of tags to add to the resource
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Empty response if successful
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    response = client.tag_resource(ResourceArn=resource_arn, Tags=tags)

    return response
