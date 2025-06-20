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
