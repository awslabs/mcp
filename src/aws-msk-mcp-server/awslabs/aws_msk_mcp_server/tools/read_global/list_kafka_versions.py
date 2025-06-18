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

"""Function to list Apache Kafka versions supported by Amazon MSK.

Maps to AWS CLI command: aws kafka list-kafka-versions.
"""


def list_kafka_versions(client):
    """Returns a list of Apache Kafka versions supported by Amazon MSK.

    Args:
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_global_info.

    Returns:
        dict: List of supported Kafka versions
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from get_global_info.'
        )

    # Example implementation
    response = client.list_kafka_versions()

    return response
