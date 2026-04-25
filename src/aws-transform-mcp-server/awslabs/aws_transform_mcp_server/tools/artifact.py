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
from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.file_validation import validate_read_path
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


class ArtifactHandler:
    """Registers artifact-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register artifact tools on the MCP server."""
        audited_tool(mcp, 'upload_artifact')(self.upload_artifact)

    async def upload_artifact(
        self,
        ctx: Context,
        workspaceId: str = Field(..., description='The workspace identifier'),
        jobId: str = Field(..., description='The job identifier'),
        content: str = Field(..., description='Local file path (preferred) or raw content string'),
        encoding: str = Field(
            'utf-8',
            description=(
                'Content encoding when passing raw content (default: utf-8). '
                'Ignored when content is a file path.'
            ),
        ),
        categoryType: str = Field(
            'CUSTOMER_INPUT',
            description='Artifact category (default: CUSTOMER_INPUT)',
        ),
        fileType: str = Field(
            'JSON',
            description='File type (default: JSON)',
        ),
        fileName: Optional[str] = Field(
            None,
            description='Optional file name',
        ),
        planStepId: Optional[str] = Field(
            None,
            description='Optional plan step ID',
        ),
    ) -> Dict[str, Any]:
        """Upload a file or raw content as an artifact.

        If content is a valid file path, reads from disk. Otherwise treats
        content as raw data (utf-8 or base64 encoded).

        Returns the artifact ID.
        """
        if not is_configured():
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

            upload_body: Dict[str, Any] = {
                'workspaceId': workspaceId,
                'jobId': jobId,
                'contentDigest': {'Sha256': sha256_digest},
                'artifactReference': {
                    'artifactType': {
                        'categoryType': categoryType,
                        'fileType': fileType,
                    },
                },
            }
            if planStepId:
                upload_body['planStepId'] = planStepId
            if resolved_file_name:
                upload_body['fileMetadata'] = {
                    'fileName': resolved_file_name,
                    'path': resolved_file_name,
                }

            init_result = await call_fes('CreateArtifactUploadUrl', upload_body)

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

            await call_fes(
                'CompleteArtifactUpload',
                {
                    'workspaceId': workspaceId,
                    'jobId': jobId,
                    'artifactId': init_result['artifactId'],
                },
            )

            return success_result({'artifactId': init_result['artifactId']})

        except Exception as error:
            return failure_result(error)
