"""awslabs Cost Analysis Report Generator.

This module provides functionality for generating cost analysis reports for AWS services.
"""

import re
from awslabs.cost_analysis_mcp_server.helpers import CostAnalysisHelper
from awslabs.cost_analysis_mcp_server.static import COST_REPORT_TEMPLATE
from mcp.server.fastmcp import Context
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _extract_services_info(custom_cost_data: Dict) -> Tuple[Dict, List[str]]:
    """Extract services information from custom cost data."""
    services_info = custom_cost_data.get("services", {})

    # If no services are provided, try to extract them from custom sections
    if not services_info:
        extracted_services = {}

        # Look for service entries with costs in the custom data
        for key, value in custom_cost_data.items():
            # Skip keys we've already processed
            if key in [
                "project_name",
                "service_name",
                "description",
                "assumptions",
                "limitations",
                "free_tier_info",
                "conclusion",
                "services",
            ]:
                continue

            if isinstance(value, dict):
                # This could be a flow or section with services
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        # Look for cost fields
                        cost = None
                        description = ""

                        # Try to find cost information
                        for cost_field in [
                            "monthly_cost",
                            "cost",
                            "price",
                            "one_time_cost",
                            "total_cost",
                        ]:
                            if cost_field in sub_value:
                                cost = sub_value[cost_field]
                                break

                        # Look for description
                        if "description" in sub_value:
                            description = sub_value["description"]

                        # If we found a cost, add this as a service
                        if cost is not None:
                            service_name = sub_key.replace("_", " ").title()
                            extracted_services[service_name] = {
                                "estimated_cost": f"${cost}",
                                "usage": description,
                            }

        # Use extracted services if we found any
        if extracted_services:
            services_info = extracted_services

    service_names = list(services_info.keys())
    return services_info, service_names


def _create_unit_pricing_details_table(services_info: Dict) -> str:
    """Create a detailed unit pricing reference table."""
    if not services_info:
        return "No unit pricing details available."

    # Check if any service has detailed pricing information
    has_detailed_pricing = any(
        "unit_pricing" in info for info in services_info.values()
    )

    if not has_detailed_pricing:
        return "No detailed unit pricing information available."

    # Create the detailed unit pricing table
    unit_pricing_details_table = (
        "| Service | Resource Type | Unit | Price | Free Tier |\n"
        "|---------|--------------|------|-------|------------|\n"
    )

    for service, info in services_info.items():
        # Skip services without unit pricing information
        if "unit_pricing" not in info or not isinstance(info["unit_pricing"], dict):
            continue

        free_tier_info = info.get("free_tier_info", "None")

        # Process each unit pricing type
        for price_type, price_value in info["unit_pricing"].items():
            # Format the resource type
            resource_type = price_type.replace("_", " ").title()

            # Extract unit from price value if possible
            unit = "1 unit"
            if "per" in price_value:
                parts = price_value.split("per")
                if len(parts) > 1:
                    unit = parts[1].strip()

            # For common units, standardize the format
            if "1K" in price_value or "1k" in price_value:
                unit = "1,000 units"
            if "1M" in price_value or "1m" in price_value:
                unit = "1,000,000 units"

            # Replace generic "units" with the actual resource type
            unit = unit.replace("units", resource_type.lower())

            # Extract just the price value
            price = price_value
            if "per" in price:
                price = price.split("per")[0].strip()

            unit_pricing_details_table += f"| {service} | {resource_type} | {unit} | {price} | {free_tier_info} |\n"

    return unit_pricing_details_table


def _create_cost_calculation_table(
    services_info: Dict,
) -> Tuple[str, float, float, Optional[float]]:
    """Create the cost calculation table and extract total min/max costs."""
    total_min = 0.0
    total_max = 0.0
    base_cost = None

    if not services_info:
        return "No cost calculation details available.", total_min, total_max, base_cost

    # Create the cost calculation table
    cost_calculation_table = (
        "| Service | Usage | Calculation | Monthly Cost |\n"
        "|---------|-------|-------------|-------------|\n"
    )

    for service, info in services_info.items():
        usage = info.get("usage", "N/A")
        cost = info.get("estimated_cost", "N/A")

        # Format usage with quantities if available
        usage_details = usage
        if "usage_quantities" in info and isinstance(info["usage_quantities"], dict):
            quantities = []
            for usage_type, usage_value in info["usage_quantities"].items():
                formatted_type = usage_type.replace("_", " ").title()
                quantities.append(f"{formatted_type}: {usage_value}")

            if quantities:
                usage_details = f'{usage} ({", ".join(quantities)})'

        # Get calculation details
        calculation = info.get("calculation_details", "N/A")

        cost_calculation_table += (
            f"| {service} | {usage_details} | {calculation} | {cost} |\n"
        )

        # Try to extract min-max values from cost strings like "$150-200/month"
        if isinstance(cost, str):
            cost_match = re.search(r"\$(\d+)-(\d+)", cost)
            if cost_match:
                total_min += int(cost_match.group(1))
                total_max += int(cost_match.group(2))
            else:
                # Try to match patterns like "$40.00" or "$40"
                cost_match = re.search(r"\$(\d+(\.\d+)?)", cost)
                if cost_match:
                    cost_val = float(cost_match.group(1))
                    total_min += cost_val
                    total_max += cost_val

    # Add total row
    if total_min > 0.0 or total_max > 0.0:
        if total_min == total_max:
            cost_calculation_table += f"| **Total** | **All services** | **Sum of all calculations** | **${total_min:.2f}/month** |\n"
            base_cost = total_min
        else:
            cost_calculation_table += f"| **Total** | **All services** | **Sum of all calculations** | **${total_min:.2f}-{total_max:.2f}/month** |\n"
            base_cost = (total_min + total_max) / 2

    return cost_calculation_table, total_min, total_max, base_cost


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
    combined_table = (
        unit_pricing_details + "\n\n### Cost Calculation\n\n" + cost_calculation_table
    )

    return combined_table, total_min, total_max, base_cost


def _create_free_tier_info(custom_cost_data: Dict, services_info: Dict) -> str:
    """Create the free tier information section."""
    free_tier_text = []

    # First look for free tier info in services
    for service_name, service_info in services_info.items():
        if "free_tier_info" in service_info:
            free_tier_text.append(
                f'- **{service_name}**: {service_info["free_tier_info"]}'
            )

    # If we found free tier info in services, use it
    if free_tier_text:
        free_tier_info = "Free tier information by service:\n" + "\n".join(
            free_tier_text
        )
    # Otherwise, check for top-level free tier info (legacy support)
    elif "free_tier_info" in custom_cost_data:
        free_tier_info = custom_cost_data["free_tier_info"]
    else:
        # Check if any services mention free tier
        has_free_tier = False

        # Look in custom data for free tier mentions
        for key, value in custom_cost_data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str) and "free" in sub_value.lower():
                        has_free_tier = True
                        free_tier_text.append(
                            f'- **{key.replace("_", " ").title()}**: {sub_value}'
                        )

        if free_tier_text:
            free_tier_info = "Free tier information:\n" + "\n".join(free_tier_text)
        elif has_free_tier:
            free_tier_info = "Some services in this solution offer free tier benefits. See service documentation for details."
        else:
            free_tier_info = "AWS offers a Free Tier for many services. Check the AWS Free Tier page for current offers and limitations."

    return free_tier_info


def _create_usage_cost_table(services_info: Dict) -> str:
    """Create the usage cost table."""
    if services_info:
        usage_tiers = {
            "Low": 0.5,  # 50% of estimated
            "Medium": 1.0,  # 100% of estimated
            "High": 2.0,  # 200% of estimated
        }

        usage_cost_table = "| Service | Low Usage | Medium Usage | High Usage |\n|---------|-----------|--------------|------------|\n"

        for service, info in services_info.items():
            cost = info.get("estimated_cost", "N/A")

            # Try to extract cost value from cost strings
            low_cost = med_cost = high_cost = "Varies"
            if isinstance(cost, str):
                # Try to match patterns like "$150-200/month"
                cost_match = re.search(r"\$(\d+)-(\d+)", cost)
                if cost_match:
                    min_val = int(cost_match.group(1))
                    max_val = int(cost_match.group(2))
                    avg = (min_val + max_val) / 2

                    low_cost = f'${int(avg * usage_tiers["Low"])}/month'
                    med_cost = f"${int(avg)}/month"
                    high_cost = f'${int(avg * usage_tiers["High"])}/month'
                else:
                    # Try to match patterns like "$40.00" or "$40"
                    cost_match = re.search(r"\$(\d+(\.\d+)?)", cost)
                    if cost_match:
                        cost_val = float(cost_match.group(1))

                        low_cost = f'${int(cost_val * usage_tiers["Low"])}/month'
                        med_cost = f"${int(cost_val)}/month"
                        high_cost = f'${int(cost_val * usage_tiers["High"])}/month'

            usage_cost_table += (
                f"| {service} | {low_cost} | {med_cost} | {high_cost} |\n"
            )
    else:
        # Create a meaningful message about where to find cost information
        usage_cost_table = "Cost scaling information not available. See Custom Analysis Data section for detailed cost information."

    return usage_cost_table


def _extract_key_factors(custom_cost_data: Dict, services_info: Dict) -> List[str]:
    """Extract key cost factors."""
    key_factors = []

    # Try to extract key factors from services info
    if services_info:
        for service, info in services_info.items():
            usage = info.get("usage", "")
            if usage:
                key_factors.append(f"- **{service}**: {usage}")

    # If we couldn't extract any key factors, try to find them in custom sections
    if not key_factors:
        for key, value in custom_cost_data.items():
            if isinstance(value, dict) and "description" in value:
                key_factors.append(
                    f'- **{key.replace("_", " ").title()}**: {value["description"]}'
                )

    # If we still don't have any key factors, use default ones
    if not key_factors:
        key_factors = [
            "- Request volume and frequency",
            "- Data storage requirements",
            "- Data transfer between services",
            "- Compute resources utilized",
        ]

    return key_factors


def _calculate_base_cost(
    custom_cost_data: Dict,
    services_info: Dict,
    total_min: float = 0,
    total_max: float = 0,
) -> Optional[float]:
    """Calculate the base cost for projections."""
    base_cost = None

    # First check if we have min-max values from unit pricing
    if total_min > 0 and total_max > 0:
        base_cost = (total_min + total_max) / 2

    # If not, look for total_monthly_cost in custom data
    if base_cost is None:
        for key, value in custom_cost_data.items():
            if isinstance(value, dict) and "total_monthly_cost" in value:
                base_cost = value["total_monthly_cost"]
                break

    # If still no base cost, try to calculate from service costs
    if base_cost is None and services_info:
        total_cost = 0
        service_count = 0

        for service, info in services_info.items():
            cost = info.get("estimated_cost", "N/A")
            if isinstance(cost, str):
                # Try to match patterns like "$150-200/month"
                cost_match = re.search(r"\$(\d+)-(\d+)", cost)
                if cost_match:
                    min_val = int(cost_match.group(1))
                    max_val = int(cost_match.group(2))
                    total_cost += (min_val + max_val) / 2
                    service_count += 1
                else:
                    # Try to match patterns like "$40.00" or "$40"
                    cost_match = re.search(r"\$(\d+(\.\d+)?)", cost)
                    if cost_match:
                        cost_val = float(cost_match.group(1))
                        total_cost += cost_val
                        service_count += 1

        if service_count > 0:
            base_cost = total_cost

    # If still no base cost, try to extract from nested pricing data
    if base_cost is None:
        total_cost = 0
        price_count = 0

        # Look for price fields in nested structures
        for key, value in custom_cost_data.items():
            if isinstance(value, dict):
                # Check if this is a flow with a pricing key
                if "pricing" in value and isinstance(value["pricing"], dict):
                    for service_name, service_info in value["pricing"].items():
                        if isinstance(service_info, dict):
                            # Look for fields containing 'price' or 'cost' in their name
                            for field_name, field_value in service_info.items():
                                if isinstance(field_value, (int, float)) and (
                                    "price" in field_name.lower()
                                    or "cost" in field_name.lower()
                                ):
                                    total_cost += float(field_value)
                                    price_count += 1
                # Also check for direct price fields
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        # Look for fields containing 'price' or 'cost' in their name
                        for field_name, field_value in sub_value.items():
                            if isinstance(field_value, (int, float)) and (
                                "price" in field_name.lower()
                                or "cost" in field_name.lower()
                            ):
                                total_cost += float(field_value)
                                price_count += 1

        if price_count > 0:
            base_cost = total_cost

    return base_cost


def _generate_projected_costs_table(
    base_cost: Optional[float], services_info: Dict
) -> str:
    """Generate the projected costs table."""
    if base_cost is not None:
        growth_rates = {
            "Steady": 1.0,  # No monthly growth
            "Moderate": 1.05,  # 5% monthly growth
            "Rapid": 1.1,  # 10% monthly growth
        }

        # Add explanation of how the base cost is calculated
        base_cost_explanation = "Base monthly cost calculation:\n\n"

        # If we have service costs, list them
        if services_info:
            base_cost_explanation += (
                "| Service | Monthly Cost |\n|---------|-------------|\n"
            )
            for service, info in services_info.items():
                cost = info.get("estimated_cost", "N/A")
                if isinstance(cost, str):
                    cost_match = re.search(r"\$(\d+(\.\d+)?)", cost)
                    if cost_match:
                        base_cost_explanation += (
                            f"| {service} | ${cost_match.group(1)} |\n"
                        )

            base_cost_explanation += (
                f"| **Total Monthly Cost** | **${int(base_cost)}** |\n\n"
            )

        projected_costs_table = (
            base_cost_explanation
            + "| Growth Pattern | Month 1 | Month 3 | Month 6 | Month 12 |\n|---------------|---------|---------|---------|----------|\n"
        )

        for pattern, rate in growth_rates.items():
            month1 = base_cost
            month3 = base_cost * (rate**2)
            month6 = base_cost * (rate**5)
            month12 = base_cost * (rate**11)

            projected_costs_table += f"| {pattern} | ${int(month1)}/mo | ${int(month3)}/mo | ${int(month6)}/mo | ${int(month12)}/mo |\n"

        # Add growth rate explanations right after the table
        projected_costs_table += "\n\n"
        projected_costs_table += (
            f'* Steady: No monthly growth ({growth_rates["Steady"]}x)\n'
        )
        projected_costs_table += f'* Moderate: {int((growth_rates["Moderate"] - 1) * 100)}% monthly growth ({growth_rates["Moderate"]}x)\n'
        projected_costs_table += f'* Rapid: {int((growth_rates["Rapid"] - 1) * 100)}% monthly growth ({growth_rates["Rapid"]}x)'
    else:
        # If we still can't determine a base cost, provide a message
        projected_costs_table = "Insufficient data to generate cost projections. See Custom Analysis Data section for available cost information."

    return projected_costs_table


def _process_recommendations(
    custom_cost_data: Dict, service_names: List[str]
) -> Tuple[List[str], List[str]]:
    """Process recommendations for the report."""
    immediate_actions = []
    best_practices = []

    if "recommendations" in custom_cost_data:
        recommendations = custom_cost_data["recommendations"]
        if isinstance(recommendations, dict):
            # Check if there's a prompt included for assistant
            if "_prompt" in recommendations:
                # Extract immediate actions
                immediate = recommendations.get("immediate", [])
                if isinstance(immediate, (list, tuple)):
                    immediate_actions.extend(str(item) for item in immediate)
                elif immediate:
                    immediate_actions.append(str(immediate))

                # Extract best practices
                best = recommendations.get("best_practices", [])
                if isinstance(best, (list, tuple)):
                    best_practices.extend(str(item) for item in best)
                elif best:
                    best_practices.append(str(best))
            else:
                # Use the provided recommendations directly
                immediate = recommendations.get("immediate", [])
                best = recommendations.get("best_practices", [])

                # Process immediate actions
                if isinstance(immediate, (list, tuple)):
                    immediate_actions.extend(str(item) for item in immediate)
                elif immediate:
                    immediate_actions.append(str(immediate))

                # Process best practices
                if isinstance(best, (list, tuple)):
                    best_practices.extend(str(item) for item in best)
                elif best:
                    best_practices.append(str(best))

    # If no recommendations were provided or they're empty, generate them
    if not immediate_actions and not best_practices:
        wa_recommendations = (
            CostAnalysisHelper.generate_well_architected_recommendations(service_names)
        )
        immediate_actions = wa_recommendations["immediate"]
        best_practices = wa_recommendations["best_practices"]

    return immediate_actions, best_practices


def _process_custom_sections(custom_cost_data: Dict) -> str:
    """Process custom sections for the report."""
    custom_sections = []

    # Convert custom_cost_data to a readable format
    if custom_cost_data:
        # Add a section for Custom Analysis Data
        custom_sections.append("## Detailed Cost Analysis\n\n")

    # Process each top-level key in custom_cost_data
    for key, value in custom_cost_data.items():
        # Skip keys we've already processed elsewhere
        if key in [
            "project_name",
            "service_name",
            "description",
            "assumptions",
            "limitations",
            "free_tier_info",
            "conclusion",
            "services",
            "pricing_data",
            "pricing_data_reference",
        ]:
            continue

        # Format the section title
        section_title = key.replace("_", " ").title()
        custom_sections.append(f"### {section_title}\n\n")

        # Special handling for assumptions and exclusions
        if key in ["assumptions", "exclusions"]:
            if isinstance(value, list):
                for item in value:
                    custom_sections.append(f"- {item}\n")
            elif isinstance(value, str):
                # Split string by newlines and create bullet points
                lines = value.split("\n")
                for line in lines:
                    if line.strip():
                        custom_sections.append(f"- {line.strip()}\n")
            custom_sections.append("\n")
            continue

        # Special handling for recommendations section
        if key.lower() == "recommendations":
            if isinstance(value, dict):
                # Process immediate actions
                if "immediate" in value and isinstance(value["immediate"], list):
                    custom_sections.append("#### Immediate Actions\n\n")
                    custom_sections.append(
                        "".join(f"- {item}\n" for item in value["immediate"])
                    )
                    custom_sections.append("\n")

                # Process best practices
                if "best_practices" in value and isinstance(
                    value["best_practices"], list
                ):
                    custom_sections.append("#### Best Practices\n\n")
                    custom_sections.append(
                        "".join(f"- {item}\n" for item in value["best_practices"])
                    )
                    custom_sections.append("\n")
            else:
                # Fallback if recommendations is not a dict
                custom_sections.append(str(value) + "\n\n")
        # Handle different value types for non-recommendations sections
        elif isinstance(value, dict):
            # For dictionaries, create a table
            custom_sections.append("| Key | Value |\n|-----|-------|\n")
            for sub_key, sub_value in value.items():
                formatted_key = sub_key.replace("_", " ").title()

                # Format the value based on its type
                if isinstance(sub_value, (int, float)):
                    # Only format as currency if the field name suggests it's a monetary value
                    monetary_fields = [
                        "cost",
                        "price",
                        "rate",
                        "fee",
                        "charge",
                        "amount",
                    ]
                    exact_monetary_fields = ["total"]

                    # Check if the field name exactly matches a monetary field or contains a monetary term
                    is_monetary = sub_key.lower() in exact_monetary_fields or any(
                        money_term in sub_key.lower()
                        and money_term == sub_key.lower()
                        or money_term + "_" in sub_key.lower()
                        or "_" + money_term in sub_key.lower()
                        for money_term in monetary_fields
                    )

                    if sub_key.lower() == "total":
                        formatted_value = f"**${sub_value}**"  # Always format totals as currency with bold
                    elif is_monetary:
                        formatted_value = (
                            f"${sub_value}"  # Format monetary values as currency
                        )
                    else:
                        formatted_value = str(
                            sub_value
                        )  # Format non-monetary values as plain numbers
                elif isinstance(sub_value, dict):
                    formatted_value = "See nested table below"
                else:
                    formatted_value = str(sub_value)

                custom_sections.append(f"| {formatted_key} | {formatted_value} |\n")

            # Add nested tables for dictionary values
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    formatted_sub_key = sub_key.replace("_", " ").title()
                    custom_sections.append(f"\n#### {formatted_sub_key}\n\n")
                    custom_sections.append("| Key | Value |\n|-----|-------|\n")

                    for nested_key, nested_value in sub_value.items():
                        formatted_nested_key = nested_key.replace("_", " ").title()

                        # Handle different types of nested values
                        if isinstance(nested_value, (int, float)):
                            # Only format as currency if the field name suggests it's a monetary value
                            monetary_fields = [
                                "cost",
                                "price",
                                "rate",
                                "fee",
                                "charge",
                                "amount",
                            ]
                            exact_monetary_fields = ["total"]

                            # Check if the field name exactly matches a monetary field or contains a monetary term
                            is_monetary = (
                                nested_key.lower() in exact_monetary_fields
                                or any(
                                    money_term in nested_key.lower()
                                    and money_term == nested_key.lower()
                                    or money_term + "_" in nested_key.lower()
                                    or "_" + money_term in nested_key.lower()
                                    for money_term in monetary_fields
                                )
                            )

                            if is_monetary:
                                formatted_nested_value = f"${nested_value}"
                            else:
                                # For non-monetary values, just use the number without $ sign
                                formatted_nested_value = str(nested_value)
                        elif isinstance(nested_value, dict):
                            # Extract key information from nested dictionaries
                            price = None
                            description = nested_value.get("description", "")

                            # Try to get price from various fields
                            for price_field in [
                                "price",
                                "price_per_1000_pages",
                                "cost",
                            ]:
                                if price_field in nested_value:
                                    price = nested_value[price_field]
                                    break

                            if price is not None:
                                formatted_nested_value = f"${price} - {description}"
                            else:
                                formatted_nested_value = description or str(
                                    nested_value
                                )
                        else:
                            formatted_nested_value = str(nested_value)

                        custom_sections.append(
                            f"| {formatted_nested_key} | {formatted_nested_value} |\n"
                        )
        elif isinstance(value, list):
            # For lists, create a bullet list
            for item in value:
                custom_sections.append(f"- {item}\n")
        else:
            # For simple values, just add the value
            custom_sections.append(f"{value}\n\n")

        # Add spacing between sections
        custom_sections.append("\n")

    # Join all custom sections
    return "".join(custom_sections) if custom_sections else ""


async def _generate_custom_data_report(
    custom_cost_data: Dict,
    output_file: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> str:
    """Generate a report using custom cost data."""
    # Get project name or use default
    project_name = custom_cost_data.get("project_name", "AWS Project")

    # Start with the template
    report = COST_REPORT_TEMPLATE

    # Replace service_name with project name
    report = report.replace("{service_name}", project_name)

    # Get project description or use default
    description = custom_cost_data.get(
        "description", "This project uses multiple AWS services."
    )
    report = report.replace("{service_description}", description)

    # Add pricing model information
    pricing_model = custom_cost_data.get("pricing_model", "ON DEMAND")
    pricing_model_section = (
        "This cost analysis is based on the following pricing model:\n"
    )
    pricing_model_section += f"- **{pricing_model}** pricing"

    # Add common description for ON DEMAND pricing
    if pricing_model.upper() == "ON DEMAND":
        pricing_model_section += " (pay-as-you-go)"

    pricing_model_section += "\n- Standard service configurations without reserved capacity or savings plans\n"
    pricing_model_section += "- No caching or optimization techniques applied"

    # Replace pricing model section in template
    report = report.replace(
        "This cost analysis is based on the following pricing model:\n- **ON DEMAND** pricing (pay-as-you-go) unless otherwise specified\n- Standard service configurations without reserved capacity or savings plans\n- No caching or optimization techniques applied",
        pricing_model_section,
    )

    # Add assumptions section
    assumptions = custom_cost_data.get(
        "assumptions",
        [
            "Standard configuration for all services",
            "Default usage patterns based on typical workloads",
            "No reserved instances or savings plans applied",
        ],
    )
    assumptions_list = []
    if isinstance(assumptions, str):
        # Handle case where assumptions is a string
        for line in assumptions.split("\n"):
            if line.strip():
                assumptions_list.append(f"- {line.strip()}")
    elif isinstance(assumptions, list):
        # Handle case where assumptions is a list
        for assumption in assumptions:
            assumptions_list.append(f"- {assumption}")
    report = report.replace("{assumptions_section}", "\n".join(assumptions_list))

    # Add limitations and exclusions section
    default_limitations = [
        "This analysis only includes confirmed compatible services and features",
        "Database costs may not be included if compatibility is uncertain",
        "Only the latest foundation models are considered for comparison",
    ]

    # Use exclusions if provided, otherwise use limitations or default
    if "exclusions" in custom_cost_data and custom_cost_data["exclusions"]:
        limitations = custom_cost_data["exclusions"]
    elif "limitations" in custom_cost_data and custom_cost_data["limitations"]:
        limitations = custom_cost_data["limitations"]
    else:
        limitations = default_limitations

    limitations_list = []
    if isinstance(limitations, str):
        # Handle case where limitations is a string
        for line in limitations.split("\n"):
            if line.strip():
                limitations_list.append(f"- {line.strip()}")
    elif isinstance(limitations, list):
        # Handle case where limitations is a list
        for limitation in limitations:
            limitations_list.append(f"- {limitation}")
    report = report.replace("{limitations_section}", "\n".join(limitations_list))

    # Extract services information
    services_info, service_names = _extract_services_info(custom_cost_data)

    # Create unit pricing details table
    unit_pricing_details_table = _create_unit_pricing_details_table(services_info)
    report = report.replace("{unit_pricing_details_table}", unit_pricing_details_table)

    # Create cost calculation table
    (
        cost_calculation_table,
        total_min,
        total_max,
        initial_base_cost,
    ) = _create_cost_calculation_table(services_info)
    report = report.replace("{cost_calculation_table}", cost_calculation_table)

    # Free tier information
    free_tier_info = _create_free_tier_info(custom_cost_data, services_info)
    report = report.replace("{free_tier_info}", free_tier_info)

    # Usage cost table
    usage_cost_table = _create_usage_cost_table(services_info)
    report = report.replace("{usage_cost_table}", usage_cost_table)

    # Key cost factors
    key_factors = _extract_key_factors(custom_cost_data, services_info)
    report = report.replace("{key_cost_factors}", "\n".join(key_factors))

    # Projected costs over time
    base_cost = _calculate_base_cost(
        custom_cost_data, services_info, total_min, total_max
    )
    projected_costs_table = _generate_projected_costs_table(base_cost, services_info)
    report = report.replace("{projected_costs}", projected_costs_table)

    # Recommendations
    immediate_actions, best_practices = _process_recommendations(
        custom_cost_data, service_names
    )

    # Replace recommendation placeholders
    if isinstance(immediate_actions, list) and len(immediate_actions) >= 3:
        report = report.replace("{recommendation_1}", str(immediate_actions[0]))
        report = report.replace("{recommendation_2}", str(immediate_actions[1]))
        report = report.replace("{recommendation_3}", str(immediate_actions[2]))
    else:
        report = report.replace(
            "- {recommendation_1}\n- {recommendation_2}\n- {recommendation_3}",
            "- Optimize resource usage based on actual requirements\n"
            "- Implement cost allocation tags\n"
            "- Set up AWS Budgets alerts",
        )

    if isinstance(best_practices, list) and len(best_practices) >= 3:
        report = report.replace("{best_practice_1}", str(best_practices[0]))
        report = report.replace("{best_practice_2}", str(best_practices[1]))
        report = report.replace("{best_practice_3}", str(best_practices[2]))
    else:
        report = report.replace(
            "- {best_practice_1}\n- {best_practice_2}\n- {best_practice_3}",
            "- Regularly review costs with AWS Cost Explorer\n"
            "- Consider reserved capacity for predictable workloads\n"
            "- Implement automated scaling based on demand",
        )

    # Process custom sections
    custom_analysis = _process_custom_sections(custom_cost_data)
    report = report.replace("{custom_analysis_sections}", str(custom_analysis))

    # Conclusion
    conclusion = custom_cost_data.get(
        "conclusion",
        f"By following the recommendations in this report, you can optimize your {project_name} costs "
        f"while maintaining performance and reliability. Regular monitoring and adjustment of your "
        f"usage patterns will help ensure cost efficiency as your workload evolves.",
    )
    report = report.replace("{conclusion}", conclusion)

    # Write to file if requested
    if output_file:
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(report)
            if ctx:
                await ctx.info(f"Report saved to {output_file}")
        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to write report to file: {e}")

    return report


async def _generate_pricing_data_report(
    pricing_data: Dict[str, Any],
    service_name: str,
    related_services: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    ctx: Optional[Context] = None,
    params: Optional[Dict] = None,
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
    report = report.replace("{service_name}", service_name.title())

    # Replace service description
    report = report.replace(
        "{service_description}", pricing_structure["service_description"]
    )

    # Add pricing model information
    pricing_model = "ON DEMAND"
    if params and "pricing_model" in params and params["pricing_model"]:
        pricing_model = params["pricing_model"]

    pricing_model_section = (
        "This cost analysis is based on the following pricing model:\n"
    )
    pricing_model_section += f"- **{pricing_model}** pricing"

    # Add common description for ON DEMAND pricing
    if pricing_model.upper() == "ON DEMAND":
        pricing_model_section += " (pay-as-you-go)"

    pricing_model_section += "\n- Standard service configurations without reserved capacity or savings plans\n"
    pricing_model_section += "- No caching or optimization techniques applied"

    # Replace pricing model section in template
    report = report.replace(
        "This cost analysis is based on the following pricing model:\n- **ON DEMAND** pricing (pay-as-you-go) unless otherwise specified\n- Standard service configurations without reserved capacity or savings plans\n- No caching or optimization techniques applied",
        pricing_model_section,
    )

    # Add assumptions section
    assumptions_list = "\n".join(
        [f"- {assumption}" for assumption in pricing_structure["assumptions"]]
    )
    report = report.replace("{assumptions_section}", assumptions_list)

    # Add limitations and exclusions section
    default_limitations = [
        f"This analysis only includes confirmed pricing information for {service_name}",
        "Database compatibility information is only included when explicitly confirmed",
        "Only the latest foundation models are considered for comparison",
        "Providing less information is better than giving incorrect information",
    ]

    # Add custom exclusions if provided
    if params and "exclusions" in params and params["exclusions"]:
        limitations = params["exclusions"] + default_limitations
    else:
        limitations = default_limitations

    limitations_list = "\n".join([f"- {limitation}" for limitation in limitations])
    report = report.replace("{limitations_section}", limitations_list)

    # Replace unit pricing details table
    report = report.replace(
        "{unit_pricing_details_table}",
        cost_tables["unit_pricing_details_table"]
        if "unit_pricing_details_table" in cost_tables
        else "No detailed unit pricing information available.",
    )

    # Replace cost calculation table
    report = report.replace(
        "{cost_calculation_table}",
        cost_tables["cost_calculation_table"]
        if "cost_calculation_table" in cost_tables
        else "No cost calculation details available.",
    )

    # Replace free tier info
    report = report.replace("{free_tier_info}", pricing_structure["free_tier"])

    # Replace usage cost table
    report = report.replace("{usage_cost_table}", cost_tables["usage_cost_table"])

    # Replace key cost factors
    key_factors = "\n".join(
        [f"- {factor}" for factor in pricing_structure["key_cost_factors"]]
    )
    report = report.replace("{key_cost_factors}", key_factors)

    # Replace projected costs
    report = report.replace("{projected_costs}", cost_tables["projected_costs_table"])

    # Replace recommendations
    if len(pricing_structure["recommendations"]["immediate"]) >= 3:
        report = report.replace(
            "{recommendation_1}", pricing_structure["recommendations"]["immediate"][0]
        )
        report = report.replace(
            "{recommendation_2}", pricing_structure["recommendations"]["immediate"][1]
        )
        report = report.replace(
            "{recommendation_3}", pricing_structure["recommendations"]["immediate"][2]
        )

    if len(pricing_structure["recommendations"]["best_practices"]) >= 3:
        report = report.replace(
            "{best_practice_1}",
            pricing_structure["recommendations"]["best_practices"][0],
        )
        report = report.replace(
            "{best_practice_2}",
            pricing_structure["recommendations"]["best_practices"][1],
        )
        report = report.replace(
            "{best_practice_3}",
            pricing_structure["recommendations"]["best_practices"][2],
        )

    # Replace conclusion
    conclusion = f"By following the recommendations in this report, you can optimize your {service_name} costs while maintaining performance and reliability. "
    conclusion += "Regular monitoring and adjustment of your usage patterns will help ensure cost efficiency as your workload evolves."
    report = report.replace("{conclusion}", conclusion)

    # Write to file if requested
    if output_file:
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(report)
            if ctx:
                await ctx.info(f"Report saved to {output_file}")
        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to write report to file: {e}")

    return report


async def generate_cost_analysis_report(
    pricing_data: Dict[str, Any],  # Required: Raw pricing data from AWS
    service_name: str,  # Required: Primary service name
    # Core parameters (simple, commonly used)
    related_services: Optional[List[str]] = None,
    pricing_model: str = "ON DEMAND",
    assumptions: Optional[List[str]] = None,
    exclusions: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    # Advanced parameters (grouped in a dictionary for complex use cases)
    detailed_cost_data: Optional[Dict[str, Any]] = None,
    ctx: Optional[Context] = None,
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

    Returns:
        The generated report in markdown format
    """
    try:
        # Create a consolidated cost data dictionary
        cost_data = {
            "project_name": service_name,
            "pricing_model": pricing_model,
        }

        # Add assumptions if provided
        if assumptions:
            cost_data["assumptions"] = "\n".join(assumptions)

        # Add exclusions if provided
        if exclusions:
            cost_data["exclusions"] = "\n".join(exclusions)

        # Merge detailed_cost_data if provided
        if detailed_cost_data:
            for key, value in detailed_cost_data.items():
                cost_data[key] = value

        # Store reference to the original pricing data
        cost_data["pricing_data_reference"] = str(pricing_data)

        # Generate the report using the consolidated cost data
        if "services" in cost_data:
            # If services are defined in detailed_cost_data, use the custom data report generator
            return await _generate_custom_data_report(cost_data, output_file, ctx)
        else:
            # Otherwise, use the pricing data report generator
            params = {
                "pricing_model": pricing_model,
                "assumptions": assumptions,
                "exclusions": exclusions,
                "detailed_calculations": True,
            }

            return await _generate_pricing_data_report(
                pricing_data=pricing_data,
                service_name=service_name,
                related_services=related_services,
                output_file=output_file,
                ctx=ctx,
                params=params,
            )
    except Exception as e:
        if ctx:
            await ctx.error(f"Error generating cost report: {str(e)}")
        return f"Error generating cost report: {str(e)}"
