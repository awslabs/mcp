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

"""Artifact download tool for AWS Transform MCP server.

Provides the ``download_artifact`` tool which downloads an artifact or connector
asset and writes its bytes to a local file.
"""

import hashlib
import os
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.file_validation import get_write_base, validate_write_path
from awslabs.aws_transform_mcp_server.tool_utils import (
    CREATE,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api_streaming
from mcp.server.mcpserver import Context
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


def _build_artifact_scope(
    artifactId: Optional[str],
    workspaceId: Optional[str],
    jobId: Optional[str],
    connectorId: Optional[str],
    assetKey: Optional[str],
) -> Dict[str, Any]:
    """Resolve the download scope from the IDs supplied.

    Raises ValueError if the combination does not map to a single scope.
    """
    if connectorId or assetKey:
        if not (connectorId and assetKey and workspaceId and jobId):
            raise ValueError(
                'Connector asset download requires connectorId, assetKey, workspaceId, and jobId.'
            )
        return {
            'connectorScope': {
                'workspaceId': workspaceId,
                'jobId': jobId,
                'connectorId': connectorId,
                'assetKey': assetKey,
            }
        }
    if not artifactId:
        raise ValueError('artifactId is required unless downloading a connector asset.')
    if workspaceId and jobId:
        return {'jobScope': {'workspaceId': workspaceId, 'jobId': jobId, 'artifactId': artifactId}}
    if workspaceId:
        raise ValueError('Workspace-scope downloads are not supported')
    return {'userScope': {'artifactId': artifactId}}


class DownloadArtifactHandler:
    """Registers the download_artifact MCP tool."""

    def __init__(self, mcp: Any) -> None:
        """Register the download tool on the MCP server."""
        audited_tool(mcp, 'download_artifact', title='Download Artifact', annotations=CREATE)(
            self.download_artifact
        )

    async def download_artifact(
        self,
        ctx: Context,
        artifactId: Annotated[
            Optional[str],
            Field(description='Artifact identifier. Omit for connector assets.'),
        ] = None,
        workspaceId: Annotated[
            Optional[str],
            Field(description='Workspace ID. Required with jobId to select a job artifact.'),
        ] = None,
        jobId: Annotated[
            Optional[str],
            Field(
                description='Job ID. Required with workspaceId for job artifacts and for connector assets.'
            ),
        ] = None,
        connectorId: Annotated[
            Optional[str],
            Field(
                description='Connector ID. Provide with assetKey (plus workspaceId and jobId) to download a connector-managed asset.'
            ),
        ] = None,
        assetKey: Annotated[
            Optional[str],
            Field(description='Connector asset key identifying the asset to download.'),
        ] = None,
        outputPath: Annotated[
            Optional[str],
            Field(
                description=(
                    'Local file or directory path to write the bytes to. A path ending in "/", '
                    'without a file extension, or naming an existing directory is treated as '
                    'a directory, and the file is saved inside it under its own file name. '
                    'Must resolve within the allowed base directory (the server working '
                    'directory, or AWS_TRANSFORM_MCP_WRITE_DIR if set). If omitted, the file '
                    'is written to that base directory using its file name.'
                )
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """Download an artifact or connector asset and write its bytes to disk.

        Selects the download scope from the IDs provided:
        connectorId+assetKey (+workspaceId+jobId) → connector asset;
        workspaceId+jobId+artifactId → job artifact;
        artifactId alone → user artifact.

        Returns the local path, file name, byte count, and SHA-256. The bytes are
        never returned inline; read them from the returned path.
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            try:
                scope = _build_artifact_scope(
                    artifactId, workspaceId, jobId, connectorId, assetKey
                )
            except ValueError as ve:
                return error_result(
                    'INVALID_SCOPE', str(ve), 'Provide IDs for exactly one download scope.'
                )

            result = await call_transform_api_streaming('GetArtifact', {'artifactScope': scope})

            stream_error = result.get('error')
            if stream_error:
                return error_result(
                    stream_error.get('code', 'STREAM_ERROR'),
                    stream_error.get('message', 'The artifact stream failed.'),
                    'Verify the artifact exists and you have Read access to its workspace/job.',
                )
            if not result.get('finished'):
                return error_result(
                    'STREAM_INCOMPLETE',
                    'The artifact stream ended before its end-of-stream event; '
                    'the download is incomplete and was not saved.',
                    'Retry the download.',
                )

            content: bytes = result.get('content') or b''
            metadata = result.get('metadata') or {}
            file_name = metadata.get('fileName') or (artifactId or 'artifact')

            # Resolve destination, confined to the server's write base. Same directory
            # heuristic as get_resource's savePath: a trailing separator, a basename
            # without a '.', or an existing directory means "save into this directory
            # under the server-supplied file name"; anything else is the target file.
            if not outputPath:
                dest = validate_write_path(get_write_base(), file_name)
            elif (
                outputPath.endswith(('/', os.sep))
                or '.' not in os.path.basename(outputPath)
                or os.path.isdir(outputPath)
            ):
                dest = validate_write_path(outputPath, file_name)
            else:
                dest = validate_write_path(
                    os.path.dirname(outputPath) or get_write_base(), os.path.basename(outputPath)
                )
            parent = os.path.dirname(dest)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(dest, 'wb') as fh:
                fh.write(content)

            sha256 = hashlib.sha256(content).hexdigest()
            data: Dict[str, Any] = {
                'path': dest,
                'fileName': file_name,
                'bytesWritten': len(content),
                'sha256': sha256,
            }
            declared = metadata.get('contentLengthBytes')
            if declared is not None:
                data['contentLengthBytes'] = declared
            if metadata.get('artifact') is not None:
                data['artifact'] = metadata['artifact']

            return success_result(data)

        except Exception as error:
            return failure_result(error)
