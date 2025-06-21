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

"""CloudWatch Application Signals MCP Server - Core server implementation."""

import boto3
import os
import sys
from . import __version__
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from time import perf_counter as timer


# Initialize FastMCP server
mcp = FastMCP('cloudwatch-appsignals')

# Configure logging
log_level = os.environ.get('MCP_CLOUDWATCH_APPSIGNALS_LOG_LEVEL', 'INFO').upper()
logger.remove()  # Remove default handler
logger.add(sys.stderr, level=log_level)
logger.debug(f'CloudWatch AppSignals MCP Server initialized with log level: {log_level}')

# Get AWS region from environment variable or use default
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
logger.debug(f'Using AWS region: {AWS_REGION}')

# Initialize AWS clients with logging
try:
    config = boto3.session.Config(
        user_agent_extra=f'awslabs.cloudwatch-appsignals-mcp-server/{__version__}'
    )
    logs_client = boto3.client('logs', region_name=AWS_REGION, config=config)
    logger.debug('AWS CloudWatch Logs client initialized successfully')
except Exception as e:
    logger.error(f'Failed to initialize AWS CloudWatch Logs client: {str(e)}')
    raise


def remove_null_values(data: dict) -> dict:
    """Remove keys with None values from a dictionary.

    Args:
        data: Dictionary to clean

    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in data.items() if v is not None}


@mcp.tool()
async def list_monitored_services() -> str:
    """List all services monitored by AWS Application Signals.

    Use this tool to:
    - Get an overview of all monitored services
    - See service names, types, and key attributes
    - Identify which services are being tracked
    - Count total number of services in your environment

    Returns a formatted list showing:
    - Service name and type
    - Key attributes (Environment, Platform, etc.)
    - Total count of services

    This is typically the first tool to use when starting monitoring or investigation.
    """
    start_time_perf = timer()
    logger.debug('Starting list_application_signals_services request')

    try:
        appsignals = boto3.client('application-signals', region_name=AWS_REGION)
        logger.debug('Application Signals client created')

        # Calculate time range (last 24 hours)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        # Get all services
        logger.debug(f'Querying services for time range: {start_time} to {end_time}')
        response = appsignals.list_services(StartTime=start_time, EndTime=end_time, MaxResults=100)
        services = response.get('ServiceSummaries', [])
        logger.debug(f'Retrieved {len(services)} services from Application Signals')

        if not services:
            logger.warning('No services found in Application Signals')
            return 'No services found in Application Signals.'

        result = f'Application Signals Services ({len(services)} total):\n\n'

        for service in services:
            # Extract service name from KeyAttributes
            key_attrs = service.get('KeyAttributes', {})
            service_name = key_attrs.get('Name', 'Unknown')
            service_type = key_attrs.get('Type', 'Unknown')

            result += f'• Service: {service_name}\n'
            result += f'  Type: {service_type}\n'

            # Add key attributes
            if key_attrs:
                result += '  Key Attributes:\n'
                for key, value in key_attrs.items():
                    result += f'    {key}: {value}\n'

            result += '\n'

        elapsed_time = timer() - start_time_perf
        logger.debug(f'list_monitored_services completed in {elapsed_time:.3f}s')
        return result

    except ClientError as e:
        logger.error(
            f'AWS ClientError in list_monitored_services: {e.response["Error"]["Code"]} - {e.response["Error"]["Message"]}'
        )
        return f'AWS Error: {e.response["Error"]["Message"]}'
    except Exception as e:
        logger.error(f'Unexpected error in list_monitored_services: {str(e)}', exc_info=True)
        return f'Error: {str(e)}'


@mcp.tool()
async def get_service_detail(
    service_name: str = Field(
        ..., description='Name of the service to get details for (case-sensitive)'
    ),
) -> str:
    """Get detailed information about a specific Application Signals service.

    Use this tool when you need to:
    - Understand a service's configuration and setup
    - Understand where this servive is deployed and where it is running such as EKS, Lambda, etc.
    - See what metrics are available for a service
    - Find log groups associated with the service
    - Get service metadata and attributes

    Returns comprehensive details including:
    - Key attributes (Type, Environment, Platform)
    - Available CloudWatch metrics with namespaces
    - Metric dimensions and types
    - Associated log groups for debugging

    This tool is essential before querying specific metrics, as it shows
    which metrics are available for the service.
    """
    start_time_perf = timer()
    logger.debug(f'Starting get_service_healthy_detail request for service: {service_name}')

    try:
        appsignals = boto3.client('application-signals', region_name=AWS_REGION)
        logger.debug('Application Signals client created')

        # Calculate time range (last 24 hours)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        # First, get all services to find the one we want
        services_response = appsignals.list_services(
            StartTime=start_time, EndTime=end_time, MaxResults=100
        )

        # Find the service with matching name
        target_service = None
        for service in services_response.get('ServiceSummaries', []):
            key_attrs = service.get('KeyAttributes', {})
            if key_attrs.get('Name') == service_name:
                target_service = service
                break

        if not target_service:
            logger.warning(f"Service '{service_name}' not found in Application Signals")
            return f"Service '{service_name}' not found in Application Signals."

        # Get detailed service information
        logger.debug(f'Getting detailed information for service: {service_name}')
        service_response = appsignals.get_service(
            StartTime=start_time, EndTime=end_time, KeyAttributes=target_service['KeyAttributes']
        )

        service_details = service_response['Service']

        # Build detailed response
        result = f'Service Details: {service_name}\n\n'

        # Key Attributes
        key_attrs = service_details.get('KeyAttributes', {})
        if key_attrs:
            result += 'Key Attributes:\n'
            for key, value in key_attrs.items():
                result += f'  {key}: {value}\n'
            result += '\n'

        # Attribute Maps (Platform, Application, Telemetry info)
        attr_maps = service_details.get('AttributeMaps', [])
        if attr_maps:
            result += 'Additional Attributes:\n'
            for attr_map in attr_maps:
                for key, value in attr_map.items():
                    result += f'  {key}: {value}\n'
            result += '\n'

        # Metric References
        metric_refs = service_details.get('MetricReferences', [])
        if metric_refs:
            result += f'Metric References ({len(metric_refs)} total):\n'
            for metric in metric_refs:
                result += f'  • {metric.get("Namespace", "")}/{metric.get("MetricName", "")}\n'
                result += f'    Type: {metric.get("MetricType", "")}\n'
                dimensions = metric.get('Dimensions', [])
                if dimensions:
                    result += '    Dimensions: '
                    dim_strs = [f'{d["Name"]}={d["Value"]}' for d in dimensions]
                    result += ', '.join(dim_strs) + '\n'
                result += '\n'

        # Log Group References
        log_refs = service_details.get('LogGroupReferences', [])
        if log_refs:
            result += f'Log Group References ({len(log_refs)} total):\n'
            for log_ref in log_refs:
                log_group = log_ref.get('Identifier', 'Unknown')
                result += f'  • {log_group}\n'
            result += '\n'

        elapsed_time = timer() - start_time_perf
        logger.debug(f"get_service_detail completed for '{service_name}' in {elapsed_time:.3f}s")
        return result

    except ClientError as e:
        logger.error(
            f"AWS ClientError in get_service_healthy_detail for '{service_name}': {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        return f'AWS Error: {e.response["Error"]["Message"]}'
    except Exception as e:
        logger.error(
            f"Unexpected error in get_service_healthy_detail for '{service_name}': {str(e)}",
            exc_info=True,
        )
        return f'Error: {str(e)}'


def main():
    """Run the MCP server."""
    import mcp

    logger.debug('Starting CloudWatch AppSignals MCP server')
    try:
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.debug('Server shutdown by user')
    except Exception as e:
        logger.error(f'Server error: {e}', exc_info=True)
        raise


if __name__ == '__main__':
    main()
