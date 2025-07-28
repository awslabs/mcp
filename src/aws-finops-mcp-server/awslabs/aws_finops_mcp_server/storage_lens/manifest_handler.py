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

"""Manifest handler for S3 Storage Lens data.

This module provides functionality to locate and parse S3 Storage Lens manifest files.
"""

import boto3
import json
import logging
import re
from awslabs.aws_finops_mcp_server.models import (
    ColumnDefinition,
    ManifestFile,
    SchemaFormat,
    SchemaInfo,
)
from typing import Any, Dict
from urllib.parse import urlparse


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManifestHandler:
    """Handler for S3 Storage Lens manifest files."""

    def __init__(self):
        """Initialize the S3 client."""
        self.s3_client = boto3.client('s3')

    async def get_manifest(self, manifest_location: str) -> Dict[str, Any]:
        """Locate and parse the manifest file from S3.

        Args:
            manifest_location: S3 URI to manifest file or folder containing manifest files
                (e.g., 's3://bucket-name/path/to/manifest.json' or 's3://bucket-name/path/to/folder/')

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        # Parse the S3 URI to get bucket and key
        parsed_uri = urlparse(manifest_location)
        bucket = parsed_uri.netloc
        key = parsed_uri.path.lstrip('/')

        if key.endswith('manifest.json'):
            return await self._read_manifest_file(bucket, key)
        else:
            return await self._find_latest_manifest(bucket, key)

    async def _read_manifest_file(self, bucket: str, key: str) -> Dict[str, Any]:
        """Read and parse a manifest file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key for the manifest file

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            manifest_content = json.loads(response['Body'].read().decode('utf-8'))
            return manifest_content
        except Exception as e:
            raise Exception(f'Failed to read manifest file at s3://{bucket}/{key}: {str(e)}')

    async def _find_latest_manifest(self, bucket: str, key: str) -> Dict[str, Any]:
        """Find the latest manifest.json file in the specified S3 location.

        Args:
            bucket: S3 bucket name
            key: S3 prefix to search for manifest files

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        # Ensure key ends with a slash
        if not key.endswith('/'):
            key += '/'

        logger.info(f'Searching for manifest.json files in s3://{bucket}/{key}')

        try:
            # List objects with the prefix and filter for manifest.json files
            manifest_files = []

            # Use pagination to handle large directories
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix=key):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'].endswith('manifest.json'):
                            # Use the ManifestFile model
                            manifest_file = ManifestFile(
                                key=obj['Key'], last_modified=obj['LastModified']
                            )
                            manifest_files.append(manifest_file)

            if not manifest_files:
                raise Exception(f'No manifest.json files found at s3://{bucket}/{key}')

            # Sort by last modified date to get the latest
            latest_manifest = sorted(manifest_files, key=lambda x: x.last_modified, reverse=True)[
                0
            ]

            # Log only the selected latest manifest file
            logger.info(
                f'Selected latest manifest: s3://{bucket}/{latest_manifest.key} (Last Modified: {latest_manifest.last_modified})'
            )

            # Get the content of the latest manifest file
            return await self._read_manifest_file(bucket, latest_manifest.key)

        except Exception as e:
            raise Exception(f'Failed to locate manifest file in s3://{bucket}/{key}: {str(e)}')

    def extract_data_location(self, manifest: Dict[str, Any]) -> str:
        """Extract the S3 location of the data files from the manifest.

        Args:
            manifest: Parsed manifest JSON content

        Returns:
            str: S3 URI to the data files
        """
        report_files = manifest.get('reportFiles', [])

        if not report_files:
            raise Exception('No report files found in manifest')

        # Determine the S3 location of the report files
        sample_file = report_files[0]['key']
        parsed_uri = urlparse(sample_file)

        if not parsed_uri.netloc:
            # If the key is relative, construct the full path
            destination_bucket = manifest.get('destinationBucket', '')
            if destination_bucket.startswith('arn:aws:s3:::'):
                bucket_name = destination_bucket.replace('arn:aws:s3:::', '')
            else:
                bucket_name = destination_bucket

            data_location = f's3://{bucket_name}/{sample_file}'
        else:
            data_location = sample_file

        # Return the directory containing the data files
        return '/'.join(data_location.split('/')[:-1])

    def parse_schema(self, manifest: Dict[str, Any]) -> SchemaInfo:
        """Parse the schema information from the manifest.

        Args:
            manifest: Parsed manifest JSON content

        Returns:
            SchemaInfo: Schema information including format, column definitions, etc.
        """
        report_format = manifest.get('reportFormat', 'CSV')
        report_schema = manifest.get('reportSchema', '')

        if report_format.upper() == 'CSV':
            # For CSV, the schema is a comma-separated list of column names
            columns = report_schema.split(',')
            column_definitions = []

            for column in columns:
                # Default to string type for all columns
                column_definitions.append(ColumnDefinition(name=column.strip(), type='STRING'))

            return SchemaInfo(
                format=SchemaFormat.CSV, columns=column_definitions, skip_header=True
            )
        else:  # Parquet format
            # For Parquet, we need to parse the message schema
            schema_str = report_schema

            # Extract field definitions from the Parquet message schema
            field_pattern = r'required\s+(\w+)\s+(\w+);'
            matches = re.findall(field_pattern, schema_str)

            column_definitions = []
            for match in matches:
                data_type, field_name = match
                # Map Parquet types to Athena types
                if data_type.lower() == 'string':
                    athena_type = 'STRING'
                elif data_type.lower() == 'long':
                    athena_type = 'BIGINT'
                elif data_type.lower() == 'double':
                    athena_type = 'DOUBLE'
                else:
                    athena_type = 'STRING'  # Default to STRING for unknown types

                column_definitions.append(ColumnDefinition(name=field_name, type=athena_type))

            return SchemaInfo(
                format=SchemaFormat.PARQUET, columns=column_definitions, skip_header=False
            )
