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

"""Simple tests for metadata_handler module."""

import pytest
from awslabs.cost_explorer_mcp_server.helpers import (
    get_available_dimension_values,
    get_available_tag_values,
)
from awslabs.cost_explorer_mcp_server.metadata_handler import get_dimension_values, get_tag_values
from awslabs.cost_explorer_mcp_server.models import DateRange, DimensionKey
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_ce_client():
    """Mock Cost Explorer client."""
    with patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def valid_date_range():
    """Valid date range for testing."""
    return DateRange(start_date='2025-01-01', end_date='2025-01-31')


@pytest.fixture
def valid_dimension():
    """Valid dimension for testing."""
    return DimensionKey(dimension_key='SERVICE')


class TestDimensionValues:
    """Test dimension value retrieval."""

    @pytest.mark.asyncio
    async def test_get_dimension_values_success(
        self, mock_ce_client, valid_date_range, valid_dimension
    ):
        """Test successful dimension values retrieval."""
        # Setup mock response
        mock_ce_client.get_dimension_values.return_value = {
            'DimensionValues': [
                {'Value': 'Amazon Elastic Compute Cloud - Compute'},
                {'Value': 'Amazon Simple Storage Service'},
            ]
        }

        ctx = MagicMock()
        result = await get_dimension_values(ctx, valid_date_range, valid_dimension)

        assert result['dimension'] == 'SERVICE'
        assert len(result['values']) == 2
        assert 'Amazon Elastic Compute Cloud - Compute' in result['values']

    @pytest.mark.asyncio
    async def test_get_dimension_values_error(
        self, mock_ce_client, valid_date_range, valid_dimension
    ):
        """Test dimension values retrieval with error."""
        mock_ce_client.get_dimension_values.side_effect = Exception('API Error')

        ctx = MagicMock()
        result = await get_dimension_values(ctx, valid_date_range, valid_dimension)

        assert 'error' in result
        assert 'API Error' in result['error']


class TestTagValues:
    """Test tag value retrieval."""

    @pytest.mark.asyncio
    async def test_get_tag_values_success(self, mock_ce_client, valid_date_range):
        """Test successful tag values retrieval."""
        mock_ce_client.get_tags.return_value = {'Tags': ['dev', 'prod', 'test']}

        ctx = MagicMock()
        result = await get_tag_values(ctx, valid_date_range, 'Environment')

        assert result['tag_key'] == 'Environment'
        assert result['values'] == ['dev', 'prod', 'test']

    @pytest.mark.asyncio
    async def test_get_tag_values_error(self, mock_ce_client, valid_date_range):
        """Test tag values retrieval with error."""
        mock_ce_client.get_tags.side_effect = Exception('API Error')

        ctx = MagicMock()
        result = await get_tag_values(ctx, valid_date_range, 'Environment')

        assert 'error' in result


class TestImplementationFunctions:
    """Tests for the implementation functions that were moved to helpers."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_dimension_values_success(self, mock_get_client):
        """Test successful dimension values retrieval."""
        # Setup mock client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_dimension_values.return_value = {
            'DimensionValues': [
                {'Value': 'EC2', 'Attributes': {}},
                {'Value': 'S3', 'Attributes': {}},
            ]
        }

        result = get_available_dimension_values('SERVICE', '2025-01-01', '2025-01-31')

        assert 'values' in result
        assert 'EC2' in result['values']
        assert 'S3' in result['values']
        mock_client.get_dimension_values.assert_called_once()

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_dimension_values_error(self, mock_get_client):
        """Test dimension values retrieval with error."""
        # Setup mock client to raise exception
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_dimension_values.side_effect = Exception('API Error')

        result = get_available_dimension_values('SERVICE', '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'API Error' in result['error']

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_tag_values_success(self, mock_get_client):
        """Test successful tag values retrieval."""
        # Setup mock client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_tags.return_value = {'Tags': ['Production', 'Development', 'Testing']}

        result = get_available_tag_values('Environment', '2025-01-01', '2025-01-31')

        assert 'values' in result
        assert 'Production' in result['values']
        assert 'Development' in result['values']
        mock_client.get_tags.assert_called_once()

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_tag_values_error(self, mock_get_client):
        """Test tag values retrieval with error."""
        # Setup mock client to raise exception
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_tags.side_effect = Exception('API Error')

        result = get_available_tag_values('Environment', '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'API Error' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.metadata_handler.get_available_dimension_values')
    async def test_get_dimension_values_error(self, mock_get_values):
        """Test get_dimension_values with error."""
        mock_get_values.return_value = {'error': 'API Error'}

        ctx = MagicMock()
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')
        dimension = DimensionKey(dimension_key='SERVICE')

        result = await get_dimension_values(ctx, date_range, dimension)

        assert 'error' in result
        assert 'API Error' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.metadata_handler.get_available_tag_values')
    async def test_get_tag_values_error(self, mock_get_values):
        """Test get_tag_values with error."""
        mock_get_values.return_value = {'error': 'Tag API Error'}

        ctx = MagicMock()
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        result = await get_tag_values(ctx, date_range, 'Environment')

        assert 'error' in result
        assert 'Tag API Error' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.metadata_handler.get_available_dimension_values')
    async def test_get_dimension_values_exception(self, mock_get_values):
        """Test get_dimension_values with exception."""
        mock_get_values.side_effect = Exception('Unexpected error')

        ctx = MagicMock()
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')
        dimension = DimensionKey(dimension_key='SERVICE')

        result = await get_dimension_values(ctx, date_range, dimension)

        assert 'error' in result
        assert 'Error getting dimension values' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.metadata_handler.get_available_tag_values')
    async def test_get_tag_values_exception(self, mock_get_values):
        """Test get_tag_values with exception."""
        mock_get_values.side_effect = Exception('Unexpected tag error')

        ctx = MagicMock()
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        result = await get_tag_values(ctx, date_range, 'Environment')

        assert 'error' in result
        assert 'Error getting tag values' in result['error']
