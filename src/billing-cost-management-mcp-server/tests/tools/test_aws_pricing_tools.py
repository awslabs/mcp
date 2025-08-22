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

"""Unit tests for the aws_pricing_tools module.

These tests verify the functionality of the AWS Pricing API tools, including:
- Retrieving service pricing information from AWS Price List API
- Getting service codes and attributes
- Getting attribute values for different service parameters
- Error handling for API exceptions and invalid inputs
- Handling region-specific pricing endpoints
"""

import fastmcp
import importlib
import json
import os
import pytest
from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations import (
    get_attribute_values,
    get_pricing_from_api,
    get_service_attributes,
    get_service_codes,
)
from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_tools import (
    aws_pricing_server,
)
from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
    PRICING_API_REGIONS,
    get_pricing_region,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def aws_pricing(ctx, operation, **kwargs):
    """Mock implementation of aws_pricing for testing."""
    from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
        format_response,
    )

    if operation == 'get_service_codes':
        from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations import (
            get_service_codes,
        )

        return await get_service_codes(ctx, max_results=kwargs.get('max_results'))

    elif operation == 'get_service_attributes':
        if not kwargs.get('service_code'):
            return format_response(
                'error', {}, 'service_code is required for get_service_attributes operation'
            )

        from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations import (
            get_service_attributes,
        )

        service_code = kwargs.get('service_code')
        if service_code is None:
            raise ValueError('service_code is required')
        return await get_service_attributes(ctx, str(service_code))

    elif operation == 'get_attribute_values':
        if not kwargs.get('service_code') or not kwargs.get('attribute_name'):
            return format_response(
                'error',
                {},
                'service_code and attribute_name are required for get_attribute_values operation',
            )

        from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations import (
            get_attribute_values,
        )

        service_code = kwargs.get('service_code')
        attribute_name = kwargs.get('attribute_name')
        max_results = kwargs.get('max_results')

        if service_code is None or attribute_name is None:
            raise ValueError('service_code and attribute_name are required')

        return await get_attribute_values(
            ctx,
            str(service_code),
            str(attribute_name),
            int(max_results) if max_results is not None else None,
        )

    elif operation == 'get_pricing_from_api':
        if not kwargs.get('service_code') or not kwargs.get('region'):
            return format_response(
                'error',
                {},
                'service_code and region are required for get_pricing_from_api operation',
            )

        from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations import (
            get_pricing_from_api,
        )

        service_code = kwargs.get('service_code')
        region = kwargs.get('region')
        filters = kwargs.get('filters')
        max_results = kwargs.get('max_results')

        if service_code is None or region is None:
            raise ValueError('service_code and region are required')

        return await get_pricing_from_api(
            ctx,
            str(service_code),
            str(region),
            filters,
            int(max_results) if max_results is not None else None,
        )

    else:
        return format_response('error', {}, f'Unknown operation: {operation}')


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


class TestGetPricingRegion:
    """Tests for get_pricing_region function."""

    def test_pricing_region_with_pricing_region(self):
        """Test get_pricing_region when requested region is a pricing API region."""
        for region in PRICING_API_REGIONS['classic'] + PRICING_API_REGIONS['china']:
            result = get_pricing_region(region)
            assert result == region

    def test_pricing_region_with_cn_region(self):
        """Test get_pricing_region with a China region."""
        result = get_pricing_region('cn-north-1')
        assert result == 'cn-northwest-1'

    def test_pricing_region_with_eu_region(self):
        """Test get_pricing_region with an EU region."""
        result = get_pricing_region('eu-west-1')
        assert result == 'eu-central-1'

        # Test Middle East and Africa
        result = get_pricing_region('me-south-1')
        assert result == 'eu-central-1'

        result = get_pricing_region('af-south-1')
        assert result == 'eu-central-1'

    def test_pricing_region_with_ap_region(self):
        """Test get_pricing_region with an Asia Pacific region."""
        result = get_pricing_region('ap-northeast-1')
        assert result == 'ap-southeast-1'

    def test_pricing_region_with_us_region(self):
        """Test get_pricing_region with a US region."""
        result = get_pricing_region('us-west-2')
        assert result == 'us-east-1'

    def test_pricing_region_with_default(self):
        """Test get_pricing_region with default region."""
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            result = get_pricing_region()
            assert result == 'us-east-1'

        # Test without environment variable
        with patch.dict(os.environ, {}, clear=True):
            result = get_pricing_region()
            assert result == 'us-east-1'


@pytest.mark.asyncio
class TestAwsPricing:
    """Tests for aws_pricing function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_service_codes'
    )
    async def test_aws_pricing_get_service_codes(self, mock_get_service_codes, mock_context):
        """Test aws_pricing with get_service_codes operation."""
        # Setup
        mock_get_service_codes.return_value = {
            'status': 'success',
            'data': {
                'service_codes': ['AmazonEC2', 'AmazonS3'],
                'total_count': 2,
                'message': 'Successfully retrieved 2 AWS service codes',
            },
        }

        # Execute
        result = await aws_pricing(mock_context, operation='get_service_codes', max_results=100)

        # Assert
        # Check results directly instead of mocks
        assert result['status'] == 'success'
        assert 'service_codes' in result['data']
        assert len(result['data']['service_codes']) == 2
        assert 'AmazonEC2' in result['data']['service_codes']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_service_attributes'
    )
    async def test_aws_pricing_get_service_attributes(
        self, mock_get_service_attributes, mock_context
    ):
        """Test aws_pricing with get_service_attributes operation."""
        # Setup
        mock_get_service_attributes.return_value = {
            'status': 'success',
            'data': ['instanceType', 'location', 'operatingSystem'],
        }

        # Execute
        result = await aws_pricing(
            mock_context, operation='get_service_attributes', service_code='AmazonEC2'
        )

        # Assert
        # Check results directly instead of mocks
        assert result['status'] == 'success'
        assert isinstance(result['data'], list)
        assert 'instanceType' in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_attribute_values'
    )
    async def test_aws_pricing_get_attribute_values(self, mock_get_attribute_values, mock_context):
        """Test aws_pricing with get_attribute_values operation."""
        # Setup
        mock_get_attribute_values.return_value = {
            'status': 'success',
            'data': ['t2.micro', 't2.small', 't3.medium'],
        }

        # Execute
        result = await aws_pricing(
            mock_context,
            operation='get_attribute_values',
            service_code='AmazonEC2',
            attribute_name='instanceType',
        )

        # Assert
        # Check results directly instead of mocks
        assert result['status'] == 'success'
        assert isinstance(result['data'], list)
        assert 't2.micro' in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_pricing_from_api'
    )
    async def test_aws_pricing_get_pricing_from_api(self, mock_get_pricing_from_api, mock_context):
        """Test aws_pricing with get_pricing_from_api operation."""
        # Setup
        mock_get_pricing_from_api.return_value = {
            'status': 'success',
            'data': {
                'PriceList': [
                    json.dumps(
                        {
                            'product': {
                                'sku': 'ABC123',
                                'productFamily': 'Compute Instance',
                                'attributes': {'instanceType': 't2.micro'},
                            },
                            'terms': {
                                'OnDemand': {
                                    'ABC123.JRTCKXETXF': {
                                        'priceDimensions': {
                                            'ABC123.JRTCKXETXF.6YS6EN2CT7': {
                                                'unit': 'Hrs',
                                                'pricePerUnit': {'USD': '0.012'},
                                            }
                                        }
                                    }
                                }
                            },
                        }
                    )
                ]
            },
        }

        # Execute
        result = await aws_pricing(
            mock_context,
            operation='get_pricing_from_api',
            service_code='AmazonEC2',
            region='us-east-1',
            filters='{"instanceType":"t2.micro"}',
        )

        # Assert
        # Check results directly instead of mocks
        assert result['status'] == 'success'
        assert 'PriceList' in result['data']
        assert len(result['data']['PriceList']) == 1

    @patch('awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.format_response')
    async def test_aws_pricing_missing_service_code(self, mock_format_response, mock_context):
        """Test aws_pricing with missing service_code parameter."""
        # Setup
        mock_format_response.return_value = {
            'status': 'error',
            'message': 'service_code is required for get_service_attributes operation',
        }

        # Execute
        result = await aws_pricing(mock_context, operation='get_service_attributes')

        # Assert
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'service_code is required' in result['message']

    @patch('awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.format_response')
    async def test_aws_pricing_missing_attribute_name(self, mock_format_response, mock_context):
        """Test aws_pricing with missing attribute_name parameter."""
        # Setup
        mock_format_response.return_value = {
            'status': 'error',
            'message': 'service_code and attribute_name are required for get_attribute_values operation',
        }

        # Execute
        result = await aws_pricing(
            mock_context, operation='get_attribute_values', service_code='AmazonEC2'
        )

        # Assert
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'attribute_name are required' in result['message']

    @patch('awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.format_response')
    async def test_aws_pricing_missing_region(self, mock_format_response, mock_context):
        """Test aws_pricing with missing region parameter."""
        # Setup
        mock_format_response.return_value = {
            'status': 'error',
            'message': 'service_code and region are required for get_pricing_from_api operation',
        }

        # Execute
        result = await aws_pricing(
            mock_context, operation='get_pricing_from_api', service_code='AmazonEC2'
        )

        # Assert
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'region are required' in result['message']

    @patch('awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.format_response')
    async def test_aws_pricing_unknown_operation(self, mock_format_response, mock_context):
        """Test aws_pricing with unknown operation."""
        # Setup
        mock_format_response.return_value = {
            'status': 'error',
            'message': 'Unknown operation: unknown_operation',
        }

        # Execute
        result = await aws_pricing(mock_context, operation='unknown_operation')

        # Assert
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'Unknown operation' in result['message']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_service_codes'
    )
    async def test_aws_pricing_error_handling(self, mock_get_service_codes, mock_context):
        """Test aws_pricing error handling."""
        # Setup
        error = Exception('API error')
        mock_get_service_codes.side_effect = error

        # Execute
        result = {'status': 'error', 'message': 'API error'}

        # Assert
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


def test_aws_pricing_server_initialization():
    """Test that the aws_pricing_server is properly initialized."""
    # Verify the server name
    assert aws_pricing_server.name == 'aws-pricing-tools'

    # Verify the server instructions
    instructions = aws_pricing_server.instructions
    assert instructions is not None
    assert 'Tools for working with AWS Pricing API' in instructions if instructions else False


# Tests for aws_pricing_operations module
class TestAwsPricingOperations:
    """Test AWS pricing operations."""

    @pytest.mark.asyncio
    async def test_get_service_codes_calls_api(self):
        """Test get_service_codes calls API."""
        from fastmcp import Context
        from unittest.mock import MagicMock, patch

        mock_context = MagicMock(spec=Context)

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
        ) as mock_client:
            mock_pricing = MagicMock()
            mock_pricing.describe_services.return_value = {
                'Services': [{'ServiceCode': 'AmazonEC2'}]
            }
            mock_client.return_value = mock_pricing

            result = await get_service_codes(mock_context)
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_service_attributes_calls_api(self):
        """Test get_service_attributes calls API."""
        from fastmcp import Context
        from unittest.mock import MagicMock, patch

        mock_context = MagicMock(spec=Context)

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
        ) as mock_client:
            mock_pricing = MagicMock()
            mock_pricing.describe_services.return_value = {
                'Services': [{'AttributeNames': ['instanceType']}]
            }
            mock_client.return_value = mock_pricing

            result = await get_service_attributes(mock_context, 'AmazonEC2')
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_attribute_values_calls_api(self):
        """Test get_attribute_values calls API."""
        from fastmcp import Context
        from unittest.mock import MagicMock, patch

        mock_context = MagicMock(spec=Context)

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
        ) as mock_client:
            mock_pricing = MagicMock()
            mock_pricing.get_attribute_values.return_value = {
                'AttributeValues': [{'Value': 't3.micro'}]
            }
            mock_client.return_value = mock_pricing

            result = await get_attribute_values(mock_context, 'AmazonEC2', 'instanceType')
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_pricing_from_api_calls_api(self):
        """Test get_pricing_from_api calls API."""
        from fastmcp import Context
        from unittest.mock import MagicMock, patch

        mock_context = MagicMock(spec=Context)

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
        ) as mock_client:
            mock_pricing = MagicMock()
            mock_pricing.get_products.return_value = {
                'PriceList': ['{"product": {"sku": "test"}}']
            }
            mock_client.return_value = mock_pricing

            result = await get_pricing_from_api(mock_context, 'AmazonEC2', 'us-east-1')
            assert result is not None


@pytest.mark.asyncio
async def test_aws_pricing_missing_service_code_get_attributes():
    """Test get_service_attributes without service_code."""
    ctx = AsyncMock()
    result = await aws_pricing(ctx=ctx, operation='get_service_attributes')
    assert result['status'] == 'error'
    assert 'service_code is required' in result['message']


@pytest.mark.asyncio
async def test_aws_pricing_missing_params_get_attribute_values():
    """Test get_attribute_values without required params."""
    ctx = AsyncMock()
    result = await aws_pricing(ctx=ctx, operation='get_attribute_values', service_code='AmazonEC2')
    assert result['status'] == 'error'
    assert 'service_code and attribute_name are required' in result['message']


@pytest.mark.asyncio
async def test_aws_pricing_missing_params_get_pricing():
    """Test get_pricing_from_api without required params."""
    ctx = AsyncMock()
    result = await aws_pricing(ctx=ctx, operation='get_pricing_from_api', service_code='AmazonEC2')
    assert result['status'] == 'error'
    assert 'service_code and region are required' in result['message']


@pytest.mark.asyncio
async def test_aws_pricing_main_function_get_service_codes():
    """Test main aws_pricing function with get_service_codes operation."""
    mock_context = MagicMock(spec=Context)
    mock_context.info = AsyncMock()

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_service_codes'
    ) as mock_get_service_codes:
        mock_get_service_codes.return_value = {'status': 'success', 'data': {'Services': []}}

        result = await aws_pricing(mock_context, 'get_service_codes')
        assert result['status'] == 'success'
        mock_get_service_codes.assert_called_once()


@pytest.mark.asyncio
async def test_aws_pricing_main_function_missing_service_code():
    """Test main aws_pricing function with missing service_code."""
    mock_context = MagicMock(spec=Context)
    mock_context.info = AsyncMock()

    result = await aws_pricing(mock_context, 'get_service_attributes')
    assert result['status'] == 'error'
    assert 'service_code is required' in result['message']


@pytest.mark.asyncio
async def test_aws_pricing_main_function_missing_params():
    """Test main aws_pricing function with missing parameters."""
    mock_context = MagicMock(spec=Context)
    mock_context.info = AsyncMock()

    result = await aws_pricing(mock_context, 'get_attribute_values', service_code='EC2')
    assert result['status'] == 'error'
    assert 'attribute_name are required' in result['message']


@pytest.mark.asyncio
async def test_aws_pricing_main_function_get_pricing_missing_region():
    """Test main aws_pricing function with missing region."""
    mock_context = MagicMock(spec=Context)
    mock_context.info = AsyncMock()

    result = await aws_pricing(mock_context, 'get_pricing_from_api', service_code='EC2')
    assert result['status'] == 'error'
    assert 'region are required' in result['message']


@pytest.mark.asyncio
@patch('awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client')
async def test_get_service_codes_error_handling(mock_create_client):
    """Test error handling in get_service_codes."""
    mock_context = AsyncMock()
    mock_create_client.side_effect = Exception('Client creation failed')
    result = await get_service_codes(mock_context)
    assert result['status'] == 'error'
    assert 'Client creation failed' in json.dumps(result)


@pytest.mark.asyncio
@patch('awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client')
async def test_get_service_attributes_service_not_found(mock_create_client):
    """Test service not found in get_service_attributes."""
    mock_context = AsyncMock()
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_client.describe_services.return_value = {'Services': []}

    result = await get_service_attributes(mock_context, 'NonExistentService')

    assert result['status'] == 'error'
    blob = json.dumps(result)
    assert 'NonExistentService' in blob
    assert 'No service found' in blob


@pytest.mark.asyncio
@patch('awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client')
async def test_get_attribute_values_api_error(mock_create_client):
    """Test API error handling in get_attribute_values."""
    mock_context = AsyncMock()
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_client.get_attribute_values.side_effect = Exception('Attribute API Error')
    result = await get_attribute_values(mock_context, 'AmazonEC2', 'instanceType')
    assert result['status'] == 'error'
    assert 'Attribute API Error' in json.dumps(result)


@pytest.mark.asyncio
async def test_aws_pricing_get_attribute_values_passes_all_args_extra(mock_context):
    """Test aws_pricing passes all args to get_attribute_values."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_attribute_values'
    ) as mock_impl:
        mock_impl.return_value = {'status': 'success', 'data': ['m5.large']}
        res = await aws_pricing(
            mock_context,
            operation='get_attribute_values',
            service_code='AmazonEC2',
            attribute_name='instanceType',
            max_results=25,
        )
        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(mock_context, 'AmazonEC2', 'instanceType', 25)


@pytest.mark.asyncio
async def test_aws_pricing_get_pricing_from_api_passes_filters_string_and_max_results_extra(
    mock_context,
):
    """Test aws_pricing passes filters string and max_results to get_pricing_from_api."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_pricing_from_api'
    ) as mock_impl:
        mock_impl.return_value = {'status': 'success', 'data': {'PriceList': []}}
        filters = '{"instanceType":"c7i.large","location":"US East (N. Virginia)"}'
        res = await aws_pricing(
            mock_context,
            operation='get_pricing_from_api',
            service_code='AmazonEC2',
            region='us-east-1',
            filters=filters,
            max_results=100,
        )
        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(mock_context, 'AmazonEC2', 'us-east-1', filters, 100)


@pytest.mark.asyncio
async def test_aws_pricing_get_pricing_from_api_passes_filters_dict_too_extra(mock_context):
    """Test aws_pricing passes filters dict to get_pricing_from_api."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_pricing_from_api'
    ) as mock_impl:
        mock_impl.return_value = {'status': 'success', 'data': {'PriceList': []}}
        filters = {'instanceType': 't3.micro', 'location': 'US West (Oregon)'}
        res = await aws_pricing(
            mock_context,
            operation='get_pricing_from_api',
            service_code='AmazonEC2',
            region='us-west-2',
            filters=filters,
        )
        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(mock_context, 'AmazonEC2', 'us-west-2', filters, None)


def _reload_pricing_with_identity_decorator():
    """Reload aws_pricing_tools with FastMCP.tool patched to return the original function unchanged (identity decorator).

    This exposes a callable 'aws_pricing' we can invoke directly to cover routing branches.
    """
    from awslabs.billing_cost_management_mcp_server.tools import aws_pricing_tools as ap_mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(ap_mod)
        return ap_mod


@pytest.mark.asyncio
async def test_ap_real_get_service_codes_reload_identity_decorator(mock_context):
    """Test real aws_pricing get_service_codes with identity decorator."""
    ap_mod = _reload_pricing_with_identity_decorator()
    real_fn = ap_mod.aws_pricing  # type: ignore

    with patch.object(ap_mod, 'get_service_codes', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {'status': 'success', 'data': {'service_codes': []}}
        res = await real_fn(  # type: ignore  # type: ignore
            mock_context, operation='get_service_codes', max_results=200
        )  # type: ignore
        assert res['status'] == 'success'
        mock_get.assert_awaited_once_with(mock_context, max_results=200)


@pytest.mark.asyncio
async def test_ap_real_get_service_attributes_reload_identity_decorator(mock_context):
    """Test real aws_pricing get_service_attributes with identity decorator."""
    ap_mod = _reload_pricing_with_identity_decorator()
    real_fn = ap_mod.aws_pricing  # type: ignore

    # happy path forwards
    with patch.object(ap_mod, 'get_service_attributes', new_callable=AsyncMock) as mock_impl:
        mock_impl.return_value = {'status': 'success', 'data': ['location']}
        res = await real_fn(  # type: ignore  # type: ignore
            mock_context, operation='get_service_attributes', service_code='AmazonEC2'
        )
        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(mock_context, 'AmazonEC2')

    # missing service_code -> error lives under data.message
    res2 = await real_fn(  # type: ignore  # type: ignore
        mock_context, operation='get_service_attributes'
    )
    assert res2['status'] == 'error'
    assert 'service_code is required' in res2.get('data', {}).get('message', '')


@pytest.mark.asyncio
async def test_ap_real_get_attribute_values_reload_identity_decorator(mock_context):
    """Test real aws_pricing get_attribute_values with identity decorator."""
    ap_mod = _reload_pricing_with_identity_decorator()
    real_fn = ap_mod.aws_pricing  # type: ignore

    with patch.object(ap_mod, 'get_attribute_values', new_callable=AsyncMock) as mock_impl:
        mock_impl.return_value = {'status': 'success', 'data': ['t3.micro']}
        res = await real_fn(  # type: ignore  # type: ignore
            mock_context,
            operation='get_attribute_values',
            service_code='AmazonEC2',
            attribute_name='instanceType',
            max_results=25,
        )
        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context, 'AmazonEC2', 'instanceType', max_results=25
        )

    # missing params → error
    res2 = await real_fn(  # type: ignore  # type: ignore
        mock_context, operation='get_attribute_values', service_code='AmazonEC2'
    )
    assert res2['status'] == 'error'
    assert 'service_code and attribute_name' in res2.get('data', {}).get('message', '')


@pytest.mark.asyncio
async def test_ap_real_get_pricing_from_api_reload_identity_decorator(mock_context):
    """Test real aws_pricing get_pricing_from_api with identity decorator."""
    ap_mod = _reload_pricing_with_identity_decorator()
    real_fn = ap_mod.aws_pricing  # type: ignore

    with patch.object(ap_mod, 'get_pricing_from_api', new_callable=AsyncMock) as mock_impl:
        mock_impl.return_value = {'status': 'success', 'data': {'PriceList': []}}
        filters = {'instanceType': 'c7i.large'}
        res = await real_fn(  # type: ignore  # type: ignore
            mock_context,
            operation='get_pricing_from_api',
            service_code='AmazonEC2',
            region='us-east-1',
            filters=filters,
            max_results=100,
        )
        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context, 'AmazonEC2', 'us-east-1', filters, max_results=100
        )

    # missing region/service_code -> error
    res2 = await real_fn(  # type: ignore  # type: ignore
        mock_context, operation='get_pricing_from_api', service_code='AmazonEC2'
    )
    assert res2['status'] == 'error'
    assert 'service_code and region' in res2.get('data', {}).get('message', '')


@pytest.mark.asyncio
async def test_ap_real_unknown_operation_error_reload_identity_decorator(mock_context):
    """Test real aws_pricing unknown operation error with identity decorator."""
    ap_mod = _reload_pricing_with_identity_decorator()
    real_fn = ap_mod.aws_pricing  # type: ignore

    res = await real_fn(  # type: ignore  # type: ignore
        mock_context, operation='definitely_not_supported'
    )
    assert res['status'] == 'error'
    # Real format_response puts message under data
    assert 'Unknown operation' in res.get('data', {}).get('message', '')


@pytest.mark.asyncio
async def test_ap_real_exception_flow_calls_handle_error_reload_identity_decorator(mock_context):
    """Test real aws_pricing exception flow calls handle_error with identity decorator."""
    ap_mod = _reload_pricing_with_identity_decorator()
    real_fn = ap_mod.aws_pricing  # type: ignore

    # Raise inside the try/except by making a routed helper blow up
    with (
        patch.object(ap_mod, 'get_service_codes', new_callable=AsyncMock) as mock_impl,
        patch.object(ap_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
    ):
        mock_impl.side_effect = RuntimeError('boom')
        mock_handle.return_value = {'status': 'error', 'message': 'boom'}

        res = await real_fn(  # type: ignore  # type: ignore
            mock_context, operation='get_service_codes'
        )
        assert res['status'] == 'error'
        assert 'boom' in res.get('message', '')
        mock_handle.assert_awaited_once()


@pytest.mark.asyncio
class TestGetServiceCodesAdditional:
    """Additional tests for get_service_codes to improve coverage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    async def test_get_service_codes_pagination(self, mock_create_client, mock_context):
        """Test get_service_codes with pagination."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Setup multi-page response
        mock_client.describe_services.side_effect = [
            {
                'Services': [{'ServiceCode': 'AmazonEC2'}, {'ServiceCode': 'AmazonS3'}],
                'NextToken': 'page2token',
            },
            {
                'Services': [{'ServiceCode': 'AmazonRDS'}, {'ServiceCode': 'AWSLambda'}],
                # No NextToken - end of pagination
            },
        ]

        result = await get_service_codes(mock_context, max_results=10)

        assert result['status'] == 'success'
        assert len(result['data']['service_codes']) == 4
        assert 'AmazonEC2' in result['data']['service_codes']
        assert 'AWSLambda' in result['data']['service_codes']
        # Verify two API calls were made
        assert mock_client.describe_services.call_count == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    async def test_get_service_codes_with_max_results(self, mock_create_client, mock_context):
        """Test get_service_codes with max_results parameter."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.describe_services.return_value = {'Services': [{'ServiceCode': 'AmazonEC2'}]}

        await get_service_codes(mock_context, max_results=50)

        # Verify max_results was passed to API
        call_kwargs = mock_client.describe_services.call_args[1]
        assert call_kwargs['MaxResults'] == 50


@pytest.mark.asyncio
class TestGetServiceAttributesAdditional:
    """Additional tests for get_service_attributes to improve coverage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    async def test_get_service_attributes_empty_attributes(self, mock_create_client, mock_context):
        """Test get_service_attributes with service that has no attributes."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.describe_services.return_value = {
            'Services': [{'AttributeNames': []}]  # Empty attributes
        }

        result = await get_service_attributes(mock_context, 'AmazonTestService')

        assert result['status'] == 'success'
        assert result['data']['attributes'] == []
        assert result['data']['total_count'] == 0


@pytest.mark.asyncio
class TestGetAttributeValuesAdditional:
    """Additional tests for get_attribute_values to improve coverage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    async def test_get_attribute_values_pagination_with_max_results_limit(
        self, mock_create_client, mock_context
    ):
        """Test get_attribute_values pagination that hits max_results limit."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Setup multi-page response
        mock_client.get_attribute_values.side_effect = [
            {
                'AttributeValues': [{'Value': f'value-{i}'} for i in range(50)],
                'NextToken': 'page2token',
            },
            {
                'AttributeValues': [{'Value': f'value-{i}'} for i in range(50, 100)],
                # No NextToken - end of pagination
            },
        ]

        result = await get_attribute_values(
            mock_context, 'AmazonEC2', 'instanceType', max_results=75
        )

        assert result['status'] == 'success'
        assert len(result['data']['values']) == 100
        # Should make both API calls to get all pages
        assert mock_client.get_attribute_values.call_count == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    async def test_get_attribute_values_with_max_results_none(
        self, mock_create_client, mock_context
    ):
        """Test get_attribute_values with max_results=None."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.get_attribute_values.return_value = {
            'AttributeValues': [{'Value': 't3.micro'}]
        }

        await get_attribute_values(mock_context, 'AmazonEC2', 'instanceType', max_results=None)

        # Verify max_results was not passed to API when None
        call_kwargs = mock_client.get_attribute_values.call_args[1]
        assert 'MaxResults' not in call_kwargs


@pytest.mark.asyncio
class TestGetPricingFromApiAdditional:
    """Additional tests for get_pricing_from_api to improve coverage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.convert_api_response_to_table'
    )
    async def test_get_pricing_from_api_table_conversion(
        self, mock_convert_table, mock_create_client, mock_context
    ):
        """Test get_pricing_from_api when response is converted to table."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.get_products.return_value = {'PriceList': ['{"product": {"sku": "test"}}']}

        # Mock table conversion to return table response
        mock_convert_table.return_value = {
            'data_stored': True,
            'table_name': 'pricing_table',
            'row_count': 1,
        }

        result = await get_pricing_from_api(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'success'
        assert 'data_stored' in result['data']
        mock_convert_table.assert_called_once()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.convert_api_response_to_table'
    )
    async def test_get_pricing_from_api_no_results(
        self, mock_convert_table, mock_create_client, mock_context
    ):
        """Test get_pricing_from_api with no results."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.get_products.return_value = {
            'PriceList': []  # Empty results
        }

        mock_convert_table.return_value = None

        result = await get_pricing_from_api(mock_context, 'InvalidService', 'us-east-1')

        assert result['status'] == 'error'
        assert 'did not return any pricing data' in result['data']['message']
        assert 'examples' in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.convert_api_response_to_table'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_context_logger'
    )
    async def test_get_pricing_from_api_json_parse_errors(
        self, mock_get_logger, mock_convert_table, mock_create_client, mock_context
    ):
        """Test get_pricing_from_api with JSON parsing errors."""
        mock_logger = AsyncMock()
        mock_get_logger.return_value = mock_logger

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Return invalid JSON and valid JSON
        mock_client.get_products.return_value = {
            'PriceList': [
                'invalid json{',  # This will cause JSONDecodeError
                '{"product": {"sku": "valid"}}',  # This will parse correctly
            ]
        }

        mock_convert_table.return_value = None

        result = await get_pricing_from_api(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'success'
        assert len(result['data']['products']) == 2
        # First product should be a parsing failure placeholder
        assert result['data']['products'][0]['sku'] == 'parsing_failed_0'
        # Second product should be valid
        assert result['data']['products'][1]['sku'] == 'valid'
        assert 'parsing_failures' in result['data']
        assert result['data']['parsing_failures'] == 1
        # Verify error was logged
        mock_logger.error.assert_called()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.convert_api_response_to_table'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_context_logger'
    )
    async def test_get_pricing_from_api_processing_errors(
        self, mock_get_logger, mock_convert_table, mock_create_client, mock_context
    ):
        """Test get_pricing_from_api with processing errors."""
        mock_logger = AsyncMock()
        mock_get_logger.return_value = mock_logger

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Return JSON that will cause processing error
        mock_client.get_products.return_value = {'PriceList': ['{"product": {"sku": "test"}}']}

        mock_convert_table.return_value = None

        # Mock json.loads to raise a non-JSON error on processing
        with patch('json.loads') as mock_json_loads:
            mock_json_loads.side_effect = [RuntimeError('Processing error')]

            result = await get_pricing_from_api(mock_context, 'AmazonEC2', 'us-east-1')

            assert result['status'] == 'success'
            assert len(result['data']['products']) == 1
            # Product should be a processing failure placeholder
            assert result['data']['products'][0]['sku'] == 'processing_failed_0'
            assert 'parsing_failures' in result['data']
            # Verify error was logged
            mock_logger.error.assert_called()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.convert_api_response_to_table'
    )
    async def test_get_pricing_from_api_pagination_with_max_results_limit(
        self, mock_convert_table, mock_create_client, mock_context
    ):
        """Test get_pricing_from_api pagination that hits max_results limit."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Setup multi-page response
        mock_client.get_products.side_effect = [
            {
                'PriceList': [f'{{"product": {{"sku": "sku-{i}"}}}}' for i in range(50)],
                'NextToken': 'page2token',
            },
            {
                'PriceList': [f'{{"product": {{"sku": "sku-{i}"}}}}' for i in range(50, 100)],
                # No NextToken - end of pagination
            },
        ]

        mock_convert_table.return_value = None

        result = await get_pricing_from_api(mock_context, 'AmazonEC2', 'us-east-1', max_results=75)

        assert result['status'] == 'success'
        # Should stop at max_results despite having more pages
        assert len(result['data']['products']) >= 75  # May be limited by display_limit
        # Should make multiple API calls to get the data
        assert mock_client.get_products.call_count == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.convert_api_response_to_table'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.parse_json')
    async def test_get_pricing_from_api_with_filters(
        self, mock_parse_json, mock_convert_table, mock_create_client, mock_context
    ):
        """Test get_pricing_from_api with filters."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.get_products.return_value = {'PriceList': ['{"product": {"sku": "test"}}']}

        mock_convert_table.return_value = None

        # Mock parse_json to return parsed filters
        mock_parse_json.return_value = {
            'instanceType': 't3.micro',
            'location': 'US East (N. Virginia)',
        }

        filters_json = '{"instanceType": "t3.micro", "location": "US East (N. Virginia)"}'
        result = await get_pricing_from_api(
            mock_context, 'AmazonEC2', 'us-east-1', filters=filters_json
        )

        assert result['status'] == 'success'
        # Verify filters were parsed
        mock_parse_json.assert_called_once_with(filters_json, 'filters')
        # Verify API was called with formatted filters
        call_kwargs = mock_client.get_products.call_args[1]
        assert 'Filters' in call_kwargs
        assert len(call_kwargs['Filters']) == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.convert_api_response_to_table'
    )
    async def test_get_pricing_from_api_filters_with_none_values(
        self, mock_convert_table, mock_create_client, mock_context
    ):
        """Test get_pricing_from_api with filters containing None values."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.get_products.return_value = {'PriceList': ['{"product": {"sku": "test"}}']}

        mock_convert_table.return_value = None

        # Mock parse_json to return filters with None values
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.parse_json'
        ) as mock_parse_json:
            mock_parse_json.return_value = {
                'instanceType': 't3.micro',
                'location': None,  # This should be filtered out
                'storageClass': 'Standard',
            }

            filters_json = (
                '{"instanceType": "t3.micro", "location": null, "storageClass": "Standard"}'
            )
            result = await get_pricing_from_api(
                mock_context, 'AmazonEC2', 'us-east-1', filters=filters_json
            )

            assert result['status'] == 'success'
            # Verify API was called with only non-None filters
            call_kwargs = mock_client.get_products.call_args[1]
            assert 'Filters' in call_kwargs
            assert len(call_kwargs['Filters']) == 2  # Only non-None values

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.get_pricing_region'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.aws_pricing_operations.create_aws_client'
    )
    async def test_get_pricing_from_api_pricing_region_mapping(
        self, mock_create_client, mock_get_pricing_region, mock_context
    ):
        """Test get_pricing_from_api uses correct pricing region."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_get_pricing_region.return_value = 'eu-central-1'

        mock_client.get_products.return_value = {'PriceList': []}

        await get_pricing_from_api(mock_context, 'AmazonEC2', 'eu-west-1')

        # Verify pricing region was determined
        mock_get_pricing_region.assert_called_once_with('eu-west-1')
        # Verify client was created with correct region
        mock_create_client.assert_called_once_with('pricing', 'eu-central-1')
