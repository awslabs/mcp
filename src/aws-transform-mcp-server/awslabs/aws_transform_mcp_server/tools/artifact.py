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

"""Artifact upload tool handler for AWS Transform MCP server.

Ported from tools/artifact.ts. Provides the upload_artifact tool which
uploads a file or raw content as an artifact and returns the artifact ID.
"""

import base64
import hashlib
import httpx
import os
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.file_validation import validate_read_path
from awslabs.aws_transform_mcp_server.tool_utils import (
    MUTATE,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    ArtifactReference,
    ArtifactType,
    CompleteArtifactUploadRequest,
    ContentDigest,
    CreateArtifactUploadUrlRequest,
    FileMetadata,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


class ArtifactHandler:
    """Registers artifact-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register artifact tools on the MCP server."""
        audited_tool(mcp, 'upload_artifact', title='Upload Artifact', annotations=MUTATE)(
            self.upload_artifact
        )

    async def upload_artifact(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace identifier')],
        jobId: Annotated[str, Field(description='The job identifier')],
        content: Annotated[
            str, Field(description='Local file path (preferred) or raw content string')
        ],
        encoding: Annotated[
            str,
            Field(
                description=(
                    'Content encoding when passing raw content (default: utf-8). '
                    'Ignored when content is a file path.'
                ),
            ),
        ] = 'utf-8',
        categoryType: Annotated[
            str,
            Field(
                description='Artifact category (default: CUSTOMER_INPUT)',
            ),
        ] = 'CUSTOMER_INPUT',
        fileType: Annotated[
            str,
            Field(
                description='File type (default: JSON)',
            ),
        ] = 'JSON',
        fileName: Annotated[
            Optional[str],
            Field(
                description='Optional file name',
            ),
        ] = None,
        planStepId: Annotated[
            Optional[str],
            Field(
                description='Optional plan step ID',
            ),
        ] = None,
        connectorId: Annotated[
            Optional[str],
            Field(
                description=(
                    'Optional connector ID. When provided, uploads directly to the '
                    "connector's S3 bucket instead of the managed artifact store."
                ),
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """Upload a file or raw content as an artifact.

        If content is a valid file path, reads from disk. Otherwise treats
        content as raw data (utf-8 or base64 encoded).

        Returns the artifact ID.
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            resolved_file_name = fileName
            content_bytes: bytes

            if os.path.exists(content):
                # Read from file path
                validated_path = validate_read_path(content)
                with open(validated_path, 'rb') as fh:
                    content_bytes = fh.read()
                if not resolved_file_name:
                    resolved_file_name = os.path.basename(validated_path)
            elif encoding == 'base64':
                content_bytes = base64.b64decode(content)
            else:
                content_bytes = content.encode('utf-8')

            sha256_digest = base64.b64encode(hashlib.sha256(content_bytes).digest()).decode(
                'ascii'
            )

            upload_req = CreateArtifactUploadUrlRequest(
                workspaceId=workspaceId,
                jobId=jobId,
                contentDigest=ContentDigest(Sha256=sha256_digest),
                artifactReference=ArtifactReference(
                    artifactType=ArtifactType(
                        categoryType=categoryType,
                        fileType=fileType,
                    ),
                ),
                connectorId=connectorId if connectorId else None,
                planStepId=planStepId if planStepId else None,
                fileMetadata=(
                    FileMetadata(path=resolved_file_name) if resolved_file_name else None
                ),
            )

            init_result = await call_transform_api('CreateArtifactUploadUrl', upload_req)

            # Flatten multi-value headers
            put_headers: Dict[str, str] = {}
            request_headers = init_result.get('requestHeaders')
            if request_headers:
                for key, values in request_headers.items():
                    if values:
                        put_headers[key] = ', '.join(values)

            async with httpx.AsyncClient() as client:
                s3_response = await client.put(
                    init_result['s3PreSignedUrl'],
                    content=content_bytes,
                    headers=put_headers,
                )
                if s3_response.status_code >= 400:
                    return error_result(
                        'UPLOAD_FAILED',
                        'Failed to upload artifact content to storage.',
                        'Retry the upload.',
                    )

            # Skip CompleteArtifactUpload when using connector-based upload
            # (file goes directly to connector S3 bucket, not managed artifact store)
            if connectorId:
                return success_result(
                    {
                        'uploaded': True,
                        'fileName': resolved_file_name,
                        'connectorId': connectorId,
                    }
                )

            await call_transform_api(
                'CompleteArtifactUpload',
                CompleteArtifactUploadRequest(
                    workspaceId=workspaceId,
                    jobId=jobId,
                    artifactId=init_result['artifactId'],
                ),
            )

            return success_result({'artifactId': init_result['artifactId']})

        except Exception as error:
            return failure_result(error)
