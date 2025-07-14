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

"""Tests for the resources module."""

import json
import pytest
from awslabs.s3_tables_mcp_server.models import (
    TableBucketsResource,
    TableBucketSummary,
)
from awslabs.s3_tables_mcp_server.resources import (
    create_error_response,
    create_resource_response,
    get_table_buckets,
    list_namespaces_resource,
    list_table_buckets_resource,
    list_tables_resource,
    paginate_and_collect,
)
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestCreateErrorResponse:
    """Test the create_error_response function."""

    def test_create_error_response(self):
        """Test creating error response."""
        # Arrange
        error = ValueError('Test error')
        resource_name = 'table_buckets'

        # Act
        result = create_error_response(error, resource_name)

        # Assert
        expected = '{"error": "Test error", "table_buckets": [], "total_count": 0}'
        assert result == expected

    def test_create_error_response_with_complex_error(self):
        """Test creating error response with complex error."""
        # Arrange
        error = RuntimeError('Complex error with details')
        resource_name = 'namespaces'

        # Act
        result = create_error_response(error, resource_name)

        # Assert
        expected = '{"error": "Complex error with details", "namespaces": [], "total_count": 0}'
        assert result == expected

    def test_create_error_response_json_parsable(self):
        """Test that error response is valid JSON."""
        # Arrange
        error = Exception('JSON test')
        resource_name = 'tables'

        # Act
        result = create_error_response(error, resource_name)

        # Assert
        parsed = json.loads(result)
        assert parsed['error'] == 'JSON test'
        assert parsed['tables'] == []
        assert parsed['total_count'] == 0


class TestPaginateAndCollect:
    """Test the paginate_and_collect function."""

    @pytest.mark.asyncio
    async def test_paginate_and_collect_single_page(self):
        """Test pagination with single page."""
        # Arrange
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'items': [{'id': '1', 'name': 'test1'}, {'id': '2', 'name': 'test2'}]}
        ]

        def item_constructor(item):
            return {'id': item['id'], 'name': item['name']}

        # Act
        result = await paginate_and_collect(
            paginator=mock_paginator,
            collection_key='items',
            item_constructor=item_constructor,
            param1='value1',
        )

        # Assert
        assert len(result) == 2
        assert result[0] == {'id': '1', 'name': 'test1'}
        assert result[1] == {'id': '2', 'name': 'test2'}
        mock_paginator.paginate.assert_called_once_with(param1='value1')

    @pytest.mark.asyncio
    async def test_paginate_and_collect_multiple_pages(self):
        """Test pagination with multiple pages."""
        # Arrange
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'items': [{'id': '1', 'name': 'test1'}]},
            {'items': [{'id': '2', 'name': 'test2'}]},
            {'items': [{'id': '3', 'name': 'test3'}]},
        ]

        def item_constructor(item):
            return {'id': item['id'], 'name': item['name']}

        # Act
        result = await paginate_and_collect(
            paginator=mock_paginator, collection_key='items', item_constructor=item_constructor
        )

        # Assert
        assert len(result) == 3
        assert result[0] == {'id': '1', 'name': 'test1'}
        assert result[1] == {'id': '2', 'name': 'test2'}
        assert result[2] == {'id': '3', 'name': 'test3'}

    @pytest.mark.asyncio
    async def test_paginate_and_collect_empty_pages(self):
        """Test pagination with empty pages."""
        # Arrange
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'items': []}, {'items': []}]

        def item_constructor(item):
            return item

        # Act
        result = await paginate_and_collect(
            paginator=mock_paginator, collection_key='items', item_constructor=item_constructor
        )

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_paginate_and_collect_missing_collection_key(self):
        """Test pagination with missing collection key."""
        # Arrange
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'other_key': [{'id': '1'}]}]

        def item_constructor(item):
            return item

        # Act
        result = await paginate_and_collect(
            paginator=mock_paginator, collection_key='items', item_constructor=item_constructor
        )

        # Assert
        assert len(result) == 0


class TestCreateResourceResponse:
    """Test the create_resource_response function."""

    @pytest.mark.asyncio
    async def test_create_resource_response_success(self):
        """Test successful resource response creation."""
        # Arrange
        items = [
            TableBucketSummary(
                arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
                name='test-bucket',
                owner_account_id='123456789012',
                created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
            )
        ]

        # Act
        result = await create_resource_response(
            items=items, resource_class=TableBucketsResource, resource_name='table_buckets'
        )

        # Assert
        parsed = json.loads(result)
        assert (
            parsed['table_buckets'][0]['arn']
            == 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
        )
        assert parsed['table_buckets'][0]['name'] == 'test-bucket'
        assert parsed['total_count'] == 1

    @pytest.mark.asyncio
    async def test_create_resource_response_with_exception(self):
        """Test resource response creation with exception."""
        # Arrange
        items = [{'invalid': 'item'}]

        # Act
        result = await create_resource_response(
            items=items, resource_class=TableBucketsResource, resource_name='table_buckets'
        )

        # Assert
        parsed = json.loads(result)
        assert 'error' in parsed
        assert parsed['table_buckets'] == []
        assert parsed['total_count'] == 0

    @pytest.mark.asyncio
    async def test_create_resource_response_empty_items(self):
        """Test resource response creation with empty items."""
        # Arrange
        items = []

        # Act
        result = await create_resource_response(
            items=items, resource_class=TableBucketsResource, resource_name='table_buckets'
        )

        # Assert
        parsed = json.loads(result)
        assert parsed['table_buckets'] == []
        assert parsed['total_count'] == 0


class TestListTableBucketsResource:
    """Test the list_table_buckets_resource function."""

    @pytest.mark.asyncio
    async def test_list_table_buckets_resource_success(self):
        """Test successful table buckets resource listing."""
        # Arrange
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'tableBuckets': [
                    {
                        'arn': 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
                        'name': 'test-bucket',
                        'ownerAccountId': '123456789012',
                        'createdAt': '2023-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        with patch(
            'awslabs.s3_tables_mcp_server.resources.get_s3tables_client', return_value=mock_client
        ):
            # Act
            result = await list_table_buckets_resource()

            # Assert
            parsed = json.loads(result)
            assert len(parsed['table_buckets']) == 1
            assert (
                parsed['table_buckets'][0]['arn']
                == 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
            )
            assert parsed['total_count'] == 1

    @pytest.mark.asyncio
    async def test_list_table_buckets_resource_exception(self):
        """Test table buckets resource listing with exception."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_paginator.side_effect = Exception('API Error')

        with patch(
            'awslabs.s3_tables_mcp_server.resources.get_s3tables_client', return_value=mock_client
        ):
            # Act
            result = await list_table_buckets_resource()

            # Assert
            parsed = json.loads(result)
            assert parsed['error'] == 'API Error'
            assert parsed['table_buckets'] == []
            assert parsed['total_count'] == 0

    @pytest.mark.asyncio
    async def test_list_table_buckets_resource_empty(self):
        """Test table buckets resource listing with empty results."""
        # Arrange
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'tableBuckets': []}]
        mock_client.get_paginator.return_value = mock_paginator

        with patch(
            'awslabs.s3_tables_mcp_server.resources.get_s3tables_client', return_value=mock_client
        ):
            # Act
            result = await list_table_buckets_resource()

            # Assert
            parsed = json.loads(result)
            assert parsed['table_buckets'] == []
            assert parsed['total_count'] == 0

    @pytest.mark.asyncio
    async def test_list_table_buckets_resource_with_region(self):
        """Test table buckets resource listing with region_name provided."""
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'tableBuckets': [
                    {
                        'arn': 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
                        'name': 'test-bucket',
                        'ownerAccountId': '123456789012',
                        'createdAt': '2023-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator
        with patch(
            'awslabs.s3_tables_mcp_server.resources.get_s3tables_client'
        ) as mock_get_client:
            mock_get_client.return_value = mock_client
            result = await list_table_buckets_resource(region_name='us-west-2')
            parsed = json.loads(result)
            assert len(parsed['table_buckets']) == 1
            mock_get_client.assert_called_once_with('us-west-2')

    @pytest.mark.asyncio
    async def test_list_table_buckets_resource_invalid_region(self):
        """Test table buckets resource listing with invalid region_name."""
        with patch(
            'awslabs.s3_tables_mcp_server.resources.get_s3tables_client'
        ) as mock_get_client:
            mock_get_client.side_effect = Exception('Invalid region')
            result = await list_table_buckets_resource(region_name='bad-region')
            parsed = json.loads(result)
            assert parsed['error'] == 'Invalid region'
            assert parsed['table_buckets'] == []
            assert parsed['total_count'] == 0


class TestGetTableBuckets:
    """Test the get_table_buckets function."""

    @pytest.mark.asyncio
    async def test_get_table_buckets_success(self):
        """Test successful table buckets retrieval."""
        # Arrange
        mock_response = '{"table_buckets": [{"arn": "arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket", "name": "test-bucket", "owner_account_id": "123456789012", "created_at": "2023-01-01T00:00:00Z"}], "total_count": 1}'

        with patch(
            'awslabs.s3_tables_mcp_server.resources.list_table_buckets_resource',
            return_value=mock_response,
        ):
            # Act
            result = await get_table_buckets()

            # Assert
            assert len(result) == 1
            assert result[0].arn == 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
            assert result[0].name == 'test-bucket'

    @pytest.mark.asyncio
    async def test_get_table_buckets_with_error(self):
        """Test table buckets retrieval with error."""
        # Arrange
        mock_response = '{"error": "API Error", "table_buckets": [], "total_count": 0}'

        with patch(
            'awslabs.s3_tables_mcp_server.resources.list_table_buckets_resource',
            return_value=mock_response,
        ):
            # Act & Assert
            with pytest.raises(Exception, match='API Error'):
                await get_table_buckets()


class TestListNamespacesResource:
    """Test the list_namespaces_resource function."""

    @pytest.mark.asyncio
    async def test_list_namespaces_resource_success(self):
        """Test successful namespaces resource listing."""
        # Arrange
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'namespaces': [
                    {
                        'namespace': ['test-namespace'],
                        'createdAt': '2023-01-01T00:00:00Z',
                        'createdBy': '123456789012',
                        'ownerAccountId': '123456789012',
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        # Mock get_table_buckets to return a bucket
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )

        with (
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_s3tables_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
        ):
            # Act
            result = await list_namespaces_resource()

            # Assert
            parsed = json.loads(result)
            assert len(parsed['namespaces']) == 1
            assert parsed['namespaces'][0]['namespace'] == ['test-namespace']
            assert parsed['total_count'] == 1

    @pytest.mark.asyncio
    async def test_list_namespaces_resource_exception(self):
        """Test namespaces resource listing with exception."""
        # Arrange
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )

        with (
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
            patch('awslabs.s3_tables_mcp_server.resources.get_s3tables_client') as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get_paginator.side_effect = Exception('API Error')
            mock_get_client.return_value = mock_client

            # Act
            result = await list_namespaces_resource()

            # Assert
            parsed = json.loads(result)
            assert parsed['error'] == 'API Error'
            assert parsed['namespaces'] == []
            assert parsed['total_count'] == 0

    @pytest.mark.asyncio
    async def test_list_namespaces_resource_no_buckets(self):
        """Test namespaces resource listing with no buckets."""
        # Arrange
        with patch('awslabs.s3_tables_mcp_server.resources.get_table_buckets', return_value=[]):
            # Act
            result = await list_namespaces_resource()

            # Assert
            parsed = json.loads(result)
            assert parsed['namespaces'] == []
            assert parsed['total_count'] == 0

    @pytest.mark.asyncio
    async def test_list_namespaces_resource_with_region(self):
        """Test namespaces resource listing with region_name provided."""
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'namespaces': [
                    {
                        'namespace': ['test-namespace'],
                        'createdAt': '2023-01-01T00:00:00Z',
                        'createdBy': '123456789012',
                        'ownerAccountId': '123456789012',
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )
        with (
            patch('awslabs.s3_tables_mcp_server.resources.get_s3tables_client') as mock_get_client,
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
        ):
            mock_get_client.return_value = mock_client
            result = await list_namespaces_resource(region_name='us-west-2')
            parsed = json.loads(result)
            assert len(parsed['namespaces']) == 1
            mock_get_client.assert_called_with('us-west-2')

    @pytest.mark.asyncio
    async def test_list_namespaces_resource_invalid_region(self):
        """Test namespaces resource listing with invalid region_name."""
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )
        with (
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
            patch('awslabs.s3_tables_mcp_server.resources.get_s3tables_client') as mock_get_client,
        ):
            mock_get_client.side_effect = Exception('Invalid region')
            result = await list_namespaces_resource(region_name='bad-region')
            parsed = json.loads(result)
            assert parsed['error'] == 'Invalid region'
            assert parsed['namespaces'] == []
            assert parsed['total_count'] == 0


class TestListTablesResource:
    """Test the list_tables_resource function."""

    @pytest.mark.asyncio
    async def test_list_tables_resource_success(self):
        """Test successful tables resource listing."""
        # Arrange
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'tables': [
                    {
                        'name': 'test-table',
                        'namespace': ['test-namespace'],
                        'type': 'customer',
                        'tableARN': 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket/table/123e4567-e89b-12d3-a456-426614174000',
                        'createdAt': '2023-01-01T00:00:00Z',
                        'modifiedAt': '2023-01-01T00:00:00Z',
                        'createdBy': '123456789012',
                        'ownerAccountId': '123456789012',
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        # Mock get_table_buckets to return a bucket
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )

        with (
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_s3tables_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
        ):
            # Act
            result = await list_tables_resource()

            # Assert
            parsed = json.loads(result)
            assert len(parsed['tables']) == 1
            assert parsed['tables'][0]['name'] == 'test-table'
            assert parsed['tables'][0]['namespace'] == ['test-namespace']
            assert parsed['total_count'] == 1

    @pytest.mark.asyncio
    async def test_list_tables_resource_exception(self):
        """Test tables resource listing with exception."""
        # Arrange
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )

        with (
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
            patch('awslabs.s3_tables_mcp_server.resources.get_s3tables_client') as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get_paginator.side_effect = Exception('API Error')
            mock_get_client.return_value = mock_client

            # Act
            result = await list_tables_resource()

            # Assert
            parsed = json.loads(result)
            assert parsed['error'] == 'API Error'
            assert parsed['tables'] == []
            assert parsed['total_count'] == 0

    @pytest.mark.asyncio
    async def test_list_tables_resource_no_buckets(self):
        """Test tables resource listing with no buckets."""
        # Arrange
        with patch('awslabs.s3_tables_mcp_server.resources.get_table_buckets', return_value=[]):
            # Act
            result = await list_tables_resource()

            # Assert
            parsed = json.loads(result)
            assert parsed['tables'] == []
            assert parsed['total_count'] == 0

    @pytest.mark.asyncio
    async def test_list_tables_resource_with_region(self):
        """Test tables resource listing with region_name provided."""
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'tables': [
                    {
                        'name': 'test-table',
                        'namespace': ['test-namespace'],
                        'type': 'customer',
                        'tableARN': 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket/table/123e4567-e89b-12d3-a456-426614174000',
                        'createdAt': '2023-01-01T00:00:00Z',
                        'modifiedAt': '2023-01-01T00:00:00Z',
                        'createdBy': '123456789012',
                        'ownerAccountId': '123456789012',
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )
        with (
            patch('awslabs.s3_tables_mcp_server.resources.get_s3tables_client') as mock_get_client,
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
        ):
            mock_get_client.return_value = mock_client
            result = await list_tables_resource(region_name='us-west-2')
            parsed = json.loads(result)
            assert len(parsed['tables']) == 1
            mock_get_client.assert_called_with('us-west-2')

    @pytest.mark.asyncio
    async def test_list_tables_resource_invalid_region(self):
        """Test tables resource listing with invalid region_name."""
        mock_bucket = TableBucketSummary(
            arn='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            name='test-bucket',
            owner_account_id='123456789012',
            created_at=datetime.fromisoformat('2023-01-01T00:00:00+00:00'),
        )
        with (
            patch(
                'awslabs.s3_tables_mcp_server.resources.get_table_buckets',
                return_value=[mock_bucket],
            ),
            patch('awslabs.s3_tables_mcp_server.resources.get_s3tables_client') as mock_get_client,
        ):
            mock_get_client.side_effect = Exception('Invalid region')
            result = await list_tables_resource(region_name='bad-region')
            parsed = json.loads(result)
            assert parsed['error'] == 'Invalid region'
            assert parsed['tables'] == []
            assert parsed['total_count'] == 0
