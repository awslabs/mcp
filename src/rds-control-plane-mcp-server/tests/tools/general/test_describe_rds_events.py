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

"""Tests for describe_rds_events tool."""

import pytest
from awslabs.rds_control_plane_mcp_server.tools.general.describe_rds_events import (
    SOURCE_TYPE_TO_EVENT_CATEGORIES,
    EventList,
    describe_rds_events,
)
from datetime import datetime


class TestDescribeRDSEvents:
    """Test cases for describe_rds_events function."""

    @pytest.mark.asyncio
    async def test_describe_events_success(self, mock_rds_client):
        """Test successful event retrieval."""
        mock_rds_client.describe_events.return_value = {
            'Events': [
                {
                    'Message': 'DB instance created',
                    'EventCategories': ['creation'],
                    'Date': datetime(2024, 1, 1, 12, 0, 0),
                    'SourceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-instance',
                },
                {
                    'Message': 'Backup completed',
                    'EventCategories': ['backup'],
                    'Date': datetime(2024, 1, 1, 13, 0, 0),
                    'SourceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-instance',
                },
            ]
        }

        result = await describe_rds_events(
            source_identifier='test-instance', source_type='db-instance', event_categories=None
        )

        assert isinstance(result, EventList)
        assert result.source_identifier == 'test-instance'
        assert result.source_type == 'db-instance'
        assert result.count == 2
        assert len(result.events) == 2
        assert result.events[0].message == 'DB instance created'
        assert result.events[1].message == 'Backup completed'

    @pytest.mark.asyncio
    async def test_describe_events_with_categories(self, mock_rds_client):
        """Test event retrieval with event categories filter."""
        mock_rds_client.describe_events.return_value = {
            'Events': [
                {
                    'Message': 'Backup completed',
                    'EventCategories': ['backup'],
                    'Date': datetime(2024, 1, 1, 13, 0, 0),
                }
            ]
        }

        result = await describe_rds_events(
            source_identifier='test-instance',
            source_type='db-instance',
            event_categories=['backup'],
        )

        assert result.count == 1

    @pytest.mark.asyncio
    async def test_describe_events_with_duration(self, mock_rds_client):
        """Test event retrieval with duration filter."""
        mock_rds_client.describe_events.return_value = {'Events': []}

        result = await describe_rds_events(
            source_identifier='test-instance',
            source_type='db-instance',
            event_categories=None,
            duration=1440,
        )

        assert result.count == 0

    @pytest.mark.asyncio
    async def test_describe_events_with_time_range(self, mock_rds_client):
        """Test event retrieval with start and end time."""
        mock_rds_client.describe_events.return_value = {'Events': []}

        result = await describe_rds_events(
            source_identifier='test-instance',
            source_type='db-instance',
            event_categories=None,
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-01T23:59:59Z',
        )

        assert result.count == 0

    @pytest.mark.asyncio
    async def test_describe_events_invalid_categories(self):
        """Test event retrieval with invalid event categories."""
        result = await describe_rds_events(
            source_identifier='test-instance',
            source_type='db-instance',
            event_categories=['invalid-category'],
        )

        assert 'error' in result
        assert 'Invalid event categories' in result['error_message']

    @pytest.mark.asyncio
    async def test_describe_events_cluster_source(self, mock_rds_client):
        """Test event retrieval for cluster source type."""
        mock_rds_client.describe_events.return_value = {
            'Events': [
                {
                    'Message': 'Cluster failover completed',
                    'EventCategories': ['failover'],
                    'Date': datetime(2024, 1, 1, 12, 0, 0),
                }
            ]
        }

        result = await describe_rds_events(
            source_identifier='test-cluster',
            source_type='db-cluster',
            event_categories=['failover'],
        )

        assert result.source_type == 'db-cluster'
        assert result.count == 1

    @pytest.mark.asyncio
    async def test_describe_events_empty_response(self, mock_rds_client):
        """Test event retrieval with empty response."""
        mock_rds_client.describe_events.return_value = {'Events': []}

        result = await describe_rds_events(
            source_identifier='test-instance', source_type='db-instance', event_categories=None
        )

        assert result.count == 0
        assert len(result.events) == 0


class TestSourceTypeEventCategories:
    """Test cases for SOURCE_TYPE_TO_EVENT_CATEGORIES mapping."""

    def test_db_instance_categories(self):
        """Test that db-instance has expected categories."""
        categories = SOURCE_TYPE_TO_EVENT_CATEGORIES['db-instance']

        assert 'availability' in categories
        assert 'backup' in categories
        assert 'configuration change' in categories
        assert 'creation' in categories
        assert 'deletion' in categories
        assert 'failover' in categories

    def test_db_cluster_categories(self):
        """Test that db-cluster has expected categories."""
        categories = SOURCE_TYPE_TO_EVENT_CATEGORIES['db-cluster']

        assert 'configuration change' in categories
        assert 'creation' in categories
        assert 'failover' in categories
        assert 'maintenance' in categories

    def test_all_source_types_present(self):
        """Test that all expected source types are present."""
        expected_types = [
            'db-instance',
            'db-cluster',
            'db-cluster-snapshot',
            'db-parameter-group',
            'db-security-group',
            'db-snapshot',
            'db-proxy',
            'blue-green-deployment',
            'custom-engine-version',
        ]

        for source_type in expected_types:
            assert source_type in SOURCE_TYPE_TO_EVENT_CATEGORIES
