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

"""S3 Operations tools for S3 Tables MCP Server."""

from .utils import get_s3_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def get_bucket_metadata_table_configuration(
    bucket: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get the metadata table configuration for an S3 bucket.

    Gets the metadata table configuration for an S3 bucket. This configuration
    determines how metadata is stored and managed for the bucket.

    Permissions:
    You must have the s3:GetBucketMetadataConfiguration permission to use this operation.

    Args:
        bucket: The name of the S3 bucket
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable
                    or defaults to 'us-east-1'.

    Returns:
        Dict containing the bucket metadata table configuration
    """
    client = get_s3_client(region_name)
    response = client.get_bucket_metadata_configuration(Bucket=bucket)
    return dict(response)
