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
from botocore.exceptions import ClientError
from src.config import settings
from typing import BinaryIO


class StorageService:
    """Service for managing file storage in S3."""

    def __init__(self):
        """Initialize StorageService with S3 client."""
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.bucket_name = settings.s3_bucket_name

    def upload_file(self, file_content: BinaryIO, s3_key: str, content_type: str) -> bool:
        """Upload file to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name, Key=s3_key, Body=file_content, ContentType=content_type
            )
            return True
        except ClientError as e:
            raise Exception(f'Failed to upload file to S3: {str(e)}')

    def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            raise Exception(f'Failed to delete file from S3: {str(e)}')

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for file download."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise Exception(f'Failed to generate presigned URL: {str(e)}')

    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


storage_service = StorageService()
