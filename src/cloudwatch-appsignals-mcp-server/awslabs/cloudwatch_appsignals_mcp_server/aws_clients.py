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

"""CloudWatch Application Signals MCP Server - AWS client initialization."""

import boto3
import os
from . import __version__
from botocore.config import Config
from loguru import logger


# Get AWS region from environment variable or use default
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
logger.debug(f'Using AWS region: {AWS_REGION}')


def _initialize_aws_clients():
    """Initialize AWS clients with proper configuration."""
    config = Config(user_agent_extra=f'awslabs.cloudwatch-appsignals-mcp-server/{__version__}')

    # Get endpoint URLs from environment variables
    appsignals_endpoint = os.environ.get('MCP_APPSIGNALS_ENDPOINT')
    logs_endpoint = os.environ.get('MCP_LOGS_ENDPOINT')
    cloudwatch_endpoint = os.environ.get('MCP_CLOUDWATCH_ENDPOINT')
    xray_endpoint = os.environ.get('MCP_XRAY_ENDPOINT')
    synthetics_endpoint = os.environ.get('MCP_SYNTHETICS_ENDPOINT')
    s3_endpoint = os.environ.get('MCP_S3_ENDPOINT')
    iam_endpoint = os.environ.get('MCP_IAM_ENDPOINT')
    lambda_endpoint = os.environ.get('MCP_LAMBDA_ENDPOINT')
    sts_endpoint = os.environ.get('MCP_STS_ENDPOINT')

    # Log endpoint overrides
    if appsignals_endpoint:
        logger.debug(f'Using Application Signals endpoint override: {appsignals_endpoint}')
    if logs_endpoint:
        logger.debug(f'Using CloudWatch Logs endpoint override: {logs_endpoint}')
    if cloudwatch_endpoint:
        logger.debug(f'Using CloudWatch endpoint override: {cloudwatch_endpoint}')
    if xray_endpoint:
        logger.debug(f'Using X-Ray endpoint override: {xray_endpoint}')
    if synthetics_endpoint:
        logger.debug(f'Using Synthetics endpoint override: {synthetics_endpoint}')
    if s3_endpoint:
        logger.debug(f'Using S3 endpoint override: {s3_endpoint}')
    if iam_endpoint:
        logger.debug(f'Using IAM endpoint override: {iam_endpoint}')
    if lambda_endpoint:
        logger.debug(f'Using Lambda endpoint override: {lambda_endpoint}')
    if sts_endpoint:
        logger.debug(f'Using STS endpoint override: {sts_endpoint}')

    # Check for AWS_PROFILE environment variable
    if aws_profile := os.environ.get('AWS_PROFILE'):
        logger.debug(f'Using AWS profile: {aws_profile}')
        session = boto3.Session(profile_name=aws_profile, region_name=AWS_REGION)
        logs = session.client('logs', config=config, endpoint_url=logs_endpoint)
        appsignals = session.client(
            'application-signals',
            region_name=AWS_REGION,
            config=config,
            endpoint_url=appsignals_endpoint,
        )
        cloudwatch = session.client('cloudwatch', config=config, endpoint_url=cloudwatch_endpoint)
        xray = session.client('xray', config=config, endpoint_url=xray_endpoint)
        synthetics = session.client('synthetics', config=config, endpoint_url=synthetics_endpoint)
        s3 = session.client('s3', config=config, endpoint_url=s3_endpoint)
        iam = session.client('iam', config=config, endpoint_url=iam_endpoint)
        lambda_client = session.client('lambda', config=config, endpoint_url=lambda_endpoint)
        sts = session.client('sts', config=config, endpoint_url=sts_endpoint)
    else:
        logs = boto3.client(
            'logs', region_name=AWS_REGION, config=config, endpoint_url=logs_endpoint
        )
        appsignals = boto3.client(
            'application-signals',
            region_name=AWS_REGION,
            config=config,
            endpoint_url=appsignals_endpoint,
        )
        cloudwatch = boto3.client(
            'cloudwatch', region_name=AWS_REGION, config=config, endpoint_url=cloudwatch_endpoint
        )
        xray = boto3.client(
            'xray', region_name=AWS_REGION, config=config, endpoint_url=xray_endpoint
        )
        # Additional clients for canary functionality
        synthetics = boto3.client(
            'synthetics', region_name=AWS_REGION, config=config, endpoint_url=synthetics_endpoint
        )
        s3 = boto3.client(
            's3', region_name=AWS_REGION, config=config, endpoint_url=s3_endpoint
        )
        iam = boto3.client(
            'iam', region_name=AWS_REGION, config=config, endpoint_url=iam_endpoint
        )
        lambda_client = boto3.client(
            'lambda', region_name=AWS_REGION, config=config, endpoint_url=lambda_endpoint
        )
        sts = boto3.client(
            'sts', region_name=AWS_REGION, config=config, endpoint_url=sts_endpoint
        )

    logger.debug('AWS clients initialized successfully')
    return logs, appsignals, cloudwatch, xray, synthetics, s3, iam, lambda_client, sts


# Initialize clients at module level
try:
    logs_client, appsignals_client, cloudwatch_client, xray_client, synthetics_client, s3_client, iam_client, lambda_client, sts_client = _initialize_aws_clients()
except Exception as e:
    logger.error(f'Failed to initialize AWS clients: {str(e)}')
    raise
