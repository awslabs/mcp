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

import json
import pytest
from awslabs.aws_pricing_mcp_server.models import PricingFilter, PricingFilters
from awslabs.aws_pricing_mcp_server.server import (
    analyze_cdk_project_wrapper,
    generate_cost_report_wrapper,
    get_bedrock_patterns,
    get_pricing_from_api,
    get_pricing_from_web,
)
from unittest.mock import MagicMock, patch


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


class TestGetPricingFromWeb:
    """Tests for the get_pricing_from_web function."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_get_valid_pricing(self, mock_get, mock_context):
        """Test getting pricing for a valid service."""
        mock_response = MagicMock()
        mock_response.text = """
        AWS Lambda Pricing
        Lambda lets you run code without provisioning servers.
        Pricing:
        - $0.20 per 1M requests
        - $0.0000166667 per GB-second
        Free Tier:
        - 1M requests free per month
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = await get_pricing_from_web(mock_context, 'lambda')

        assert result is not None
        assert result['status'] == 'success'
        assert result['service_name'] == 'lambda'
        assert 'data' in result
        assert '$0.20 per 1M requests' in result['data']

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_get_pricing_connection_error(self, mock_get, mock_context):
        """Test handling of connection errors."""
        mock_get.side_effect = Exception('Connection failed')

        result = await get_pricing_from_web(mock_context, 'lambda')

        assert result is None
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_get_pricing_invalid_service(self, mock_get, mock_context):
        """Test getting pricing for an invalid service."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception('404 Not Found')
        mock_get.return_value = mock_response

        result = await get_pricing_from_web(mock_context, 'invalid-service')

        assert result is None
        mock_context.error.assert_called_once()


class TestGetPricingFromApi:
    """Tests for the get_pricing_from_api function."""

    @pytest.mark.asyncio
    async def test_get_valid_pricing(self, mock_boto3, mock_context):
        """Test getting pricing for a valid service."""
        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_from_api(mock_context, 'AWSLambda', 'us-west-2')

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
        """Test getting pricing with filters using PricingFilters model."""
        # Create filters using the Pydantic models
        filters = PricingFilters(
            filters=[
                PricingFilter(Field='instanceType', Value='t3.medium', Type='TERM_MATCH'),
                PricingFilter(Field='location', Value='US East (N. Virginia)', Type='TERM_MATCH'),
            ]
        )

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_from_api(mock_context, 'AmazonEC2', 'us-east-1', filters)

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
    async def test_pricing_filters_model_validation(self):
        """Test that PricingFilters model validates correctly."""
        # Test valid filter creation
        valid_filter = PricingFilter(Field='instanceType', Value='t3.medium')
        assert valid_filter.field == 'instanceType'
        assert valid_filter.value == 't3.medium'
        assert valid_filter.type == 'TERM_MATCH'  # Default value

        # Test serialization with aliases
        filter_dict = valid_filter.model_dump(by_alias=True)
        assert 'Field' in filter_dict
        assert 'Value' in filter_dict
        assert 'Type' in filter_dict
        assert filter_dict['Field'] == 'instanceType'
        assert filter_dict['Value'] == 't3.medium'
        assert filter_dict['Type'] == 'TERM_MATCH'

        # Test PricingFilters container
        filters = PricingFilters(filters=[valid_filter])
        assert len(filters.filters) == 1
        assert filters.filters[0].field == 'instanceType'

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
            result = await get_pricing_from_api(mock_context, 'AmazonEC2', 'us-east-1')

        # Validate top-level response structure
        assert result['status'] == 'success'
        assert result['service_name'] == 'AmazonEC2'
        assert isinstance(result['data'], list)
        assert len(result['data']) == 1
        assert isinstance(result['message'], str)

        pricing_item = json.loads(result['data'][0])

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
            result = await get_pricing_from_api(mock_context, 'InvalidService', 'us-west-2')

        assert result is not None
        assert result['status'] == 'error'
        assert result['error_type'] == 'empty_results'
        assert 'InvalidService' in result['message']
        assert result['service_code'] == 'InvalidService'
        assert result['region'] == 'us-west-2'
        assert 'examples' in result
        assert 'AmazonES' in result['examples']['OpenSearch']
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_api_error(self, mock_boto3, mock_context):
        """Test handling of API errors."""
        pricing_client = mock_boto3.Session().client('pricing')
        pricing_client.get_products.side_effect = Exception('API Error')

        with patch('boto3.Session', return_value=mock_boto3.Session()):
            result = await get_pricing_from_api(mock_context, 'AWSLambda', 'us-west-2')

        assert result is not None
        assert result['status'] == 'error'
        assert result['error_type'] == 'api_error'
        assert 'API Error' in result['message']
        assert result['service_code'] == 'AWSLambda'
        assert result['region'] == 'us-west-2'
        assert 'suggestion' in result
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_client_creation_error(self, mock_context):
        """Test handling of client creation errors."""
        with patch(
            'awslabs.cost_analysis_mcp_server.server.create_pricing_client',
            side_effect=Exception('Client creation failed'),
        ):
            result = await get_pricing_from_api(mock_context, 'AWSLambda', 'us-west-2')

        assert result is not None
        assert result['status'] == 'error'
        assert result['error_type'] == 'client_creation_failed'
        assert 'Failed to create AWS Pricing client' in result['message']
        assert 'Client creation failed' in result['message']
        assert result['service_code'] == 'AWSLambda'
        assert result['region'] == 'us-west-2'
        mock_context.error.assert_called_once()


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


class TestServerIntegration:
    """Integration tests for the server module."""

    @pytest.mark.asyncio
    async def test_pricing_workflow(self, mock_context, mock_boto3):
        """Test the complete pricing analysis workflow."""
        # 1. Get pricing from web
        web_pricing = await get_pricing_from_web(mock_context, 'lambda')
        assert web_pricing is not None
        assert web_pricing['status'] == 'success'

        # 2. Get pricing from API as fallback
        with patch('boto3.Session', return_value=mock_boto3.Session()):
            api_pricing = await get_pricing_from_api(mock_context, 'AWSLambda', 'us-west-2')
        assert api_pricing is not None
        assert api_pricing['status'] == 'success'

        # 3. Generate cost report
        report = await generate_cost_report_wrapper(
            mock_context,
            pricing_data=web_pricing,
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
