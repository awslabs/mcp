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

"""Data import tools for the AWS HealthOmics MCP server."""

import botocore.exceptions
import os
import re
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    create_aws_client,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def parse_s3_uri(s3_uri: str) -> Dict[str, str]:
    """Parse S3 URI into bucket and key components.

    Args:
        s3_uri: S3 URI (e.g., s3://bucket-name/path/to/file)

    Returns:
        Dictionary with bucket and key
    """
    if not s3_uri.startswith('s3://'):
        raise ValueError(f'Invalid S3 URI format: {s3_uri}')

    parsed = urlparse(s3_uri)
    return {'bucket': parsed.netloc, 'key': parsed.path.lstrip('/')}


async def validate_aho_s3_uri_format(
    ctx: Context,
    s3_uri: str = Field(
        ...,
        description='S3 URI to validate (e.g., s3://bucket/path/file.txt)',
    ),
) -> Dict[str, Any]:
    """Validate S3 URI format and syntax.

    Args:
        ctx: MCP context for error reporting
        s3_uri: S3 URI to validate

    Returns:
        Dictionary containing validation results

    Raises:
        Exception: If there's an error validating the S3 URI
    """
    try:
        # Basic format validation
        if not isinstance(s3_uri, str):
            return {'valid': False, 'error': 'S3 URI must be a string', 's3Uri': s3_uri}

        if not s3_uri.startswith('s3://'):
            return {'valid': False, 'error': 'S3 URI must start with s3://', 's3Uri': s3_uri}

        try:
            parsed = parse_s3_uri(s3_uri)
        except ValueError as e:
            return {'valid': False, 'error': str(e), 's3Uri': s3_uri}

        # Validate bucket name
        bucket = parsed['bucket']
        if not bucket:
            return {'valid': False, 'error': 'Bucket name cannot be empty', 's3Uri': s3_uri}

        # Basic bucket name validation (simplified)
        if not re.match(r'^[a-z0-9][a-z0-9\-\.]*[a-z0-9]$', bucket):
            return {'valid': False, 'error': 'Invalid bucket name format', 's3Uri': s3_uri}

        return {'valid': True, 'bucket': bucket, 'key': parsed['key'], 's3Uri': s3_uri}

    except Exception as e:
        logger.error(f'Unexpected error validating S3 URI: {str(e)}')
        return {'valid': False, 'error': f'Validation error: {str(e)}', 's3Uri': s3_uri}


async def discover_aho_genomic_files(
    ctx: Context,
    s3_uri: str = Field(
        ...,
        description='S3 URI to search for genomic files (e.g., s3://bucket/genomics/)',
    ),
    file_types: Optional[List[str]] = Field(
        None,
        description='List of file types to search for (default: FASTQ, BAM, CRAM, VCF)',
    ),
    max_files: int = Field(
        1000,
        description='Maximum number of files to discover',
        ge=1,
        le=10000,
    ),
) -> Dict[str, Any]:
    """Auto-discover genomic files in S3 location.

    Args:
        ctx: MCP context for error reporting
        s3_uri: S3 URI to search in
        file_types: List of file types to search for
        max_files: Maximum number of files to discover

    Returns:
        Dictionary containing discovered genomic files

    Raises:
        Exception: If there's an error discovering files
    """
    try:
        # Validate S3 URI
        validation_result = await validate_aho_s3_uri_format(ctx, s3_uri)
        if not validation_result['valid']:
            raise Exception(f'Invalid S3 URI: {validation_result["error"]}')

        # Default file types for genomic data
        if file_types is None:
            file_types = ['FASTQ', 'BAM', 'CRAM', 'VCF', 'FASTA', 'FA']

        # File extensions mapping
        extension_map = {
            'FASTQ': ['.fastq', '.fq', '.fastq.gz', '.fq.gz'],
            'BAM': ['.bam'],
            'CRAM': ['.cram'],
            'VCF': ['.vcf', '.vcf.gz'],
            'FASTA': ['.fasta', '.fa', '.fasta.gz', '.fa.gz'],
            'FA': ['.fa', '.fa.gz'],
        }

        # Build list of extensions to search for
        target_extensions = []
        for file_type in file_types:
            if file_type.upper() in extension_map:
                target_extensions.extend(extension_map[file_type.upper()])

        s3_client = create_aws_client('s3')
        parsed = parse_s3_uri(s3_uri)

        discovered_files = []

        # List objects in S3
        paginator = s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(
            Bucket=parsed['bucket'], Prefix=parsed['key'], MaxKeys=max_files
        ):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                file_name = os.path.basename(key)

                # Check if file matches any target extensions
                for ext in target_extensions:
                    if file_name.lower().endswith(ext.lower()):
                        # Determine file type
                        detected_type = None
                        for ft, extensions in extension_map.items():
                            if any(file_name.lower().endswith(e.lower()) for e in extensions):
                                detected_type = ft
                                break

                        discovered_files.append(
                            {
                                'fileName': file_name,
                                'fileType': detected_type,
                                's3Uri': f's3://{parsed["bucket"]}/{key}',
                                'size': obj['Size'],
                                'lastModified': obj['LastModified'].isoformat(),
                                'etag': obj['ETag'].strip('"'),
                            }
                        )
                        break

                if len(discovered_files) >= max_files:
                    break

            if len(discovered_files) >= max_files:
                break

        return {
            'discoveredFiles': discovered_files,
            'totalCount': len(discovered_files),
            'searchLocation': s3_uri,
            'searchedFileTypes': file_types,
            'maxFilesReached': len(discovered_files) >= max_files,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to discover genomic files: {error_code} - {error_message}')

        raise Exception(f'Failed to discover genomic files: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error discovering genomic files: {str(e)}')
        raise Exception(f'Failed to discover genomic files: {str(e)}')


async def list_aho_s3_bucket_contents(
    ctx: Context,
    s3_uri: str = Field(
        ...,
        description='S3 URI to browse (e.g., s3://bucket/path/)',
    ),
    pattern: Optional[str] = Field(
        None,
        description='File name pattern to filter by (supports wildcards)',
    ),
    max_keys: int = Field(
        1000,
        description='Maximum number of objects to list',
        ge=1,
        le=10000,
    ),
) -> Dict[str, Any]:
    """Browse S3 bucket contents with optional filtering.

    Args:
        ctx: MCP context for error reporting
        s3_uri: S3 URI to browse
        pattern: File name pattern to filter by
        max_keys: Maximum number of objects to list

    Returns:
        Dictionary containing S3 object listing

    Raises:
        Exception: If there's an error listing S3 contents
    """
    try:
        # Validate S3 URI
        validation_result = await validate_aho_s3_uri_format(ctx, s3_uri)
        if not validation_result['valid']:
            raise Exception(f'Invalid S3 URI: {validation_result["error"]}')

        s3_client = create_aws_client('s3')
        parsed = parse_s3_uri(s3_uri)

        objects = []

        # List objects in S3
        paginator = s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(
            Bucket=parsed['bucket'], Prefix=parsed['key'], MaxKeys=max_keys
        ):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                file_name = os.path.basename(key)

                # Apply pattern filter if specified
                if pattern:
                    import fnmatch

                    if not fnmatch.fnmatch(file_name, pattern):
                        continue

                objects.append(
                    {
                        'key': key,
                        'fileName': file_name,
                        's3Uri': f's3://{parsed["bucket"]}/{key}',
                        'size': obj['Size'],
                        'lastModified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"'),
                        'storageClass': obj.get('StorageClass', 'STANDARD'),
                    }
                )

                if len(objects) >= max_keys:
                    break

            if len(objects) >= max_keys:
                break

        return {
            'objects': objects,
            'totalCount': len(objects),
            'bucketLocation': s3_uri,
            'appliedPattern': pattern,
            'maxKeysReached': len(objects) >= max_keys,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list S3 bucket contents: {error_code} - {error_message}')

        raise Exception(f'Failed to list S3 bucket contents: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing S3 bucket contents: {str(e)}')
        raise Exception(f'Failed to list S3 bucket contents: {str(e)}')


async def get_aho_s3_file_metadata(
    ctx: Context,
    s3_uri: str = Field(
        ...,
        description='S3 URI of the file to get metadata for',
    ),
) -> Dict[str, Any]:
    """Get metadata for a specific S3 file.

    Args:
        ctx: MCP context for error reporting
        s3_uri: S3 URI of the file

    Returns:
        Dictionary containing file metadata

    Raises:
        Exception: If there's an error retrieving file metadata
    """
    try:
        # Validate S3 URI
        validation_result = await validate_aho_s3_uri_format(ctx, s3_uri)
        if not validation_result['valid']:
            raise Exception(f'Invalid S3 URI: {validation_result["error"]}')

        s3_client = create_aws_client('s3')
        parsed = parse_s3_uri(s3_uri)

        # Get object metadata
        response = s3_client.head_object(Bucket=parsed['bucket'], Key=parsed['key'])

        return {
            'fileMetadata': {
                's3Uri': s3_uri,
                'bucket': parsed['bucket'],
                'key': parsed['key'],
                'fileName': os.path.basename(parsed['key']),
                'size': response['ContentLength'],
                'lastModified': response['LastModified'].isoformat(),
                'etag': response['ETag'].strip('"'),
                'contentType': response.get('ContentType'),
                'storageClass': response.get('StorageClass', 'STANDARD'),
                'serverSideEncryption': response.get('ServerSideEncryption'),
                'metadata': response.get('Metadata', {}),
            }
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        if error_code == 'NoSuchKey':
            raise Exception(f'File not found: {s3_uri}')
        elif error_code == 'NoSuchBucket':
            raise Exception(f'Bucket not found: {parsed["bucket"]}')
        else:
            logger.error(f'Failed to get S3 file metadata: {error_code} - {error_message}')
            raise Exception(f'Failed to get S3 file metadata: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting S3 file metadata: {str(e)}')
        raise Exception(f'Failed to get S3 file metadata: {str(e)}')


async def prepare_aho_import_sources(
    ctx: Context,
    files: List[Dict[str, Any]] = Field(
        ...,
        description='List of file information to prepare for import',
    ),
    sample_id: Optional[str] = Field(
        None,
        description='Sample ID for the import',
    ),
    subject_id: Optional[str] = Field(
        None,
        description='Subject ID for the import',
    ),
    reference_arn: Optional[str] = Field(
        None,
        description='Reference ARN to use for the import',
    ),
) -> Dict[str, Any]:
    """Prepare source file configurations for HealthOmics import operations.

    Args:
        ctx: MCP context for error reporting
        files: List of file information
        sample_id: Sample ID for the import
        subject_id: Subject ID for the import
        reference_arn: Reference ARN to use

    Returns:
        Dictionary containing prepared import sources

    Raises:
        Exception: If there's an error preparing import sources
    """
    try:
        prepared_sources = []

        for file_info in files:
            s3_uri = file_info.get('s3Uri') or file_info.get('s3_uri')
            file_type = file_info.get('fileType') or file_info.get('file_type', 'FASTQ')

            if not s3_uri:
                raise Exception(f'Missing s3Uri in file info: {file_info}')

            # Validate S3 URI
            validation_result = await validate_aho_s3_uri_format(ctx, s3_uri)
            if not validation_result['valid']:
                raise Exception(f'Invalid S3 URI: {validation_result["error"]}')

            source_config = {
                'sourceFileType': file_type.upper(),
                'sourceFiles': {'source1': s3_uri},
            }

            # Add metadata
            if sample_id:
                source_config['sampleId'] = sample_id
            if subject_id:
                source_config['subjectId'] = subject_id
            if reference_arn:
                source_config['referenceArn'] = reference_arn

            # For paired-end FASTQ files, check for R2
            if file_type.upper() == 'FASTQ':
                file_name = os.path.basename(s3_uri)
                if '_R1' in file_name or '_1.fastq' in file_name:
                    # Look for corresponding R2 file
                    r2_uri = s3_uri.replace('_R1', '_R2').replace('_1.fastq', '_2.fastq')

                    # Check if R2 file exists in the provided files
                    for other_file in files:
                        other_uri = other_file.get('s3Uri') or other_file.get('s3_uri')
                        if other_uri == r2_uri:
                            source_config['sourceFiles']['source2'] = r2_uri
                            break

            prepared_sources.append(source_config)

        return {
            'importSources': prepared_sources,
            'totalFiles': len(prepared_sources),
            'configuration': {
                'sampleId': sample_id,
                'subjectId': subject_id,
                'referenceArn': reference_arn,
            },
        }

    except Exception as e:
        logger.error(f'Unexpected error preparing import sources: {str(e)}')
        raise Exception(f'Failed to prepare import sources: {str(e)}')
