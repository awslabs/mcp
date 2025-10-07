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

"""S3 search engine for genomics files."""

import asyncio
from awslabs.aws_healthomics_mcp_server.models import GenomicsFile, SearchConfig
from awslabs.aws_healthomics_mcp_server.search.file_type_detector import FileTypeDetector
from awslabs.aws_healthomics_mcp_server.search.pattern_matcher import PatternMatcher
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from awslabs.aws_healthomics_mcp_server.utils.config_utils import (
    get_genomics_search_config,
    validate_bucket_access_permissions,
)
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import parse_s3_path
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from typing import Any, Dict, List, Optional


class S3SearchEngine:
    """Search engine for genomics files in S3 buckets."""

    def __init__(self, config: SearchConfig):
        """Initialize the S3 search engine.

        Args:
            config: Search configuration containing S3 bucket paths and other settings
        """
        self.config = config
        self.session = get_aws_session()
        self.s3_client = self.session.client('s3')
        self.file_type_detector = FileTypeDetector()
        self.pattern_matcher = PatternMatcher()

    @classmethod
    def from_environment(cls) -> 'S3SearchEngine':
        """Create an S3SearchEngine using configuration from environment variables.

        Returns:
            S3SearchEngine instance configured from environment

        Raises:
            ValueError: If configuration is invalid or S3 access fails
        """
        config = get_genomics_search_config()

        # Validate bucket access during initialization
        try:
            accessible_buckets = validate_bucket_access_permissions()
            # Update config to only include accessible buckets
            config.s3_bucket_paths = accessible_buckets
        except ValueError as e:
            logger.error(f'S3 bucket access validation failed: {e}')
            raise

        return cls(config)

    async def search_buckets(
        self, bucket_paths: List[str], file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search for genomics files across multiple S3 bucket paths.

        Args:
            bucket_paths: List of S3 bucket paths to search
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects matching the search criteria

        Raises:
            ValueError: If bucket paths are invalid
            ClientError: If S3 access fails
        """
        if not bucket_paths:
            logger.warning('No S3 bucket paths provided for search')
            return []

        all_files = []

        # Create tasks for concurrent bucket searches
        tasks = []
        for bucket_path in bucket_paths:
            task = self._search_single_bucket_path(bucket_path, file_type, search_terms)
            tasks.append(task)

        # Execute searches concurrently with semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)

        async def bounded_search(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(
            *[bounded_search(task) for task in tasks], return_exceptions=True
        )

        # Collect results and handle exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f'Error searching bucket path {bucket_paths[i]}: {result}')
            else:
                all_files.extend(result)

        return all_files

    async def _search_single_bucket_path(
        self, bucket_path: str, file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search a single S3 bucket path for genomics files.

        Args:
            bucket_path: S3 bucket path (e.g., 's3://bucket-name/prefix/')
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects found in this bucket path
        """
        try:
            bucket_name, prefix = parse_s3_path(bucket_path)

            # Validate bucket access
            await self._validate_bucket_access(bucket_name)

            # List objects in the bucket with the given prefix
            objects = await self._list_s3_objects(bucket_name, prefix)

            # Filter and convert objects to GenomicsFile instances
            genomics_files = []
            for obj in objects:
                genomics_file = await self._convert_s3_object_to_genomics_file(
                    obj, bucket_name, file_type, search_terms
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.info(f'Found {len(genomics_files)} files in {bucket_path}')
            return genomics_files

        except Exception as e:
            logger.error(f'Error searching bucket path {bucket_path}: {e}')
            raise

    async def _validate_bucket_access(self, bucket_name: str) -> None:
        """Validate that we have access to the specified S3 bucket.

        Args:
            bucket_name: Name of the S3 bucket

        Raises:
            ClientError: If bucket access validation fails
        """
        try:
            # Use head_bucket to check if bucket exists and we have access
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.s3_client.head_bucket, {'Bucket': bucket_name})
            logger.debug(f'Validated access to bucket: {bucket_name}')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ClientError(
                    {
                        'Error': {
                            'Code': 'NoSuchBucket',
                            'Message': f'Bucket {bucket_name} does not exist',
                        }
                    },
                    'HeadBucket',
                )
            elif error_code == '403':
                raise ClientError(
                    {
                        'Error': {
                            'Code': 'AccessDenied',
                            'Message': f'Access denied to bucket {bucket_name}',
                        }
                    },
                    'HeadBucket',
                )
            else:
                raise

    async def _list_s3_objects(self, bucket_name: str, prefix: str) -> List[Dict[str, Any]]:
        """List objects in an S3 bucket with the given prefix.

        Args:
            bucket_name: Name of the S3 bucket
            prefix: Object key prefix to filter by

        Returns:
            List of S3 object dictionaries
        """
        objects = []
        continuation_token = None

        while True:
            try:
                # Prepare list_objects_v2 parameters
                params = {
                    'Bucket': bucket_name,
                    'Prefix': prefix,
                    'MaxKeys': 1000,  # AWS maximum
                }

                if continuation_token:
                    params['ContinuationToken'] = continuation_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, self.s3_client.list_objects_v2, params)

                # Add objects from this page
                if 'Contents' in response:
                    objects.extend(response['Contents'])

                # Check if there are more pages
                if response.get('IsTruncated', False):
                    continuation_token = response.get('NextContinuationToken')
                else:
                    break

            except ClientError as e:
                logger.error(
                    f'Error listing objects in bucket {bucket_name} with prefix {prefix}: {e}'
                )
                raise

        logger.debug(f'Listed {len(objects)} objects in s3://{bucket_name}/{prefix}')
        return objects

    async def _convert_s3_object_to_genomics_file(
        self,
        s3_object: Dict[str, Any],
        bucket_name: str,
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> Optional[GenomicsFile]:
        """Convert an S3 object to a GenomicsFile if it matches the search criteria.

        Args:
            s3_object: S3 object dictionary from list_objects_v2
            bucket_name: Name of the S3 bucket
            file_type_filter: Optional file type to filter by
            search_terms: List of search terms to match against

        Returns:
            GenomicsFile object if the file matches criteria, None otherwise
        """
        key = s3_object['Key']
        s3_path = f's3://{bucket_name}/{key}'

        # Detect file type from extension
        detected_file_type = self.file_type_detector.detect_file_type(key)
        if not detected_file_type:
            # Skip files that are not recognized genomics file types
            return None

        # Apply file type filter if specified
        if file_type_filter and detected_file_type.value != file_type_filter:
            return None

        # Get object tags for pattern matching
        tags = await self._get_object_tags(bucket_name, key)

        # Check if file matches search terms
        if search_terms and not self._matches_search_terms(s3_path, tags, search_terms):
            return None

        # Create GenomicsFile object
        genomics_file = GenomicsFile(
            path=s3_path,
            file_type=detected_file_type,
            size_bytes=s3_object.get('Size', 0),
            storage_class=s3_object.get('StorageClass', 'STANDARD'),
            last_modified=s3_object.get('LastModified', datetime.now()),
            tags=tags,
            source_system='s3',
            metadata={
                'bucket_name': bucket_name,
                'key': key,
                'etag': s3_object.get('ETag', '').strip('"'),
            },
        )

        return genomics_file

    async def _get_object_tags(self, bucket_name: str, key: str) -> Dict[str, str]:
        """Get tags for an S3 object.

        Args:
            bucket_name: Name of the S3 bucket
            key: Object key

        Returns:
            Dictionary of object tags
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self.s3_client.get_object_tagging, {'Bucket': bucket_name, 'Key': key}
            )

            # Convert tag list to dictionary
            tags = {}
            for tag in response.get('TagSet', []):
                tags[tag['Key']] = tag['Value']

            return tags

        except ClientError as e:
            # If we can't get tags (e.g., no permission), return empty dict
            logger.debug(f'Could not get tags for s3://{bucket_name}/{key}: {e}')
            return {}

    def _matches_search_terms(
        self, s3_path: str, tags: Dict[str, str], search_terms: List[str]
    ) -> bool:
        """Check if a file matches the search terms.

        Args:
            s3_path: Full S3 path of the file
            tags: Dictionary of object tags
            search_terms: List of search terms to match against

        Returns:
            True if the file matches the search terms, False otherwise
        """
        if not search_terms:
            return True

        # Use pattern matcher to check if any search term matches the path or tags
        for term in search_terms:
            # Check path match
            path_score = self.pattern_matcher.calculate_path_match_score(s3_path, term)
            if path_score > 0:
                return True

            # Check tag matches
            tag_score = self.pattern_matcher.calculate_tag_match_score(tags, term)
            if tag_score > 0:
                return True

        return False
