# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the \"License\"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Prometheus MCP Server implementation."""

import os
import json
import sys
import argparse
from typing import Any, Dict, List, Optional
import time
import logging
from urllib.parse import urlparse

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
import requests
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.prometheus_mcp_server.models import PrometheusConfig
from awslabs.prometheus_mcp_server.consts import (
    DEFAULT_AWS_REGION,
    DEFAULT_SERVICE_NAME,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    API_VERSION_PATH,
    LOG_FORMAT,
    ENV_AWS_PROFILE,
    ENV_AWS_REGION,
    ENV_PROMETHEUS_URL,
    ENV_AWS_SERVICE_NAME,
    ENV_LOG_LEVEL,
    SERVER_INSTRUCTIONS
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Prometheus MCP Server')
    parser.add_argument('--profile', type=str, help='AWS profile name to use')
    parser.add_argument('--region', type=str, help='AWS region to use')
    parser.add_argument('--url', type=str, help='Prometheus URL')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()

def load_config(args):
    """Load configuration from file, environment variables, and command line arguments."""
    # Load .env file if it exists
    load_dotenv()
    
    # Initialize config with default values
    config_data = {
        'aws_profile': None,
        'aws_region': DEFAULT_AWS_REGION,
        'prometheus_url': '',
        'service_name': DEFAULT_SERVICE_NAME,
        'max_retries': DEFAULT_MAX_RETRIES,
        'retry_delay': DEFAULT_RETRY_DELAY,
    }
    
    # Load from config file if specified
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                file_config = json.load(f)
                config_data.update(file_config)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Override with environment variables
    if os.getenv(ENV_AWS_PROFILE):
        config_data['aws_profile'] = os.getenv(ENV_AWS_PROFILE)
    if os.getenv(ENV_AWS_REGION):
        config_data['aws_region'] = os.getenv(ENV_AWS_REGION)
    if os.getenv(ENV_PROMETHEUS_URL):
        config_data['prometheus_url'] = os.getenv(ENV_PROMETHEUS_URL)
    if os.getenv(ENV_AWS_SERVICE_NAME):
        config_data['service_name'] = os.getenv(ENV_AWS_SERVICE_NAME)
    
    # Override with command line arguments
    if args.profile:
        config_data['aws_profile'] = args.profile
    if args.region:
        config_data['aws_region'] = args.region
    if args.url:
        config_data['prometheus_url'] = args.url
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    return config_data

def setup_environment(config):
    """Setup and validate environment variables."""
    logger.info("Setting up environment...")
    
    # Validate Prometheus URL
    if not config['prometheus_url']:
        logger.error("Prometheus URL not configured")
        return False
    
    try:
        parsed_url = urlparse(config['prometheus_url'])
        if not all([parsed_url.scheme, parsed_url.netloc]):
            logger.error(f"Invalid Prometheus URL format: {config['prometheus_url']}")
            return False
    except Exception as e:
        logger.error(f"Error parsing Prometheus URL: {e}")
        return False
    
    logger.info("Prometheus configuration:")
    logger.info(f"  Server URL: {config['prometheus_url']}")
    logger.info(f"  AWS Region: {config['aws_region']}")
    
    # Test AWS credentials
    try:
        session = boto3.Session(profile_name=config['aws_profile'], region_name=config['aws_region'])
        credentials = session.get_credentials()
        if credentials:
            logger.info("  AWS Credentials: Available")
            if credentials.token:
                logger.info("  Credential Type: Temporary (includes session token)")
            else:
                logger.info("  Credential Type: Long-term")
            
            # Test if credentials have necessary permissions
            try:
                sts = session.client('sts')
                identity = sts.get_caller_identity()
                logger.info(f"  AWS Identity: {identity['Arn']}")
            except ClientError as e:
                logger.warning(f"Could not verify AWS identity: {e}")
        else:
            logger.error("  AWS Credentials: Not found")
            return False
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        return False
    except Exception as e:
        logger.error(f"Error setting up AWS session: {e}")
        return False
    
    return True

def make_prometheus_request(endpoint: str, params: Dict = None, max_retries: int = 3) -> Any:
    """Make a request to the Prometheus HTTP API with AWS SigV4 authentication."""
    if not config.prometheus_url:
        raise ValueError("Prometheus URL not configured")

    # Ensure the URL ends with /api/v1
    base_url = config.prometheus_url
    if not base_url.endswith(API_VERSION_PATH):
        base_url = f"{base_url.rstrip('/')}{API_VERSION_PATH}"

    url = f"{base_url}/{endpoint.lstrip('/')}"
    
    # Create AWS request
    aws_request = AWSRequest(
        method='GET',
        url=url,
        params=params
    )

    # Sign request with SigV4
    session = boto3.Session(profile_name=config.aws_profile, region_name=config.aws_region)
    credentials = session.get_credentials()
    if not credentials:
        raise ValueError("AWS credentials not found")

    SigV4Auth(credentials, config.service_name, config.aws_region).add_auth(aws_request)
    
    # Convert to requests format
    prepared_request = requests.Request(
        method=aws_request.method,
        url=aws_request.url,
        headers=dict(aws_request.headers),
        params=params
    ).prepare()

    # Send request with retry logic
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            with requests.Session() as session:
                logger.debug(f"Making request to {url} (attempt {retry_count + 1}/{max_retries})")
                response = session.send(prepared_request)
                response.raise_for_status()
                data = response.json()

                if data['status'] != 'success':
                    error_msg = data.get('error', 'Unknown error')
                    logger.error(f"Prometheus API request failed: {error_msg}")
                    raise RuntimeError(f"Prometheus API request failed: {error_msg}")
                
                return data['data']
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_exception = e
            retry_count += 1
            if retry_count < max_retries:
                retry_delay = config.retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                logger.warning(f"Request failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Request failed after {max_retries} attempts: {e}")
                raise
    
    if last_exception:
        raise last_exception
    return None

def test_prometheus_connection():
    """Test the connection to Prometheus."""
    logger.info("Testing Prometheus connection...")
    try:
        make_prometheus_request("label/__name__/values")
        logger.info("Successfully connected to Prometheus!")
        return True
    except Exception as e:
        logger.error(f"Error connecting to Prometheus: {e}")
        return False

# Initialize MCP
mcp = FastMCP(name="Prometheus MCP", instructions=SERVER_INSTRUCTIONS)

# Global config object
config = None

@mcp.tool(description="Execute a PromQL instant query against Prometheus")
async def execute_query(
    query: str = Field(..., description="The PromQL query to execute"),
    time: Optional[str] = Field(
        None, 
        description="Optional timestamp for query evaluation (RFC3339 or Unix timestamp)"
    )
) -> Dict[str, Any]:
    """Execute an instant query and return the result.
    
    ## Usage
    - Use this tool to execute a PromQL query at a specific instant in time
    - The query will return the current value of the specified metrics
    - For time series data over a range, use execute_range_query instead
    
    ## Example queries
    - `up` - Shows which targets are up
    - `rate(node_cpu_seconds_total{mode="system"}[1m])` - CPU usage rate
    - `sum by(instance) (rate(node_network_receive_bytes_total[5m]))` - Network receive rate by instance
    """
    params = {'query': query}
    if time:
        params['time'] = time
    
    return make_prometheus_request('query', params, config.max_retries)

@mcp.tool(description="Execute a PromQL range query with start time, end time, and step interval")
async def execute_range_query(
    query: str = Field(..., description="The PromQL query to execute"),
    start: str = Field(..., description="Start timestamp (RFC3339 or Unix timestamp)"),
    end: str = Field(..., description="End timestamp (RFC3339 or Unix timestamp)"),
    step: str = Field(..., description="Query resolution step width (duration format, e.g. '15s', '1m', '1h')")
) -> Dict[str, Any]:
    """Execute a range query and return the result.
    
    ## Usage
    - Use this tool to execute a PromQL query over a time range
    - The query will return a series of values for the specified time range
    - Useful for generating time series data for graphs or trend analysis
    
    ## Example
    - Query: `rate(node_cpu_seconds_total{mode="system"}[5m])`
    - Start: `2023-04-01T00:00:00Z`
    - End: `2023-04-01T01:00:00Z`
    - Step: `5m`
    
    This will return CPU usage rate sampled every 5 minutes over a 1-hour period.
    """
    params = {
        'query': query,
        'start': start,
        'end': end,
        'step': step
    }
    
    return make_prometheus_request('query_range', params, config.max_retries)

@mcp.tool(description="List all available metrics in Prometheus")
async def list_metrics() -> List[str]:
    """Get a list of all metric names.
    
    ## Usage
    - Use this tool to discover available metrics in the Prometheus server
    - Returns a sorted list of all metric names
    - Useful for exploration before crafting specific queries
    
    ## Example
    ```
    metrics = await list_metrics()
    print("Available metrics:", metrics[:10])  # Show first 10 metrics
    ```
    """
    data = make_prometheus_request('label/__name__/values', max_retries=config.max_retries)
    return sorted(data)

@mcp.tool(description="Get information about the Prometheus server configuration")
async def get_server_info() -> Dict[str, Any]:
    """Get information about the Prometheus server configuration.
    
    ## Usage
    - Use this tool to retrieve the current server configuration
    - Returns details about the Prometheus URL, AWS region, profile, and service name
    - Useful for debugging connection issues
    
    ## Example
    ```
    info = await get_server_info()
    print(f"Connected to Prometheus at {info['prometheus_url']} in region {info['aws_region']}")
    ```
    """
    return {
        "prometheus_url": config.prometheus_url,
        "aws_region": config.aws_region,
        "aws_profile": config.aws_profile or "default",
        "service_name": config.service_name
    }

def main():
    """Run the MCP server with CLI argument support."""
    logger.info("Starting Prometheus MCP Server...")
    
    # Parse arguments
    args = parse_arguments()
    
    # Load configuration
    config_data = load_config(args)
    
    # Create config object
    global config
    config = PrometheusConfig(
        prometheus_url=config_data['prometheus_url'],
        aws_region=config_data['aws_region'],
        aws_profile=config_data['aws_profile'],
        service_name=config_data['service_name'],
        retry_delay=config_data['retry_delay'],
        max_retries=config_data['max_retries']
    )
    
    # Setup environment
    if not setup_environment(config_data):
        sys.exit(1)
    
    # Test connection
    if not test_prometheus_connection():
        sys.exit(1)
    
    logger.info("Starting server...")
    # Run with stdio transport
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()