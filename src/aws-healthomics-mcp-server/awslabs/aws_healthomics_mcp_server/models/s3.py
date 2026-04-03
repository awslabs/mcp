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

"""S3 file models and utilities for handling S3 objects."""

from awslabs.aws_healthomics_mcp_server.consts import (
    FASTQ_EXTENSIONS,
    FASTQ_PAIR_PATTERNS,
    GENOMICS_INDEX_PATTERNS,
)
from dataclasses import field
from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


class S3File(BaseModel):
    """Centralized model for handling S3 files with URI construction and validation."""

    bucket: str
    key: str
    version_id: Optional[str] = None
    size_bytes: Optional[int] = None
    last_modified: Optional[datetime] = None
    storage_class: Optional[str] = None
    etag: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    @field_validator('bucket')
    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """Validate S3 bucket name format according to AWS naming rules.

        See: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
        """
        if not v:
            raise ValueError('Bucket name cannot be empty')

        # Length validation
        if len(v) < 3 or len(v) > 63:
            raise ValueError('Bucket name must be between 3 and 63 characters')

        # Can only contain lowercase letters, numbers, hyphens, and periods
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-.')
        if not all(c in allowed_chars for c in v):
            raise ValueError(
                'Bucket name can only contain lowercase letters, numbers, hyphens, and periods'
            )

        # Must start and end with a letter or number
        if not (v[0].isalnum() and v[-1].isalnum()):
            raise ValueError('Bucket name must begin and end with a letter or number')

        # Must not contain two adjacent periods
        if '..' in v:
            raise ValueError('Bucket name must not contain two adjacent periods')

        # Must not be formatted as an IP address
        parts = v.split('.')
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            raise ValueError('Bucket name must not be formatted as an IP address')

        # Must not start with reserved prefixes
        if v.startswith('xn--'):
            raise ValueError('Bucket name must not start with the prefix "xn--"')
        if v.startswith('sthree-'):
            raise ValueError('Bucket name must not start with the prefix "sthree-"')
        if v.startswith('amzn-s3-demo-'):
            raise ValueError('Bucket name must not start with the prefix "amzn-s3-demo-"')

        # Must not end with reserved suffixes
        if v.endswith('-s3alias'):
            raise ValueError('Bucket name must not end with the suffix "-s3alias"')
        if v.endswith('--ol-s3'):
            raise ValueError('Bucket name must not end with the suffix "--ol-s3"')
        if v.endswith('.mrap'):
            raise ValueError('Bucket name must not end with the suffix ".mrap"')
        if v.endswith('--x-s3'):
            raise ValueError('Bucket name must not end with the suffix "--x-s3"')
        if v.endswith('--table-s3'):
            raise ValueError('Bucket name must not end with the suffix "--table-s3"')

        return v

    @field_validator('key')
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate S3 object key."""
        if not v:
            raise ValueError('Object key cannot be empty')

        # S3 keys can be up to 1024 characters
        if len(v) > 1024:
            raise ValueError('Object key cannot exceed 1024 characters')

        return v

    @property
    def uri(self) -> str:
        """Get the complete S3 URI for this file."""
        return f's3://{self.bucket}/{self.key}'

    @property
    def arn(self) -> str:
        """Get the S3 ARN for this file."""
        if self.version_id:
            return f'arn:aws:s3:::{self.bucket}/{self.key}?versionId={self.version_id}'
        return f'arn:aws:s3:::{self.bucket}/{self.key}'

    @property
    def console_url(self) -> str:
        """Get the AWS Console URL for this S3 object."""
        # URL encode the key for console compatibility
        from urllib.parse import quote

        encoded_key = quote(self.key, safe='/')
        return f'https://s3.console.aws.amazon.com/s3/object/{self.bucket}?prefix={encoded_key}'

    @property
    def filename(self) -> str:
        """Extract the filename from the S3 key."""
        return self.key.split('/')[-1] if '/' in self.key else self.key

    @property
    def directory(self) -> str:
        """Extract the directory path from the S3 key."""
        if '/' not in self.key:
            return ''
        return '/'.join(self.key.split('/')[:-1])

    @property
    def extension(self) -> str:
        """Extract the file extension from the filename."""
        filename = self.filename
        if '.' not in filename:
            return ''
        return filename.split('.')[-1].lower()

    def get_presigned_url(self, expiration: int = 3600, client_method: str = 'get_object') -> str:
        """Generate a presigned URL for this S3 object.

        Args:
            expiration: URL expiration time in seconds (default: 1 hour)
            client_method: S3 client method to use (default: 'get_object')

        Returns:
            Presigned URL string

        Note:
            This method requires an S3 client to be available in the calling context.
        """
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session

        session = get_aws_session()
        s3_client = session.client('s3')

        params = {'Bucket': self.bucket, 'Key': self.key}
        if self.version_id and client_method == 'get_object':
            params['VersionId'] = self.version_id

        return s3_client.generate_presigned_url(client_method, Params=params, ExpiresIn=expiration)

    @classmethod
    def from_uri(cls, uri: str, **kwargs) -> 'S3File':
        """Create an S3File instance from an S3 URI.

        Args:
            uri: S3 URI (e.g., 's3://bucket/path/to/file.txt')
            **kwargs: Additional fields to set on the S3File instance

        Returns:
            S3File instance

        Raises:
            ValueError: If the URI format is invalid
        """
        if not uri.startswith('s3://'):
            raise ValueError(f"Invalid S3 URI format: {uri}. Must start with 's3://'")

        parsed = urlparse(uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')

        if not bucket:
            raise ValueError(f'Invalid S3 URI format: {uri}. Missing bucket name')

        if not key:
            raise ValueError(f'Invalid S3 URI format: {uri}. Missing object key')

        return cls(bucket=bucket, key=key, **kwargs)

    @classmethod
    def from_bucket_and_key(cls, bucket: str, key: str, **kwargs) -> 'S3File':
        """Create an S3File instance from bucket and key.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            **kwargs: Additional fields to set on the S3File instance

        Returns:
            S3File instance
        """
        return cls(bucket=bucket, key=key, **kwargs)

    def with_key(self, new_key: str) -> 'S3File':
        """Create a new S3File instance with a different key in the same bucket.

        Args:
            new_key: New object key

        Returns:
            New S3File instance
        """
        return self.model_copy(update={'key': new_key})

    def with_suffix(self, suffix: str) -> 'S3File':
        """Create a new S3File instance with a suffix added to the key.

        Args:
            suffix: Suffix to add to the key

        Returns:
            New S3File instance
        """
        return self.with_key(f'{self.key}{suffix}')

    def with_extension(self, extension: str) -> 'S3File':
        """Create a new S3File instance with a different file extension.

        Args:
            extension: New file extension (without the dot)

        Returns:
            New S3File instance
        """
        base_key = self.key
        if '.' in self.filename:
            # Remove existing extension
            parts = base_key.split('.')
            base_key = '.'.join(parts[:-1])

        return self.with_key(f'{base_key}.{extension}')

    def is_in_directory(self, directory_path: str) -> bool:
        """Check if this file is in the specified directory.

        Args:
            directory_path: Directory path to check (without trailing slash)

        Returns:
            True if the file is in the directory
        """
        if not directory_path:
            return '/' not in self.key

        normalized_dir = directory_path.rstrip('/')
        return self.key.startswith(f'{normalized_dir}/')

    def get_relative_path(self, base_directory: str = '') -> str:
        """Get the relative path from a base directory.

        Args:
            base_directory: Base directory path (without trailing slash)

        Returns:
            Relative path from the base directory
        """
        if not base_directory:
            return self.key

        normalized_base = base_directory.rstrip('/')
        if self.key.startswith(f'{normalized_base}/'):
            return self.key[len(normalized_base) + 1 :]

        return self.key

    def __str__(self) -> str:
        """String representation returns the S3 URI."""
        return self.uri

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f'S3File(bucket="{self.bucket}", key="{self.key}")'


# S3 File Utility Functions


def create_s3_file_from_object(
    bucket: str, s3_object: Dict[str, Any], tags: Optional[Dict[str, str]] = None
) -> S3File:
    """Create an S3File instance from an S3 object dictionary.

    Args:
        bucket: S3 bucket name
        s3_object: S3 object dictionary from list_objects_v2 or similar
        tags: Optional tags dictionary

    Returns:
        S3File instance
    """
    return S3File(
        bucket=bucket,
        key=s3_object['Key'],
        size_bytes=s3_object.get('Size'),
        last_modified=s3_object.get('LastModified'),
        storage_class=s3_object.get('StorageClass'),
        etag=s3_object.get('ETag', '').strip('"'),  # Remove quotes from ETag
        tags=tags or {},
    )


def build_s3_uri(bucket: str, key: str) -> str:
    """Build an S3 URI from bucket and key components.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Complete S3 URI

    Raises:
        ValueError: If bucket or key is invalid
    """
    if not bucket:
        raise ValueError('Bucket name cannot be empty')
    if not key:
        raise ValueError('Object key cannot be empty')

    return f's3://{bucket}/{key}'


def parse_s3_uri(uri: str) -> Tuple[str, str]:
    """Parse an S3 URI into bucket and key components.

    Args:
        uri: S3 URI (e.g., 's3://bucket/path/to/file.txt')

    Returns:
        Tuple of (bucket, key)

    Raises:
        ValueError: If the URI format is invalid
    """
    if not uri.startswith('s3://'):
        raise ValueError(f"Invalid S3 URI format: {uri}. Must start with 's3://'")

    parsed = urlparse(uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')

    if not bucket:
        raise ValueError(f'Invalid S3 URI format: {uri}. Missing bucket name')

    if not key:
        raise ValueError(f'Invalid S3 URI format: {uri}. Missing object key')

    return bucket, key


def get_s3_file_associations(primary_file: S3File) -> List[S3File]:
    """Get potential associated files for a primary S3 file based on naming conventions.

    Args:
        primary_file: Primary S3File to find associations for

    Returns:
        List of potential associated S3File instances

    Note:
        This function generates potential associations based on common patterns.
        The actual existence of these files should be verified separately.
    """
    associations = []

    # Check for index files using patterns from consts
    for ext, index_exts in GENOMICS_INDEX_PATTERNS.items():
        if primary_file.key.endswith(ext):
            for index_ext in index_exts:
                if index_ext.startswith(ext):
                    # Full extension replacement (e.g., .bam -> .bam.bai)
                    index_key = f'{primary_file.key}{index_ext[len(ext) :]}'
                else:
                    # Replace extension (e.g., .bam -> .bai)
                    base_key = primary_file.key[: -len(ext)]
                    index_key = f'{base_key}{index_ext}'

                associations.append(S3File(bucket=primary_file.bucket, key=index_key))

    # FASTQ pair patterns (R1/R2) - check extension properly
    filename = primary_file.filename
    if any(filename.endswith(f'.{ext}') for ext in FASTQ_EXTENSIONS):
        key = primary_file.key

        # Look for paired-end read patterns using patterns from consts
        for pattern1, pattern2 in FASTQ_PAIR_PATTERNS:
            if pattern1 in key:
                pair_key = key.replace(pattern1, pattern2)
                associations.append(S3File(bucket=primary_file.bucket, key=pair_key))
                break  # Only match the first pattern found

    return associations
