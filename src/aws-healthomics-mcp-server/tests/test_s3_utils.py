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

"""Unit tests for S3 utility functions."""

import pytest
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import ensure_s3_uri_ends_with_slash


def test_ensure_s3_uri_ends_with_slash_already_has_slash():
    """Test URI that already ends with a slash."""
    uri = 's3://bucket/path/'
    result = ensure_s3_uri_ends_with_slash(uri)
    assert result == 's3://bucket/path/'


def test_ensure_s3_uri_ends_with_slash_no_slash():
    """Test URI that doesn't end with a slash."""
    uri = 's3://bucket/path'
    result = ensure_s3_uri_ends_with_slash(uri)
    assert result == 's3://bucket/path/'


def test_ensure_s3_uri_ends_with_slash_root_bucket():
    """Test URI for root bucket path."""
    uri = 's3://bucket'
    result = ensure_s3_uri_ends_with_slash(uri)
    assert result == 's3://bucket/'


def test_ensure_s3_uri_ends_with_slash_root_bucket_with_slash():
    """Test URI for root bucket path that already has slash."""
    uri = 's3://bucket/'
    result = ensure_s3_uri_ends_with_slash(uri)
    assert result == 's3://bucket/'


def test_ensure_s3_uri_ends_with_slash_invalid_scheme():
    """Test URI that doesn't start with s3://."""
    uri = 'https://bucket/path'
    with pytest.raises(ValueError, match='URI must start with s3://'):
        ensure_s3_uri_ends_with_slash(uri)


def test_ensure_s3_uri_ends_with_slash_empty_string():
    """Test empty string input."""
    uri = ''
    with pytest.raises(ValueError, match='URI must start with s3://'):
        ensure_s3_uri_ends_with_slash(uri)
