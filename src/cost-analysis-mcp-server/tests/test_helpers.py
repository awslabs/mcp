# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the helpers module."""

from awslabs.cost_analysis_mcp_server.helpers import CostAnalysisHelper


class TestCostAnalysisHelper:
    """Tests for the CostAnalysisHelper class."""

    def test_parse_pricing_data_web(self, sample_pricing_data_web):
        """Test parsing web-scraped pricing data."""
        result = CostAnalysisHelper.parse_pricing_data(sample_pricing_data_web, 'AWS Lambda')

        assert result is not None
        assert result['service_name'] == 'AWS Lambda'
        assert result['service_description'] != ''

    def test_parse_pricing_data_api(self, sample_pricing_data_api):
        """Test parsing API pricing data."""
        result = CostAnalysisHelper.parse_pricing_data(sample_pricing_data_api, 'AWS Lambda')

        assert result is not None

    def test_parse_pricing_data_with_related_services(self, sample_pricing_data_web):
        """Test parsing pricing data with related services context."""
        result = CostAnalysisHelper.parse_pricing_data(
            sample_pricing_data_web, 'AWS Lambda', related_services=['DynamoDB', 'S3']
        )

        assert result is not None

    def test_parse_pricing_data_bedrock_kb(self, sample_pricing_data_web):
        """Test parsing pricing data for Bedrock Knowledge Base with OpenSearch."""
        result = CostAnalysisHelper.parse_pricing_data(
            sample_pricing_data_web,
            'Amazon Bedrock',
            related_services=['Knowledge Base', 'OpenSearch Serverless'],
        )

        assert result is not None

    def test_parse_pricing_data_empty(self):
        """Test parsing empty pricing data."""
        result = CostAnalysisHelper.parse_pricing_data(
            {'data': '', 'status': 'success'}, 'Test Service'
        )

        assert result is not None
        assert result['service_name'] == 'Test Service'

    def test_generate_cost_table_full_data(self, sample_pricing_data_web):
        """Test generating cost tables with full pricing data."""
        pricing_structure = CostAnalysisHelper.parse_pricing_data(
            sample_pricing_data_web, 'AWS Lambda'
        )
        tables = CostAnalysisHelper.generate_cost_table(pricing_structure)

        assert 'unit_pricing_details_table' in tables
        assert 'cost_calculation_table' in tables
        assert 'usage_cost_table' in tables
        assert 'projected_costs_table' in tables

        # Check table contents
        assert 'Service' in tables['unit_pricing_details_table']
        assert 'AWS Lambda' in tables['unit_pricing_details_table']

    def test_generate_cost_table_minimal_data(self):
        """Test generating cost tables with minimal data."""
        pricing_structure = {
            'service_name': 'Test Service',
            'service_description': 'Test Description',
            'unit_pricing': [],
            'free_tier': 'No free tier',
            'usage_levels': {'low': {}, 'medium': {}, 'high': {}},
            'key_cost_factors': [],
            'projected_costs': {},
            'recommendations': {'immediate': [], 'best_practices': []},
        }

        tables = CostAnalysisHelper.generate_cost_table(pricing_structure)

        assert 'unit_pricing_details_table' in tables

    def test_generate_well_architected_recommendations_lambda(self):
        """Test generating Well-Architected recommendations for Lambda."""
        recommendations = CostAnalysisHelper.generate_well_architected_recommendations(['lambda'])

        assert 'immediate' in recommendations
        assert 'best_practices' in recommendations
        assert len(recommendations['immediate']) > 0
        assert len(recommendations['best_practices']) > 0

        # Check for Lambda-specific recommendations
        all_recommendations = recommendations['immediate'] + recommendations['best_practices']
        assert any('Lambda' in rec for rec in all_recommendations)
        assert any('memory' in rec.lower() for rec in all_recommendations)

    def test_generate_well_architected_recommendations_bedrock(self):
        """Test generating Well-Architected recommendations for Bedrock."""
        recommendations = CostAnalysisHelper.generate_well_architected_recommendations(['bedrock'])

        assert 'immediate' in recommendations
        assert 'best_practices' in recommendations

        # Check for Bedrock-specific recommendations
        all_recommendations = recommendations['immediate'] + recommendations['best_practices']
        assert any('prompt' in rec.lower() for rec in all_recommendations)
        assert any('token' in rec.lower() for rec in all_recommendations)

    def test_generate_well_architected_recommendations_multiple_services(self):
        """Test generating recommendations for multiple services."""
        recommendations = CostAnalysisHelper.generate_well_architected_recommendations(
            ['lambda', 'dynamodb', 's3']
        )

        assert 'immediate' in recommendations
        assert 'best_practices' in recommendations

        # Check for service-specific recommendations
        all_recommendations = recommendations['immediate'] + recommendations['best_practices']
        services_mentioned = [
            any(service.lower() in rec.lower() for rec in all_recommendations)
            for service in ['Lambda', 'DynamoDB', 'S3']
        ]
        assert any(services_mentioned)

    def test_generate_well_architected_recommendations_empty(self):
        """Test generating recommendations with no services."""
        recommendations = CostAnalysisHelper.generate_well_architected_recommendations([])

        assert 'immediate' in recommendations
        assert 'best_practices' in recommendations
        assert len(recommendations['immediate']) > 0
        assert len(recommendations['best_practices']) > 0

        # Check for generic cost optimization recommendations
        all_recommendations = recommendations['immediate'] + recommendations['best_practices']
        assert any('cost' in rec.lower() for rec in all_recommendations)
        assert any('monitor' in rec.lower() for rec in all_recommendations)

    def test_parse_pricing_data_with_invalid_input(self):
        """Test parsing invalid pricing data."""
        result = CostAnalysisHelper.parse_pricing_data(
            {'data': '', 'status': 'error'}, 'Test Service'
        )

        assert result is not None
        assert result['service_name'] == 'Test Service'

    def test_generate_cost_table_with_invalid_input(self):
        """Test generating cost tables with invalid input."""
        tables = CostAnalysisHelper.generate_cost_table(
            {
                'service_name': 'Test Service',
                'service_description': 'Test Description',
                'unit_pricing': [],
                'free_tier': 'No free tier',
                'usage_levels': {'low': {}, 'medium': {}, 'high': {}},
                'key_cost_factors': [],
                'projected_costs': {},
                'recommendations': {'immediate': [], 'best_practices': []},
            }
        )

        assert 'unit_pricing_details_table' in tables
        assert 'cost_calculation_table' in tables
        assert 'usage_cost_table' in tables
        assert 'projected_costs_table' in tables
