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

"""Artifact upload helpers for HITL task responses and file uploads.

Ported from upload-helper.ts. Provides the 3-step upload flow:
  1. CreateArtifactUploadUrl (get pre-signed URL + artifactId)
  2. PUT content to S3
  3. CompleteArtifactUpload
"""

import base64
import hashlib
import httpx
import os
from awslabs.aws_transform_mcp_server.file_validation import validate_read_path
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    ArtifactReference,
    ArtifactType,
    CompleteArtifactUploadRequest,
    ContentDigest,
    CreateArtifactUploadUrlRequest,
    FileMetadata,
)
from typing import Dict, List, Optional


# Maximum file size for uploads (500 MB).
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


def _flatten_request_headers(
    request_headers: Optional[Dict[str, List[str]]],
) -> Dict[str, str]:
    """Flatten multi-value header lists into single comma-separated strings."""
    if not request_headers:
        return {}
    result: Dict[str, str] = {}
    for key, values in request_headers.items():
        if values:
            result[key] = ', '.join(values)
    return result


async def upload_json_artifact(
    workspace_id: str,
    job_id: str,
    content: str,
) -> str:
    """Upload a JSON string as an artifact and return the artifactId.

    3-step flow:
      1. SHA256 of content bytes -> base64 digest
      2. CreateArtifactUploadUrl -> get pre-signed URL + artifactId
      3. PUT to S3 + CompleteArtifactUpload

    Args:
        workspace_id: The workspace identifier.
        job_id: The job identifier.
        content: JSON string to upload.

    Returns:
        The artifactId of the uploaded artifact.

    Raises:
        Exception: On upload failure.
    """
    content_bytes = content.encode('utf-8')
    sha256_digest = base64.b64encode(hashlib.sha256(content_bytes).digest()).decode('ascii')

    init_result = await call_transform_api(
        'CreateArtifactUploadUrl',
        CreateArtifactUploadUrlRequest(
            workspaceId=workspace_id,
            jobId=job_id,
            contentDigest=ContentDigest(Sha256=sha256_digest),
            artifactReference=ArtifactReference(
                artifactType=ArtifactType(
                    categoryType='HITL_FROM_USER',
                    fileType='JSON',
                ),
            ),
        ),
    )

    put_headers = _flatten_request_headers(init_result.get('requestHeaders'))

    async with httpx.AsyncClient() as client:
        s3_response = await client.put(
            init_result['s3PreSignedUrl'],
            content=content_bytes,
            headers=put_headers,
        )
        if s3_response.status_code >= 400:
            body = s3_response.text
            error = Exception(
                f'Failed to upload artifact content to storage (HTTP {s3_response.status_code}).'
            )
            error.status_code = s3_response.status_code  # type: ignore[attr-defined]
            error.body = body  # type: ignore[attr-defined]
            raise error

    await call_transform_api(
        'CompleteArtifactUpload',
        CompleteArtifactUploadRequest(
            workspaceId=workspace_id,
            jobId=job_id,
            artifactId=init_result['artifactId'],
        ),
    )

    return init_result['artifactId']


async def upload_file_artifact(
    workspace_id: str,
    job_id: str,
    file_path: str,
    file_type: Optional[str] = None,
    category_type: str = 'HITL_FROM_USER',
) -> str:
    """Upload a binary file to the artifact store. Returns the artifact ID.

    Args:
        workspace_id: The workspace identifier.
        job_id: The job identifier.
        file_path: Path to the local file.
        file_type: Override file type (default: 'JSON').
        category_type: Artifact category (default: 'HITL_FROM_USER').

    Returns:
        The artifactId of the uploaded artifact.

    Raises:
        Exception: If file is too large or upload fails.
    """
    file_stat = os.stat(file_path)
    if file_stat.st_size > MAX_FILE_SIZE_BYTES:
        raise Exception(
            f'File too large ({file_stat.st_size / (1024 * 1024):.1f} MB). '
            f'Maximum allowed: {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.'
        )

    validated_path = validate_read_path(file_path)
    with open(validated_path, 'rb') as fh:
        content_bytes = fh.read()

    file_name = os.path.basename(file_path)
    sha256_digest = base64.b64encode(hashlib.sha256(content_bytes).digest()).decode('ascii')

    init_result = await call_transform_api(
        'CreateArtifactUploadUrl',
        CreateArtifactUploadUrlRequest(
            workspaceId=workspace_id,
            jobId=job_id,
            contentDigest=ContentDigest(Sha256=sha256_digest),
            artifactReference=ArtifactReference(
                artifactType=ArtifactType(
                    categoryType=category_type,
                    fileType=file_type or 'JSON',
                ),
            ),
            fileMetadata=FileMetadata(path=file_name),
        ),
    )

    put_headers = _flatten_request_headers(init_result.get('requestHeaders'))

    async with httpx.AsyncClient() as client:
        s3_response = await client.put(
            init_result['s3PreSignedUrl'],
            content=content_bytes,
            headers=put_headers,
        )
        if s3_response.status_code >= 400:
            raise Exception(f'Failed to upload file to storage (HTTP {s3_response.status_code}).')

    await call_transform_api(
        'CompleteArtifactUpload',
        CompleteArtifactUploadRequest(
            workspaceId=workspace_id,
            jobId=job_id,
            artifactId=init_result['artifactId'],
        ),
    )

    return init_result['artifactId']


def infer_file_type(file_path: str) -> str:
    """Infer file type from extension."""
    ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''
    mapping = {
        'json': 'JSON',
        'pdf': 'PDF',
        'html': 'HTML',
        'htm': 'HTML',
        'txt': 'TXT',
        'csv': 'TXT',
        'md': 'TXT',
        'log': 'TXT',
        'zip': 'TXT',
        'gz': 'TXT',
        'tar': 'TXT',
        'tgz': 'TXT',
        'parquet': 'TXT',
    }
    return mapping.get(ext, 'TXT')
