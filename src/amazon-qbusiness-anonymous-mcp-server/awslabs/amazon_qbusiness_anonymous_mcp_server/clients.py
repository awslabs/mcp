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
import os
import secrets
from botocore.exceptions import ClientError
from mypy_boto3_qbusiness.client import QBusinessClient
from mypy_boto3_qbusiness.type_defs import ChatSyncOutputTypeDef


def get_qbiz_client() -> QBusinessClient:
    """Create and return an Amazon Q Business client.

    Returns:
        QBusinessClient: Configured Q Business client instance

    Raises:
        Exception: If AWS_REGION environment variable is not set
        Exception: If AWS credentials are not found or configured
        Exception: If client creation fails for any other reason

    Environment Variables:
        AWS_REGION: The AWS region where Q Business is deployed
    """
    try:
        region = os.getenv('AWS_REGION')
        if not region:
            raise ValueError('AWS_REGION environment variable is not set')
        AWS_PROFILE = os.environ.get('AWS_PROFILE')
        if AWS_PROFILE:
            aq_client: QBusinessClient = boto3.Session(
                profile_name=AWS_PROFILE, region_name=region
            ).client('qbusiness')
            return aq_client

        aq_client: QBusinessClient = boto3.client('qbusiness', region_name=region)
        return aq_client
    except Exception as e:
        raise Exception(f'Failed to create Q Business client: {str(e)}')


def make_query(client: QBusinessClient, query: str) -> ChatSyncOutputTypeDef:
    """Execute a synchronous chat query against Amazon Q Business.

    Args:
        client (boto3.client): Configured Q Business client
        query (str): The user's question or query to send to Q Business

    Returns:
        Dict[str, Any]: Raw response from Q Business API containing systemMessage and metadata

    Raises:
        Exception: If QBUSINESS_APPLICATION_ID environment variable is not set
        Exception: If Amazon Q Business API returns an error
        Exception: If the query fails for any other reason

    Environment Variables:
        QBUSINESS_APPLICATION_ID: The ID of the Q Business application to query
    """
    try:
        app_id = os.getenv('QBUSINESS_APPLICATION_ID')
        if not app_id:
            raise ValueError('QBUSINESS_APPLICATION_ID environment variable is not set')

        resp = client.chat_sync(
            applicationId=app_id,
            userMessage=query,
            clientToken=str(secrets.SystemRandom().randint(0, 10000)),
        )
        return resp
    except ClientError as e:
        raise Exception(f'Amazon Q Business API error {str(e)}')
