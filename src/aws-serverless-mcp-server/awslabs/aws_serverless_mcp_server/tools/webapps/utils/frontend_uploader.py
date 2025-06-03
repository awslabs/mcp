# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Frontend Uploader for AWS Serverless MCP Server.

Handles uploading frontend assets to S3 buckets.
"""

import mimetypes
import os
from awslabs.aws_serverless_mcp_server.models import DeployWebAppRequest
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from typing import Any, Dict, Optional


async def upload_frontend_assets(
    configuration: DeployWebAppRequest, deploy_result: Dict[str, Any]
) -> None:
    """Upload frontend assets to S3.

    Args:
        configuration: Deployment configuration
        deploy_result: Result of the deployment

    Raises:
        Exception: If upload fails
    """
    try:
        project_name = configuration.project_name
        frontend_configuration = configuration.frontend_configuration

        if not frontend_configuration or not frontend_configuration.built_assets_path:
            logger.info(f'No frontend configuration found for {project_name}, skipping upload')
            return

        # Get S3 bucket name from deployment result
        bucket_name = deploy_result.get('outputs', {}).get('WebsiteBucket')
        if not bucket_name:
            raise Exception('S3 bucket name not found in deployment outputs')

        logger.info(f'Uploading frontend assets for {project_name} to bucket {bucket_name}')

        # Verify that the built assets path exists
        built_assets_path = frontend_configuration.built_assets_path
        if not os.path.exists(built_assets_path):
            raise Exception(f'Built assets path not found: {built_assets_path}')

        # Upload to S3
        region = configuration.region
        await upload_to_s3(built_assets_path, bucket_name, region)

        logger.info(f'Frontend assets uploaded successfully for {project_name}')
    except Exception as e:
        logger.error(f'Failed to upload frontend assets: {str(e)}')
        raise


async def upload_to_s3(source_path: str, bucket_name: str, region: Optional[str] = None) -> None:
    """Upload directory contents to S3 bucket using boto3.

    Args:
        source_path: Path to the directory to upload
        bucket_name: Name of the S3 bucket
        region: AWS region

    Raises:
        Exception: If upload fails
    """
    logger.info(f'Starting S3 upload from {source_path} to bucket {bucket_name} using boto3')
    s3_client = get_aws_client('s3', region)

    def upload_file(file_path, s3_key):
        try:
            mime_type, _ = mimetypes.guess_type(s3_key)
            content_type = mime_type or 'application/octet-stream'
            s3_client.upload_file(
                file_path, bucket_name, s3_key, ExtraArgs={'ContentType': content_type}
            )
            logger.info(f'Uploaded {file_path} to s3://{bucket_name}/{s3_key}')
        except (BotoCoreError, ClientError) as e:
            logger.error(f'Failed to upload {file_path} to S3: {str(e)}')
            raise

    # Walk through the directory and upload files
    for root, _, files in os.walk(source_path):
        for file in files:
            file_path = os.path.join(root, file)
            s3_key = os.path.relpath(file_path, source_path)
            upload_file(file_path, s3_key)

    logger.info(f'S3 upload completed successfully to bucket {bucket_name}')
