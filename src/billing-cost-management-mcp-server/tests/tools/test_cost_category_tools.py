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

import asyncio
import fastmcp
import importlib
import json
import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.cost_category_tools import (
    cost_category_server,
)
from botocore.exceptions import ClientError
from fastmcp import Context
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


COST_CATEGORY_ARN = 'arn:aws:ce::123456789012:costcategory/abcd-1234-efgh-5678'


@pytest.fixture(scope='module', autouse=True)
def _restore_real_tool_module():
    """Reload the module with the real FastMCP.tool after this file's tests.

    _reload_with_identity_decorator() leaves the module's server with no registered tools;
    restoring it keeps later test files from seeing that state.
    """
    yield
    from awslabs.billing_cost_management_mcp_server.tools import cost_category_tools as module

    importlib.reload(module)


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
    context.warning = AsyncMock()
    context.debug = AsyncMock()
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

    async def test_describe_date_only_effective_on_gets_midnight_utc(
        self, mock_context, mock_ce_client
    ):
        """A YYYY-MM-DD effective_on is sent as midnight UTC (the API needs a full datetime)."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.describe_cost_category_definition(
                mock_context, COST_CATEGORY_ARN, effective_on='2024-06-01'
            )

        mock_ce_client.describe_cost_category_definition.assert_called_once_with(
            CostCategoryArn=COST_CATEGORY_ARN,
            EffectiveOn='2024-06-01T00:00:00Z',
        )
        assert result['status'] == 'success'

    async def test_describe_impossible_date_effective_on_is_rejected_locally(
        self, mock_context, mock_ce_client
    ):
        """A YYYY-MM-DD value that is not a real date gets an error naming it; no API call."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.describe_cost_category_definition(
                mock_context, COST_CATEGORY_ARN, effective_on='2023-02-29'
            )

        mock_ce_client.describe_cost_category_definition.assert_not_called()
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'DescribeCostCategoryDefinition'
        assert '2023-02-29' in result['data']['message']

    async def test_describe_offset_effective_on_passes_unchanged(
        self, mock_context, mock_ce_client
    ):
        """A full datetime with a UTC offset is sent as given."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            await mod.describe_cost_category_definition(
                mock_context, COST_CATEGORY_ARN, effective_on='2024-06-01T00:00:00+07:00'
            )

        mock_ce_client.describe_cost_category_definition.assert_called_once_with(
            CostCategoryArn=COST_CATEGORY_ARN,
            EffectiveOn='2024-06-01T00:00:00+07:00',
        )


@pytest.mark.asyncio
class TestListCostCategoryDefinitions:
    """Tests for list_cost_category_definitions function."""

    async def test_list_no_filters(self, mock_context, mock_ce_client):
        """Test listing categories with no filters."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(mock_context)

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(MaxResults=100)
        assert result['status'] == 'success'
        assert len(result['data']['CostCategoryReferences']) == 1
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_list_with_effective_on(self, mock_context, mock_ce_client):
        """Test listing categories filtered by effective date."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(
                mock_context, effective_on='2024-06-01T00:00:00Z'
            )

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(
            EffectiveOn='2024-06-01T00:00:00Z', MaxResults=100
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
            SupportedResourceTypes=['billing:billingview'], MaxResults=100
        )
        assert result['status'] == 'success'

    async def test_list_with_max_items(self, mock_context, mock_ce_client):
        """max_items below the page maximum sets the page size."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(mock_context, max_items=10)

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
                max_items=5,
            )

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(
            EffectiveOn='2024-06-01T00:00:00Z',
            SupportedResourceTypes=['billing:billingview'],
            MaxResults=5,
        )
        assert result['status'] == 'success'

    async def test_list_without_max_items_fetches_every_page(self, mock_context):
        """Without max_items every page is fetched at the largest page size."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_category_definitions.side_effect = [
            {'CostCategoryReferences': [{'Name': 'A'}], 'NextToken': 't1'},
            {'CostCategoryReferences': [{'Name': 'B'}]},
        ]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_category_definitions(
                mock_context, effective_on='2024-06-01T00:00:00Z'
            )

        assert [c['Name'] for c in result['data']['CostCategoryReferences']] == ['A', 'B']
        assert 'complete_dataset' not in result['data']
        assert [c.kwargs for c in client.list_cost_category_definitions.call_args_list] == [
            {'EffectiveOn': '2024-06-01T00:00:00Z', 'MaxResults': 100},
            {'EffectiveOn': '2024-06-01T00:00:00Z', 'MaxResults': 100, 'NextToken': 't1'},
        ]

    async def test_list_max_items_stops_with_token(self, mock_context):
        """max_items stops after the requested total and returns the service token."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_category_definitions.return_value = {
            'CostCategoryReferences': [{'Name': 'A'}],
            'NextToken': 't1',
        }

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_category_definitions(mock_context, max_items=1)

        client.list_cost_category_definitions.assert_called_once_with(MaxResults=1)
        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 't1'
        assert result['data']['pagination']['has_more'] is True

    async def test_list_continuation_sends_caller_token(self, mock_context):
        """A continuation sends the caller's token and otherwise identical params."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_category_definitions.return_value = {
            'CostCategoryReferences': [{'CostCategoryArn': COST_CATEGORY_ARN}]
        }

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_category_definitions(
                mock_context, effective_on='2024-06-01T00:00:00Z', next_token='token456'
            )

        client.list_cost_category_definitions.assert_called_once_with(
            EffectiveOn='2024-06-01T00:00:00Z', MaxResults=100, NextToken='token456'
        )
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
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'ListCostCategoryDefinitions'
        assert result['service'] == 'Cost Explorer'

    async def test_list_date_only_effective_on_gets_midnight_utc(
        self, mock_context, mock_ce_client
    ):
        """A YYYY-MM-DD effective_on is sent as midnight UTC (the API needs a full datetime)."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(
                mock_context, effective_on='2024-06-01'
            )

        mock_ce_client.list_cost_category_definitions.assert_called_once_with(
            EffectiveOn='2024-06-01T00:00:00Z', MaxResults=100
        )
        assert result['status'] == 'success'

    async def test_list_impossible_date_effective_on_is_rejected_locally(
        self, mock_context, mock_ce_client
    ):
        """A YYYY-MM-DD value that is not a real date gets an error naming it; no API call."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_category_definitions(
                mock_context, effective_on='2023-02-29'
            )

        mock_ce_client.list_cost_category_definitions.assert_not_called()
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'ListCostCategoryDefinitions'
        assert '2023-02-29' in result['data']['message']


def _served_description(name: str) -> str:
    tool = asyncio.run(cost_category_server.get_tool(name))
    assert tool is not None
    return ' '.join((tool.description or '').split())


def test_describe_description_lists_rule_dimensions():
    """Rules use SERVICE_CODE, not SERVICE, and the first matching rule wins."""
    description = _served_description('describe-cost-category-definition')

    assert '(SERVICE, LINKED_ACCOUNT, USAGE_TYPE)' not in description
    assert 'Linked accounts can describe' not in description
    for dimension in (
        'LINKED_ACCOUNT',
        'SERVICE_CODE',
        'RECORD_TYPE',
        'LINKED_ACCOUNT_NAME',
        'REGION',
        'USAGE_TYPE',
    ):
        assert re.search(rf'\b{dimension}\b', description), dimension
    assert 'first rule that matches' in description
    for option in ('STARTS_WITH', 'ENDS_WITH', 'CONTAINS'):
        assert option in description


def test_list_description_states_resource_type_filter_semantics():
    """The filter takes three types, needs all of them, and returns [] for an unknown type."""
    description = _served_description('list-cost-category-definitions')

    for resource_type in (
        'billing:rispgroupsharing',
        'billing:billingview',
        'billing:creditsharing',
    ):
        assert resource_type in description
    assert 'support every listed type' in description
    assert 'that is not a known type returns no categories, not an error' in description
    assert '"billingview" or "billing:", fails with ValidationException' in description
    assert 'At most 5 values' in description


def test_descriptions_state_effective_on_formats():
    """Both tools accept YYYY-MM-DD and say versions start on the first of a month."""
    for name in ('describe-cost-category-definition', 'list-cost-category-definitions'):
        description = _served_description(name)
        assert 'YYYY-MM-DD' in description, name
        assert 'first day of a month' in description, name


@pytest.mark.parametrize(
    'value, expected',
    [
        ('2024-06-01', '2024-06-01T00:00:00Z'),
        ('2024-06-01T00:00:00Z', '2024-06-01T00:00:00Z'),
        ('2024-06-01T00:00:00+07:00', '2024-06-01T00:00:00+07:00'),
        (' 2024-06-01', ' 2024-06-01'),
        ('2024-06-01T00:00:00', '2024-06-01T00:00:00'),
        ('2024-06-01\n', '2024-06-01\n'),
    ],
)
def test_normalize_effective_on(value, expected):
    """Only a real YYYY-MM-DD date is rewritten; any other shape is left for the API to judge."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_category_tools as mod

    assert mod._normalize_effective_on(value) == expected


@pytest.mark.parametrize('value', ['2023-02-29', '2024-02-30', '2024-13-01', '2024-00-10'])
def test_normalize_effective_on_rejects_impossible_dates(value):
    """A YYYY-MM-DD shaped value that is not a calendar date raises, naming the value."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_category_tools as mod

    with pytest.raises(ValueError, match=value):
        mod._normalize_effective_on(value)
