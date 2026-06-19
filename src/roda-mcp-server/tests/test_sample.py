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

"""Tests for the sample_dataset tool.

Covers dataset not found, no public bucket, successful text/binary reads,
large file truncation, file not found (NoSuchKey), and access denied.

Run: uv run python -m pytest tests/test_sample.py -v
"""

import awslabs.roda_mcp_server.server as server_module
import json
import pytest
from awslabs.roda_mcp_server.server import sample_dataset
from unittest.mock import AsyncMock, MagicMock, patch


# Minimal datasets for sample testing — just need one open and one restricted
SAMPLE_DATASETS = [
    {
        'Slug': 'open-data',
        'Name': 'Open Dataset',
        'Description': 'A publicly accessible dataset',
        'License': 'Public Domain',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'Tags': ['climate'],
        'Resources': [
            {'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::open-bucket', 'Region': 'us-east-1'}
        ],
    },
    {
        'Slug': 'requester-pays',
        'Name': 'Requester Pays Dataset',
        'Description': 'Dataset requiring requester-pays',
        'License': 'Apache 2.0',
        'ManagedBy': '[NIH](https://www.nih.gov/)',
        'Tags': ['genomics'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::rp-bucket',
                'Region': 'us-east-1',
                'RequesterPays': True,
            }
        ],
    },
]


@pytest.fixture(autouse=True)
def setup_sample_state():
    """Pre-populate the server cache with sample-specific data."""
    server_module._datasets_cache = SAMPLE_DATASETS
    yield
    server_module._datasets_cache = None
    server_module._cache_timestamp = None


@pytest.fixture
def patch_fetch():
    """Mock fetch_datasets to return sample data."""
    with patch('awslabs.roda_mcp_server.server.fetch_datasets', new_callable=AsyncMock) as mock:
        mock.return_value = SAMPLE_DATASETS
        yield mock


@pytest.fixture
def mock_boto3():
    """Mock boto3.client for S3 operations."""
    with patch('boto3.client') as mock_client:
        yield mock_client


async def test_dataset_not_found(patch_fetch):
    """Sampling from a nonexistent dataset returns error."""
    result = await sample_dataset('nonexistent', file_key='test.csv')
    data = json.loads(result)

    assert 'error' in data
    assert 'nonexistent' in data['error']


async def test_no_public_bucket(patch_fetch):
    """Sampling from a requester-pays-only dataset returns error."""
    result = await sample_dataset('requester-pays', file_key='test.csv')
    data = json.loads(result)

    assert 'error' in data
    assert 'No publicly accessible' in data['error']


async def test_text_file(patch_fetch, mock_boto3):
    """Sampling a UTF-8 text file returns decoded content."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3

    file_content = b'header1,header2\nvalue1,value2\n'
    mock_s3.head_object.return_value = {'ContentLength': len(file_content)}
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=file_content)),
    }

    result = await sample_dataset('open-data', file_key='data.csv')
    data = json.loads(result)

    assert data['dataset'] == 'Open Dataset'
    assert data['encoding'] == 'utf-8'
    assert 'header1,header2' in data['content']
    assert data['file_size_bytes'] == len(file_content)
    assert data['is_partial'] is False
    assert data['license'] == 'Public Domain'
    assert '--no-sign-request' in data['cli_command']


async def test_binary_file(patch_fetch, mock_boto3):
    """Sampling a binary file returns a notice instead of garbled text."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3

    binary_content = bytes(range(256))
    mock_s3.head_object.return_value = {'ContentLength': len(binary_content)}
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=binary_content)),
    }

    result = await sample_dataset('open-data', file_key='image.tif')
    data = json.loads(result)

    assert data['encoding'] == 'binary'
    assert 'Binary file' in data['content']


async def test_large_file_truncated(patch_fetch, mock_boto3):
    """Files larger than 100KB are partially read (is_partial=True)."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3

    file_size = 200 * 1024
    partial_content = b'x' * (100 * 1024)
    mock_s3.head_object.return_value = {'ContentLength': file_size}
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=partial_content)),
    }

    result = await sample_dataset('open-data', file_key='big-file.csv')
    data = json.loads(result)

    assert data['is_partial'] is True
    assert data['file_size_bytes'] == file_size
    assert data['bytes_read'] == 100 * 1024


async def test_file_not_found(patch_fetch, mock_boto3):
    """NoSuchKey error returns a file-not-found message."""
    from botocore.exceptions import ClientError

    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.head_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
        'HeadObject',
    )

    result = await sample_dataset('open-data', file_key='missing.csv')
    data = json.loads(result)

    assert 'error' in data
    assert 'not found' in data['error'].lower()


async def test_access_denied(patch_fetch, mock_boto3):
    """AccessDenied error returns a credentials-required message."""
    from botocore.exceptions import ClientError

    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.head_object.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Forbidden'}},
        'HeadObject',
    )

    result = await sample_dataset('open-data', file_key='secret.csv')
    data = json.loads(result)

    assert 'error' in data
    assert 'credentials' in data['error'].lower() or 'access denied' in data['error'].lower()
