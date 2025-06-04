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

import boto3
from typing import Any, Optional


def get_aws_client(service_name: str, region: Optional[str]) -> Any:
    """Creates and returns a boto3 client for the specified AWS service.

    Args:
        service_name (str): The name of the AWS service (e.g., 's3', 'ec2').
        region (Optional[str]): The AWS region to use for the client. If None, the default region is used.

    Returns:
        object: A boto3 client instance for the specified AWS service.

    Notes:
        - The client is configured with a custom user agent string for identification.
        - Requires valid AWS credentials to be configured in the environment.
    """
    session = boto3.Session(region_name=region) if region else boto3.Session()
    return session.client(service_name)
