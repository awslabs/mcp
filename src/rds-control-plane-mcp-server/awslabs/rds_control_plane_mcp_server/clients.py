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
from mypy_boto3_pi.client import PIClient
from mypy_boto3_rds.client import RDSClient
from typing import Optional


def get_rds_client(
    region_name: Optional[str] = 'us-east-1', profile_name: Optional[str] = None
) -> RDSClient:
    """Get an Amazon RDS client.

    Amazon Relational Database Service (RDS) makes it easy to set up, operate,
    and scale a relational database in the cloud.

    Args:
        region_name: The AWS region name to use for the client
        profile_name: Optional AWS profile name to use

    Returns:
        An RDS client instance
    """
    if profile_name:
        client = boto3.Session(profile_name=profile_name).client(
            'rds', region_name=region_name or 'us-east-1'
        )
        return client  # type: ignore
    client = boto3.client('rds', region_name=region_name or 'us-east-1')
    return client  # type: ignore


def get_pi_client(
    region_name: Optional[str] = 'us-east-1', profile_name: Optional[str] = None
) -> PIClient:
    """Get a Performance Insights client.

    AWS Performance Insights provides a dashboard for monitoring and analyzing database performance.

    Args:
        region_name: The AWS region name to use for the client
        profile_name: Optional AWS profile name to use

    Returns:
        A Performance Insights (PI) client instance
    """
    if profile_name:
        client = boto3.Session(profile_name=profile_name).client(
            'pi', region_name=region_name or 'us-east-1'
        )
        return client  # type: ignore
    client = boto3.client('pi', region_name=region_name or 'us-east-1')
    return client  # type: ignore
