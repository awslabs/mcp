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

"""Tests for the server module of the aws-pricing-mcp-server."""

import pytest
from awslabs.aws_pricing_mcp_server.models import PricingFilter
from awslabs.aws_pricing_mcp_server.pricing_transformer import (
    _is_free_product,
)
from awslabs.aws_pricing_mcp_server.server import (
    analyze_cdk_project_wrapper,
    generate_cost_report_wrapper,
    get_bedrock_patterns,
    get_price_list_urls,
    get_pricing,
    get_pricing_attribute_values,
    get_pricing_service_attributes,
    get_pricing_service_codes,
)
from unittest.mock import patch


class TestAnalyzeCdkProject:
    """Tests for the analyze_cdk_project_wrapper function."""

    @pytest.mark.asyncio
    async def test_analyze_valid_project(self, mock_context, sample_cdk_project):
        """Test analyzing a valid CDK project."""
        result = await analyze_cdk_project_wrapper(mock_context, sample_cdk_project)

        assert result is not None
        assert result['status'] == 'success'
        assert 'services' in result

        # Check for expected services
        services = {service['name'] for service in result['services']}
        assert 'lambda' in services
        assert 'dynamodb' in services
        assert 's3' in services
        assert 'iam' in services

    @pytest.mark.asyncio
    async def test_analyze_invalid_project(self, mock_context, temp_output_dir):
        """Test analyzing an invalid/empty project directory."""
        result = await analyze_cdk_project_wrapper(mock_context, temp_output_dir)

        assert result is not None
        assert result['status'] == 'success'
        assert 'services' in result
        assert (
            len(result['services']) == 0
        )  # Empty project still returns success with empty services

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_project(self, mock_context):
        """Test analyzing a nonexistent project directory."""
        result = await analyze_cdk_project_wrapper(mock_context, '/nonexistent/path')

        assert result is not None
        assert 'services' in result
        assert len(result['services']) == 0  # Nonexistent path returns success with empty services


class TestGetPricing:
    """Tests for the get_pricing function."""

    @pytest.mark.asyncio
    async def test_get_valid_pricing(self, mock_boto3, mock_context):
        """Test getting pricing for a valid service."""
        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'AWSLambda', 'us-west-2')

        assert result is not None
        assert result['status'] == 'success'
        assert result['service_name'] == 'AWSLambda'
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0
        assert 'message' in result
        assert 'AWSLambda' in result['message']
        assert 'us-west-2' in result['message']

    @pytest.mark.asyncio
    async def test_get_pricing_with_filters(self, mock_boto3, mock_context):
        """Test getting pricing with filters."""
        # Create filters using the Pydantic models
        filters = [
            PricingFilter(Field='instanceType', Value='t3.medium'),
            PricingFilter(Field='location', Value='US East (N. Virginia)', Type='EQUALS'),
        ]

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'AmazonEC2', 'us-east-1', filters)

        assert result is not None
        assert result['status'] == 'success'
        assert result['service_name'] == 'AmazonEC2'
        assert isinstance(result['data'], list)

        # Verify that the mocked pricing client was called with correct filters
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.assert_called_once()
        call_args = pricing_client.get_products.call_args[1]
        assert 'Filters' in call_args
        assert len(call_args['Filters']) == 3  # region + 2 custom filters

        # Check that our custom filters are included
        filter_fields = [f['Field'] for f in call_args['Filters']]
        assert 'instanceType' in filter_fields
        assert 'location' in filter_fields
        assert 'regionCode' in filter_fields  # Always added by the function

    @pytest.mark.asyncio
    async def test_pricing_filter_model_validation(self):
        """Test that PricingFilter model validates correctly."""
        # Test valid filter creation
        valid_filter = PricingFilter(Field='instanceType', Value='t3.medium')
        assert valid_filter.field == 'instanceType'
        assert valid_filter.value == 't3.medium'
        assert valid_filter.type == 'EQUALS'

        # Test serialization with aliases
        filter_dict = valid_filter.model_dump(by_alias=True)
        assert 'Field' in filter_dict
        assert 'Value' in filter_dict
        assert 'Type' in filter_dict
        assert filter_dict['Field'] == 'instanceType'
        assert filter_dict['Value'] == 't3.medium'
        assert filter_dict['Type'] == 'EQUALS'

    @pytest.mark.asyncio
    async def test_new_filter_types_validation(self):
        """Test that new filter types work correctly."""
        # Test ANY_OF filter type
        any_of_filter = PricingFilter(
            Field='instanceType', Value=['t3.medium', 'm5.large'], Type='ANY_OF'
        )
        assert any_of_filter.type == 'ANY_OF'
        assert any_of_filter.value == ['t3.medium', 'm5.large']

        # Test CONTAINS filter type
        contains_filter = PricingFilter(Field='instanceType', Value='m5', Type='CONTAINS')
        assert contains_filter.type == 'CONTAINS'
        assert contains_filter.value == 'm5'

        # Test NONE_OF filter type
        none_of_filter = PricingFilter(Field='instanceType', Value=['t2', 'm4'], Type='NONE_OF')
        assert none_of_filter.type == 'NONE_OF'
        assert none_of_filter.value == ['t2', 'm4']

        # Test serialization converts ANY_OF and NONE_OF to comma-separated strings
        any_of_dict = any_of_filter.model_dump(by_alias=True)
        assert any_of_dict['Type'] == 'ANY_OF'
        assert any_of_dict['Value'] == 't3.medium,m5.large'  # Should be comma-separated string

        contains_dict = contains_filter.model_dump(by_alias=True)
        assert contains_dict['Type'] == 'CONTAINS'
        assert contains_dict['Value'] == 'm5'  # Should remain as string

        none_of_dict = none_of_filter.model_dump(by_alias=True)
        assert none_of_dict['Type'] == 'NONE_OF'
        assert none_of_dict['Value'] == 't2,m4'  # Should be comma-separated string

    @pytest.mark.asyncio
    async def test_filter_serialization_comma_separated(self):
        """Test that ANY_OF and NONE_OF filters serialize values as comma-separated strings."""
        # Test ANY_OF filter serialization
        any_of_filter = PricingFilter(
            Field='instanceType', Value=['t3.medium', 'm5.large'], Type='ANY_OF'
        )
        serialized = any_of_filter.model_dump(by_alias=True)
        assert serialized['Value'] == 't3.medium,m5.large'  # Should be comma-separated string
        assert serialized['Type'] == 'ANY_OF'

        # Test NONE_OF filter serialization
        none_of_filter = PricingFilter(
            Field='instanceType', Value=['t2.micro', 'm4.large'], Type='NONE_OF'
        )
        serialized = none_of_filter.model_dump(by_alias=True)
        assert serialized['Value'] == 't2.micro,m4.large'  # Should be comma-separated string
        assert serialized['Type'] == 'NONE_OF'

        # Test EQUALS filter serialization (should not change)
        equals_filter = PricingFilter(Field='instanceType', Value='m5.large', Type='EQUALS')
        serialized = equals_filter.model_dump(by_alias=True)
        assert serialized['Value'] == 'm5.large'  # Should remain a string
        assert serialized['Type'] == 'EQUALS'

        # Test CONTAINS filter serialization (should not change)
        contains_filter = PricingFilter(Field='instanceType', Value='m5', Type='CONTAINS')
        serialized = contains_filter.model_dump(by_alias=True)
        assert serialized['Value'] == 'm5'  # Should remain a string
        assert serialized['Type'] == 'CONTAINS'

    @pytest.mark.asyncio
    async def test_multi_region_pricing(self, mock_boto3, mock_context):
        """Test getting pricing for multiple regions using ANY_OF filter."""
        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(
                mock_context, 'AmazonEC2', ['us-east-1', 'us-west-2', 'eu-west-1']
            )

        assert result is not None
        assert result['status'] == 'success'
        assert result['service_name'] == 'AmazonEC2'

        # Verify that the mocked pricing client was called with correct multi-region filter
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.assert_called_once()
        call_args = pricing_client.get_products.call_args[1]
        assert 'Filters' in call_args

        # Should have exactly one region filter (automatically added)
        region_filters = [f for f in call_args['Filters'] if f['Field'] == 'regionCode']
        assert len(region_filters) == 1

        # The region filter should use ANY_OF with comma-separated values
        region_filter = region_filters[0]
        assert region_filter['Type'] == 'ANY_OF'
        assert region_filter['Value'] == 'us-east-1,us-west-2,eu-west-1'

    @pytest.mark.asyncio
    async def test_single_region_backward_compatibility(self, mock_boto3, mock_context):
        """Test that single region strings still work with TERM_MATCH for backward compatibility."""
        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'AmazonEC2', 'us-east-1')

        assert result is not None
        assert result['status'] == 'success'
        assert result['service_name'] == 'AmazonEC2'

        # Verify that the mocked pricing client was called with TERM_MATCH for single region
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.assert_called_once()
        call_args = pricing_client.get_products.call_args[1]
        assert 'Filters' in call_args

        # Should have exactly one region filter
        region_filters = [f for f in call_args['Filters'] if f['Field'] == 'regionCode']
        assert len(region_filters) == 1

        # The region filter should use TERM_MATCH for backward compatibility
        region_filter = region_filters[0]
        assert region_filter['Type'] == 'TERM_MATCH'
        assert region_filter['Value'] == 'us-east-1'

    @pytest.mark.asyncio
    async def test_get_pricing_response_structure_validation(self, mock_boto3, mock_context):
        """Test that the response structure is properly validated."""
        # Mock a more realistic pricing response
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = {
            'PriceList': [
                '{"product":{"sku":"ABC123","productFamily":"Compute","attributes":{"instanceType":"t3.medium"}},"terms":{"OnDemand":{"ABC123.TERM1":{"priceDimensions":{"ABC123.TERM1.DIM1":{"unit":"Hrs","pricePerUnit":{"USD":"0.0416"}}}}}},"serviceCode":"AmazonEC2"}'
            ]
        }

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'AmazonEC2', 'us-east-1')

        # Validate top-level response structure
        assert result['status'] == 'success'
        assert result['service_name'] == 'AmazonEC2'
        assert isinstance(result['data'], list)
        assert len(result['data']) == 1
        assert isinstance(result['message'], str)

        # Validate the pricing data structure (data is already parsed from JSON)
        pricing_item = result['data'][0]

        # Validate required fields in pricing item
        assert 'product' in pricing_item
        assert 'terms' in pricing_item
        assert 'sku' in pricing_item['product']
        assert 'attributes' in pricing_item['product']
        assert 'OnDemand' in pricing_item['terms']

        # Validate pricing structure
        product = pricing_item['product']
        assert product['sku'] == 'ABC123'
        assert 'instanceType' in product['attributes']
        assert product['attributes']['instanceType'] == 't3.medium'

    @pytest.mark.asyncio
    async def test_get_pricing_empty_results(self, mock_boto3, mock_context):
        """Test handling of empty pricing results."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = {'PriceList': []}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'InvalidService', 'us-west-2')

        assert result is not None
        assert result['status'] == 'error'
        assert result['error_type'] == 'empty_results'
        assert 'InvalidService' in result['message']
        assert 'No results found for given filters' in result['message']
        assert result['service_code'] == 'InvalidService'
        assert result['region'] == 'us-west-2'
        assert 'examples' in result
        assert 'Example service codes' in result['examples']
        assert 'Example regions' in result['examples']
        assert 'suggestion' in result
        assert (
            'Verify that the service code is valid. Use get_service_codes() to get valid service codes'
            in result['suggestion']
        )
        assert (
            'Validate region and filter values using get_pricing_attribute_values()'
            in result['suggestion']
        )
        assert 'Test with fewer filters' in result['suggestion']
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_api_error(self, mock_boto3, mock_context):
        """Test handling of API errors."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.side_effect = Exception('API Error')

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'AWSLambda', 'us-west-2')

        assert result is not None
        assert result['status'] == 'error'
        assert result['error_type'] == 'api_error'
        assert 'API Error' in result['message']
        assert result['service_code'] == 'AWSLambda'
        assert result['region'] == 'us-west-2'
        assert 'suggestion' in result
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_data_processing_error(self, mock_boto3, mock_context):
        """Test handling of data processing errors in transform_pricing_data."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = {'PriceList': ['invalid json']}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'AWSLambda', 'us-west-2')

        assert result is not None
        assert result['status'] == 'error'
        assert result['error_type'] == 'data_processing_error'
        assert 'Failed to process pricing data' in result['message']
        assert result['service_code'] == 'AWSLambda'
        assert result['region'] == 'us-west-2'
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_client_creation_error(self, mock_context):
        """Test handling of client creation errors."""
        with patch(
            'awslabs.aws_pricing_mcp_server.server.create_pricing_client',
            side_effect=Exception('Client creation failed'),
        ):
            result = await get_pricing(mock_context, 'AWSLambda', 'us-west-2')

        assert result is not None
        assert result['status'] == 'error'
        assert result['error_type'] == 'client_creation_failed'
        assert 'Failed to create AWS Pricing client' in result['message']
        assert 'Client creation failed' in result['message']
        assert result['service_code'] == 'AWSLambda'
        assert result['region'] == 'us-west-2'
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_result_threshold_exceeded(self, mock_boto3, mock_context):
        """Test that the tool returns an error when result character count exceeds the threshold."""
        # Create a mock response with large JSON records that exceed character threshold
        # Each record is about 500 characters, so 100 records = ~50,000 characters (exceeds 40,000 default)
        large_price_list = []
        for i in range(100):
            record = f'{{"sku":"SKU{i:03d}","product":{{"productFamily":"Compute Instance","attributes":{{"instanceType":"m5.large","location":"US East (N. Virginia)","tenancy":"Shared","operatingSystem":"Linux"}}}},"terms":{{"OnDemand":{{"SKU{i:03d}.JRTCKXETXF":{{"priceDimensions":{{"SKU{i:03d}.JRTCKXETXF.6YS6EN2CT7":{{"unit":"Hrs","pricePerUnit":{{"USD":"0.096"}}}}}}}}}}}}}}'
            large_price_list.append(record)

        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = {'PriceList': large_price_list}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(
                mock_context, 'AmazonEC2', 'us-east-1', max_allowed_characters=10000
            )

        assert result['status'] == 'error'
        assert result['error_type'] == 'result_too_large'
        assert 'exceeding the limit of 10,000' in result['message']
        assert 'output_options={"pricing_terms": ["OnDemand"]}' in result['message']
        assert 'significantly reduce response size' in result['suggestion']
        assert result['total_count'] == 100
        assert result['max_allowed_characters'] == 10000
        assert len(result['sample_records']) == 3  # First 3 records as context
        assert 'Add more specific filters' in result['suggestion']
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_unlimited_results(self, mock_boto3, mock_context):
        """Test that max_allowed_characters=-1 allows unlimited results."""
        # Create a mock response with large records that would normally exceed character limit
        large_price_list = []
        for i in range(100):
            record = f'{{"sku":"SKU{i:03d}","product":{{"productFamily":"Compute Instance","attributes":{{"instanceType":"m5.large","location":"US East (N. Virginia)","tenancy":"Shared","operatingSystem":"Linux"}}}},"terms":{{"OnDemand":{{"SKU{i:03d}.JRTCKXETXF":{{"priceDimensions":{{"SKU{i:03d}.JRTCKXETXF.6YS6EN2CT7":{{"unit":"Hrs","pricePerUnit":{{"USD":"0.096"}}}}}}}}}}}}}}'
            large_price_list.append(record)

        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = {'PriceList': large_price_list}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(
                mock_context, 'AmazonEC2', 'us-east-1', max_allowed_characters=-1
            )

        assert result['status'] == 'success'
        assert len(result['data']) == 100  # All results should be returned
        assert 'Retrieved pricing for AmazonEC2' in result['message']
        mock_context.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_custom_threshold(self, mock_context, mock_boto3):
        """Test that custom max_allowed_characters threshold works correctly."""
        # Create a mock response with small records that fit within lower thresholds
        small_price_list = [f'{{"sku":"SKU{i}","product":{{}}}}' for i in range(10)]

        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = {'PriceList': small_price_list}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            # Should succeed with threshold of 1000 characters (small records should fit)
            result = await get_pricing(
                mock_context, 'AmazonEC2', 'us-east-1', None, max_allowed_characters=1000
            )
            assert result['status'] == 'success'
            assert len(result['data']) == 10

            # Should fail with threshold of 100 characters (records are too large)
            result = await get_pricing(
                mock_context, 'AmazonEC2', 'us-east-1', None, max_allowed_characters=100
            )
            assert result['status'] == 'error'
            assert result['error_type'] == 'result_too_large'
            assert result['total_count'] == 10
            assert result['max_allowed_characters'] == 100

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'max_results,next_token,expected_max_results,expect_next_token',
        [
            (None, None, 100, False),  # Default values
            (25, None, 25, False),  # Custom max_results
            (None, 'test-token-123', 100, True),  # Custom next_token
            (50, 'input-token-abc', 50, True),  # Both parameters
        ],
    )
    async def test_get_pricing_pagination_parameters(
        self,
        mock_context,
        mock_boto3,
        max_results,
        next_token,
        expected_max_results,
        expect_next_token,
    ):
        """Test various pagination parameter combinations."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = {'PriceList': ['{"sku":"ABC123"}']}

        kwargs = {'service_code': 'AmazonEC2', 'region': 'us-east-1'}
        if max_results is not None:
            kwargs['max_results'] = max_results
        if next_token is not None:
            kwargs['next_token'] = next_token

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, **kwargs)

        assert result['status'] == 'success'

        # Verify pagination parameters were passed correctly
        pricing_client.get_products.assert_called_once()
        call_kwargs = pricing_client.get_products.call_args[1]
        assert call_kwargs['MaxResults'] == expected_max_results

        if expect_next_token:
            assert call_kwargs['NextToken'] == next_token
        else:
            assert 'NextToken' not in call_kwargs

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'api_response,expected_next_token_in_result',
        [
            (
                {'PriceList': ['{"sku":"ABC123"}'], 'NextToken': 'next-page-token-456'},
                'next-page-token-456',
            ),  # API returns NextToken
            ({'PriceList': ['{"sku":"ABC123"}']}, None),  # API doesn't return NextToken
            (
                {
                    'PriceList': ['{"sku":"ABC123"}', '{"sku":"DEF456"}'],
                    'NextToken': 'final-token-789',
                },
                'final-token-789',
            ),  # Multiple records with NextToken
        ],
    )
    async def test_get_pricing_response_next_token(
        self, mock_context, mock_boto3, api_response, expected_next_token_in_result
    ):
        """Test next_token handling in response based on API response."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.return_value = api_response

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'success'

        if expected_next_token_in_result:
            assert 'next_token' in result
            assert result['next_token'] == expected_next_token_in_result
        else:
            assert 'next_token' not in result


class TestGetBedrockPatterns:
    """Tests for the get_bedrock_patterns function."""

    @pytest.mark.asyncio
    async def test_get_patterns(self, mock_context):
        """Test getting Bedrock architecture patterns."""
        result = await get_bedrock_patterns(mock_context)

        assert result is not None
        assert isinstance(result, str)
        assert 'Bedrock' in result
        assert 'Knowledge Base' in result


class TestGenerateCostReport:
    """Tests for the generate_cost_report_wrapper function."""

    @pytest.mark.asyncio
    async def test_generate_markdown_report(self, mock_context, sample_pricing_data_web):
        """Test generating a markdown cost report."""
        result = await generate_cost_report_wrapper(
            mock_context,
            pricing_data=sample_pricing_data_web,
            service_name='AWS Lambda',
            related_services=['DynamoDB'],
            pricing_model='ON DEMAND',
            assumptions=['Standard configuration'],
            exclusions=['Custom configurations'],
            format='markdown',
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_csv_report(self, mock_context, sample_pricing_data_web):
        """Test generating a CSV cost report."""
        result = await generate_cost_report_wrapper(
            mock_context,
            pricing_data=sample_pricing_data_web,
            service_name='AWS Lambda',
            format='csv',
            pricing_model='ON DEMAND',
            related_services=None,
            assumptions=None,
            exclusions=None,
            output_file=None,
            detailed_cost_data=None,
            recommendations=None,
        )

        assert result is not None
        assert isinstance(result, str)
        assert ',' in result  # Verify it's CSV format

        # Verify basic structure
        lines = result.split('\n')
        assert len(lines) > 1  # Has header and data

    @pytest.mark.asyncio
    async def test_generate_report_with_detailed_data(
        self, mock_context, sample_pricing_data_web, temp_output_dir
    ):
        """Test generating a report with detailed cost data."""
        detailed_cost_data = {
            'services': {
                'AWS Lambda': {
                    'usage': '1M requests per month',
                    'estimated_cost': '$20.00',
                    'unit_pricing': {
                        'requests': '$0.20 per 1M requests',
                        'compute': '$0.0000166667 per GB-second',
                    },
                }
            }
        }

        result = await generate_cost_report_wrapper(
            mock_context,
            pricing_data=sample_pricing_data_web,
            service_name='AWS Lambda',
            detailed_cost_data=detailed_cost_data,
            output_file=f'{temp_output_dir}/report.md',
            pricing_model='ON DEMAND',
            related_services=None,
            assumptions=None,
            exclusions=None,
            recommendations=None,
        )

        assert result is not None
        assert isinstance(result, str)
        assert 'AWS Lambda' in result
        assert '$20.00' in result
        assert '1M requests per month' in result

    @pytest.mark.asyncio
    async def test_generate_report_error_handling(self, mock_context):
        """Test error handling in report generation."""
        result = await generate_cost_report_wrapper(
            mock_context,
            pricing_data={'status': 'error'},
            service_name='Invalid Service',
            pricing_model='ON DEMAND',
            related_services=None,
            assumptions=None,
            exclusions=None,
            output_file=None,
            detailed_cost_data=None,
            recommendations=None,
        )

        assert '# Invalid Service Cost Analysis' in result


class TestGetPricingServiceAttributes:
    """Tests for the get_pricing_service_attributes function."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'service_code,attributes,expected',
        [
            (
                'AmazonEC2',
                ['instanceType', 'location', 'tenancy', 'operatingSystem'],
                ['instanceType', 'location', 'operatingSystem', 'tenancy'],
            ),
            (
                'AmazonRDS',
                ['engineCode', 'instanceType', 'location', 'databaseEngine'],
                ['databaseEngine', 'engineCode', 'instanceType', 'location'],
            ),
        ],
    )
    async def test_get_pricing_service_attributes(
        self, mock_context, mock_boto3, service_code, attributes, expected
    ):
        """Test getting service attributes for various AWS services."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.describe_services.return_value = {
            'Services': [{'ServiceCode': service_code, 'AttributeNames': attributes}]
        }

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_service_attributes(mock_context, service_code)

            assert result == expected
            pricing_client.describe_services.assert_called_once_with(ServiceCode=service_code)
            mock_context.info.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_service_attributes_service_not_found(
        self, mock_context, mock_boto3
    ):
        """Test getting service attributes for invalid service returns proper error response."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.describe_services.return_value = {'Services': []}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_service_attributes(mock_context, 'InvalidService')

            # Verify error response structure
            assert isinstance(result, dict)
            assert result['status'] == 'error'
            assert result['error_type'] == 'service_not_found'
            assert 'InvalidService' in result['message']
            assert result['service_code'] == 'InvalidService'
            assert 'get_service_codes()' in result['suggestion']
            assert 'examples' in result
            assert 'AmazonES' in result['examples']['OpenSearch']
            mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_service_attributes_api_error(self, mock_context, mock_boto3):
        """Test handling of API errors when getting service attributes."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.describe_services.side_effect = Exception('API Error')

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_service_attributes(mock_context, 'AmazonEC2')

            # Verify error response structure
            assert isinstance(result, dict)
            assert result['status'] == 'error'
            assert result['error_type'] == 'api_error'
            assert 'API Error' in result['message']
            assert result['service_code'] == 'AmazonEC2'
            assert 'suggestion' in result
            mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_service_attributes_empty_attributes(self, mock_context, mock_boto3):
        """Test handling when service exists but has no attributes."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.describe_services.return_value = {
            'Services': [{'ServiceCode': 'TestService', 'AttributeNames': []}]
        }

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_service_attributes(mock_context, 'TestService')

            # Verify error response structure
            assert isinstance(result, dict)
            assert result['status'] == 'error'
            assert result['error_type'] == 'empty_results'
            assert 'TestService' in result['message']
            assert 'no filterable attributes available' in result['message']
            assert result['service_code'] == 'TestService'
            assert 'Try using get_pricing() without filters' in result['suggestion']
            mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_service_attributes_client_creation_error(self, mock_context):
        """Test handling of client creation errors."""
        with patch(
            'awslabs.aws_pricing_mcp_server.server.create_pricing_client',
            side_effect=Exception('Client creation failed'),
        ):
            result = await get_pricing_service_attributes(mock_context, 'AmazonEC2')

        assert isinstance(result, dict)
        assert result['status'] == 'error'
        assert result['error_type'] == 'client_creation_failed'
        assert 'Failed to create AWS Pricing client' in result['message']
        assert 'Client creation failed' in result['message']
        assert result['service_code'] == 'AmazonEC2'
        mock_context.error.assert_called()


class TestGetPricingAttributeValues:
    """Tests for the get_pricing_attribute_values function."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'service_code,attribute_names,raw_values_map,expected',
        [
            # Single attribute test
            (
                'AmazonEC2',
                ['instanceType'],
                {'instanceType': ['t2.micro', 't2.small', 't3.medium', 'm5.large']},
                {'instanceType': ['m5.large', 't2.micro', 't2.small', 't3.medium']},
            ),
            # Multiple attributes test
            (
                'AmazonEC2',
                ['instanceType', 'location'],
                {
                    'instanceType': ['t2.micro', 't2.small', 't3.medium'],
                    'location': ['US East (N. Virginia)', 'US West (Oregon)', 'EU (Ireland)'],
                },
                {
                    'instanceType': ['t2.micro', 't2.small', 't3.medium'],
                    'location': ['EU (Ireland)', 'US East (N. Virginia)', 'US West (Oregon)'],
                },
            ),
            # Multiple attributes from different service
            (
                'AmazonRDS',
                ['engineCode', 'instanceType'],
                {
                    'engineCode': ['mysql', 'postgres', 'aurora-mysql'],
                    'instanceType': ['db.t3.micro', 'db.t3.small'],
                },
                {
                    'engineCode': ['aurora-mysql', 'mysql', 'postgres'],
                    'instanceType': ['db.t3.micro', 'db.t3.small'],
                },
            ),
        ],
    )
    async def test_get_pricing_attribute_values_success(
        self, mock_context, mock_boto3, service_code, attribute_names, raw_values_map, expected
    ):
        """Test getting attribute values for various AWS service attributes."""
        pricing_client = mock_boto3.Session().client('pricing')

        # Set up mock to return different values based on the attribute name
        def mock_get_attribute_values(ServiceCode, AttributeName, **kwargs):
            if AttributeName in raw_values_map:
                return {
                    'AttributeValues': [{'Value': val} for val in raw_values_map[AttributeName]]
                }
            return {'AttributeValues': []}

        pricing_client.get_attribute_values.side_effect = mock_get_attribute_values

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_attribute_values(
                mock_context, service_code, attribute_names
            )

            assert result == expected
            assert pricing_client.get_attribute_values.call_count == len(attribute_names)
            mock_context.info.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_attribute_values_single_attribute_with_pagination(
        self, mock_context, mock_boto3
    ):
        """Test getting attribute values with pagination handling for single attribute."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_attribute_values.side_effect = [
            {
                'AttributeValues': [{'Value': 't2.micro'}, {'Value': 't2.small'}],
                'NextToken': 'token',
            },
            {'AttributeValues': [{'Value': 't3.medium'}, {'Value': 'm5.large'}]},
        ]

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_attribute_values(
                mock_context, 'AmazonEC2', ['instanceType']
            )

            expected = {'instanceType': ['m5.large', 't2.micro', 't2.small', 't3.medium']}
            assert result == expected
            assert pricing_client.get_attribute_values.call_count == 2
            assert (
                pricing_client.get_attribute_values.call_args_list[1][1].get('NextToken')
                == 'token'
            )

    @pytest.mark.asyncio
    async def test_get_pricing_attribute_values_empty_attribute_list(
        self, mock_context, mock_boto3
    ):
        """Test error handling when empty attribute list is provided."""
        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_attribute_values(mock_context, 'AmazonEC2', [])

            # Verify error response structure
            assert isinstance(result, dict)
            assert result['status'] == 'error'
            assert result['error_type'] == 'empty_attribute_list'
            assert 'No attribute names provided' in result['message']
            assert result['service_code'] == 'AmazonEC2'
            assert result['attribute_names'] == []
            assert 'get_pricing_service_attributes()' in result['suggestion']
            mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_attribute_values_single_attribute_empty(
        self, mock_context, mock_boto3
    ):
        """Test getting attribute values when no values are returned for single attribute."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_attribute_values.return_value = {'AttributeValues': []}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_attribute_values(
                mock_context, 'InvalidService', ['invalidAttribute']
            )

            # Verify error response structure
            assert isinstance(result, dict)
            assert result['status'] == 'error'
            assert result['error_type'] == 'no_attribute_values_found'
            assert 'InvalidService' in result['message']
            assert 'invalidAttribute' in result['message']
            assert result['service_code'] == 'InvalidService'
            assert result['attribute_name'] == 'invalidAttribute'
            assert result['failed_attribute'] == 'invalidAttribute'
            assert result['requested_attributes'] == ['invalidAttribute']
            assert 'get_service_codes()' in result['suggestion']
            assert 'get_service_attributes()' in result['suggestion']
            assert 'examples' in result
            assert 'Common service codes' in result['examples']
            assert 'Common attributes' in result['examples']
            mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_attribute_values_all_or_nothing_failure(
        self, mock_context, mock_boto3
    ):
        """Test all-or-nothing behavior when one attribute fails in multi-attribute request."""
        pricing_client = mock_boto3.Session().client('pricing')

        # First attribute succeeds, second fails
        def mock_get_attribute_values(ServiceCode, AttributeName, **kwargs):
            if AttributeName == 'instanceType':
                return {'AttributeValues': [{'Value': 't2.micro'}, {'Value': 't3.medium'}]}
            elif AttributeName == 'invalidAttribute':
                return {'AttributeValues': []}  # Empty result causes failure

        pricing_client.get_attribute_values.side_effect = mock_get_attribute_values

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_attribute_values(
                mock_context, 'AmazonEC2', ['instanceType', 'invalidAttribute']
            )

            # Should return error because second attribute failed
            assert isinstance(result, dict)
            assert result['status'] == 'error'
            assert result['error_type'] == 'no_attribute_values_found'
            assert (
                'Failed to retrieve values for attribute "invalidAttribute"' in result['message']
            )
            assert result['failed_attribute'] == 'invalidAttribute'
            assert result['requested_attributes'] == ['instanceType', 'invalidAttribute']

    @pytest.mark.asyncio
    async def test_get_pricing_attribute_values_api_error_in_multi_attribute(
        self, mock_context, mock_boto3
    ):
        """Test handling of API errors when getting attribute values in multi-attribute request."""
        pricing_client = mock_boto3.Session().client('pricing')

        # First attribute succeeds, second raises API error
        def mock_get_attribute_values(ServiceCode, AttributeName, **kwargs):
            if AttributeName == 'instanceType':
                return {'AttributeValues': [{'Value': 't2.micro'}, {'Value': 't3.medium'}]}
            elif AttributeName == 'location':
                raise Exception('API Error')

        pricing_client.get_attribute_values.side_effect = mock_get_attribute_values

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_attribute_values(
                mock_context, 'AmazonEC2', ['instanceType', 'location']
            )

            # Should return error because second attribute had API error
            assert isinstance(result, dict)
            assert result['status'] == 'error'
            assert result['error_type'] == 'api_error'
            assert 'Failed to retrieve values for attribute "location"' in result['message']
            assert 'API Error' in result['message']
            assert result['failed_attribute'] == 'location'
            assert result['requested_attributes'] == ['instanceType', 'location']

    @pytest.mark.asyncio
    async def test_get_pricing_attribute_values_client_creation_error(self, mock_context):
        """Test handling of client creation errors."""
        with patch(
            'awslabs.aws_pricing_mcp_server.server.create_pricing_client',
            side_effect=Exception('Client creation failed'),
        ):
            result = await get_pricing_attribute_values(
                mock_context, 'AmazonEC2', ['instanceType']
            )

        assert isinstance(result, dict)
        assert result['status'] == 'error'
        assert result['error_type'] == 'client_creation_failed'
        assert 'Failed to create AWS Pricing client' in result['message']
        assert 'Client creation failed' in result['message']
        assert result['service_code'] == 'AmazonEC2'
        assert result['attribute_names'] == ['instanceType']
        mock_context.error.assert_called()


class TestServerIntegration:
    """Integration tests for the server module."""

    @pytest.mark.asyncio
    async def test_get_pricing_service_codes_integration(self, mock_context, mock_boto3):
        """Test the get_pricing_service_codes tool returns well-known service codes."""
        # Mock the boto3 pricing client response
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.describe_services.return_value = {
            'Services': [
                {'ServiceCode': 'AmazonEC2'},
                {'ServiceCode': 'AmazonS3'},
                {'ServiceCode': 'AmazonRDS'},
                {'ServiceCode': 'AWSLambda'},
                {'ServiceCode': 'AmazonDynamoDB'},
            ]
        }

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            # Call the get_pricing_service_codes function directly
            service_codes = await get_pricing_service_codes(mock_context)

            # Verify we got a successful response
            assert service_codes is not None
            assert isinstance(service_codes, list)

            # Check for well-known AWS service codes that should be present
            expected_codes = ['AmazonEC2', 'AmazonS3', 'AmazonRDS', 'AWSLambda', 'AmazonDynamoDB']

            # Assert that the expected codes are present in the response
            for code in expected_codes:
                assert code in service_codes, f'Expected service code {code} not found in response'

            # Verify that the mock was called correctly
            pricing_client.describe_services.assert_called()

            # Verify context was used correctly
            mock_context.info.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'error_scenario,side_effect,expected_error_type',
        [
            ('client_creation_failed', 'create_pricing_client', 'client_creation_failed'),
            ('api_error', 'describe_services', 'api_error'),
            ('empty_results', None, 'empty_results'),
        ],
    )
    async def test_get_pricing_service_codes_errors(
        self, mock_context, mock_boto3, error_scenario, side_effect, expected_error_type
    ):
        """Test error handling scenarios for get_pricing_service_codes."""
        if error_scenario == 'client_creation_failed':
            with patch(
                'awslabs.aws_pricing_mcp_server.server.create_pricing_client',
                side_effect=Exception('Client creation failed'),
            ):
                result = await get_pricing_service_codes(mock_context)
        elif error_scenario == 'api_error':
            pricing_client = mock_boto3.Session().client('pricing')
            pricing_client.describe_services.side_effect = Exception('API Error')
            with patch('boto3.Session', return_value=mock_boto3.Session()):
                result = await get_pricing_service_codes(mock_context)
        elif error_scenario == 'empty_results':
            pricing_client = mock_boto3.Session().client('pricing')
            pricing_client.describe_services.return_value = {'Services': []}
            with patch('boto3.Session', return_value=mock_boto3.Session()):
                result = await get_pricing_service_codes(mock_context)
        else:
            # Should not reach here with current parametrize values
            raise ValueError(f'Unknown error scenario: {error_scenario}')

        assert isinstance(result, dict)
        assert result['status'] == 'error'
        assert result['error_type'] == expected_error_type
        mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_pricing_service_codes_pagination(self, mock_context, mock_boto3):
        """Test that get_pricing_service_codes correctly handles pagination."""
        # Mock the boto3 pricing client response for pagination
        pricing_client = mock_boto3.Session().client('pricing')

        # Set up a mock with pagination
        pricing_client.describe_services.side_effect = [
            # First call returns first page with NextToken
            {
                'Services': [
                    {'ServiceCode': 'AmazonEC2'},
                    {'ServiceCode': 'AmazonS3'},
                ],
                'NextToken': 'page2token',
            },
            # Second call with NextToken returns second page
            {
                'Services': [
                    {'ServiceCode': 'AmazonRDS'},
                    {'ServiceCode': 'AWSLambda'},
                    {'ServiceCode': 'AmazonDynamoDB'},
                ]
                # No NextToken in the response means this is the last page
            },
        ]

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            # Call the get_pricing_service_codes function directly
            service_codes = await get_pricing_service_codes(mock_context)

            # Verify we got a successful response that combines both pages
            assert service_codes is not None
            assert isinstance(service_codes, list)
            assert len(service_codes) == 5  # Total from both pages

            # Verify pagination happened
            assert pricing_client.describe_services.call_count == 2

            # First call should have no NextToken
            first_call_kwargs = pricing_client.describe_services.call_args_list[0][1]
            assert 'NextToken' not in first_call_kwargs

            # Second call should include the NextToken from the first response
            second_call_kwargs = pricing_client.describe_services.call_args_list[1][1]
            assert second_call_kwargs.get('NextToken') == 'page2token'

    @pytest.mark.asyncio
    async def test_pricing_workflow(self, mock_context, mock_boto3):
        """Test the complete pricing analysis workflow."""
        # 1. Get pricing from API
        with patch('boto3.Session', return_value=mock_boto3.Session()):
            api_pricing = await get_pricing(mock_context, 'AWSLambda', 'us-west-2')
        assert api_pricing is not None
        assert api_pricing['status'] == 'success'

        # 2. Generate cost report
        report = await generate_cost_report_wrapper(
            mock_context,
            pricing_data=api_pricing,
            service_name='AWS Lambda',
            pricing_model='ON DEMAND',
            related_services=None,
            assumptions=None,
            exclusions=None,
            output_file=None,
            detailed_cost_data=None,
            recommendations=None,
        )
        assert report is not None
        assert isinstance(report, str)
        assert 'AWS Lambda' in report


class TestIsFreeProduct:
    """Tests for the _is_free_product function with multi-currency support."""

    def _create_pricing_data(self, price_per_unit: dict) -> dict:
        """Helper to create test pricing data structure."""
        return {
            'terms': {
                'OnDemand': {
                    'TEST.TERM.CODE': {
                        'priceDimensions': {'TEST.TERM.CODE.DIM': {'pricePerUnit': price_per_unit}}
                    }
                }
            }
        }

    @pytest.mark.parametrize(
        'price_per_unit,expected_result,test_description',
        [
            # Test case 1: All currencies zero (truly free)
            ({'USD': '0.0000', 'CNY': '0.0000'}, True, 'truly_free_all_zero'),
            # Test case 2: CNY only, non-zero (should be False)
            ({'CNY': '5.2000'}, False, 'cny_only_paid'),
            # Test case 3: Free in USD, paid in CNY (should be False)
            ({'USD': '0.0000', 'CNY': '3.5000'}, False, 'usd_free_cny_paid'),
            # Test case 4: Invalid CNY price format (should be False)
            ({'CNY': 'N/A'}, False, 'invalid_cny_format'),
            # Test case 5: Multiple currencies with CNY paid
            (
                {'USD': '0.0000', 'EUR': '0.0000', 'CNY': '8.7500'},
                False,
                'multi_currency_cny_paid',
            ),
        ],
    )
    def test_is_free_product_multi_currency(
        self, price_per_unit, expected_result, test_description
    ):
        """Test _is_free_product correctly handles CNY and other currencies."""
        pricing_data = self._create_pricing_data(price_per_unit)
        result = _is_free_product(pricing_data)

        assert result == expected_result, (
            f"Failed test case '{test_description}': "
            f'Expected {expected_result}, got {result} for pricing {price_per_unit}'
        )


class TestGetPriceListUrls:
    """Tests for the get_price_list_urls function."""

    @pytest.mark.asyncio
    async def test_get_price_list_urls_success(self, mock_context, mock_boto3):
        """Test successful retrieval of price list file URLs for all formats."""
        pricing_client = mock_boto3.Session().client('pricing')

        # Mock list_price_lists response
        pricing_client.list_price_lists.return_value = {
            'PriceLists': [
                {
                    'PriceListArn': 'arn:aws:pricing::123456789012:price-list/AmazonEC2',
                    'FileFormats': ['CSV', 'JSON'],
                }
            ]
        }

        # Mock get_price_list_file_url response - called for each format
        pricing_client.get_price_list_file_url.side_effect = [
            {'Url': 'https://example.com/pricing.csv'},
            {'Url': 'https://example.com/pricing.json'},
        ]

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(
                mock_context, 'AmazonEC2', 'us-east-1', '2023-06-01 00:00'
            )

        # Check that we get all available format URLs
        assert len(result) == 2  # csv + json
        assert result['csv'] == 'https://example.com/pricing.csv'
        assert result['json'] == 'https://example.com/pricing.json'

        # Verify API calls
        pricing_client.list_price_lists.assert_called_once_with(
            ServiceCode='AmazonEC2',
            EffectiveDate='2023-06-01 00:00',
            RegionCode='us-east-1',
            CurrencyCode='USD',
        )

        # Verify get_price_list_file_url was called for each format
        assert pricing_client.get_price_list_file_url.call_count == 2
        pricing_client.get_price_list_file_url.assert_any_call(
            PriceListArn='arn:aws:pricing::123456789012:price-list/AmazonEC2', FileFormat='CSV'
        )
        pricing_client.get_price_list_file_url.assert_any_call(
            PriceListArn='arn:aws:pricing::123456789012:price-list/AmazonEC2', FileFormat='JSON'
        )

    @pytest.mark.asyncio
    async def test_get_price_list_urls_default_date(self, mock_context, mock_boto3):
        """Test that current timestamp is used when effective_date is not provided."""
        pricing_client = mock_boto3.Session().client('pricing')

        pricing_client.list_price_lists.return_value = {
            'PriceLists': [
                {
                    'PriceListArn': 'arn:aws:pricing::123456789012:price-list/AmazonS3',
                    'FileFormats': ['CSV'],
                }
            ]
        }

        pricing_client.get_price_list_file_url.return_value = {
            'Url': 'https://example.com/pricing.csv'
        }

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'AmazonS3', 'us-west-2')

        # Check that we get all available format URLs
        assert len(result) == 1  # csv only
        assert result['csv'] == 'https://example.com/pricing.csv'

    @pytest.mark.asyncio
    async def test_get_price_list_urls_format_failure(self, mock_context, mock_boto3):
        """Test that any format failure results in an error."""
        pricing_client = mock_boto3.Session().client('pricing')

        # Mock list_price_lists response with both formats
        pricing_client.list_price_lists.return_value = {
            'PriceLists': [
                {
                    'PriceListArn': 'arn:aws:pricing::123456789012:price-list/AmazonEC2',
                    'FileFormats': ['CSV', 'JSON'],
                }
            ]
        }

        # Mock CSV succeeding but JSON failing
        pricing_client.get_price_list_file_url.side_effect = [
            {'Url': 'https://example.com/pricing.csv'},  # CSV succeeds
            Exception('Failed to get JSON URL'),  # JSON fails
        ]

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'AmazonEC2', 'us-east-1')

        # Should return error when any format fails
        assert result['status'] == 'error'
        assert result['error_type'] == 'format_url_failed'
        assert 'Failed to get download URL for format "JSON"' in result['message']
        assert result['price_list_arn'] == 'arn:aws:pricing::123456789012:price-list/AmazonEC2'
        assert result['file_format'] == 'json'

        # Verify error was logged
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_price_list_urls_no_price_lists(self, mock_context, mock_boto3):
        """Test error handling when no price lists are found."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.list_price_lists.return_value = {'PriceLists': []}

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'InvalidService', 'us-east-1')

        assert result['status'] == 'error'
        assert result['error_type'] == 'no_price_list_found'
        assert 'InvalidService' in result['message']
        assert result['service_code'] == 'InvalidService'
        assert result['region'] == 'us-east-1'
        mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_price_list_urls_unsupported_format(self, mock_context, mock_boto3):
        """Test handling when some formats are not supported."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.list_price_lists.return_value = {
            'PriceLists': [
                {
                    'PriceListArn': 'arn:aws:pricing::123456789012:price-list/AmazonEC2',
                    'FileFormats': ['CSV'],  # Only CSV supported
                }
            ]
        }

        pricing_client.get_price_list_file_url.return_value = {
            'Url': 'https://example.com/pricing.csv'
        }

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'AmazonEC2', 'us-east-1')

        # Should still return successful result with available formats
        assert len(result) == 1  # csv only
        assert result['csv'] == 'https://example.com/pricing.csv'
        assert 'json' not in result  # JSON format not supported

    @pytest.mark.asyncio
    async def test_get_price_list_urls_list_api_error(self, mock_context, mock_boto3):
        """Test error handling when list_price_lists API call fails."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.list_price_lists.side_effect = Exception('API Error')

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'error'
        assert result['error_type'] == 'list_price_lists_failed'
        assert 'API Error' in result['message']
        assert result['service_code'] == 'AmazonEC2'
        assert result['region'] == 'us-east-1'
        mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_price_list_urls_get_url_api_error(self, mock_context, mock_boto3):
        """Test error handling when get_price_list_file_url API call fails."""
        pricing_client = mock_boto3.Session().client('pricing')

        pricing_client.list_price_lists.return_value = {
            'PriceLists': [
                {
                    'PriceListArn': 'arn:aws:pricing::123456789012:price-list/AmazonEC2',
                    'FileFormats': ['CSV'],
                }
            ]
        }

        pricing_client.get_price_list_file_url.side_effect = Exception('URL API Error')

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'error'
        assert result['error_type'] == 'format_url_failed'
        assert 'Failed to get download URL for format "CSV"' in result['message']
        assert result['price_list_arn'] == 'arn:aws:pricing::123456789012:price-list/AmazonEC2'
        assert result['file_format'] == 'csv'
        mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_price_list_urls_no_download_url(self, mock_context, mock_boto3):
        """Test error handling when no download URL is returned."""
        pricing_client = mock_boto3.Session().client('pricing')

        pricing_client.list_price_lists.return_value = {
            'PriceLists': [
                {
                    'PriceListArn': 'arn:aws:pricing::123456789012:price-list/AmazonEC2',
                    'FileFormats': ['CSV'],
                }
            ]
        }

        pricing_client.get_price_list_file_url.return_value = {}  # No URL

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'error'
        assert result['error_type'] == 'empty_url_response'
        assert 'AWS API returned empty URL for format "CSV"' in result['message']
        assert result['price_list_arn'] == 'arn:aws:pricing::123456789012:price-list/AmazonEC2'
        assert result['file_format'] == 'csv'
        mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_price_list_urls_unexpected_error(self, mock_context):
        """Test error handling for unexpected errors."""
        with patch('boto3.Session', side_effect=Exception('Unexpected Error')):
            result = await get_price_list_urls(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'error'
        assert result['error_type'] == 'client_creation_failed'
        assert 'Unexpected Error' in result['message']
        assert result['service_code'] == 'AmazonEC2'
        assert result['region'] == 'us-east-1'
        mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_price_list_urls_no_supported_formats(self, mock_context, mock_boto3):
        """Test error handling when price list has no supported formats."""
        pricing_client = mock_boto3.Session().client('pricing')

        pricing_client.list_price_lists.return_value = {
            'PriceLists': [
                {
                    'PriceListArn': 'arn:aws:pricing::123456789012:price-list/AmazonEC2',
                    'FileFormats': [],  # Empty list of formats
                }
            ]
        }

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_price_list_urls(mock_context, 'AmazonEC2', 'us-east-1')

        assert result['status'] == 'error'
        assert result['error_type'] == 'no_formats_available'
        assert 'no file formats are available for service "AmazonEC2"' in result['message']
        assert result['service_code'] == 'AmazonEC2'
        assert result['region'] == 'us-east-1'
        assert result['price_list_arn'] == 'arn:aws:pricing::123456789012:price-list/AmazonEC2'
        mock_context.error.assert_called()
