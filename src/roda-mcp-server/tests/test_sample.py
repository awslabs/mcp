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
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::open-bucket',
                'Region': 'us-east-1',
            }
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


async def test_zero_byte_file(patch_fetch, mock_boto3):
    """Zero-byte file returns a message instead of crashing with invalid Range header."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.head_object.return_value = {'ContentLength': 0}

    result = await sample_dataset('open-data', file_key='empty.csv')
    data = json.loads(result)

    assert data['file_size_bytes'] == 0
    assert 'empty' in data['message'].lower()
    assert data['bucket'] == 'open-bucket'
    assert data['license'] == 'Public Domain'


async def test_text_truncation_at_line_boundary(patch_fetch, mock_boto3):
    """Text >2000 chars is truncated at the last newline before 2000, with flags set."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3

    # Build content with lines that exceed 2000 chars total
    # Each line is 50 chars + newline = 51 chars, so 50 lines = 2550 chars
    lines = [f'line-{i:03d},' + 'x' * 44 for i in range(50)]
    file_content = ('\n'.join(lines) + '\n').encode('utf-8')

    mock_s3.head_object.return_value = {'ContentLength': len(file_content)}
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=file_content)),
    }

    result = await sample_dataset('open-data', file_key='big-text.csv')
    data = json.loads(result)

    # content_truncated flag should be set
    assert data['content_truncated'] is True
    # is_partial should reflect the display truncation
    assert data['is_partial'] is True
    # Content should end with the truncation marker
    assert '... (truncated for display)' in data['content']
    # Content should NOT cut mid-line — last real line should be complete
    content_lines = data['content'].split('\n')
    # The second-to-last line (before the marker) should be a complete line
    real_lines = [l for l in content_lines if not l.startswith('...')]
    for line in real_lines:
        if line:  # skip empty lines
            assert line.startswith('line-')


async def test_short_text_not_truncated(patch_fetch, mock_boto3):
    """Text <=2000 chars is returned in full without truncation flags."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3

    file_content = b'short content\nonly two lines\n'
    mock_s3.head_object.return_value = {'ContentLength': len(file_content)}
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=file_content)),
    }

    result = await sample_dataset('open-data', file_key='small.csv')
    data = json.loads(result)

    assert data['content_truncated'] is False
    assert data['content'] == 'short content\nonly two lines\n'
    assert '... (truncated' not in data['content']


async def test_multi_bucket_no_arn_prompts_choice(patch_fetch, mock_boto3):
    """Multi-bucket dataset without bucket_arn asks user to choose."""
    # Temporarily add a multi-bucket dataset to the cache
    multi_bucket_ds = {
        'Slug': 'multi-bucket',
        'Name': 'Multi Bucket Dataset',
        'Description': 'Has two public buckets',
        'License': 'MIT',
        'ManagedBy': '[Test](https://test.com/)',
        'Tags': [],
        'Resources': [
            {'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::bucket-a', 'Region': 'us-east-1'},
            {'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::bucket-b', 'Region': 'us-west-2'},
        ],
    }
    server_module._datasets_cache.append(multi_bucket_ds)  # type: ignore[union-attr]

    result = await sample_dataset('multi-bucket', file_key='data.csv')
    data = json.loads(result)

    assert 'available_buckets' in data
    assert len(data['available_buckets']) == 2
    assert 'Please specify bucket_arn' in data['message']


async def test_multi_bucket_wrong_arn(patch_fetch, mock_boto3):
    """Providing a bucket_arn that doesn't belong to the dataset returns error."""
    multi_bucket_ds = {
        'Slug': 'multi-bucket-2',
        'Name': 'Multi Bucket Dataset 2',
        'Description': 'Has two public buckets',
        'License': 'MIT',
        'ManagedBy': '[Test](https://test.com/)',
        'Tags': [],
        'Resources': [
            {'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::bucket-x', 'Region': 'us-east-1'},
            {'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::bucket-y', 'Region': 'us-west-2'},
        ],
    }
    server_module._datasets_cache.append(multi_bucket_ds)  # type: ignore[union-attr]

    result = await sample_dataset(
        'multi-bucket-2', file_key='data.csv', bucket_arn='arn:aws:s3:::wrong-bucket'
    )
    data = json.loads(result)

    assert 'error' in data
    assert 'wrong-bucket' in data['error']
    assert 'available_arns' in data


async def test_network_error_endpoint_connection(patch_fetch, mock_boto3):
    """EndpointConnectionError returns a network error message."""
    from botocore.exceptions import EndpointConnectionError

    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.head_object.side_effect = EndpointConnectionError(
        endpoint_url='https://s3.amazonaws.com'
    )

    result = await sample_dataset('open-data', file_key='data.csv')
    data = json.loads(result)

    assert 'error' in data
    assert 'network' in data['error'].lower() or 'Network' in data['error']
