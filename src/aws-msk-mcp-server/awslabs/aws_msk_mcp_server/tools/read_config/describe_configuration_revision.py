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

"""Function to describe a specific revision of an MSK configuration.

Maps to AWS CLI command: aws kafka describe-configuration-revision.
"""


def describe_configuration_revision(arn, revision, client):
    """Returns information about a specific revision of an MSK configuration.

    Args:
        arn (str): The Amazon Resource Name (ARN) of the configuration
        revision (int): The revision number of the configuration
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_configuration_info.

    Returns:
        dict: Information about the configuration revision
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_configuration_info.'
        )

    response = client.describe_configuration_revision(Arn=arn, Revision=revision)

    return response
