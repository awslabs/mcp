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
"""Utility functions for AWS Documentation MCP Server."""

import boto3
import os
from mypy_boto3_kendra.client import KendraClient


def get_kendra_client(region=None) -> KendraClient:
    """Get a Kendra runtime client.

    Allows access to Kendra Indexes for RAG via the Kendra runtime client.

    Returns:
        boto3.client: A boto3 Kendra client instance.
    """
    # Initialize the Kendra client with given region or profile
    AWS_PROFILE = os.environ.get('AWS_PROFILE')
    AWS_REGION = region or os.environ.get('AWS_REGION', 'us-east-1')
    if AWS_PROFILE:
        kendra_client = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION).client(
            'kendra'
        )
        return kendra_client

    kendra_client = boto3.client('kendra', region_name=AWS_REGION)
    return kendra_client
