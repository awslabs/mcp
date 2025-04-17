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

"""Tests for the report generator module."""

import os
import pytest
from awslabs.cost_analysis_mcp_server.helpers import CostAnalysisHelper
from awslabs.cost_analysis_mcp_server.report_generator import (
    ServiceInfo,
    _create_cost_calculation_table,
    _create_free_tier_info,
    _create_unit_pricing_details_table,
    _create_usage_cost_table,
    _extract_services_info,
    _format_value,
    _generate_csv_report,
    _generate_custom_data_report,
    _generate_pricing_data_report,
    _process_custom_sections,
    _process_recommendations,
    generate_cost_report,
)


class TestReportGenerator:
    """Tests for the report generator module."""

    def test_extract_services_info_direct(self):
        """Test extracting services info from direct services data."""
        custom_cost_data = {
            'services': {
                'AWS Lambda': {
                    'estimated_cost': '$20.00',
                    'usage': '1M requests per month',
                    'unit_pricing': {
                        'requests': '$0.20 per 1M requests',
                        'compute': '$0.0000166667 per GB-second',
                    },
                }
            }
        }

        services_info, service_names = _extract_services_info(custom_cost_data)

        assert len(services_info) == 1
        assert 'AWS Lambda' in services_info
        assert services_info['AWS Lambda'].estimated_cost == '$20.00'
        assert services_info['AWS Lambda'].usage == '1M requests per month'
        assert services_info['AWS Lambda'].unit_pricing is not None
        assert len(services_info['AWS Lambda'].unit_pricing) == 2  # type: ignore

    def test_extract_services_info_nested(self):
        """Test extracting services info from nested cost data."""
        custom_cost_data = {
            'compute_costs': {
                'lambda_function': {'monthly_cost': 20.00, 'description': '1M requests per month'}
            }
        }

        services_info, service_names = _extract_services_info(custom_cost_data)

        assert len(services_info) == 1
        assert 'Lambda Function' in services_info
        assert services_info['Lambda Function'].estimated_cost == '$20.0'

    def test_create_unit_pricing_details_table(self):
        """Test creating unit pricing details table."""
        services_info = {
            'AWS Lambda': ServiceInfo(
                name='AWS Lambda',
                estimated_cost='$20.00',
                usage='1M requests per month',
                unit_pricing={
                    'requests': '$0.20 per 1M requests',
                    'compute': '$0.0000166667 per GB-second',
                },
            )
        }

        table = _create_unit_pricing_details_table(services_info)

        assert '| Service | Resource Type | Unit | Price | Free Tier |' in table
        assert 'AWS Lambda' in table
        assert '$0.20' in table
        assert 'requests' in table.lower()
        assert 'GB-second' in table

    def test_create_cost_calculation_table(self):
        """Test creating cost calculation table."""
        services_info = {
            'AWS Lambda': ServiceInfo(
                name='AWS Lambda',
                estimated_cost='$20.00',
                usage='1M requests per month',
                calculation_details='$0.20 × 100 requests',
            )
        }

        table, total_min, total_max, base_cost = _create_cost_calculation_table(services_info)

        assert '| Service | Usage | Calculation | Monthly Cost |' in table
        assert 'AWS Lambda' in table
        assert '$20.00' in table
        assert total_min == 20.0
        assert total_max == 20.0
        assert base_cost == 20.0

    def test_create_free_tier_info(self):
        """Test creating free tier information."""
        custom_cost_data = {
            'services': {
                'AWS Lambda': ServiceInfo(
                    name='AWS Lambda',
                    estimated_cost='$20.00',
                    usage='1M requests per month',
                    free_tier_info='1M free requests per month',
                )
            }
        }

        free_tier_info = _create_free_tier_info(custom_cost_data, custom_cost_data['services'])

        assert 'Free tier information by service:' in free_tier_info
        assert 'AWS Lambda' in free_tier_info
        assert '1M free requests per month' in free_tier_info

    def test_create_usage_cost_table(self):
        """Test creating usage cost table."""
        services_info = {
            'AWS Lambda': ServiceInfo(
                name='AWS Lambda',
                estimated_cost='$20.00',
                usage='1M requests per month',
                unit_pricing={},  # Initialize with empty dict instead of None
            )
        }

        table = _create_usage_cost_table(services_info)

        assert '| Service | Low Usage | Medium Usage | High Usage |' in table
        assert 'AWS Lambda' in table
        assert '$10' in table  # Low usage (50%)
        assert '$20' in table  # Medium usage (100%)
        assert '$40' in table  # High usage (200%)

    @pytest.mark.asyncio
    async def test_generate_custom_data_report(self, mock_context, temp_output_dir):
        """Test generating a report from custom data."""
        custom_cost_data = {
            'project_name': 'Test Project',
            'description': 'A test project',
            'services': {
                'AWS Lambda': {
                    'estimated_cost': '$20.00',
                    'usage': '1M requests per month',
                    'unit_pricing': {'requests': '$0.20 per 1M requests'},
                }
            },
        }

        output_file = os.path.join(temp_output_dir, 'report.md')
        report = await _generate_custom_data_report(
            custom_cost_data, output_file=output_file, ctx=mock_context
        )

        assert report is not None
        assert os.path.exists(output_file)

    @pytest.mark.asyncio
    async def test_generate_pricing_data_report(self, mock_context, sample_pricing_data_web):
        """Test generating a report from pricing data."""
        report = await _generate_pricing_data_report(
            pricing_data=sample_pricing_data_web,
            service_name='AWS Lambda',
            related_services=['DynamoDB'],
            ctx=mock_context,
        )

        assert report is not None

    @pytest.mark.asyncio
    async def test_generate_csv_report(self, mock_context, temp_output_dir):
        """Test generating a CSV report."""
        cost_data = {
            'project_name': 'Test Project',
            'services': {
                'AWS Lambda': {
                    'estimated_cost': '$20.00',
                    'usage': '1M requests per month',
                    'unit_pricing': {'requests': '$0.20 per 1M requests'},
                }
            },
        }

        output_file = os.path.join(temp_output_dir, 'report.csv')
        csv_content = await _generate_csv_report(
            cost_data, output_file=output_file, ctx=mock_context
        )

        assert csv_content is not None
        assert ',' in csv_content  # Verify it's CSV format
        assert os.path.exists(output_file)

        # Verify basic structure
        lines = csv_content.split('\n')
        assert len(lines) > 1  # Has header and data

    @pytest.mark.asyncio
    async def test_generate_cost_report_markdown(
        self, mock_context, sample_pricing_data_web, temp_output_dir
    ):
        """Test the main generate_cost_report function with markdown output."""
        output_file = os.path.join(temp_output_dir, 'report.md')
        report = await generate_cost_report(
            pricing_data=sample_pricing_data_web,
            service_name='AWS Lambda',
            related_services=['DynamoDB'],
            output_file=output_file,
            ctx=mock_context,
        )

        assert report is not None
        assert os.path.exists(output_file)

    @pytest.mark.asyncio
    async def test_generate_cost_report_csv(
        self, mock_context, sample_pricing_data_web, temp_output_dir
    ):
        """Test the main generate_cost_report function with CSV output."""
        output_file = os.path.join(temp_output_dir, 'report.csv')
        report = await generate_cost_report(
            pricing_data=sample_pricing_data_web,
            service_name='AWS Lambda',
            format='csv',
            output_file=output_file,
            ctx=mock_context,
        )

        assert report is not None
        assert ',' in report  # Verify it's CSV format
        assert os.path.exists(output_file)

        # Verify basic structure
        lines = report.split('\n')
        assert len(lines) > 1  # Has header and data

    @pytest.mark.asyncio
    async def test_generate_cost_report_error_handling(self, mock_context):
        """Test error handling in generate_cost_report."""
        report = await generate_cost_report(
            pricing_data={'status': 'error'}, service_name='Invalid Service', ctx=mock_context
        )

        assert '# Invalid Service Cost Analysis' in report

    def test_process_recommendations_with_prompt(self):
        """Test processing recommendations with a prompt template."""
        custom_cost_data = {
            'recommendations': {
                '_prompt': 'Generate recommendations for Lambda',
                'immediate': ['Optimize memory settings'],
                'best_practices': ['Monitor usage patterns'],
            }
        }

        immediate, best_practices = _process_recommendations(custom_cost_data, ['lambda'])

        assert len(immediate) > 0
        assert len(best_practices) > 0
        assert 'memory' in ' '.join(immediate).lower()
        assert 'monitor' in ' '.join(best_practices).lower()

    def test_process_recommendations_fallback(self):
        """Test recommendations fallback to Well-Architected framework."""
        custom_cost_data = {}
        immediate, best_practices = _process_recommendations(custom_cost_data, ['lambda'])

        assert len(immediate) > 0
        assert len(best_practices) > 0
        assert any('Lambda' in rec for rec in immediate + best_practices)

    def test_format_value_monetary(self):
        """Test formatting monetary values."""
        assert _format_value('total', 100) == '**$100**'
        assert _format_value('cost', 50.5) == '$50.5'
        assert _format_value('price', 25) == '$25'

    def test_format_value_non_monetary(self):
        """Test formatting non-monetary values."""
        assert _format_value('count', 100) == '100'
        assert _format_value('name', 'test') == 'test'
        assert _format_value('details', {'key': 'value'}) == 'See nested table below'

    def test_format_value_edge_cases(self):
        """Test formatting edge cases and invalid inputs."""
        # Test with None key (converted to empty string)
        assert _format_value('', 100) == '100'

        # Test with boolean key (converted to string)
        assert _format_value('true', 100) == '100'

        # Test with None value
        assert _format_value('key', None) == 'None'

        # Test with numeric key (converted to string)
        assert _format_value('123', 100) == '100'

    def test_process_custom_sections(self):
        """Test processing custom sections."""
        custom_data = {
            'usage_patterns': {
                'low': {'requests': 1000},
                'medium': {'requests': 5000},
                'high': {'requests': 10000},
            },
            'cost_factors': ['Requests', 'Duration'],
            'recommendations': {'immediate': ['Optimize now'], 'best_practices': ['Plan ahead']},
        }

        result = _process_custom_sections(custom_data)

        assert '## Detailed Cost Analysis' in result
        assert 'Usage Patterns' in result
        assert 'Cost Factors' in result
        assert 'Recommendations' in result
        assert 'Optimize now' in result
        assert 'Plan ahead' in result

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

    def test_service_info_creation(self):
        """Test creating ServiceInfo objects."""
        service = ServiceInfo(
            name='AWS Lambda',
            estimated_cost='$20.00',
            usage='1M requests per month',
            unit_pricing={'requests': '$0.20 per 1M requests'},
            usage_quantities={'requests': '1M'},
            calculation_details='$0.20 × 1M requests',
            free_tier_info='1M free requests per month',
        )

        assert service.name == 'AWS Lambda'
        assert service.estimated_cost == '$20.00'
        assert service.usage == '1M requests per month'
        assert service.unit_pricing == {'requests': '$0.20 per 1M requests'}
        assert service.usage_quantities == {'requests': '1M'}
        assert service.calculation_details == '$0.20 × 1M requests'
        assert service.free_tier_info == '1M free requests per month'
