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

"""Tests for the preview_dataset tool.

Covers dataset not found, no public buckets (requester-pays, controlled access),
multi-bucket selection, successful listing, access denied, ARN parsing, and
empty bucket.

Run: uv run python -m pytest tests/test_preview.py -v
"""

import awslabs.roda_mcp_server.server as server_module
import json
import pytest
from awslabs.roda_mcp_server.server import preview_dataset
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# Datasets with various access configurations for preview testing
PREVIEW_DATASETS = [
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
        'Slug': 'multi-bucket',
        'Name': 'Multi Bucket Dataset',
        'Description': 'Dataset with multiple public S3 buckets',
        'License': 'MIT',
        'ManagedBy': '[NOAA](https://www.noaa.gov/)',
        'Tags': ['weather'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::bucket-a',
                'Region': 'us-east-1',
                'Description': 'Primary',
            },
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::bucket-b',
                'Region': 'us-west-2',
                'Description': 'Secondary',
            },
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
    {
        'Slug': 'controlled-access',
        'Name': 'Controlled Access Dataset',
        'Description': 'Dataset with controlled access',
        'License': 'Restricted',
        'ManagedBy': '[NIH](https://www.nih.gov/)',
        'Tags': ['health'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::controlled-bucket',
                'Region': 'us-east-1',
                'ControlledAccess': 'https://example.com/request-access',
            }
        ],
    },
    {
        'Slug': 'prefixed-data',
        'Name': 'Prefixed Dataset',
        'Description': 'Dataset with a prefix in the ARN',
        'License': 'Public Domain',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'Tags': ['satellite'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::prefixed-bucket/data/v2',
                'Region': 'us-west-2',
            }
        ],
    },
]


@pytest.fixture(autouse=True)
def setup_preview_state():
    """Pre-populate the server cache with preview-specific sample data."""
    server_module._datasets_cache = PREVIEW_DATASETS
    yield
    server_module._datasets_cache = None
    server_module._cache_timestamp = None


@pytest.fixture
def patch_fetch():
    """Mock fetch_datasets to return preview sample data."""
    with patch('awslabs.roda_mcp_server.server.fetch_datasets', new_callable=AsyncMock) as mock:
        mock.return_value = PREVIEW_DATASETS
        yield mock


@pytest.fixture
def mock_boto3():
    """Mock boto3.client for S3 operations."""
    with patch('boto3.client') as mock_client:
        yield mock_client


async def test_dataset_not_found(patch_fetch):
    """Previewing a nonexistent dataset returns an error with suggestion."""
    result = await preview_dataset('nonexistent')
    data = json.loads(result)

    assert 'error' in data
    assert 'nonexistent' in data['error']
    assert 'suggestion' in data


async def test_requester_pays(patch_fetch):
    """Requester-pays datasets can't be previewed — returns helpful message."""
    result = await preview_dataset('requester-pays')
    data = json.loads(result)

    assert 'message' in data
    assert 'requester-pays' in data['message'].lower()


async def test_controlled_access(patch_fetch):
    """Controlled access datasets return message with access request URL."""
    result = await preview_dataset('controlled-access')
    data = json.loads(result)

    assert 'message' in data
    assert 'controlled access' in data['message'].lower()
    assert data['access_request_url'] == 'https://example.com/request-access'


async def test_multi_bucket_no_arn(patch_fetch):
    """Multi-bucket datasets without bucket_arn ask user to choose."""
    result = await preview_dataset('multi-bucket')
    data = json.loads(result)

    assert 'available_buckets' in data
    assert len(data['available_buckets']) == 2
    assert '2 public S3 buckets' in data['message']


async def test_multi_bucket_with_arn(patch_fetch, mock_boto3):
    """Multi-bucket dataset with specific bucket_arn previews that bucket."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'file1.csv', 'Size': 1024, 'LastModified': datetime(2024, 1, 1)},
            {'Key': 'file2.csv', 'Size': 2048, 'LastModified': datetime(2024, 1, 2)},
        ],
        'IsTruncated': False,
    }

    result = await preview_dataset('multi-bucket', bucket_arn='arn:aws:s3:::bucket-a')
    data = json.loads(result)

    assert data['bucket'] == 'bucket-a'
    assert data['object_count'] == 2


async def test_multi_bucket_wrong_arn(patch_fetch):
    """Providing a bucket_arn that doesn't belong to the dataset returns error."""
    result = await preview_dataset('multi-bucket', bucket_arn='arn:aws:s3:::wrong-bucket')
    data = json.loads(result)

    assert 'error' in data
    assert 'wrong-bucket' in data['error']
    assert 'available_arns' in data


async def test_successful_listing(patch_fetch, mock_boto3):
    """Successful preview returns bucket info, objects, and CLI commands."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.list_objects_v2.return_value = {
        'Contents': [
            {
                'Key': 'data/2024/obs.csv',
                'Size': 5120,
                'LastModified': datetime(2024, 6, 1),
            },
        ],
        'IsTruncated': False,
    }

    result = await preview_dataset('open-data')
    data = json.loads(result)

    assert data['dataset'] == 'Open Dataset'
    assert data['bucket'] == 'open-bucket'
    assert data['region'] == 'us-east-1'
    assert data['license'] == 'Public Domain'
    assert data['object_count'] == 1
    assert '--no-sign-request' in data['cli_commands']['list']


async def test_with_prefix(patch_fetch, mock_boto3):
    """ARN with a path prefix uses that prefix when listing objects."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.list_objects_v2.return_value = {
        'Contents': [
            {
                'Key': 'data/v2/file.parquet',
                'Size': 9999,
                'LastModified': datetime(2024, 3, 1),
            },
        ],
        'IsTruncated': False,
    }

    result = await preview_dataset('prefixed-data')
    data = json.loads(result)

    assert data['bucket'] == 'prefixed-bucket'
    assert data['prefix'] == 'data/v2/'
    call_kwargs = mock_s3.list_objects_v2.call_args[1]
    assert call_kwargs['Prefix'] == 'data/v2/'


async def test_access_denied(patch_fetch, mock_boto3):
    """AccessDenied from S3 returns a credentials-required error."""
    from botocore.exceptions import ClientError

    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.list_objects_v2.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
        'ListObjectsV2',
    )

    result = await preview_dataset('open-data')
    data = json.loads(result)

    assert 'error' in data
    assert 'credentials' in data['error'].lower() or 'access denied' in data['error'].lower()


async def test_empty_bucket(patch_fetch, mock_boto3):
    """Empty bucket returns a message indicating no contents."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.list_objects_v2.return_value = {}

    result = await preview_dataset('open-data')
    data = json.loads(result)

    assert 'message' in data
    assert 'empty' in data['message'].lower() or 'restricted' in data['message'].lower()


async def test_network_error_endpoint_connection(patch_fetch, mock_boto3):
    """EndpointConnectionError returns a network error message."""
    from botocore.exceptions import EndpointConnectionError

    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.list_objects_v2.side_effect = EndpointConnectionError(
        endpoint_url='https://s3.amazonaws.com'
    )

    result = await preview_dataset('open-data')
    data = json.loads(result)

    assert 'error' in data
    assert 'network' in data['error'].lower() or 'Network' in data['error']
