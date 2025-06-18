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
"""Function to update an MSK configuration.

Maps to AWS CLI command: aws kafka update-configuration.
"""


def update_configuration(arn, server_properties, client, description=''):
    """Updates an MSK configuration.

    Args:
        arn (str): The Amazon Resource Name (ARN) of the configuration to update
        server_properties (str): Contents of the server.properties file.
                                 Supported properties are documented in the MSK Developer Guide
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.
        description (str, optional): The description of the configuration revision

    Returns:
        dict: Result of the update operation containing the ARN and latest revision
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    # Build the request parameters
    params = {'Arn': arn, 'ServerProperties': server_properties}

    # Add optional parameters if provided
    if description:
        params['Description'] = description

    response = client.update_configuration(**params)

    return response
