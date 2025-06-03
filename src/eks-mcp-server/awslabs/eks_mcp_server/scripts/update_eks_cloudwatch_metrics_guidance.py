#!/usr/bin/env python3
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

"""Script to scrape CloudWatch metrics data from AWS documentation and update the metrics guidance JSON file.

This script fetches the EKS and Kubernetes Container Insights metrics table from the AWS documentation,
extracts the metric names, dimensions, and descriptions, and updates the eks_cloudwatch_metrics_guidance.json file.
"""

import json
import logging
import os
import re
import requests
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, List


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL of the AWS documentation page containing the metrics table
DOCS_URL = 'https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html'

# Path to the metrics guidance JSON file (relative to the script location)
METRICS_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data',
    'eks_cloudwatch_metrics_guidance.json',
)


def fetch_documentation_page() -> str:
    """Fetch the AWS documentation page containing the metrics table.

    Returns:
        str: HTML content of the documentation page
    """
    try:
        response = requests.get(DOCS_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f'Failed to fetch documentation page: {e}')
        raise


def parse_metrics_table(html_content: str) -> List[Dict[str, Any]]:
    """Parse the metrics table from the HTML content.

    Args:
        html_content: HTML content of the documentation page

    Returns:
        List[Dict[str, Any]]: List of metrics with their names, dimensions, and descriptions
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the metrics table
    # Use a function that returns a boolean to avoid type issues
    def table_id_matcher(x: str) -> bool:
        return bool(x and 'w420aac24b7c33c15b7' in x)

    table = soup.find('table', id=table_id_matcher)
    if not table:
        logger.error('Metrics table not found in the documentation page')
        raise ValueError('Metrics table not found')

    metrics = []
    rows = table.find_all('tr') if isinstance(table, Tag) else []

    # Skip the header row
    for row in rows[1:]:
        cells = row.find_all('td') if isinstance(row, Tag) else []
        if len(cells) == 3:
            # Extract metric name
            metric_name_cell = cells[0]
            metric_name_element = None
            if isinstance(metric_name_cell, Tag):
                metric_name_element = metric_name_cell.find('code', attrs={'class': 'code'})

            if not metric_name_element:
                continue

            metric_name = (
                metric_name_element.text.strip() if hasattr(metric_name_element, 'text') else ''
            )

            # Extract dimensions
            dimensions_cell = cells[1]
            dimensions = []

            # Find all paragraph elements in the dimensions cell
            paragraphs = []
            if isinstance(dimensions_cell, Tag):
                paragraphs = dimensions_cell.find_all('p')

            # Process each paragraph
            for paragraph in paragraphs:
                # Find all code elements within this paragraph
                code_elements = []
                if isinstance(paragraph, Tag):
                    code_elements = paragraph.find_all('code', attrs={'class': 'code'})

                if len(code_elements) > 1:
                    # Multiple dimensions in a single paragraph - combine them
                    combined_dimensions = []
                    for code in code_elements:
                        if hasattr(code, 'text'):
                            combined_dimensions.append(code.text.strip())

                    # Join the dimensions with commas
                    if combined_dimensions:
                        dimensions.append(','.join(combined_dimensions))
                elif len(code_elements) == 1:
                    # Single dimension in a paragraph
                    code = code_elements[0]
                    if hasattr(code, 'text'):
                        dimension_text = code.text.strip()
                        if ',' in dimension_text:
                            # Already comma-separated in the text
                            dimensions.append(dimension_text)
                        else:
                            dimensions.append(dimension_text)

            # Also check for any code elements directly in the cell (not in paragraphs)
            dimension_codes = []
            if isinstance(dimensions_cell, Tag):
                dimension_codes = dimensions_cell.find_all(
                    'code', attrs={'class': 'code'}, recursive=False
                )

            for dimension_code in dimension_codes:
                if hasattr(dimension_code, 'text'):
                    dimension_text = dimension_code.text.strip()
                    if dimension_text and dimension_text not in dimensions:
                        dimensions.append(dimension_text)

            # Extract description
            description_cell = cells[2]
            description_element = None
            if isinstance(description_cell, Tag):
                description_element = description_cell.find('p')

            if not description_element:
                continue

            # Get the description and normalize whitespace (replace multiple spaces with a single space)
            description_text = (
                description_element.text.strip() if hasattr(description_element, 'text') else ''
            )
            description = re.sub(r'\s+', ' ', description_text)

            metrics.append(
                {'description': description, 'dimensions': dimensions, 'name': metric_name}
            )

    return metrics


def organize_metrics_by_resource_type(
    metrics: List[Dict[str, Any]],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Organize metrics by resource type based on their names.

    Args:
        metrics: List of metrics with their names, dimensions, and descriptions

    Returns:
        Dict[str, Dict[str, List[Dict[str, Any]]]]: Metrics organized by resource type
    """
    resource_types = {'cluster': [], 'namespace': [], 'node': [], 'pod': [], 'service': []}

    for metric in metrics:
        name = metric['name']

        # Determine resource type based on metric name prefix
        if name.startswith('cluster_'):
            resource_type = 'cluster'
        elif name.startswith('namespace_'):
            resource_type = 'namespace'
        elif name.startswith('node_'):
            resource_type = 'node'
        elif name.startswith('pod_'):
            resource_type = 'pod'
        elif name.startswith('service_'):
            resource_type = 'service'
        else:
            logger.warning(f'Unknown resource type for metric: {name}')
            continue

        resource_types[resource_type].append(metric)

    # Convert to the required format
    result = {}
    for resource_type, metrics_list in resource_types.items():
        result[resource_type] = {'metrics': metrics_list}

    return result


def load_existing_metrics() -> Dict[str, Any]:
    """Load existing metrics from the JSON file.

    Returns:
        Dict[str, Any]: Existing metrics data
    """
    try:
        with open(METRICS_FILE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f'Failed to load existing metrics file: {e}')
        return {}


def save_metrics(metrics_data: Dict[str, Any]) -> None:
    """Save metrics data to the JSON file.

    Args:
        metrics_data: Metrics data to save
    """
    try:
        with open(METRICS_FILE_PATH, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        logger.info(f'Metrics data saved to {METRICS_FILE_PATH}')
    except IOError as e:
        logger.error(f'Failed to save metrics data: {e}')
        raise


def main() -> None:
    """Main function to update the metrics guidance JSON file."""
    logger.info('Starting CloudWatch metrics guidance update')

    try:
        # Fetch the documentation page
        logger.info(f'Fetching documentation from {DOCS_URL}')
        html_content = fetch_documentation_page()

        # Parse the metrics table
        logger.info('Parsing metrics table')
        metrics = parse_metrics_table(html_content)
        logger.info(f'Found {len(metrics)} metrics in the documentation')

        # Organize metrics by resource type
        logger.info('Organizing metrics by resource type')
        organized_metrics = organize_metrics_by_resource_type(metrics)

        # Load existing metrics for comparison
        existing_metrics = load_existing_metrics()

        # Check if there are any changes
        if existing_metrics == organized_metrics:
            logger.info('No changes detected in metrics data')
        else:
            # Save the updated metrics
            logger.info('Changes detected in metrics data, updating file')
            save_metrics(organized_metrics)
            logger.info('Metrics guidance JSON file updated successfully')

    except Exception as e:
        logger.error(f'Failed to update metrics guidance: {e}')
        raise


if __name__ == '__main__':
    main()
