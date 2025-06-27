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

"""AWS Cost Analysis Report Generator.

This module provides functionality for generating cost analysis reports for AWS services.
It supports both markdown and CSV output formats with detailed cost breakdowns.
"""

import csv
import io
import re
from awslabs.cost_analysis_mcp_server.helpers import CostAnalysisHelper
from awslabs.cost_analysis_mcp_server.static import COST_REPORT_TEMPLATE
from dataclasses import dataclass
from mcp.server.fastmcp import Context
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# Constants
SKIP_KEYS = {
    'project_name',
    'service_name',
    'description',
    'assumptions',
    'limitations',
    'free_tier_info',
    'conclusion',
    'services',
}

COST_FIELDS = {'monthly_cost', 'cost', 'price', 'one_time_cost', 'total_cost'}

MONETARY_FIELDS = {'cost', 'price', 'rate', 'fee', 'charge', 'amount', 'total'}


@dataclass
class ServiceInfo:
    """Container for service cost information."""

    name: str
    estimated_cost: str
    usage: str
    unit_pricing: Optional[Dict[str, str]] = None
    usage_quantities: Optional[Dict[str, str]] = None
    calculation_details: Optional[str] = None
    free_tier_info: Optional[str] = None


def _extract_services_info(custom_cost_data: Dict) -> Tuple[Dict[str, ServiceInfo], List[str]]:
    """Extract services information from custom cost data."""
    services_info = {}

    # First try to get services directly
    if 'services' in custom_cost_data:
        for name, info in custom_cost_data['services'].items():
            services_info[name] = ServiceInfo(
                name=name,
                estimated_cost=info.get('estimated_cost', 'N/A'),
                usage=info.get('usage', ''),
                unit_pricing=info.get('unit_pricing'),
                usage_quantities=info.get('usage_quantities'),
                calculation_details=info.get('calculation_details'),
                free_tier_info=info.get('free_tier_info'),
            )

    # If no services found, try to extract from custom sections
    if not services_info:
        for key, value in custom_cost_data.items():
            if key in SKIP_KEYS or not isinstance(value, dict):
                continue

            for sub_key, sub_value in value.items():
                if not isinstance(sub_value, dict):
                    continue

                cost = next(
                    (sub_value[field] for field in COST_FIELDS if field in sub_value), None
                )

                if cost is not None:
                    name = sub_key.replace('_', ' ').title()
                    services_info[name] = ServiceInfo(
                        name=name,
                        estimated_cost=f'${cost}',
                        usage=sub_value.get('description', ''),
                    )

    return services_info, list(services_info.keys())


def _create_unit_pricing_details_table(services_info: Dict[str, ServiceInfo]) -> str:
    """Create a detailed unit pricing reference table."""
    # Check if any service has unit pricing information
    has_pricing = False
    for service in services_info.values():
        if isinstance(service.unit_pricing, dict) and service.unit_pricing:
            has_pricing = True
            break

    if not has_pricing:
        return 'No detailed unit pricing information available.'

    table = [
        '| Service | Resource Type | Unit | Price | Free Tier |',
        '|---------|--------------|------|-------|------------|',
    ]

    for service in services_info.values():
        if not isinstance(service.unit_pricing, dict) or not service.unit_pricing:
            continue

        for price_type, price_value in service.unit_pricing.items():
            if not isinstance(price_value, str):
                continue

            resource_type = price_type.replace('_', ' ').title()

            # Parse unit and price
            unit = '1 unit'
            price = price_value
            if 'per' in price_value:
                parts = price_value.split('per', 1)
                if len(parts) == 2:
                    price, unit = parts
                    price = price.strip()
                    unit = unit.strip()

            # Standardize units
            unit = unit.replace('1K', '1,000').replace('1M', '1,000,000')
            unit = unit.replace('units', resource_type.lower())

            # Get free tier info with safe fallback
            free_tier = service.free_tier_info if hasattr(service, 'free_tier_info') else None

            table.append(
                f'| {service.name} | {resource_type} | {unit} | {price} | {free_tier or "None"} |'
            )

    return '\n'.join(table)


def _parse_cost_value(cost_str: str) -> Tuple[float, float]:
    """Parse cost string into min and max values."""
    if not isinstance(cost_str, str):
        return 0.0, 0.0

    # Try to match "$X-Y" pattern
    if match := re.search(r'\$(\d+)-(\d+)', cost_str):
        return float(match.group(1)), float(match.group(2))

    # Try to match "$X" pattern
    if match := re.search(r'\$(\d+(\.\d+)?)', cost_str):
        value = float(match.group(1))
        return value, value

    return 0.0, 0.0


def _create_cost_calculation_table(
    services_info: Dict[str, ServiceInfo],
) -> Tuple[str, float, float, Optional[float]]:
    """Create the cost calculation table and extract total min/max costs."""
    if not services_info:
        return 'No cost calculation details available.', 0.0, 0.0, None

    table = [
        '| Service | Usage | Calculation | Monthly Cost |',
        '|---------|-------|-------------|-------------|',
    ]

    total_min = total_max = 0.0

    for service in services_info.values():
        # Format usage details
        usage_details = service.usage
        if service.usage_quantities:
            quantities = [
                f'{k.replace("_", " ").title()}: {v}' for k, v in service.usage_quantities.items()
            ]
            if quantities:
                usage_details = f'{usage_details} ({", ".join(quantities)})'

        # Add table row
        table.append(
            f'| {service.name} | {usage_details} | '
            f'{service.calculation_details or "N/A"} | {service.estimated_cost} |'
        )

        # Update totals
        min_cost, max_cost = _parse_cost_value(service.estimated_cost)
        total_min += min_cost
        total_max += max_cost

    # Add total row if we have costs
    if total_min > 0 or total_max > 0:
        if total_min == total_max:
            table.append(
                f'| **Total** | **All services** | **Sum of all calculations** | '
                f'**${total_min:.2f}/month** |'
            )
            base_cost = total_min
        else:
            table.append(
                f'| **Total** | **All services** | **Sum of all calculations** | '
                f'**${total_min:.2f}-{total_max:.2f}/month** |'
            )
            base_cost = (total_min + total_max) / 2
    else:
        base_cost = None

    return '\n'.join(table), total_min, total_max, base_cost


def _create_unit_pricing_table(
    services_info: Dict,
) -> Tuple[str, float, float, Optional[float]]:
    """Legacy function to maintain backward compatibility."""
    # This function is kept for backward compatibility
    # It now delegates to the new functions

    unit_pricing_details = _create_unit_pricing_details_table(services_info)
    (
        cost_calculation_table,
        total_min,
        total_max,
        base_cost,
    ) = _create_cost_calculation_table(services_info)

    # Combine both tables for backward compatibility
    combined_table = unit_pricing_details + '\n\n### Cost Calculation\n\n' + cost_calculation_table

    return combined_table, total_min, total_max, base_cost


def _create_free_tier_info(custom_cost_data: Dict, services_info: Dict[str, ServiceInfo]) -> str:
    """Create the free tier information section."""
    free_tier_entries = []

    # Collect free tier info from services
    for service in services_info.values():
        if service.free_tier_info:
            free_tier_entries.append(f'- **{service.name}**: {service.free_tier_info}')

    # If no service-specific info found, check custom data
    if not free_tier_entries:
        if 'free_tier_info' in custom_cost_data:
            return custom_cost_data['free_tier_info']

        # Search for free tier mentions in custom data
        for key, value in custom_cost_data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str) and 'free' in sub_value.lower():
                        free_tier_entries.append(
                            f'- **{key.replace("_", " ").title()}**: {sub_value}'
                        )

    # Return appropriate message based on findings
    if free_tier_entries:
        return 'Free tier information by service:\n' + '\n'.join(free_tier_entries)

    return 'AWS offers a Free Tier for many services. Check the AWS Free Tier page for current offers and limitations.'


def _create_usage_cost_table(services_info: Dict[str, ServiceInfo]) -> str:
    """Create the usage cost table with different usage tiers."""
    if not services_info:
        return 'Cost scaling information not available. See Custom Analysis Data section for detailed cost information.'

    USAGE_TIERS = {
        'Low': 0.5,  # 50% of estimated
        'Medium': 1.0,  # 100% of estimated
        'High': 2.0,  # 200% of estimated
    }

    table = [
        '| Service | Low Usage | Medium Usage | High Usage |',
        '|---------|-----------|--------------|------------|',
    ]

    for service in services_info.values():
        min_cost, max_cost = _parse_cost_value(service.estimated_cost)

        if min_cost == 0 and max_cost == 0:
            table.append(f'| {service.name} | Varies | Varies | Varies |')
            continue

        # Use average if range provided
        base_cost = max_cost if min_cost == max_cost else (min_cost + max_cost) / 2

        costs = {
            tier: f'${int(base_cost * multiplier)}/month'
            for tier, multiplier in USAGE_TIERS.items()
        }

        table.append(f'| {service.name} | {costs["Low"]} | {costs["Medium"]} | {costs["High"]} |')

    return '\n'.join(table)


def _extract_key_factors(
    custom_cost_data: Dict, services_info: Dict[str, ServiceInfo]
) -> List[str]:
    """Extract key cost factors from services and custom data."""
    DEFAULT_FACTORS = [
        '- Request volume and frequency',
        '- Data storage requirements',
        '- Data transfer between services',
        '- Compute resources utilized',
    ]

    # Extract from services
    factors = [
        f'- **{service.name}**: {service.usage}'
        for service in services_info.values()
        if service.usage
    ]

    # If no service factors found, try custom sections
    if not factors:
        factors = [
            f'- **{key.replace("_", " ").title()}**: {value["description"]}'
            for key, value in custom_cost_data.items()
            if isinstance(value, dict) and 'description' in value
        ]

    return factors if factors else DEFAULT_FACTORS


def _calculate_base_cost(
    custom_cost_data: Dict,
    services_info: Dict[str, ServiceInfo],
    total_min: float = 0,
    total_max: float = 0,
) -> Optional[float]:
    """Calculate the base cost for projections using multiple strategies."""
    # Strategy 1: Use min-max values from unit pricing
    if total_min > 0 and total_max > 0:
        return (total_min + total_max) / 2

    # Strategy 2: Look for total_monthly_cost in custom data
    for value in custom_cost_data.values():
        if isinstance(value, dict) and 'total_monthly_cost' in value:
            return float(value['total_monthly_cost'])

    # Strategy 3: Calculate from service costs
    if services_info:
        total = 0
        count = 0

        for service in services_info.values():
            min_cost, max_cost = _parse_cost_value(service.estimated_cost)
            if min_cost > 0 or max_cost > 0:
                total += max_cost if min_cost == max_cost else (min_cost + max_cost) / 2
                count += 1

        if count > 0:
            return total

    # Strategy 4: Extract from nested pricing data
    total = 0
    count = 0

    def extract_costs(data: Dict) -> Tuple[float, int]:
        """Recursively extract costs from nested dictionaries."""
        subtotal = 0
        subcount = 0

        for key, value in data.items():
            if isinstance(value, dict):
                if 'pricing' in value and isinstance(value['pricing'], dict):
                    sub_total, sub_count = extract_costs(value['pricing'])
                    subtotal += sub_total
                    subcount += sub_count

                for field_name, field_value in value.items():
                    if isinstance(field_value, (int, float)) and (
                        'price' in field_name.lower() or 'cost' in field_name.lower()
                    ):
                        subtotal += float(field_value)
                        subcount += 1

        return subtotal, subcount

    total, count = extract_costs(custom_cost_data)
    return total if count > 0 else None


def _generate_projected_costs_table(
    base_cost: Optional[float], services_info: Dict[str, ServiceInfo]
) -> str:
    """Generate the projected costs table with growth patterns."""
    if base_cost is None:
        return 'Insufficient data to generate cost projections. See Custom Analysis Data section for available cost information.'

    GROWTH_RATES = {
        'Steady': 1.0,  # No monthly growth
        'Moderate': 1.05,  # 5% monthly growth
        'Rapid': 1.1,  # 10% monthly growth
    }

    MONTHS = {
        1: 0,  # base_cost * (rate^0)
        3: 2,  # base_cost * (rate^2)
        6: 5,  # base_cost * (rate^5)
        12: 11,  # base_cost * (rate^11)
    }

    # Generate base cost explanation
    sections = ['Base monthly cost calculation:\n']

    if services_info:
        sections.extend(['| Service | Monthly Cost |', '|---------|-------------|'])

        for service in services_info.values():
            min_cost, max_cost = _parse_cost_value(service.estimated_cost)
            if min_cost > 0 or max_cost > 0:
                cost = max_cost if min_cost == max_cost else (min_cost + max_cost) / 2
                sections.append(f'| {service.name} | ${cost:.2f} |')

        sections.extend([f'| **Total Monthly Cost** | **${int(base_cost)}** |', ''])

    # Generate growth projections
    sections.extend(
        [
            '| Growth Pattern | Month 1 | Month 3 | Month 6 | Month 12 |',
            '|---------------|---------|---------|---------|----------|',
        ]
    )

    for pattern, rate in GROWTH_RATES.items():
        costs = [
            f'${int(base_cost * (rate**power))}/mo'
            for power in [MONTHS[month] for month in [1, 3, 6, 12]]
        ]
        sections.append(f'| {pattern} | {" | ".join(costs)} |')

    # Add growth rate explanations
    sections.extend(
        [
            '',
            *[
                f'* {pattern}: {int((rate - 1) * 100)}% monthly growth ({rate}x)'
                if rate > 1
                else f'* {pattern}: No monthly growth ({rate}x)'
                for pattern, rate in GROWTH_RATES.items()
            ],
        ]
    )

    return '\n'.join(sections)


def _process_recommendations(
    custom_cost_data: Dict, service_names: List[str]
) -> Tuple[List[str], List[str]]:
    """Process recommendations for the report."""

    def extract_items(items: Any) -> List[str]:
        """Extract items into a list of strings."""
        if isinstance(items, (list, tuple)):
            return [str(item) for item in items]
        elif items:
            return [str(items)]
        return []

    immediate_actions = []
    best_practices = []

    if recommendations := custom_cost_data.get('recommendations'):
        if isinstance(recommendations, dict):
            # Extract recommendations regardless of prompt presence
            immediate_actions = extract_items(recommendations.get('immediate', []))
            best_practices = extract_items(recommendations.get('best_practices', []))

    # If no recommendations found, generate from Well-Architected Framework
    if not immediate_actions and not best_practices:
        wa_recommendations = CostAnalysisHelper.generate_well_architected_recommendations(
            service_names
        )
        immediate_actions = wa_recommendations['immediate']
        best_practices = wa_recommendations['best_practices']

    return immediate_actions, best_practices


def _format_value(key: Any, value: Any) -> str:
    """Format a value based on its type and key name."""
    try:
        # Ensure key is a string and handle None case
        key_str = str(key).lower() if key is not None else ''

        if isinstance(value, (int, float)):
            # Check if the field name suggests it's a monetary value
            is_total = key_str == 'total'
            is_monetary = is_total or any(
                term in key_str for term in MONETARY_FIELDS if isinstance(term, str)
            )

            if is_total:
                return f'**${value}**'
            elif is_monetary:
                return f'${value}'
            return str(value)

        elif isinstance(value, dict):
            return 'See nested table below'

        return str(value)
    except Exception:
        # Fallback to safe string conversion if any error occurs
        return str(value)


def _process_custom_sections(custom_cost_data: Dict) -> str:
    """Process custom sections for the report."""
    if not custom_cost_data:
        return ''

    SKIP_KEYS = {
        'project_name',
        'service_name',
        'description',
        'assumptions',
        'limitations',
        'free_tier_info',
        'conclusion',
        'services',
        'pricing_data',
        'pricing_data_reference',
    }

    def format_list_as_bullets(items: Union[List, str]) -> str:
        """Format a list or string as bullet points."""
        if isinstance(items, str):
            items = items.split('\n')
        return ''.join(f'- {item.strip()}\n' for item in items if item.strip())

    def create_table(data: Dict, nested: bool = False) -> str:
        """Create a markdown table from dictionary data."""
        table = ['| Key | Value |', '|-----|-------|']

        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()
            formatted_value = _format_value(key, value)
            table.append(f'| {formatted_key} | {formatted_value} |')

        return '\n'.join(table)

    sections = ['## Detailed Cost Analysis\n\n']

    for key, value in custom_cost_data.items():
        if key in SKIP_KEYS:
            continue

        section_title = key.replace('_', ' ').title()
        sections.append(f'### {section_title}\n\n')

        # Handle different section types
        if key in ['assumptions', 'exclusions']:
            sections.append(format_list_as_bullets(value))

        elif key.lower() == 'recommendations' and isinstance(value, dict):
            if immediate := value.get('immediate'):
                sections.extend(['#### Immediate Actions\n\n', format_list_as_bullets(immediate)])
            if best_practices := value.get('best_practices'):
                sections.extend(
                    ['#### Best Practices\n\n', format_list_as_bullets(best_practices)]
                )

        elif isinstance(value, dict):
            sections.append(create_table(value))

            # Handle nested tables
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    sections.extend(
                        [
                            f'\n#### {sub_key.replace("_", " ").title()}\n\n',
                            create_table(sub_value, nested=True),
                        ]
                    )

        elif isinstance(value, list):
            sections.append(format_list_as_bullets(value))

        else:
            sections.append(f'{value}\n\n')

        sections.append('\n')

    return ''.join(sections)


async def _generate_custom_data_report(
    custom_cost_data: Dict,
    output_file: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> str:
    """Generate a report using custom cost data."""
    # Get project name or use default
    project_name = custom_cost_data.get('project_name', 'AWS Project')

    # Start with the template
    report = COST_REPORT_TEMPLATE

    # Replace service_name with project name
    report = report.replace('{service_name}', project_name)

    # Get project description or use default
    description = custom_cost_data.get('description', 'This project uses multiple AWS services.')
    report = report.replace('{service_description}', description)

    # Add pricing model information
    pricing_model = custom_cost_data.get('pricing_model', 'ON DEMAND')
    pricing_model_section = 'This cost analysis is based on the following pricing model:\n'
    pricing_model_section += f'- **{pricing_model}** pricing'

    # Add common description for ON DEMAND pricing
    if pricing_model.upper() == 'ON DEMAND':
        pricing_model_section += ' (pay-as-you-go)'

    pricing_model_section += (
        '\n- Standard service configurations without reserved capacity or savings plans\n'
    )
    pricing_model_section += '- No caching or optimization techniques applied'

    # Replace pricing model section in template
    report = report.replace(
        'This cost analysis is based on the following pricing model:\n- **ON DEMAND** pricing (pay-as-you-go) unless otherwise specified\n- Standard service configurations without reserved capacity or savings plans\n- No caching or optimization techniques applied',
        pricing_model_section,
    )

    # Add assumptions section
    default_assumptions = [
        'Standard configuration for all services',
        'Default usage patterns based on typical workloads',
        'No reserved instances or savings plans applied',
    ]

    assumptions = custom_cost_data.get('assumptions', default_assumptions)
    assumptions_list = []

    if assumptions is None:
        assumptions = default_assumptions

    if isinstance(assumptions, str):
        # Handle case where assumptions is a string
        for line in assumptions.split('\n'):
            if line and line.strip():
                assumptions_list.append(f'- {line.strip()}')
    elif isinstance(assumptions, list):
        # Handle case where assumptions is a list
        for assumption in assumptions:
            if assumption is not None:
                assumptions_list.append(f'- {str(assumption).strip()}')
    report = report.replace('{assumptions_section}', '\n'.join(assumptions_list))

    # Add limitations and exclusions section
    default_limitations = [
        'This analysis only includes confirmed compatible services and features',
        'Database costs may not be included if compatibility is uncertain',
        'Only the latest foundation models are considered for comparison',
    ]

    # Use exclusions if provided, otherwise use limitations or default
    if 'exclusions' in custom_cost_data and custom_cost_data['exclusions']:
        limitations = custom_cost_data['exclusions']
    elif 'limitations' in custom_cost_data and custom_cost_data['limitations']:
        limitations = custom_cost_data['limitations']
    else:
        limitations = default_limitations

    limitations_list = []
    if isinstance(limitations, str):
        # Handle case where limitations is a string
        for line in limitations.split('\n'):
            if line.strip():
                limitations_list.append(f'- {line.strip()}')
    elif isinstance(limitations, list):
        # Handle case where limitations is a list
        for limitation in limitations:
            limitations_list.append(f'- {limitation}')
    report = report.replace('{limitations_section}', '\n'.join(limitations_list))

    # Extract services information
    services_info, service_names = _extract_services_info(custom_cost_data)

    # Create unit pricing details table
    unit_pricing_details_table = _create_unit_pricing_details_table(services_info)
    report = report.replace('{unit_pricing_details_table}', unit_pricing_details_table)

    # Create cost calculation table
    (
        cost_calculation_table,
        total_min,
        total_max,
        initial_base_cost,
    ) = _create_cost_calculation_table(services_info)
    report = report.replace('{cost_calculation_table}', cost_calculation_table)

    # Free tier information
    free_tier_info = _create_free_tier_info(custom_cost_data, services_info)
    report = report.replace('{free_tier_info}', free_tier_info)

    # Usage cost table
    usage_cost_table = _create_usage_cost_table(services_info)
    report = report.replace('{usage_cost_table}', usage_cost_table)

    # Key cost factors
    key_factors = _extract_key_factors(custom_cost_data, services_info)
    report = report.replace('{key_cost_factors}', '\n'.join(key_factors))

    # Projected costs over time
    base_cost = _calculate_base_cost(custom_cost_data, services_info, total_min, total_max)
    projected_costs_table = _generate_projected_costs_table(base_cost, services_info)
    report = report.replace('{projected_costs}', projected_costs_table)

    # Recommendations
    immediate_actions, best_practices = _process_recommendations(custom_cost_data, service_names)

    # Replace recommendation placeholders
    if isinstance(immediate_actions, list) and len(immediate_actions) >= 3:
        report = report.replace('{recommendation_1}', str(immediate_actions[0]))
        report = report.replace('{recommendation_2}', str(immediate_actions[1]))
        report = report.replace('{recommendation_3}', str(immediate_actions[2]))
    else:
        report = report.replace(
            '- {recommendation_1}\n- {recommendation_2}\n- {recommendation_3}',
            '- Optimize resource usage based on actual requirements\n'
            '- Implement cost allocation tags\n'
            '- Set up AWS Budgets alerts',
        )

    if isinstance(best_practices, list) and len(best_practices) >= 3:
        report = report.replace('{best_practice_1}', str(best_practices[0]))
        report = report.replace('{best_practice_2}', str(best_practices[1]))
        report = report.replace('{best_practice_3}', str(best_practices[2]))
    else:
        report = report.replace(
            '- {best_practice_1}\n- {best_practice_2}\n- {best_practice_3}',
            '- Regularly review costs with AWS Cost Explorer\n'
            '- Consider reserved capacity for predictable workloads\n'
            '- Implement automated scaling based on demand',
        )

    # Process custom sections
    custom_analysis = _process_custom_sections(custom_cost_data)
    report = report.replace('{custom_analysis_sections}', str(custom_analysis))

    # Conclusion
    conclusion = custom_cost_data.get(
        'conclusion',
        f'By following the recommendations in this report, you can optimize your {project_name} costs '
        f'while maintaining performance and reliability. Regular monitoring and adjustment of your '
        f'usage patterns will help ensure cost efficiency as your workload evolves.',
    )
    report = report.replace('{conclusion}', conclusion)

    # Write to file if requested
    if output_file:
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report)
            if ctx:
                await ctx.info(f'Report saved to {output_file}')
        except Exception as e:
            if ctx:
                await ctx.error(f'Failed to write report to file: {e}')

    return report


async def _generate_pricing_data_report(
    pricing_data: Dict[str, Any],
    service_name: str,
    related_services: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    ctx: Optional[Context] = None,
    params: Optional[Dict] = None,
    format: str = 'markdown',
) -> str:
    """Generate a report using pricing data."""
    # Parse the pricing data with related services context
    pricing_structure = CostAnalysisHelper.parse_pricing_data(
        pricing_data, service_name, related_services
    )

    # Generate cost tables
    cost_tables = CostAnalysisHelper.generate_cost_table(pricing_structure)

    # Start with the template
    report = COST_REPORT_TEMPLATE

    # Replace service name
    report = report.replace('{service_name}', service_name.title())

    # Replace service description
    report = report.replace('{service_description}', pricing_structure['service_description'])

    # Add pricing model information
    pricing_model = 'ON DEMAND'
    if params and 'pricing_model' in params and params['pricing_model']:
        pricing_model = params['pricing_model']

    pricing_model_section = 'This cost analysis is based on the following pricing model:\n'
    pricing_model_section += f'- **{pricing_model}** pricing'

    # Add common description for ON DEMAND pricing
    if pricing_model.upper() == 'ON DEMAND':
        pricing_model_section += ' (pay-as-you-go)'

    pricing_model_section += (
        '\n- Standard service configurations without reserved capacity or savings plans\n'
    )
    pricing_model_section += '- No caching or optimization techniques applied'

    # Replace pricing model section in template
    report = report.replace(
        'This cost analysis is based on the following pricing model:\n- **ON DEMAND** pricing (pay-as-you-go) unless otherwise specified\n- Standard service configurations without reserved capacity or savings plans\n- No caching or optimization techniques applied',
        pricing_model_section,
    )

    # Add assumptions section
    assumptions_list = '\n'.join(
        [f'- {assumption}' for assumption in pricing_structure['assumptions']]
    )
    report = report.replace('{assumptions_section}', assumptions_list)

    # Add limitations and exclusions section
    default_limitations = [
        f'This analysis only includes confirmed pricing information for {service_name}',
        'Database compatibility information is only included when explicitly confirmed',
        'Only the latest foundation models are considered for comparison',
        'Providing less information is better than giving incorrect information',
    ]

    # Add custom exclusions if provided
    if params and 'exclusions' in params and params['exclusions']:
        limitations = params['exclusions'] + default_limitations
    else:
        limitations = default_limitations

    limitations_list = '\n'.join([f'- {limitation}' for limitation in limitations])
    report = report.replace('{limitations_section}', limitations_list)

    # Replace unit pricing details table
    report = report.replace(
        '{unit_pricing_details_table}',
        cost_tables['unit_pricing_details_table']
        if 'unit_pricing_details_table' in cost_tables
        else 'No detailed unit pricing information available.',
    )

    # Replace cost calculation table
    report = report.replace(
        '{cost_calculation_table}',
        cost_tables['cost_calculation_table']
        if 'cost_calculation_table' in cost_tables
        else 'No cost calculation details available.',
    )

    # Replace free tier info
    report = report.replace('{free_tier_info}', pricing_structure['free_tier'])

    # Replace usage cost table
    report = report.replace('{usage_cost_table}', cost_tables['usage_cost_table'])

    # Replace key cost factors
    key_factors = '\n'.join([f'- {factor}' for factor in pricing_structure['key_cost_factors']])
    report = report.replace('{key_cost_factors}', key_factors)

    # Replace projected costs
    report = report.replace('{projected_costs}', cost_tables['projected_costs_table'])

    # Replace recommendations
    if len(pricing_structure['recommendations']['immediate']) >= 3:
        report = report.replace(
            '{recommendation_1}', pricing_structure['recommendations']['immediate'][0]
        )
        report = report.replace(
            '{recommendation_2}', pricing_structure['recommendations']['immediate'][1]
        )
        report = report.replace(
            '{recommendation_3}', pricing_structure['recommendations']['immediate'][2]
        )

    if len(pricing_structure['recommendations']['best_practices']) >= 3:
        report = report.replace(
            '{best_practice_1}',
            pricing_structure['recommendations']['best_practices'][0],
        )
        report = report.replace(
            '{best_practice_2}',
            pricing_structure['recommendations']['best_practices'][1],
        )
        report = report.replace(
            '{best_practice_3}',
            pricing_structure['recommendations']['best_practices'][2],
        )

    # Replace conclusion
    conclusion = f'By following the recommendations in this report, you can optimize your {service_name} costs while maintaining performance and reliability. '
    conclusion += 'Regular monitoring and adjustment of your usage patterns will help ensure cost efficiency as your workload evolves.'
    report = report.replace('{conclusion}', conclusion)

    # Write to file if requested
    if output_file:
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report)
            if ctx:
                await ctx.info(f'Report saved to {output_file}')
        except Exception as e:
            if ctx:
                await ctx.error(f'Failed to write report to file: {e}')

    return report


async def _generate_csv_report(
    cost_data: Dict[str, Any],
    output_file: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> str:
    """Generate a CSV format cost analysis report.

    Args:
        cost_data: Dictionary containing cost analysis data
        output_file: Optional path to save the CSV file
        ctx: Optional MCP context for logging

    Returns:
        The generated report in CSV format
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Extract services information
    services_info, service_names = _extract_services_info(cost_data)

    # Write header
    writer.writerow(['AWS Cost Analysis Report'])
    writer.writerow([])

    # Project Information
    writer.writerow(['Project Information'])
    writer.writerow(['Name', cost_data.get('project_name', 'AWS Project')])
    writer.writerow(['Pricing Model', cost_data.get('pricing_model', 'ON DEMAND')])
    writer.writerow([])

    # Assumptions
    writer.writerow(['Assumptions'])
    assumptions = cost_data.get(
        'assumptions',
        [
            'Standard configuration for all services',
            'Default usage patterns based on typical workloads',
            'No reserved instances or savings plans applied',
        ],
    )
    if isinstance(assumptions, str):
        assumptions = assumptions.split('\n')
    for assumption in assumptions:
        writer.writerow(['', assumption.strip()])
    writer.writerow([])

    # Unit Pricing
    writer.writerow(['Unit Pricing'])
    writer.writerow(['Service', 'Resource Type', 'Unit', 'Price', 'Free Tier'])
    for service_name, service_info in services_info.items():
        if not service_info.unit_pricing:
            continue

        free_tier_info = service_info.free_tier_info or 'None'

        for price_type, price_value in service_info.unit_pricing.items():
            resource_type = price_type.replace('_', ' ').title()

            # Extract unit from price value
            unit = '1 unit'
            if 'per' in price_value:
                parts = price_value.split('per')
                if len(parts) > 1:
                    unit = parts[1].strip()

            # Standardize common units
            if '1K' in price_value or '1k' in price_value:
                unit = '1,000 units'
            if '1M' in price_value or '1m' in price_value:
                unit = '1,000,000 units'

            # Replace generic "units" with resource type
            unit = unit.replace('units', resource_type.lower())

            # Extract price
            price = price_value
            if 'per' in price:
                price = price.split('per')[0].strip()

            writer.writerow([service_name, resource_type, unit, price, free_tier_info])
    writer.writerow([])

    # Cost Calculations
    writer.writerow(['Cost Calculations'])
    writer.writerow(['Service', 'Usage', 'Calculation', 'Monthly Cost'])
    total_cost = 0.0
    for service_name, service_info in services_info.items():
        usage = service_info.usage or 'N/A'
        calculation = service_info.calculation_details or 'N/A'
        cost = service_info.estimated_cost or 'N/A'

        # Add usage quantities if available
        if service_info.usage_quantities:
            quantities = []
            for usage_type, usage_value in service_info.usage_quantities.items():
                formatted_type = usage_type.replace('_', ' ').title()
                quantities.append(f'{formatted_type}: {usage_value}')
            if quantities:
                usage = f'{usage} ({", ".join(quantities)})'

        writer.writerow([service_name, usage, calculation, cost])

        # Extract cost value for total
        if isinstance(cost, str):
            cost_match = re.search(r'\$(\d+(\.\d+)?)', cost)
            if cost_match:
                total_cost += float(cost_match.group(1))

    if total_cost > 0:
        writer.writerow(
            ['Total', 'All services', 'Sum of all calculations', f'${total_cost:.2f}/month']
        )
    writer.writerow([])

    # Recommendations
    immediate_actions, best_practices = _process_recommendations(cost_data, service_names)

    writer.writerow(['Immediate Actions'])
    for action in immediate_actions:
        writer.writerow(['', action])
    writer.writerow([])

    writer.writerow(['Best Practices'])
    for practice in best_practices:
        writer.writerow(['', practice])

    # Get the final CSV content
    csv_content = output.getvalue()
    output.close()

    # Write to file if requested
    if output_file:
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(csv_content)
            if ctx:
                await ctx.info(f'CSV report saved to {output_file}')
        except Exception as e:
            if ctx:
                await ctx.error(f'Failed to write CSV report to file: {e}')

    return csv_content


async def generate_cost_report(
    pricing_data: Dict[str, Any],  # Required: Raw pricing data from AWS
    service_name: str,  # Required: Primary service name
    # Core parameters (simple, commonly used)
    related_services: Optional[List[str]] = None,
    pricing_model: str = 'ON DEMAND',
    assumptions: Optional[List[str]] = None,
    exclusions: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    # Advanced parameters (grouped in a dictionary for complex use cases)
    detailed_cost_data: Optional[Dict[str, Any]] = None,
    ctx: Optional[Context] = None,
    format: str = 'markdown',  # Output format ('markdown' or 'csv')
) -> str:
    """Main entry point for generating cost analysis reports.

    This function generates comprehensive cost analysis reports based on AWS pricing data,
    with optional detailed cost information for more complex scenarios.

    Args:
        pricing_data: Raw pricing data from AWS pricing tools (required)
        service_name: Name of the primary service (required)
        related_services: List of related services to include in the analysis
        pricing_model: The pricing model used (default: "ON DEMAND")
        assumptions: List of assumptions made for the cost analysis
        exclusions: List of items excluded from the cost analysis
        output_file: Path to save the report to a file
        detailed_cost_data: Dictionary containing detailed cost information for complex scenarios
            This can include:
            - services: Dictionary mapping service names to their detailed cost information
                - unit_pricing: Dictionary mapping price types to their values
                - usage_quantities: Dictionary mapping usage types to their quantities
                - calculation_details: String showing the calculation breakdown
        ctx: MCP context for logging and error handling
        format: Output format for the cost analysis report
            - Supported values: "markdown" (default) or "csv"
            - markdown: Generates a well-formatted markdown report with:
                * Tables for pricing and calculations
                * Sections for assumptions and recommendations
                * Rich text formatting for better readability
            - csv: Generates a comma-separated values report with:
                * Structured data format for spreadsheet compatibility
                * Headers for each data section
                * Raw values without text formatting
            - Example: format="csv" for spreadsheet-compatible output

    Returns:
        The generated report in markdown format
    """
    try:
        # Create a consolidated cost data dictionary
        cost_data = {
            'project_name': service_name,
            'pricing_model': pricing_model,
        }

        # Add assumptions if provided
        if assumptions:
            cost_data['assumptions'] = '\n'.join(assumptions)

        # Add exclusions if provided
        if exclusions:
            cost_data['exclusions'] = '\n'.join(exclusions)

        # Merge detailed_cost_data if provided
        if detailed_cost_data:
            for key, value in detailed_cost_data.items():
                cost_data[key] = value

        # Store reference to the original pricing data
        cost_data['pricing_data_reference'] = str(pricing_data)

        # Validate format parameter
        if format not in ['markdown', 'csv']:
            if ctx:
                await ctx.warning(f"Invalid format '{format}'. Using 'markdown' as default.")
            format = 'markdown'

        # Generate the report using the consolidated cost data
        if format == 'csv':
            # For CSV format, use the CSV report generator
            return await _generate_csv_report(cost_data, output_file, ctx)
        else:
            # For markdown format, use the appropriate report generator based on data
            if 'services' in cost_data:
                # If services are defined in detailed_cost_data, use the custom data report generator
                return await _generate_custom_data_report(cost_data, output_file, ctx)
            else:
                # Otherwise, use the pricing data report generator
                params = {
                    'pricing_model': pricing_model,
                    'assumptions': assumptions,
                    'exclusions': exclusions,
                }

                return await _generate_pricing_data_report(
                    pricing_data=pricing_data,
                    service_name=service_name,
                    related_services=related_services,
                    output_file=output_file,
                    ctx=ctx,
                    params=params,
                    format=format,
                )
    except Exception as e:
        if ctx:
            await ctx.error(f'Error generating cost report: {str(e)}')
        return f'Error generating cost report: {str(e)}'
