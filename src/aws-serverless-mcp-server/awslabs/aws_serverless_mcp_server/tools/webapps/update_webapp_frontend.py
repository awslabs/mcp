# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
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

"""Update Frontend Tool for AWS Serverless MCP Server.

Handles updating frontend assets without redeploying the entire infrastructure.
Uses boto3 instead of AWS CLI.
"""

import datetime
import mimetypes
import os
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional


class UpdateFrontendTool:
    """Tool to update frontend assets of a deployed web application."""

    def __init__(self, mcp: FastMCP):
        """Initialize the update frontend tool."""
        mcp.tool(name='update_webapp_frontend')(self.update_webapp_frontend_tool)

    async def update_webapp_frontend_tool(
        self,
        ctx: Context,
        project_name: str = Field(description='Project name'),
        project_root: str = Field(description='Project root'),
        built_assets_path: str = Field(description='Absolute path to pre-built frontend assets'),
        invalidate_cache: Optional[bool] = Field(
            default=True, description='Whether to invalidate the CloudFront cache'
        ),
        region: Optional[str] = Field(
            default=None, description='AWS region to use (e.g., us-east-1)'
        ),
    ) -> Dict[str, Any]:
        """Update the frontend assets of a deployed web application.

        This tool uploads new frontend assets to S3 and optionally invalidates the CloudFront cache.
        """
        await ctx.info(f'Updating frontend for project {project_name}')

        try:
            logger.info(f'[UPDATE FRONTEND] Starting frontend update for {project_name}')

            # Convert relative path to absolute if needed
            if not os.path.isabs(built_assets_path):
                built_assets_path = os.path.join(project_root, built_assets_path)

            # Verify that the built assets path exists
            if not os.path.exists(built_assets_path):
                return {
                    'status': 'error',
                    'message': f'Built assets path not found: {built_assets_path}',
                    'content': [
                        {
                            'type': 'text',
                            'text': f'Error: Built assets path not found: {built_assets_path}',
                        }
                    ],
                }

            # Initialize AWS clients
            cfn_client = get_aws_client('cloudformation', region)
            s3_client = get_aws_client('s3', region)
            cloudfront_client = get_aws_client('cloudfront', region)

            # Get the CloudFormation stack outputs to find the S3 bucket
            stack_name = project_name
            logger.info(f'Looking up CloudFormation stack: {stack_name}')

            try:
                # Get stack outputs
                describe_stacks_result = cfn_client.describe_stacks(StackName=stack_name)

                if not describe_stacks_result.get('Stacks'):
                    return {
                        'status': 'error',
                        'message': f'CloudFormation stack {stack_name} not found',
                        'content': [
                            {
                                'type': 'text',
                                'text': f'Error: CloudFormation stack {stack_name} not found. Please deploy the application first using the deploy tool.',
                            }
                        ],
                    }

                # Extract the S3 bucket name from stack outputs
                outputs = describe_stacks_result['Stacks'][0].get('Outputs', [])
                bucket_output = next(
                    (output for output in outputs if output.get('OutputKey') == 'WebsiteBucket'),
                    None,
                )

                if not bucket_output or not bucket_output.get('OutputValue'):
                    return {
                        'status': 'error',
                        'message': f'Could not find WebsiteBucket output in CloudFormation stack {stack_name}',
                        'content': [
                            {
                                'type': 'text',
                                'text': f'Error: Could not find WebsiteBucket output in CloudFormation stack {stack_name}. This suggests the stack was not deployed as a frontend or fullstack application.',
                            }
                        ],
                    }

                bucket_name = bucket_output['OutputValue']
                logger.info(f'Found S3 bucket: {bucket_name}')

                # Upload the frontend assets to the S3 bucket
                logger.info(
                    f'Uploading frontend assets from {built_assets_path} to bucket {bucket_name}'
                )

                await self._sync_directory_to_s3(s3_client, built_assets_path, bucket_name)

                # Check if there's a CloudFront distribution to invalidate
                cloudfront_output = next(
                    (
                        output
                        for output in outputs
                        if output.get('OutputKey')
                        in [
                            'CloudFrontDistribution',
                            'CloudFrontDomain',
                            'CloudFrontDistributionId',
                            'CloudFrontURL',
                        ]
                    ),
                    None,
                )

                if cloudfront_output and cloudfront_output.get('OutputValue'):
                    # Get the distribution ID - it might be directly the ID or a URL
                    distribution_id = cloudfront_output['OutputValue']

                    # If we have a CloudFront URL instead of an ID, look for the ID specifically
                    if distribution_id.startswith('http'):
                        distribution_id_output = next(
                            (
                                output
                                for output in outputs
                                if output.get('OutputKey') == 'CloudFrontDistributionId'
                            ),
                            None,
                        )

                        if distribution_id_output and distribution_id_output.get('OutputValue'):
                            distribution_id = distribution_id_output['OutputValue']
                        else:
                            logger.warning(
                                'Found CloudFront URL but no distribution ID, skipping invalidation'
                            )
                            return {
                                'status': 'success',
                                'message': f"Frontend assets updated successfully for {project_name}, but couldn't create CloudFront invalidation",
                                'content': [
                                    {
                                        'type': 'text',
                                        'text': f'Frontend assets for {project_name} have been successfully updated.',
                                    },
                                    {
                                        'type': 'text',
                                        'text': f'Assets were uploaded to S3 bucket: {bucket_name}',
                                    },
                                    {
                                        'type': 'text',
                                        'text': 'CloudFront distribution was found, but no distribution ID was available for cache invalidation. You may need to manually invalidate the cache.',
                                    },
                                ],
                            }

                    logger.info(f'Found CloudFront distribution: {distribution_id}')

                    # Create CloudFront invalidation to clear the cache
                    logger.info(
                        f'Creating CloudFront invalidation for distribution {distribution_id}'
                    )

                    cloudfront_client.create_invalidation(
                        DistributionId=distribution_id,
                        InvalidationBatch={
                            'Paths': {'Quantity': 1, 'Items': ['/*']},
                            'CallerReference': str(int(datetime.datetime.now().timestamp())),
                        },
                    )

                    logger.info('CloudFront invalidation created successfully')

                # Return success response
                return {
                    'status': 'success',
                    'message': f'Frontend assets updated successfully for {project_name}',
                    'content': [
                        {
                            'type': 'text',
                            'text': f'Frontend assets for {project_name} have been successfully updated.',
                        },
                        {
                            'type': 'text',
                            'text': f'Assets were uploaded to S3 bucket: {bucket_name}',
                        },
                        {
                            'type': 'text',
                            'text': 'CloudFront cache invalidation has been initiated and may take a few minutes to complete.',
                        }
                        if cloudfront_output
                        else {
                            'type': 'text',
                            'text': 'No CloudFront distribution found, so no cache invalidation was needed.',
                        },
                    ],
                }

            except Exception as e:
                logger.error(f'Error getting CloudFormation stack: {str(e)}')

                # Check if the error is because the stack doesn't exist
                if 'does not exist' in str(e):
                    return {
                        'status': 'error',
                        'message': f'CloudFormation stack {stack_name} does not exist. Please deploy the application first.',
                        'content': [
                            {
                                'type': 'text',
                                'text': f'Error: CloudFormation stack {stack_name} does not exist. Please deploy the application first using the deploy tool.',
                            }
                        ],
                    }

                # Return general error
                return {
                    'status': 'error',
                    'message': f'Failed to update frontend assets: {str(e)}',
                    'content': [
                        {
                            'type': 'text',
                            'text': f'Error: Failed to update frontend assets: {str(e)}',
                        }
                    ],
                }

        except Exception as e:
            logger.error(f'[UPDATE FRONTEND ERROR] {str(e)}')
            return {
                'status': 'error',
                'message': f'Failed to update frontend assets: {str(e)}',
                'content': [
                    {'type': 'text', 'text': f'Error: Failed to update frontend assets: {str(e)}'}
                ],
            }

    async def _get_all_files(
        self,
        dir_path: str,
        array_of_files: Optional[List[str]] = None,
        base_path: Optional[str] = None,
    ) -> List[str]:
        """Recursively get all files in a directory.

        Args:
            dir_path: Path to the directory
            array_of_files: List of files (used for recursion)
            base_path: Base path for recursion

        Returns:
            List[str]: List of file paths
        """
        if array_of_files is None:
            array_of_files = []

        if base_path is None:
            base_path = dir_path

        files = os.listdir(dir_path)

        for file in files:
            file_path = os.path.join(dir_path, file)
            if os.path.isdir(file_path):
                array_of_files = await self._get_all_files(file_path, array_of_files, base_path)
            else:
                array_of_files.append(file_path)

        return array_of_files

    async def _upload_file_to_s3(
        self, s3_client: Any, file_path: str, bucket_name: str, base_path: str
    ) -> None:
        """Upload a file to S3.

        Args:
            s3_client: Boto3 S3 client
            file_path: Path to the file
            bucket_name: Name of the S3 bucket
            base_path: Base path for calculating S3 key
        """
        # Get the relative path for the S3 key
        key = file_path.replace(base_path, '').lstrip('/')

        # Read the file
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Determine content type
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name, Key=key, Body=file_content, ContentType=content_type
        )

        logger.debug(f'Uploaded {key} to {bucket_name}')

    async def _sync_directory_to_s3(
        self, s3_client: Any, directory_path: str, bucket_name: str
    ) -> None:
        """Sync directory to S3 bucket (upload new/modified files, delete removed files).

        Args:
            s3_client: Boto3 S3 client
            directory_path: Path to the directory
            bucket_name: Name of the S3 bucket
        """
        logger.info(f'Syncing directory {directory_path} to S3 bucket {bucket_name}')

        # Get all local files
        local_files = await self._get_all_files(directory_path)
        local_file_keys = [file.replace(directory_path, '').lstrip('/') for file in local_files]

        # Get all S3 objects
        s3_objects = []
        continuation_token = None

        while True:
            list_kwargs = {'Bucket': bucket_name}
            if continuation_token:
                list_kwargs['ContinuationToken'] = continuation_token

            response = s3_client.list_objects_v2(**list_kwargs)

            if 'Contents' in response:
                for obj in response['Contents']:
                    if 'Key' in obj:
                        s3_objects.append(obj['Key'])

            if not response.get('IsTruncated'):
                break

            continuation_token = response.get('NextContinuationToken')

        # Upload new and modified files
        for local_file in local_files:
            await self._upload_file_to_s3(s3_client, local_file, bucket_name, directory_path)

        # Delete files that exist in S3 but not locally
        for s3_key in s3_objects:
            if s3_key not in local_file_keys:
                logger.debug(f'Deleting {s3_key} from {bucket_name}')
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)

        logger.info(
            f'Sync completed: {len(local_files)} files uploaded, {len(s3_objects) - len(local_file_keys)} files deleted'
        )
