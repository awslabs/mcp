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

"""Tests for the RegionalDataProvider."""

import json
import time

import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch

from awslabs.aws_api_mcp_server.core.aws.regional_data import RegionalDataProvider


# ---------------------------------------------------------------------------
# URI parsing
# ---------------------------------------------------------------------------


class TestParseS3Uri:
    """Tests for _parse_s3_uri."""

    def test_standard_s3_uri(self):
        """Parse a standard s3://bucket/prefix URI."""
        bucket, prefix = RegionalDataProvider._parse_s3_uri('s3://my-bucket/some/prefix')
        assert bucket == 'my-bucket'
        assert prefix == 'some/prefix'

    def test_s3_uri_no_prefix(self):
        """Parse an s3:// URI with no prefix."""
        bucket, prefix = RegionalDataProvider._parse_s3_uri('s3://my-bucket')
        assert bucket == 'my-bucket'
        assert prefix == ''

    def test_s3_uri_trailing_slash(self):
        """Trailing slashes are stripped from the prefix."""
        bucket, prefix = RegionalDataProvider._parse_s3_uri('s3://my-bucket/prefix/')
        assert prefix == 'prefix'

    def test_access_point_arn(self):
        """Parse an S3 access-point ARN with prefix."""
        arn = 'arn:aws:s3:us-east-1:123456789012:accesspoint/my-ap/data/v1'
        bucket, prefix = RegionalDataProvider._parse_s3_uri(arn)
        assert bucket == 'arn:aws:s3:us-east-1:123456789012:accesspoint/my-ap'
        assert prefix == 'data/v1'

    def test_access_point_arn_no_prefix(self):
        """Parse an S3 access-point ARN with no prefix beyond the AP name."""
        arn = 'arn:aws:s3:us-east-1:123456789012:accesspoint/my-ap'
        bucket, prefix = RegionalDataProvider._parse_s3_uri(arn)
        assert bucket == 'arn:aws:s3:us-east-1:123456789012:accesspoint/my-ap'
        assert prefix == ''

    def test_invalid_scheme(self):
        """Non-s3:// URIs should raise ValueError."""
        with pytest.raises(ValueError, match='Invalid S3 URI'):
            RegionalDataProvider._parse_s3_uri('https://example.com/bucket')


# ---------------------------------------------------------------------------
# Helper to build a provider with a mocked S3 client
# ---------------------------------------------------------------------------

def _make_provider(s3_objects=None, cache_ttl=300):
    """Create a RegionalDataProvider with a mocked S3 client.

    Args:
        s3_objects: dict mapping S3 keys to Python objects (will be JSON-encoded).
        cache_ttl: cache TTL in seconds.
    """
    s3_objects = s3_objects or {}

    with patch(
        'awslabs.aws_api_mcp_server.core.aws.regional_data.boto3.Session'
    ) as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        def get_object(Bucket, Key):
            if Key in s3_objects:
                body = MagicMock()
                body.read.return_value = json.dumps(s3_objects[Key]).encode('utf-8')
                return {'Body': body}
            error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}}
            raise ClientError(error_response, 'GetObject')

        mock_client.get_object.side_effect = get_object

        # Default: no listing
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = []
        mock_client.get_paginator.return_value = mock_paginator

        provider = RegionalDataProvider(s3_uri='s3://test-bucket/data', cache_ttl=cache_ttl)

    return provider


# ---------------------------------------------------------------------------
# Data loading tests
# ---------------------------------------------------------------------------


class TestLoadData:
    """Tests for data loading and caching."""

    def test_load_with_services_index(self):
        """Load data when services.json exists."""
        s3_data = {
            'data/services.json': {
                'services': [
                    {'service': 'ec2', 'features': [{'feature': 'instances'}]},
                ]
            },
            'data/ec2/instances.json': {
                'regions': {'us-east-1': 'AVAILABLE', 'eu-west-1': 'AVAILABLE'}
            },
        }
        provider = _make_provider(s3_data)
        data = provider._load_data()

        assert 'ec2' in data
        assert 'instances' in data['ec2']
        assert data['ec2']['instances']['us-east-1'] == 'AVAILABLE'

    def test_load_service_level_data(self):
        """Load service-level data when no features are listed."""
        s3_data = {
            'data/services.json': {
                'services': [{'service': 's3', 'features': []}]
            },
            'data/s3.json': {
                'regions': {'us-east-1': 'AVAILABLE'}
            },
        }
        provider = _make_provider(s3_data)
        data = provider._load_data()

        assert 's3' in data
        assert data['s3']['_service']['us-east-1'] == 'AVAILABLE'

    def test_cache_hit(self):
        """Subsequent calls within TTL return cached data without re-loading."""
        s3_data = {
            'data/services.json': {'services': [{'service': 'ec2', 'features': []}]},
            'data/ec2.json': {'regions': {'us-east-1': 'AVAILABLE'}},
        }
        provider = _make_provider(s3_data, cache_ttl=300)

        # First load
        data1 = provider._load_data()
        # Mutate internal to prove caching
        provider._cache['_marker'] = True
        data2 = provider._load_data()
        assert data2.get('_marker') is True

    def test_cache_expiry(self):
        """After TTL expires, data is reloaded."""
        s3_data = {
            'data/services.json': {'services': [{'service': 'ec2', 'features': []}]},
            'data/ec2.json': {'regions': {'us-east-1': 'AVAILABLE'}},
        }
        provider = _make_provider(s3_data, cache_ttl=0)

        provider._load_data()
        provider._cache['_marker'] = True
        # TTL=0 means always stale
        data = provider._load_data()
        assert '_marker' not in data

    def test_fallback_listing_when_no_index(self):
        """When services.json is missing, build index from S3 listing."""
        provider = _make_provider({}, cache_ttl=300)

        # Set up paginator mock to return objects
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'data/lambda/functions.json'},
                    {'Key': 'data/lambda/layers.json'},
                ]
            }
        ]
        provider._s3_client.get_paginator.return_value = mock_paginator

        # Now set up get_object for the discovered files
        def get_object(Bucket, Key):
            files = {
                'data/lambda/functions.json': {'regions': {'us-east-1': 'AVAILABLE'}},
                'data/lambda/layers.json': {'regions': {'us-west-2': 'AVAILABLE'}},
            }
            if Key in files:
                body = MagicMock()
                body.read.return_value = json.dumps(files[Key]).encode('utf-8')
                return {'Body': body}
            error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}}
            raise ClientError(error_response, 'GetObject')

        provider._s3_client.get_object.side_effect = get_object

        data = provider._load_data()
        assert 'lambda' in data
        assert 'functions' in data['lambda']


# ---------------------------------------------------------------------------
# Query API tests
# ---------------------------------------------------------------------------


class TestGetAvailability:
    """Tests for get_availability."""

    def _provider_with_data(self):
        s3_data = {
            'data/services.json': {
                'services': [
                    {'service': 'ec2', 'features': [{'feature': 'instances'}, {'feature': 'vpcs'}]},
                ]
            },
            'data/ec2/instances.json': {
                'regions': {
                    'us-east-1': 'AVAILABLE',
                    'us-west-2': 'AVAILABLE',
                    'eu-west-1': 'PREVIEW',
                }
            },
            'data/ec2/vpcs.json': {
                'regions': {'us-east-1': 'AVAILABLE'}
            },
        }
        return _make_provider(s3_data)

    def test_query_service_and_feature(self):
        """Query for a specific service and feature."""
        provider = self._provider_with_data()
        result = provider.get_availability('ec2', 'instances')

        assert result['service'] == 'ec2'
        assert result['feature'] == 'instances'
        assert result['regions']['us-east-1'] == 'AVAILABLE'

    def test_query_service_only(self):
        """Query for a service without specifying a feature returns first available."""
        provider = self._provider_with_data()
        result = provider.get_availability('ec2')

        assert result['service'] == 'ec2'
        assert result['regions']  # Should have data from first feature

    def test_filter_by_regions(self):
        """Region list filters the output."""
        provider = self._provider_with_data()
        result = provider.get_availability('ec2', 'instances', regions=['us-east-1', 'ap-south-1'])

        assert result['regions']['us-east-1'] == 'AVAILABLE'
        assert result['regions']['ap-south-1'] == 'UNKNOWN'

    def test_unknown_service(self):
        """Unknown service returns an error message."""
        provider = self._provider_with_data()
        result = provider.get_availability('nonexistent')

        assert result['regions'] == {}
        assert 'error' in result

    def test_unknown_feature(self):
        """Unknown feature returns an error message."""
        provider = self._provider_with_data()
        result = provider.get_availability('ec2', 'nonexistent')

        assert result['regions'] == {}
        assert 'error' in result


class TestListServices:
    """Tests for list_services."""

    def test_list_services(self):
        """List services returns all services with features."""
        s3_data = {
            'data/services.json': {
                'services': [
                    {'service': 'ec2', 'features': [{'feature': 'instances'}]},
                    {'service': 's3', 'features': []},
                ]
            },
            'data/ec2/instances.json': {'regions': {'us-east-1': 'AVAILABLE'}},
            'data/s3.json': {'regions': {'us-east-1': 'AVAILABLE'}},
        }
        provider = _make_provider(s3_data)
        result = provider.list_services()

        services = {s['service'] for s in result}
        assert 'ec2' in services
        assert 's3' in services

        ec2 = next(s for s in result if s['service'] == 'ec2')
        assert 'instances' in ec2['features']


# ---------------------------------------------------------------------------
# S3 error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for S3 error handling."""

    def test_access_denied(self):
        """AccessDenied from S3 is propagated."""
        with patch(
            'awslabs.aws_api_mcp_server.core.aws.regional_data.boto3.Session'
        ) as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Forbidden'}}
            mock_client.get_object.side_effect = ClientError(error_response, 'GetObject')

            provider = RegionalDataProvider(s3_uri='s3://locked-bucket/data', cache_ttl=300)

            with pytest.raises(ClientError):
                provider._load_data()
