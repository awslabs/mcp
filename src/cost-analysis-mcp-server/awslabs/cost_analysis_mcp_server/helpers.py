"""awslabs MCP Cost Analysis mcp server helper classes.

This module provides helper classes for analyzing AWS service costs.
"""

import json
import re

import boto3
import pandas as pd
import os
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class CostAnalysisHelper:
    """Helper class for cost analysis operations."""

    @staticmethod
    def parse_pricing_data(
        pricing_data: Dict,
        service_name: str,
        related_services: Optional[List[str]] = None,
    ) -> Dict:
        """Extract and structure the most relevant pricing information.

        This handles both web-scraped text and API responses, focusing on
        extracting the core pricing tiers and units.

        Args:
            pricing_data: Raw pricing data from web scraping or API
            service_name: Name of the AWS service
            related_services: List of related services for context-aware defaults

        Returns:
            Dict: Structured pricing information
        """
        pricing_structure = {
            'service_name': service_name,
            'service_description': '',
            'unit_pricing': [],
            'free_tier': '',
            'usage_levels': {'low': {}, 'medium': {}, 'high': {}},
            'key_cost_factors': [],
            'projected_costs': {},
            'recommendations': {'immediate': [], 'best_practices': []},
            'assumptions': [],  # New field for tracking assumptions
        }

        # Check if we have web-scraped data or API data
        if isinstance(pricing_data.get('data'), str):
            # Web-scraped data (text)
            text_data = pricing_data.get('data', '')

            # Extract service description
            description_patterns = [
                rf'{service_name.title()} is a fully managed service that (.*?)\.',
                rf'{service_name.title()} is a serverless service that (.*?)\.',
                rf'{service_name.title()} is an AWS service that (.*?)\.',
            ]

            for pattern in description_patterns:
                match = re.search(pattern, text_data, re.IGNORECASE)
                if match:
                    pricing_structure['service_description'] = match.group(1)
                    break

            if not pricing_structure['service_description']:
                pricing_structure['service_description'] = (
                    f'provides {service_name} functionality in the AWS cloud'
                )

            # Extract pricing information
            # Look for pricing tables or pricing information sections
            price_section_match = re.search(
                r'(?:Pricing|Price|Costs?|Fees?)(.*?)(?:Free Tier|Features|Benefits|FAQs)',
                text_data,
                re.DOTALL | re.IGNORECASE,
            )

            if price_section_match:
                price_text = price_section_match.group(1)

                # Extract pricing points using regex patterns
                price_patterns = [
                    r'\$([\d,.]+) per ([\w\s-]+)',
                    r'([\w\s-]+) costs? \$([\d,.]+)',
                    r'([\w\s-]+): \$([\d,.]+)',
                ]

                for pattern in price_patterns:
                    matches = re.findall(pattern, price_text, re.IGNORECASE)
                    for match in matches:
                        if len(match) == 2:
                            if pattern == price_patterns[0]:  # First pattern has price first
                                price, unit = match
                                pricing_structure['unit_pricing'].append(
                                    {'unit': unit.strip(), 'price': price.strip()}
                                )
                            else:  # Other patterns have unit first
                                unit, price = match
                                pricing_structure['unit_pricing'].append(
                                    {'unit': unit.strip(), 'price': price.strip()}
                                )

            # Extract free tier information
            free_tier_match = re.search(
                r'Free Tier(.*?)(?:Pricing|Features|Benefits|FAQs)',
                text_data,
                re.DOTALL | re.IGNORECASE,
            )

            if free_tier_match:
                pricing_structure['free_tier'] = free_tier_match.group(1).strip()
            else:
                pricing_structure['free_tier'] = 'No free tier information found.'

            # Extract key cost factors
            cost_factors = []
            factor_patterns = [
                r'(?:factors|considerations) (?:that|which) affect(.*?)(?:pricing|cost)',
                r'(?:pricing|cost) (?:is based on|depends on)(.*?)(?:\.|\n)',
            ]

            for pattern in factor_patterns:
                match = re.search(pattern, text_data, re.IGNORECASE | re.DOTALL)
                if match:
                    factors_text = match.group(1)
                    # Split by common separators and clean up
                    for factor in re.split(r'[,.]', factors_text):
                        factor = factor.strip()
                        if factor and len(factor) > 5:  # Avoid very short matches
                            cost_factors.append(factor)

            if not cost_factors:
                # Default cost factors based on service type
                if 'lambda' in service_name.lower():
                    cost_factors = [
                        'Number of requests',
                        'Duration of execution',
                        'Memory allocated',
                    ]
                elif 'dynamodb' in service_name.lower():
                    cost_factors = [
                        'Read and write throughput',
                        'Storage used',
                        'Data transfer',
                    ]
                elif 's3' in service_name.lower():
                    cost_factors = ['Storage used', 'Requests made', 'Data transfer']
                else:
                    cost_factors = [
                        'Usage volume',
                        'Resource allocation',
                        'Data transfer',
                    ]

            pricing_structure['key_cost_factors'] = cost_factors

        else:
            # API data (JSON)
            price_list = pricing_data.get('data', [])

            if isinstance(price_list, list) and price_list:
                # Process the first few price list items
                for i, price_item in enumerate(price_list[:5]):
                    if isinstance(price_item, str):
                        try:
                            price_data = json.loads(price_item)
                            product = price_data.get('product', {})

                            # Extract service description if not already set
                            if (
                                not pricing_structure['service_description']
                                and 'attributes' in product
                            ):
                                attrs = product['attributes']
                                if 'productFamily' in attrs and 'description' in attrs:
                                    pricing_structure['service_description'] = (
                                        f'{attrs["productFamily"]} that {attrs["description"]}'
                                    )

                            # Extract pricing information
                            if 'terms' in price_data:
                                terms = price_data['terms']
                                for term_type, term_values in terms.items():
                                    for _, price_dimensions in term_values.items():
                                        for _, dimension in price_dimensions.items():
                                            if 'pricePerUnit' in dimension and 'unit' in dimension:
                                                unit = dimension['unit']
                                                price = dimension.get('pricePerUnit', {}).get(
                                                    'USD', 'N/A'
                                                )
                                                description = dimension.get('description', '')

                                                pricing_structure['unit_pricing'].append(
                                                    {
                                                        'unit': unit,
                                                        'price': price,
                                                        'description': description,
                                                    }
                                                )
                        except (json.JSONDecodeError, KeyError):
                            continue

            # Set default description if none found
            if not pricing_structure['service_description']:
                pricing_structure['service_description'] = (
                    f'provides {service_name} functionality in the AWS cloud'
                )

            # Set default free tier info if none found
            pricing_structure['free_tier'] = (
                'Please check the AWS Free Tier page for current offers.'
            )

            # Set default key cost factors based on service
            if 'lambda' in service_name.lower():
                pricing_structure['key_cost_factors'] = [
                    'Number of requests',
                    'Duration of execution',
                    'Memory allocated',
                ]
            elif 'dynamodb' in service_name.lower():
                pricing_structure['key_cost_factors'] = [
                    'Read and write throughput',
                    'Storage used',
                    'Data transfer',
                ]
            elif 's3' in service_name.lower():
                pricing_structure['key_cost_factors'] = [
                    'Storage used',
                    'Requests made',
                    'Data transfer',
                ]
            else:
                pricing_structure['key_cost_factors'] = [
                    'Usage volume',
                    'Resource allocation',
                    'Data transfer',
                ]

        # Generate usage level costs based on unit pricing
        if pricing_structure['unit_pricing']:
            # Define multipliers for different usage levels
            multipliers = {'low': 1, 'medium': 10, 'high': 100}

            for level, multiplier in multipliers.items():
                level_costs = {}
                for price_item in pricing_structure['unit_pricing']:
                    unit = price_item['unit']
                    try:
                        # Clean price string and convert to float
                        price_str = price_item['price']
                        if isinstance(price_str, str):
                            price_str = price_str.replace('$', '').replace(',', '')
                        price = float(price_str)

                        # Calculate cost for this usage level
                        level_costs[unit] = f'${price * multiplier:.2f}'
                    except (ValueError, TypeError):
                        level_costs[unit] = 'Calculation not available'

                pricing_structure['usage_levels'][level] = level_costs

        # Generate projected costs (simple linear growth model)
        months = [1, 3, 6, 12]
        growth_rates = {
            'steady': 1.0,  # No growth
            'moderate': 1.1,  # 10% monthly growth
            'rapid': 1.2,  # 20% monthly growth
        }

        for growth_name, growth_rate in growth_rates.items():
            monthly_costs = {}

            # Start with medium usage level as baseline
            baseline = 0
            for unit, cost in pricing_structure['usage_levels']['medium'].items():
                try:
                    if isinstance(cost, str) and '$' in cost:
                        baseline += float(cost.replace('$', '').replace(',', ''))
                except (ValueError, TypeError):
                    pass

            if baseline == 0:
                baseline = 100  # Default baseline if no costs could be calculated

            for month in months:
                # Calculate compound growth
                factor = 1
                for i in range(month):
                    factor *= growth_rate

                monthly_costs[f'Month {month}'] = f'${baseline * factor:.2f}'

            pricing_structure['projected_costs'][growth_name] = monthly_costs

        # Add default assumptions based on service
        if 'lambda' in service_name.lower():
            pricing_structure['assumptions'] = [
                'Default memory allocation: 128 MB',
                'Average execution time: 100ms per invocation',
                '1 million invocations per month',
            ]
        elif 'dynamodb' in service_name.lower():
            pricing_structure['assumptions'] = [
                'On-demand capacity mode',
                '5 million read requests per month',
                '1 million write requests per month',
                '10 GB of data storage',
            ]
        elif 's3' in service_name.lower():
            pricing_structure['assumptions'] = [
                'Standard storage class',
                '100 GB of data storage',
                '10,000 GET requests per month',
                '1,000 PUT requests per month',
            ]
        elif 'bedrock' in service_name.lower():
            pricing_structure['assumptions'] = [
                'Using Claude 3.5 Sonnet model',
                '1 million input tokens per month',
                '500,000 output tokens per month',
            ]
        elif 'opensearch' in service_name.lower():
            # Check if related to knowledge base
            if related_services and any(
                'knowledge' in s.lower() or 'kb' in s.lower() or 'bedrock' in s.lower()
                for s in related_services
            ):
                pricing_structure['assumptions'] = [
                    'Using OpenSearch Serverless (required for Knowledge Base)',
                    '2 OCUs for indexing and 2 OCUs for search',
                    '50 GB of vector storage',
                ]
                # Update service description for serverless
                pricing_structure['service_description'] = (
                    'provides serverless vector storage for knowledge bases and search applications'
                )
            else:
                pricing_structure['assumptions'] = [
                    'Using provisioned OpenSearch cluster',
                    '3 x t3.small.search instances',
                    '50 GB of EBS storage',
                ]
        else:
            pricing_structure['assumptions'] = [
                'Standard configuration',
                'Moderate usage patterns',
                'No reserved instances or savings plans',
            ]

        # Generate recommendations based on service type
        if 'lambda' in service_name.lower():
            pricing_structure['recommendations']['immediate'] = [
                'Right-size memory allocations to match function requirements',
                'Implement request batching where possible',
                'Use Provisioned Concurrency for predictable workloads',
            ]
            pricing_structure['recommendations']['best_practices'] = [
                'Monitor and optimize function duration',
                'Consider AWS Graviton processors for better price-performance',
                'Use Savings Plans for predictable workloads',
            ]
        elif 'dynamodb' in service_name.lower():
            pricing_structure['recommendations']['immediate'] = [
                'Use on-demand capacity mode for unpredictable workloads',
                'Implement efficient data access patterns',
                'Consider DynamoDB Accelerator (DAX) for read-heavy workloads',
            ]
            pricing_structure['recommendations']['best_practices'] = [
                'Use sparse indexes to minimize storage costs',
                'Implement TTL for automatic data expiration',
                'Consider Reserved Capacity for predictable workloads',
            ]
        elif 's3' in service_name.lower():
            pricing_structure['recommendations']['immediate'] = [
                'Implement lifecycle policies to transition data to cheaper storage tiers',
                'Use S3 Intelligent-Tiering for data with unknown access patterns',
                'Enable S3 analytics to identify cost-saving opportunities',
            ]
            pricing_structure['recommendations']['best_practices'] = [
                'Use S3 Transfer Acceleration only when needed',
                'Optimize request patterns to minimize costs',
                'Consider S3 Batch Operations for large-scale changes',
            ]
        elif 'opensearch' in service_name.lower():
            # Different recommendations based on deployment type
            if related_services and any(
                'knowledge' in s.lower() or 'kb' in s.lower() or 'bedrock' in s.lower()
                for s in related_services
            ):
                # Serverless recommendations
                pricing_structure['recommendations']['immediate'] = [
                    'Optimize document chunking to reduce vector storage requirements',
                    'Configure indexing and search OCUs separately based on workload',
                    'Use caching for frequently accessed vectors',
                ]
                pricing_structure['recommendations']['best_practices'] = [
                    'Monitor OCU utilization and adjust as needed',
                    'Implement efficient vector search queries',
                    'Use compression techniques for vector embeddings',
                ]
            else:
                # Provisioned recommendations
                pricing_structure['recommendations']['immediate'] = [
                    'Right-size instance types based on workload',
                    'Use UltraWarm for less frequently accessed indices',
                    'Implement index lifecycle management',
                ]
                pricing_structure['recommendations']['best_practices'] = [
                    'Consider Reserved Instances for predictable workloads',
                    'Optimize shard allocation for better performance',
                    'Use Auto-Tune for automatic optimization',
                ]
        else:
            pricing_structure['recommendations']['immediate'] = [
                'Monitor usage patterns to identify optimization opportunities',
                'Right-size resources to match actual requirements',
                'Implement auto-scaling to match demand',
            ]
            pricing_structure['recommendations']['best_practices'] = [
                'Use AWS Cost Explorer to track and analyze costs',
                'Consider reserved capacity options for predictable workloads',
                'Regularly review and optimize resource utilization',
            ]

        return pricing_structure

    @staticmethod
    def generate_cost_table(pricing_structure: Dict) -> Dict:
        """Generate detailed pricing tables for different usage levels.

        Creates markdown tables showing unit pricing details and cost calculations.

        Args:
            pricing_structure: Structured pricing information

        Returns:
            Dict: Markdown tables with pricing information
        """
        # Create unit pricing details table
        unit_pricing_details_table = '| Service | Resource Type | Unit | Price | Free Tier |\n|---------|--------------|------|-------|------------|\n'

        service_name = pricing_structure.get('service_name', 'AWS Service')
        free_tier_info = pricing_structure.get('free_tier', 'No free tier information available')

        # Format free tier info for display
        if len(free_tier_info) > 50:
            free_tier_info = free_tier_info[:47] + '...'

        has_pricing_data = False

        for item in pricing_structure['unit_pricing']:
            has_pricing_data = True
            unit = item.get('unit', 'N/A')
            price = item.get('price', 'N/A')
            if isinstance(price, str) and not price.startswith('$') and price != 'N/A':
                price = f'${price}'

            # Extract resource type from unit or description
            resource_type = item.get('description', unit).split(' ')[0]
            if resource_type == unit:
                resource_type = unit.split(' ')[0]

            unit_pricing_details_table += (
                f'| {service_name} | {resource_type} | {unit} | {price} | {free_tier_info} |\n'
            )

        if not has_pricing_data:
            unit_pricing_details_table += (
                f'| {service_name} | N/A | N/A | N/A | {free_tier_info} |\n'
            )

        # Create cost calculation table
        cost_calculation_table = '| Service | Usage | Calculation | Monthly Cost |\n|---------|-------|-------------|-------------|\n'

        # For each usage level, create a calculation row
        for level, costs in pricing_structure['usage_levels'].items():
            if level != 'medium':  # Only include medium usage in calculation table
                continue

            calculation = 'See pricing details'
            monthly_cost = 'Varies'

            # Try to extract a total cost
            total_cost = 0
            for unit, cost in costs.items():
                if isinstance(cost, str) and '$' in cost:
                    try:
                        cost_value = float(cost.replace('$', '').replace(',', ''))
                        total_cost += cost_value
                    except ValueError:
                        pass

            if total_cost > 0:
                monthly_cost = f'${total_cost:.2f}'

            usage_description = f'{level.title()} usage level'
            cost_calculation_table += (
                f'| {service_name} | {usage_description} | {calculation} | {monthly_cost} |\n'
            )

        # Create usage cost table (keep the existing implementation)
        usage_cost_table = '| Service | Low Usage | Medium Usage | High Usage |\n|---------|-----------|--------------|------------|\n'

        # Simplify to show one row with costs for each usage level
        low_cost = 'Varies'
        med_cost = 'Varies'
        high_cost = 'Varies'

        # Try to extract total costs for each level
        for level, costs in pricing_structure['usage_levels'].items():
            total_cost = 0
            for unit, cost in costs.items():
                if isinstance(cost, str) and '$' in cost:
                    try:
                        cost_value = float(cost.replace('$', '').replace(',', ''))
                        total_cost += cost_value
                    except ValueError:
                        pass

            if total_cost > 0:
                if level == 'low':
                    low_cost = f'${total_cost:.2f}/month'
                elif level == 'medium':
                    med_cost = f'${total_cost:.2f}/month'
                elif level == 'high':
                    high_cost = f'${total_cost:.2f}/month'

        usage_cost_table += f'| {service_name} | {low_cost} | {med_cost} | {high_cost} |\n'

        # Create projected costs table (keep the existing implementation)
        projected_costs_table = (
            '| Growth Pattern | '
            + ' | '.join([f'Month {month}' for month in [1, 3, 6, 12]])
            + ' |\n'
        )
        projected_costs_table += '|---------------|' + '|'.join(['----' for _ in range(4)]) + '|\n'

        for pattern, costs in pricing_structure['projected_costs'].items():
            row = f'| {pattern.title()} | '
            for month in [1, 3, 6, 12]:
                key = f'Month {month}'
                cost = costs.get(key, 'N/A')
                row += f'{cost} | '
            projected_costs_table += row + '\n'

        return {
            'unit_pricing_details_table': unit_pricing_details_table,
            'cost_calculation_table': cost_calculation_table,
            'usage_cost_table': usage_cost_table,
            'projected_costs_table': projected_costs_table,
        }

    @staticmethod
    def generate_well_architected_recommendations(services: List[str]) -> Dict:
        """Generate basic cost optimization recommendations based on AWS Well-Architected framework.

        This is a fallback method that returns minimal recommendations when the
        more advanced recommendation generation approach is not available.

        Args:
            services: List of AWS services used in the project

        Returns:
            Dict: Recommendations organized by categories
        """
        # Default recommendations that apply to most AWS architectures
        recommendations = {
            'immediate': [
                'Right-size resources based on actual usage patterns',
                'Implement cost allocation tags to track spending by component',
                'Set up AWS Budgets alerts to monitor costs',
            ],
            'best_practices': [
                'Regularly review and analyze cost patterns with AWS Cost Explorer',
                'Consider reserved capacity options for predictable workloads',
                'Implement automated scaling based on demand',
            ],
        }

        # Add a few service-specific recommendations based on common services
        services_lower = [s.lower() for s in services]

        if any(s in services_lower for s in ['bedrock', 'amazon bedrock']):
            recommendations['immediate'].insert(
                0, 'Optimize prompt engineering to reduce token usage in Bedrock models'
            )
            recommendations['best_practices'].append(
                'Monitor runtime metrics with CloudWatch filtered by application inference profile ARN'
            )

        if any(s in services_lower for s in ['lambda', 'aws lambda']):
            recommendations['immediate'].append(
                'Optimize Lambda memory settings based on function requirements'
            )
            recommendations['best_practices'].append(
                'Use AWS Lambda Power Tuning tool to find optimal memory settings'
            )

        if any(s in services_lower for s in ['s3', 'amazon s3']):
            recommendations['best_practices'].append(
                'Implement S3 lifecycle policies to transition older data to cheaper storage tiers'
            )

        if any(s in services_lower for s in ['dynamodb', 'amazon dynamodb']):
            recommendations['best_practices'].append(
                'Use DynamoDB on-demand capacity for unpredictable workloads'
            )

        # Limit the number of recommendations to avoid overwhelming the user
        recommendations['immediate'] = recommendations['immediate'][:5]
        recommendations['best_practices'] = recommendations['best_practices'][:5]

        return recommendations

class DaysParam(BaseModel):
    """Parameters for specifying the number of days to look back."""
    
    days: int = Field(
        default=7,
        description="Number of days to look back for cost data"
    )


class BedrockLogsParams(BaseModel):
    """Parameters for retrieving Bedrock invocation logs."""
    days: int = Field(
        default=7,
        description="Number of days to look back for Bedrock logs",
        ge=1,
        le=90
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region to retrieve logs from"
    )
    log_group_name: str = Field(
        description="Bedrock Log Group Name",
        default=os.environ.get('BEDROCK_LOG_GROUP_NAME', 'BedrockModelInvocationLogGroup')
    )

def get_instance_type_breakdown(ce_client, date, region, service, dimension_key):
    """
    Helper function to get instance type or usage type breakdown for a specific service.
    
    Args:
        ce_client: The Cost Explorer client
        date: The date to query
        region: The AWS region
        service: The AWS service name
        dimension_key: The dimension to group by (e.g., 'INSTANCE_TYPE' or 'USAGE_TYPE')
    
    Returns:
        DataFrame containing the breakdown or None if no data
    """
    tomorrow = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    
    instance_response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': date,
            'End': tomorrow
        },
        Granularity='DAILY',
        Filter={
            'And': [
                {
                    'Dimensions': {
                        'Key': 'REGION',
                        'Values': [region]
                    }
                },
                {
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service]
                    }
                }
            ]
        },
        Metrics=['UnblendedCost'],
        GroupBy=[
            {
                'Type': 'DIMENSION',
                'Key': dimension_key
            }
        ]
    )
    
    if ('ResultsByTime' in instance_response and 
        instance_response['ResultsByTime'] and 
        'Groups' in instance_response['ResultsByTime'][0] and 
        instance_response['ResultsByTime'][0]['Groups']):
        
        instance_data = instance_response['ResultsByTime'][0]
        instance_costs = []
        
        for instance_group in instance_data['Groups']:
            type_value = instance_group['Keys'][0]
            cost_value = float(instance_group['Metrics']['UnblendedCost']['Amount'])
            
            # Add a better label for the dimension used
            column_name = 'Instance Type' if dimension_key == 'INSTANCE_TYPE' else 'Usage Type'
            
            instance_costs.append({
                column_name: type_value,
                'Cost': cost_value
            })
        
        # Create DataFrame and sort by cost
        result_df = pd.DataFrame(instance_costs)
        if not result_df.empty:
            result_df = result_df.sort_values('Cost', ascending=False)
            return result_df
    
    return None

def get_bedrock_logs(params: BedrockLogsParams) -> Optional[pd.DataFrame]:
    """
    Retrieve Bedrock invocation logs for the last n days in a given region as a dataframe

    Args:
        params: Pydantic model containing parameters:
            - days: Number of days to look back (default: 7)
            - region: AWS region to query (default: us-east-1)

    Returns:
        pd.DataFrame: DataFrame containing the log data with columns:
            - timestamp: Timestamp of the invocation
            - region: AWS region
            - modelId: Bedrock model ID
            - userId: User ARN
            - inputTokens: Number of input tokens
            - completionTokens: Number of completion tokens
            - totalTokens: Total tokens used
    """
    # Initialize CloudWatch Logs client
    client = boto3.client("logs", region_name=params.region)

    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=params.days)

    # Convert to milliseconds since epoch
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)

    filtered_logs = []

    try:
        paginator = client.get_paginator("filter_log_events")

        # Parameters for the log query        
        query_params = {
            "logGroupName": params.log_group_name,  # Use the provided log group name
            "logStreamNames": [
                "aws/bedrock/modelinvocations"
            ],  # The specific log stream
            "startTime": start_time_ms,
            "endTime": end_time_ms,
        }
        
        # Paginate through results
        for page in paginator.paginate(**query_params):
            for event in page.get("events", []):
                try:
                    # Parse the message as JSON
                    message = json.loads(event["message"])

                    # Get user prompt from the input messages
                    prompt = ""
                    if (
                        message.get("input", {})
                        .get("inputBodyJson", {})
                        .get("messages")
                    ):
                        for msg in message["input"]["inputBodyJson"]["messages"]:
                            if msg.get("role") == "user" and msg.get("content"):
                                for content in msg["content"]:
                                    if content.get("text"):
                                        prompt += content["text"] + " "
                        prompt = prompt.strip()

                    # Extract only the required fields
                    filtered_event = {
                        "timestamp": message.get("timestamp"),
                        "region": message.get("region"),
                        "modelId": message.get("modelId"),
                        "userId": message.get("identity", {}).get("arn"),
                        "inputTokens": message.get("input", {}).get("inputTokenCount"),
                        "completionTokens": message.get("output", {}).get(
                            "outputTokenCount"
                        ),
                        "totalTokens": (
                            message.get("input", {}).get("inputTokenCount", 0)
                            + message.get("output", {}).get("outputTokenCount", 0)
                        ),
                    }

                    filtered_logs.append(filtered_event)
                except json.JSONDecodeError:
                    continue  # Skip non-JSON messages
                except KeyError:
                    continue  # Skip messages missing required fields
        
        # Create DataFrame if we have logs
        if filtered_logs:
            df = pd.DataFrame(filtered_logs)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        else:
            print("No logs found for the specified time period.")
            return None

    except client.exceptions.ResourceNotFoundException:
        print(
            f"Log group '{params.log_group_name}' or stream 'aws/bedrock/modelinvocations' not found"
        )
        return None
    except Exception as e:
        print(f"Error retrieving logs: {str(e)}")
        return None


