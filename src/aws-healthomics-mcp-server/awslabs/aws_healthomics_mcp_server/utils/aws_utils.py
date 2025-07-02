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

"""AWS utility functions for the HealthOmics MCP server."""

import base64
import boto3
import botocore.session
import io
import os
import zipfile
from awslabs.aws_healthomics_mcp_server import __version__
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_REGION
from typing import Dict, Optional


def get_aws_session(region: Optional[str] = None) -> boto3.Session:
    """Get an AWS session with the specified or default region.

    Args:
        region: AWS region name (optional)

    Returns:
        boto3.Session: Configured AWS session
    """
    botocore_session = botocore.session.Session()
    user_agent_extra = f'awslabs/mcp/aws-healthomics-mcp-server/{__version__}'
    botocore_session.user_agent_extra = user_agent_extra
    region = region or os.environ.get('AWS_REGION', DEFAULT_REGION)
    return boto3.Session(region_name=region, botocore_session=botocore_session)


def create_zip_file(files: Dict[str, str]) -> bytes:
    """Create a ZIP file in memory from a dictionary of files.

    Args:
        files: Dictionary mapping filenames to file contents

    Returns:
        bytes: ZIP file content as bytes
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.read()


def encode_to_base64(data: bytes) -> str:
    """Encode bytes to base64 string.

    Args:
        data: Bytes to encode

    Returns:
        str: Base64-encoded string
    """
    return base64.b64encode(data).decode('utf-8')


def decode_from_base64(data: str) -> bytes:
    """Decode base64 string to bytes.

    Args:
        data: Base64-encoded string

    Returns:
        bytes: Decoded bytes
    """
    return base64.b64decode(data)
