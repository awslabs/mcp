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

"""Unit tests for the cost_category_tools module.

These tests verify the functionality of the Cost Category API tools, including:
- Describing cost category definitions
- Listing cost category definitions with various filters
- Pagination handling
- Error handling for API exceptions and invalid inputs
"""

import fastmcp
import importlib
import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_category_tools import (
    cost_category_server,
)
from botocore.exceptions import ClientError
from fastmcp import Context
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


COST_CATEGORY_ARN = 'arn:aws:ce::123456789012:costcategory/abcd-1234-efgh-5678'


def _reload_with_identity_decorator() -> Any:
    """Reload module with FastMCP.tool patched to return the original function."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_category_tools as mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(mod)
        return mod


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    mock_client = MagicMock()

    mock_client.describe_cost_category_definition.return_value = {
        'CostCategory': {
            'CostCategoryArn': COST_CATEGORY_ARN,
            'Name': 'Environment',
            'RuleVersion': 'CostCategoryExpression.v1',
            'Rules': [
                {
                    'Value': 'Production',
                    'Rule': {
                        'Tags': {
                            'Key': 'Environment',
                            'Values': ['prod', 'production'],
                            'MatchOptions': ['EQUALS'],
                        }
                    },
                    'Type': 'REGULAR',
                },
            ],
            'DefaultValue': 'Other',
            'EffectiveStart': '2024-01-01T00:00:00Z',
            'EffectiveEnd': None,
            'ProcessingStatus': [{'Component': 'COST_EXPLORER', 'Status': 'APPLIED'}],
        },
    }

    mock_client.list_cost_category_definitions.return_value = {
        'CostCategoryReferences': [
            {
                'CostCategoryArn': COST_CATEGORY_ARN,
                'Name': 'Environment',
                'NumberOfRules': 3,
                'EffectiveStart': '2024-01-01T00:00:00Z',
                'EffectiveEnd': None,
                'DefaultValue': 'Other',
                'Values': ['Production', 'Development', 'Other'],
                'ProcessingStatus': [{'Component': 'COST_EXPLORER', 'Status': 'APPLIED'}],
            },
        ],
    }

    return mock_client


def test_cost_category_server_initialization():
    """Test that the cost_category_server is properly initialized."""
    assert cost_category_server.name == 'cost-category-tools'
    instructions = cost_category_server.instructions
    assert instructions is not None
    assert 'Cost Categories' in instructions if instructions else False


@pytest.mark.asyncio
class TestDescribeCostCategoryDefinition:
    """Tests for describe_cost_category_definition function."""

    async def test_describe_success(self, mock_context, mock_ce_client):
        """Test successful describe of a cost category."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.describe_cost_category_definition(mock_context, COST_CATEGORY_ARN)

        mock_ce_client.describe_cost_category_definition.assert_called_once_with(
            CostCategoryArn=COST_CATEGORY_ARN
        )
        assert result['status'] == 'success'
        assert result['data']['CostCategory']['Name'] == 'Environment'
        assert result['data']['CostCategory']['DefaultValue'] == 'Other'

    async def test_describe_with_effective_on(self, mock_context, mock_ce_client):
        """Test describe with effective_on parameter."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.describe_cost_category_definition(
                mock_context, COST_CATEGORY_ARN, effective_on='2024-06-01T00:00:00Z'
            )

        mock_ce_client.describe_cost_category_definition.assert_called_once_with(
            CostCategoryArn=COST_CATEGORY_ARN,
            EffectiveOn='2024-06-01T00:00:00Z',
        )
        assert result['status'] == 'success'

    async def test_describe_not_found(self, mock_context):
        """Test error handling when cost category is not found."""
        mod = _reload_with_identity_decorator()
        error = ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Cost category not found',
                }
            },
            'DescribeCostCategoryDefinition',
        )
        mock_client = MagicMock()
        mock_client.describe_cost_category_definition.side_effect = error
        mock_handle = AsyncMock(
            return_value={'status': 'error', 'message': 'Cost category not found'}
        )

        with (
            patch.object(mod, 'create_aws_client', return_value=mock_client),
            patch.object(mod, 'handle_aws_error', mock_handle),
        ):
            result = await mod.describe_cost_category_definition(mock_context, COST_CATEGORY_ARN)

        mock_handle.assert_called_once_with(
            mock_context, error, 'DescribeCostCategoryDefinition', 'Cost Explorer'
        )
        assert result['status'] == 'error'

    async def test_describe_generic_exception(self, mock_context):
        """Test error handling for generic exceptions."""
        mod = _reload_with_identity_decorator()
        error = Exception('Unexpected error')
        mock_handle = AsyncMock(return_value={'status': 'error', 'message': 'Unexpected error'})

        with (
            patch.object(mod, 'create_aws_client', side_effect=error),
            patch.object(mod, 'handle_aws_error', mock_handle),
        ):
            result = await mod.describe_cost_category_definition(mock_context, COST_CATEGORY_ARN)

        mock_handle.assert_called_once_with(
            mock_context, error, 'DescribeCostCategoryDefinition', 'Cost Explorer'
        )
        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestListCostCategoryDefinitions:
    """Tests for list_cost_category_definitions function."""

    async def test_list_no_filters(self, mock_context, mock_ce_client):
        """Test listing categories with no filters."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(mock_context)

        mock_ce_client.list_cost_category_definitions.assert_called_once_with()
        assert result['status'] == 'success'
        assert len(result['data']['CostCategoryReferences']) == 1

    async def test_list_with_effective_on(self, mock_context, mock_ce_client):
        """Test listing categories filtered by effective date."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(
                mock_context, effective_on='2024-06-01T00:00:00Z'
            )

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(
            EffectiveOn='2024-06-01T00:00:00Z'
        )
        assert result['status'] == 'success'

    async def test_list_with_supported_resource_types(self, mock_context, mock_ce_client):
        """Test listing categories filtered by supported resource types."""
        mod = _reload_with_identity_decorator()
        resource_types = json.dumps(['billing:billingview'])

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(
                mock_context, supported_resource_types=resource_types
            )

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(
            SupportedResourceTypes=['billing:billingview']
        )
        assert result['status'] == 'success'

    async def test_list_with_max_results(self, mock_context, mock_ce_client):
        """Test listing categories with max_results."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(mock_context, max_results=10)

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(MaxResults=10)
        assert result['status'] == 'success'

    async def test_list_with_all_filters(self, mock_context, mock_ce_client):
        """Test listing categories with all filters combined."""
        mod = _reload_with_identity_decorator()
        resource_types = json.dumps(['billing:billingview'])

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(
                mock_context,
                effective_on='2024-06-01T00:00:00Z',
                supported_resource_types=resource_types,
                max_results=5,
            )

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(
            EffectiveOn='2024-06-01T00:00:00Z',
            SupportedResourceTypes=['billing:billingview'],
            MaxResults=5,
        )
        assert result['status'] == 'success'

    async def test_list_with_max_pages(self, mock_context, mock_ce_client):
        """Test listing categories with auto-pagination."""
        mod = _reload_with_identity_decorator()
        mock_paginate = AsyncMock(
            return_value=(
                [{'CostCategoryArn': COST_CATEGORY_ARN, 'Name': 'Environment'}],
                {'total_results': 1, 'pages_fetched': 1},
            )
        )

        with (
            patch.object(mod, 'create_aws_client', return_value=mock_ce_client),
            patch.object(mod, 'paginate_aws_response', mock_paginate),
        ):
            result = await mod.list_cost_category_definitions(mock_context, max_pages=5)

        mock_paginate.assert_called_once()
        assert result['status'] == 'success'
        assert len(result['data']['CostCategoryReferences']) == 1

    async def test_list_with_next_token(self, mock_context, mock_ce_client):
        """Test listing categories with next_token triggers pagination."""
        mod = _reload_with_identity_decorator()
        mock_paginate = AsyncMock(
            return_value=(
                [{'CostCategoryArn': COST_CATEGORY_ARN, 'Name': 'Environment'}],
                {'total_results': 1, 'pages_fetched': 1},
            )
        )

        with (
            patch.object(mod, 'create_aws_client', return_value=mock_ce_client),
            patch.object(mod, 'paginate_aws_response', mock_paginate),
        ):
            result = await mod.list_cost_category_definitions(mock_context, next_token='token456')

        mock_paginate.assert_called_once()
        assert result['status'] == 'success'

    async def test_list_client_error(self, mock_context):
        """Test error handling for ClientError."""
        mod = _reload_with_identity_decorator()
        error = ClientError(
            {'Error': {'Code': 'ServiceException', 'Message': 'Service error'}},
            'ListCostCategoryDefinitions',
        )
        mock_handle = AsyncMock(return_value={'status': 'error', 'message': 'Service error'})

        with (
            patch.object(mod, 'create_aws_client', side_effect=error),
            patch.object(mod, 'handle_aws_error', mock_handle),
        ):
            result = await mod.list_cost_category_definitions(mock_context)

        mock_handle.assert_called_once_with(
            mock_context, error, 'ListCostCategoryDefinitions', 'Cost Explorer'
        )
        assert result['status'] == 'error'

    async def test_list_invalid_resource_types_json(self, mock_context):
        """Test error handling for invalid JSON in supported_resource_types."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=MagicMock()):
            result = await mod.list_cost_category_definitions(
                mock_context, supported_resource_types='not valid json'
            )

        assert result['status'] == 'error'
        assert 'Invalid JSON for supported_resource_types parameter' in result['data']['message']
