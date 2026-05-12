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

"""S3 utility functions for the HealthOmics MCP server."""

from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from awslabs.aws_healthomics_mcp_server.utils.path_utils import validate_s3_uri_format
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from typing import List, Optional, Tuple
from urllib.parse import urlparse


def ensure_s3_uri_ends_with_slash(uri: str) -> str:
    """Ensure an S3 URI begins with s3:// and ends with a slash.

    Args:
        uri: S3 URI

    Returns:
        str: S3 URI with trailing slash

    Raises:
        ValueError: If the URI doesn't start with s3://
    """
    if not uri.startswith('s3://'):
        raise ValueError(f'URI must start with s3://: {uri}')

    if not uri.endswith('/'):
        uri += '/'

    return uri


def parse_s3_path(s3_path: str) -> Tuple[str, str]:
    """Parse an S3 path into bucket name and prefix.

    Args:
        s3_path: S3 path (e.g., 's3://bucket-name/prefix/')

    Returns:
        Tuple of (bucket_name, prefix)

    Raises:
        ValueError: If the S3 path is invalid
    """
    if not s3_path.startswith('s3://'):
        raise ValueError(f"Invalid S3 path format: {s3_path}. Must start with 's3://'")

    parsed = urlparse(s3_path)
    bucket_name = parsed.netloc
    prefix = parsed.path.lstrip('/')

    if not bucket_name:
        raise ValueError(f'Invalid S3 path format: {s3_path}. Missing bucket name')

    return bucket_name, prefix


def is_valid_bucket_name(bucket_name: str) -> bool:
    """Perform basic validation of S3 bucket name format.

    Args:
        bucket_name: Bucket name to validate

    Returns:
        True if bucket name appears valid, False otherwise
    """
    # Basic validation - AWS has more complex rules, but this covers common cases
    if not bucket_name:
        return False

    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False

    # Must start and end with alphanumeric
    if not (bucket_name[0].isalnum() and bucket_name[-1].isalnum()):
        return False

    # Can contain lowercase letters, numbers, hyphens, and periods
    allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-.')
    if not all(c in allowed_chars for c in bucket_name):
        return False

    return True


def validate_and_normalize_s3_path(s3_path: str) -> str:
    """Validate and normalize an S3 path.

    Args:
        s3_path: S3 path to validate

    Returns:
        Normalized S3 path with trailing slash

    Raises:
        ValueError: If the S3 path is invalid
    """
    if not s3_path.startswith('s3://'):
        raise ValueError("S3 path must start with 's3://'")

    # Parse the URL to validate structure
    bucket_name, _ = parse_s3_path(s3_path)

    # Validate bucket name format (basic validation)
    if not is_valid_bucket_name(bucket_name):
        raise ValueError(f'Invalid bucket name: {bucket_name}')

    # Ensure path ends with slash for consistent prefix matching
    return ensure_s3_uri_ends_with_slash(s3_path)


def validate_bucket_access(bucket_paths: List[str]) -> List[str]:
    """Validate that we have access to S3 buckets from the given paths.

    Args:
        bucket_paths: List of S3 bucket paths to validate

    Returns:
        List of bucket paths that are accessible

    Raises:
        ValueError: If no buckets are accessible
    """
    if not bucket_paths:
        raise ValueError('No S3 bucket paths provided')

    session = get_aws_session()
    s3_client = session.client('s3')

    # Parse and deduplicate bucket names while preserving path mapping
    bucket_to_paths = {}
    errors = []

    for bucket_path in bucket_paths:
        try:
            # Validate S3 path format first
            if not bucket_path.startswith('s3://'):
                raise ValueError(f"Invalid S3 path format: {bucket_path}. Must start with 's3://'")

            # Parse bucket name from path
            bucket_name, _ = parse_s3_path(bucket_path)

            # Group paths by bucket name
            if bucket_name not in bucket_to_paths:
                bucket_to_paths[bucket_name] = []
            bucket_to_paths[bucket_name].append(bucket_path)

        except ValueError as e:
            errors.append(str(e))
            continue

    # If we couldn't parse any valid paths, raise error
    if not bucket_to_paths:
        error_summary = 'No valid S3 bucket paths found. Errors: ' + '; '.join(errors)
        raise ValueError(error_summary)

    # Test access for each unique bucket
    accessible_buckets = []

    for bucket_name, paths in bucket_to_paths.items():
        try:
            # Test bucket access (only once per unique bucket)
            s3_client.head_bucket(Bucket=bucket_name)

            # If successful, add all paths for this bucket
            accessible_buckets.extend(paths)
            logger.info(f'Validated access to bucket: {bucket_name}')

        except NoCredentialsError:
            error_msg = 'AWS credentials not found'
            logger.error(error_msg)
            errors.append(error_msg)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                error_msg = f'Bucket {bucket_name} does not exist'
            elif error_code == '403':
                error_msg = f'Access denied to bucket {bucket_name}'
            else:
                error_msg = f'Error accessing bucket {bucket_name}: {e}'

            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f'Unexpected error accessing bucket {bucket_name}: {e}'
            logger.error(error_msg)
            errors.append(error_msg)

    if not accessible_buckets:
        error_summary = 'No S3 buckets are accessible. Errors: ' + '; '.join(errors)
        raise ValueError(error_summary)

    if errors:
        logger.warning(f'Some buckets are not accessible: {"; ".join(errors)}')

    return accessible_buckets


def validate_s3_bucket_for_write(
    s3_client,
    bucket: str,
    expected_bucket_owner: Optional[str] = None,
) -> None:
    """Validate that an S3 bucket exists, is accessible, and optionally owned by the expected account.

    Args:
        s3_client: A boto3 S3 client.
        bucket: The bucket name.
        expected_bucket_owner: AWS account ID for owner verification. None skips the check.

    Raises:
        ValueError: If the bucket does not exist, is not accessible, or owner mismatch.
        NoCredentialsError: If AWS credentials are not available.
    """
    try:
        head_bucket_args = {'Bucket': bucket}
        if expected_bucket_owner is not None:
            head_bucket_args['ExpectedBucketOwner'] = expected_bucket_owner
        s3_client.head_bucket(**head_bucket_args)
    except NoCredentialsError:
        raise
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            raise ValueError(f'S3 bucket does not exist: {bucket}')
        elif error_code == '403':
            if expected_bucket_owner is not None:
                raise ValueError(
                    f'Access denied to S3 bucket: {bucket}. '
                    f'The bucket may not be owned by account {expected_bucket_owner}.'
                )
            raise ValueError(f'Access denied to S3 bucket: {bucket}')
        else:
            raise ValueError(f'Error accessing S3 bucket {bucket}: {e}')


def write_svg_to_s3(
    svg_content: str,
    s3_path: str,
    expected_bucket_owner: Optional[str] = None,
) -> str:
    """Parse S3 path, validate bucket, check no-overwrite, and upload SVG.

    Args:
        svg_content: The SVG string to upload.
        s3_path: The S3 URI (s3://bucket/key).
        expected_bucket_owner: AWS account ID for owner verification. None skips the check.

    Returns:
        The S3 URI where the object was written.

    Raises:
        ValueError: If path parsing or bucket validation fails.
        FileExistsError: If an object already exists at the key.
        ClientError: If the S3 upload fails.
    """
    bucket, key = validate_s3_uri_format(s3_path)

    if not key:
        raise ValueError(f'Invalid S3 URI format: {s3_path}. Missing object key')

    session = get_aws_session()
    s3_client = session.client('s3')

    validate_s3_bucket_for_write(s3_client, bucket, expected_bucket_owner)

    # Check that the object does not already exist (no-overwrite)
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        # If head_object succeeds, the object exists — refuse to overwrite
        raise FileExistsError(f'S3 object already exists: {s3_path}')
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ('404'):
            # Object does not exist — this is the expected case
            pass
        else:
            raise

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=svg_content.encode('utf-8'),
        ContentType='image/svg+xml',
    )

    return s3_path


def write_zip_to_s3(
    zip_data: bytes,
    s3_path: str,
    expected_bucket_owner: Optional[str] = None,
) -> str:
    """Parse S3 path, validate bucket, check no-overwrite, and upload a ZIP archive.

    Args:
        zip_data: The raw ZIP bytes to upload.
        s3_path: The S3 URI (s3://bucket/key).
        expected_bucket_owner: AWS account ID for owner verification. None skips the check.

    Returns:
        The S3 URI where the object was written.

    Raises:
        ValueError: If path parsing or bucket validation fails.
        FileExistsError: If an object already exists at the key.
        ClientError: If the S3 upload fails.
    """
    bucket, key = validate_s3_uri_format(s3_path)

    if not key:
        raise ValueError(f'Invalid S3 URI format: {s3_path}. Missing object key')

    session = get_aws_session()
    s3_client = session.client('s3')

    validate_s3_bucket_for_write(s3_client, bucket, expected_bucket_owner)

    # Check that the object does not already exist (no-overwrite)
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        raise FileExistsError(f'S3 object already exists: {s3_path}')
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ('404'):
            pass
        else:
            raise

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=zip_data,
        ContentType='application/zip',
    )

    return s3_path
