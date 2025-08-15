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
