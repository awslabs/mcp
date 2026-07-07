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

"""Tests for the aws_client helper module.

Run: uv run python -m pytest tests/test_aws_client.py -v
"""

import pytest
from awslabs.roda_mcp_server.aws_client import get_s3_client
from unittest.mock import MagicMock, patch


def test_returns_s3_client():
    """get_s3_client returns a configured boto3 S3 client."""
    with patch('awslabs.roda_mcp_server.aws_client.boto3.client') as mock_client:
        mock_client.return_value = MagicMock()
        client = get_s3_client(region='us-west-2')

        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args
        assert call_kwargs[0][0] == 's3'
        assert call_kwargs[1]['region_name'] == 'us-west-2'
        assert call_kwargs[1]['verify'] is True
        assert client is mock_client.return_value


def test_default_region():
    """get_s3_client defaults to us-east-1."""
    with patch('awslabs.roda_mcp_server.aws_client.boto3.client') as mock_client:
        mock_client.return_value = MagicMock()
        get_s3_client()

        call_kwargs = mock_client.call_args
        assert call_kwargs[1]['region_name'] == 'us-east-1'


def test_raises_on_failure():
    """get_s3_client re-raises exceptions from boto3."""
    with patch('awslabs.roda_mcp_server.aws_client.boto3.client') as mock_client:
        mock_client.side_effect = RuntimeError('No credentials')

        with pytest.raises(RuntimeError, match='No credentials'):
            get_s3_client()
