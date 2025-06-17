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

"""Prometheus MCP Server implementation."""

import argparse
import boto3
import json
import os
import requests
import sys
import time
from awslabs.prometheus_mcp_server.consts import (
    API_VERSION_PATH,
    DEFAULT_AWS_REGION,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SERVICE_NAME,
    ENV_AWS_PROFILE,
    ENV_AWS_REGION,
    ENV_AWS_SERVICE_NAME,
    ENV_LOG_LEVEL,
    ENV_PROMETHEUS_URL,
    SERVER_INSTRUCTIONS,
)
from awslabs.prometheus_mcp_server.models import (
    MetricsList,
    PrometheusConfig,
    ServerInfo,
)
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Optional
from urllib.parse import urlparse


# Configure loguru
logger.remove()
logger.add(sys.stderr, level=os.getenv(ENV_LOG_LEVEL, 'INFO'))


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
        'prometheus_url': None,
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
            logger.info(f'Loaded configuration from {args.config}')
        except Exception as e:
            logger.error(f'Error loading config file: {e}')

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
        logger.level('DEBUG')
        logger.debug('Debug logging enabled')

    return config_data


def find_active_workspace(aps_client):
    """Find an active Prometheus workspace.
    
    Args:
        aps_client: The AMP boto3 client
        
    Returns:
        The first active workspace found, or None if no active workspaces exist
    """
    try:
        workspaces = aps_client.list_workspaces()
        active_workspaces = [ws for ws in workspaces['workspaces'] if ws['status']['statusCode'] == 'ACTIVE']
        
        if active_workspaces:
            logger.info(f'Found {len(active_workspaces)} active Prometheus workspaces')
            return active_workspaces[0]
        else:
            logger.warning('No active Prometheus workspaces found')
            return None
    except Exception as e:
        logger.error(f'Error finding active workspaces: {e}')
        return None


def setup_environment(config_data):
    """Setup and validate environment variables."""
    logger.info('Setting up environment...')

    try:
        # Create session with profile if specified
        if config_data['aws_profile']:
            logger.info(f'  Using AWS Profile: {config_data["aws_profile"]}')
            session = boto3.Session(
                profile_name=config_data['aws_profile'], 
                region_name=config_data['aws_region']
            )
        else:
            logger.info('  Using default AWS credentials')
            session = boto3.Session(region_name=config_data['aws_region'])

        # If Prometheus URL is not provided, try to get it from AWS
        if not config_data['prometheus_url']:
            try:
                aps_client = session.client('amp')
                active_workspace = find_active_workspace(aps_client)
                if active_workspace:
                    workspace_id = active_workspace['workspaceId']
                    region = config_data['aws_region']
                    config_data['prometheus_url'] = f'https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}'
                    logger.info(f'Found active Prometheus workspace: {workspace_id}')
                else:
                    logger.error('No active Prometheus workspaces found in the current region')
                    return False
            except Exception as e:
                logger.error(f'Error getting Prometheus workspace: {e}')
                return False

        # Validate Prometheus URL
        parsed_url = urlparse(config_data['prometheus_url'])
        if not all([parsed_url.scheme, parsed_url.netloc]):
            logger.error(f'ERROR: Invalid Prometheus URL format: {config_data["prometheus_url"]}')
            logger.error('URL must include scheme (https://) and hostname')
            return False

        # Verify URL points to AWS Prometheus
        if not (
            parsed_url.netloc.endswith('.amazonaws.com') and 'aps-workspaces' in parsed_url.netloc
        ):
            logger.warning(
                f"WARNING: URL doesn't appear to be an AWS Managed Prometheus endpoint: {config_data['prometheus_url']}"
            )
            logger.warning(
                'Expected format: https://aps-workspaces.[region].amazonaws.com/workspaces/ws-[id]'
            )

        logger.info('Prometheus configuration:')
        logger.info(f'  Server URL: {config_data["prometheus_url"]}')
        logger.info(f'  AWS Region: {config_data["aws_region"]}')

        # Test AWS credentials
        if not config_data['aws_region']:
            logger.error(
                'ERROR: AWS region not configured. Please set using --region parameter or AWS_REGION environment variable.'
            )
            return False

        credentials = session.get_credentials()
        if credentials:
            logger.info('  AWS Credentials: Available')
            if credentials.token:
                logger.info('  Credential Type: Temporary (includes session token)')
            else:
                logger.info('  Credential Type: Long-term')

            # Test if credentials have necessary permissions
            try:
                sts = session.client('sts')
                identity = sts.get_caller_identity()
                logger.info(f'  AWS Identity: {identity["Arn"]}')
            except ClientError as e:
                logger.warning(f'WARNING: Could not verify AWS identity: {e}')
                logger.warning(
                    'This may indicate insufficient permissions for STS:GetCallerIdentity'
                )
        else:
            logger.error('ERROR: AWS Credentials not found')
            logger.error('Please configure AWS credentials using:')
            logger.error('  - AWS CLI: aws configure')
            logger.error('  - Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY')
            logger.error('  - Or specify a profile with --profile')
            return False
    except NoCredentialsError:
        logger.error('ERROR: AWS credentials not found')
        logger.error('Please configure AWS credentials using:')
        logger.error('  - AWS CLI: aws configure')
        logger.error('  - Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY')
        logger.error('  - Or specify a profile with --profile')
        return False
    except Exception as e:
        logger.error(f'ERROR: Error setting up AWS session: {e}')
        return False

    return True


def validate_params(params: Dict) -> bool:
    """Validate request parameters for potential security issues.

    Args:
        params: The parameters to validate

    Returns:
        bool: True if the parameters are safe, False otherwise
    """
    if not params:
        return True

    # List of dangerous patterns to check for
    dangerous_patterns = [
        # Command injection attempts
        ';',
        '&&',
        '||',
        '`',
        '$(',
        '${',
        # File access attempts
        'file://',
        '/etc/',
        '/var/log',
        # Network access attempts
        'http://',
        'https://',
    ]

    # Check each parameter value
    for key, value in params.items():
        if not isinstance(value, str):
            continue

        for pattern in dangerous_patterns:
            if pattern in value:
                logger.warning(f'Potentially dangerous parameter detected: {key}={value}')
                return False

    return True


async def make_prometheus_request(
    endpoint: str, params: Optional[Dict] = None, max_retries: int = 3
) -> Any:
    """Make a request to the Prometheus HTTP API with AWS SigV4 authentication.

    Args:
        endpoint: The Prometheus API endpoint to call
        params: Query parameters to include in the request
        max_retries: Maximum number of retry attempts

    Returns:
        The data portion of the Prometheus API response

    Raises:
        ValueError: If Prometheus URL or AWS credentials are not configured
        RuntimeError: If the Prometheus API returns an error status
        requests.RequestException: If there's a network or HTTP error
        json.JSONDecodeError: If the response is not valid JSON
    """
    if not config or not config.prometheus_url:
        raise ValueError('Prometheus URL not configured')

    # Validate endpoint
    if not isinstance(endpoint, str):
        raise ValueError('Endpoint must be a string')

    if ';' in endpoint or '&&' in endpoint or '||' in endpoint:
        raise ValueError('Invalid endpoint: potentially dangerous characters detected')

    # Validate parameters
    if params and not validate_params(params):
        raise ValueError('Invalid parameters: potentially dangerous values detected')

    # Ensure the URL ends with /api/v1
    base_url = config.prometheus_url
    if not base_url.endswith(API_VERSION_PATH):
        base_url = f'{base_url.rstrip("/")}{API_VERSION_PATH}'

    url = f'{base_url}/{endpoint.lstrip("/")}'

    # Create AWS request
    aws_request = AWSRequest(method='GET', url=url, params=params or {})

    # Sign request with SigV4
    session = boto3.Session(profile_name=config.aws_profile, region_name=config.aws_region)
    credentials = session.get_credentials()
    if not credentials:
        raise ValueError('AWS credentials not found')

    SigV4Auth(credentials, config.service_name, config.aws_region).add_auth(aws_request)

    # Convert to requests format
    prepared_request = requests.Request(
        method=aws_request.method,
        url=aws_request.url,
        headers=dict(aws_request.headers),
        params=params or {},
    ).prepare()

    # Send request with retry logic
    retry_count = 0
    last_exception = None
    retry_delay_seconds = 1  # Default retry delay if config.retry_delay is None

    while retry_count < max_retries:
        try:
            with requests.Session() as session:
                logger.debug(f'Making request to {url} (attempt {retry_count + 1}/{max_retries})')
                response = session.send(prepared_request)
                response.raise_for_status()
                data = response.json()

                if data['status'] != 'success':
                    error_msg = data.get('error', 'Unknown error')
                    logger.error(f'Prometheus API request failed: {error_msg}')
                    raise RuntimeError(f'Prometheus API request failed: {error_msg}')

                return data['data']
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_exception = e
            retry_count += 1
            if retry_count < max_retries:
                if config and hasattr(config, 'retry_delay') and config.retry_delay is not None:
                    retry_delay_seconds = config.retry_delay * (
                        2 ** (retry_count - 1)
                    )  # Exponential backoff
                else:
                    retry_delay_seconds = 1 * (
                        2 ** (retry_count - 1)
                    )  # Default exponential backoff
                logger.warning(f'Request failed: {e}. Retrying in {retry_delay_seconds}s...')
                time.sleep(retry_delay_seconds)
            else:
                logger.error(f'Request failed after {max_retries} attempts: {e}')
                raise

    if last_exception:
        raise last_exception
    return None


async def test_prometheus_connection():
    """Test the connection to Prometheus.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    logger.info('Testing Prometheus connection...')
    try:
        await make_prometheus_request('label/__name__/values', params={})
        logger.info('Successfully connected to Prometheus!')
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'AccessDeniedException':
            logger.error('ERROR: Access denied when connecting to Prometheus')
            logger.error('Please check that your AWS credentials have the following permissions:')
            logger.error('  - aps:QueryMetrics')
            logger.error('  - aps:GetLabels')
            logger.error('  - aps:GetMetricMetadata')
        elif error_code == 'ResourceNotFoundException':
            logger.error('ERROR: Prometheus workspace not found')
            prometheus_url = 'Not configured'
            if config and hasattr(config, 'prometheus_url') and config.prometheus_url:
                prometheus_url = config.prometheus_url
            logger.error(
                f'Please verify the workspace ID in your Prometheus URL: {prometheus_url}'
            )
        else:
            logger.error(f'ERROR: AWS API error when connecting to Prometheus: {error_code}')
            logger.error(f'Details: {str(e)}')
        return False
    except requests.RequestException as e:
        logger.error(f'ERROR: Network error when connecting to Prometheus: {str(e)}')
        logger.error('Please check your network connection and Prometheus URL')
        return False
    except Exception as e:
        logger.error(f'ERROR: Error connecting to Prometheus: {str(e)}')
        logger.error('Common issues:')
        logger.error('1. Incorrect Prometheus URL')
        logger.error('2. Missing or incorrect AWS region')
        logger.error('3. Invalid AWS credentials or insufficient permissions')
        return False


# Initialize MCP
mcp = FastMCP(
    name='awslabs-prometheus-mcp-server',
    instructions=SERVER_INSTRUCTIONS,
    dependencies=[
        'boto3',
        'requests',
        'pydantic',
        'python-dotenv',
        'loguru',
    ],
)

# Global config object
config = None  # Will be initialized in main()


@mcp.tool(name='ExecuteQuery')
def validate_query(query: str) -> bool:
    """Validate a PromQL query for potential security issues.

    Args:
        query: The PromQL query to validate

    Returns:
        bool: True if the query is safe, False otherwise

    This function checks for potentially dangerous patterns in PromQL queries.
    """
    # List of dangerous patterns to check for
    dangerous_patterns = [
        # Command injection attempts
        ';',
        '&&',
        '||',
        '`',
        '$(',
        '${',
        # File access attempts
        'file://',
        '/etc/',
        '/var/log',
        # Network access attempts
        'http://',
        'https://',
    ]

    # Check for dangerous patterns
    for pattern in dangerous_patterns:
        if pattern in query:
            logger.warning(f'Potentially dangerous query pattern detected: {pattern}')
            return False

    return True


@mcp.tool(name='ExecuteQuery')
async def execute_query(
    ctx: Context,
    query: str = Field(..., description='The PromQL query to execute'),
    time: Optional[str] = Field(
        None, description='Optional timestamp for query evaluation (RFC3339 or Unix timestamp)'
    ),
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
    try:
        logger.info(f'Executing instant query: {query}')

        # Validate query for security
        if not validate_query(query):
            error_msg = 'Query validation failed: potentially dangerous query pattern detected'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise ValueError(error_msg)

        params = {'query': query}
        if time:
            params['time'] = time

        max_retries = 3  # Default value
        if config and hasattr(config, 'max_retries') and config.max_retries is not None:
            max_retries = config.max_retries

        return await make_prometheus_request('query', params, max_retries)
    except Exception as e:
        error_msg = f'Error executing query: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise


@mcp.tool(name='ExecuteRangeQuery')
async def execute_range_query(
    ctx: Context,
    query: str = Field(..., description='The PromQL query to execute'),
    start: str = Field(..., description='Start timestamp (RFC3339 or Unix timestamp)'),
    end: str = Field(..., description='End timestamp (RFC3339 or Unix timestamp)'),
    step: str = Field(
        ..., description="Query resolution step width (duration format, e.g. '15s', '1m', '1h')"
    ),
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
    try:
        logger.info(f'Executing range query: {query} from {start} to {end} with step {step}')

        # Validate query for security
        if not validate_query(query):
            error_msg = 'Query validation failed: potentially dangerous query pattern detected'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise ValueError(error_msg)

        params = {'query': query, 'start': start, 'end': end, 'step': step}

        max_retries = 3  # Default value
        if config and hasattr(config, 'max_retries') and config.max_retries is not None:
            max_retries = config.max_retries

        return await make_prometheus_request('query_range', params, max_retries)
    except Exception as e:
        error_msg = f'Error executing range query: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise


@mcp.tool(name='ListMetrics')
async def list_metrics(ctx: Context) -> MetricsList:
    """Get a list of all metric names.

    ## Usage
    - Use this tool to discover available metrics in the Prometheus server
    - Returns a sorted list of all metric names
    - Useful for exploration before crafting specific queries

    ## Example
    ```
    metrics_response = await list_metrics()
    print('Available metrics:', metrics_response.metrics[:10])  # Show first 10 metrics
    ```
    """
    try:
        logger.info('Listing all available metrics')
        max_retries = 3  # Default value
        if config and hasattr(config, 'max_retries') and config.max_retries is not None:
            max_retries = config.max_retries

        data = await make_prometheus_request(
            'label/__name__/values', params={}, max_retries=max_retries
        )
        return MetricsList(metrics=sorted(data))
    except Exception as e:
        error_msg = f'Error listing metrics: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise


@mcp.tool(name='GetServerInfo')
async def get_server_info(ctx: Context) -> ServerInfo:
    """Get information about the Prometheus server configuration.

    ## Usage
    - Use this tool to retrieve the current server configuration
    - Returns details about the Prometheus URL, AWS region, profile, and service name
    - Useful for debugging connection issues

    ## Example
    ```
    info = await get_server_info()
    print(f'Connected to Prometheus at {info.prometheus_url} in region {info.aws_region}')
    ```
    """
    try:
        logger.info('Retrieving server configuration information')
        if not config:
            return ServerInfo(
                prometheus_url='Not configured',
                aws_region='Not configured',
                aws_profile='Not configured',
                service_name='Not configured',
            )

        return ServerInfo(
            prometheus_url=config.prometheus_url or 'Not configured',
            aws_region=config.aws_region or 'Not configured',
            aws_profile=config.aws_profile or 'default',
            service_name=config.service_name or DEFAULT_SERVICE_NAME,
        )
    except Exception as e:
        error_msg = f'Error retrieving server info: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise


@mcp.tool(name='SetPrometheusWorkspace')
async def set_prometheus_workspace(
    ctx: Context,
    workspace_id: str = Field(..., description='The Prometheus workspace ID to use'),
    region: Optional[str] = Field(None, description='AWS region (defaults to current region)'),
) -> ServerInfo:
    """Set the Prometheus workspace ID and build the URL.

    ## Usage
    - Use this tool to set the Prometheus workspace ID
    - The URL will be built automatically using the workspace ID and region
    - Returns updated server configuration

    ## Example
    ```
    info = await set_prometheus_workspace(workspace_id='ws-12345678-abcd-1234-efgh-123456789012')
    print(f'Connected to Prometheus workspace: {info.prometheus_url}')
    ```
    """
    try:
        logger.info(f'Setting Prometheus workspace ID to: {workspace_id}')
        
        # Validate workspace ID format
        if not workspace_id.startswith('ws-'):
            logger.warning(f'Workspace ID "{workspace_id}" does not start with "ws-", which is unusual')
        
        # Use provided region or current config region or default
        aws_region = region
        if not aws_region and config and config.aws_region:
            aws_region = config.aws_region
        if not aws_region:
            aws_region = DEFAULT_AWS_REGION
            
        # Build the URL
        url = f'https://aps-workspaces.{aws_region}.amazonaws.com/workspaces/{workspace_id}'
        logger.info(f'Built Prometheus URL: {url}')
        
        # Update global config
        global config
        if not config:
            config = PrometheusConfig(
                prometheus_url=url,
                aws_region=aws_region,
                aws_profile=None,
                service_name=DEFAULT_SERVICE_NAME,
            )
        else:
            config.prometheus_url = url
            if region:  # Only update region if explicitly provided
                config.aws_region = aws_region

        # Test connection with new URL
        if not await test_prometheus_connection():
            error_msg = 'Failed to connect to Prometheus with new workspace ID'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info('Successfully updated Prometheus workspace')
        return await get_server_info(ctx)
    except Exception as e:
        error_msg = f'Error setting Prometheus workspace: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise





async def async_main():
    """Run the async initialization tasks."""
    # Test connection
    if not await test_prometheus_connection():
        logger.error('Prometheus connection test failed')
        sys.exit(1)

    logger.info('Prometheus connection successful')


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting Prometheus MCP Server...')

    # Parse arguments
    args = parse_arguments()

    # Load configuration
    config_data = load_config(args)

    # If no URL is provided, try to discover one
    if not config_data['prometheus_url']:
        logger.info('No Prometheus URL provided, attempting to auto-discover...')
        if not setup_environment(config_data):
            logger.error('Environment setup failed')
            sys.exit(1)
        
        # Double-check that we have a URL after setup_environment
        if not config_data['prometheus_url']:
            logger.error('Failed to discover Prometheus URL')
            sys.exit(1)
    else:
        # If URL is provided, still validate AWS credentials
        logger.info(f'Using provided Prometheus URL: {config_data["prometheus_url"]}')
        # Just validate AWS credentials without changing the URL
        if not setup_environment(config_data):
            logger.error('Environment setup failed')
            sys.exit(1)

    # Create config object
    global config
    config = PrometheusConfig(
        prometheus_url=config_data['prometheus_url'],
        aws_region=config_data['aws_region'],
        aws_profile=config_data['aws_profile'],
        service_name=config_data['service_name'],
        retry_delay=config_data['retry_delay'],
        max_retries=config_data['max_retries'],
    )

    # Run async initialization in an event loop
    import asyncio

    asyncio.run(async_main())

    logger.info('Starting server...')
    
    # Run with stdio transport
    try:
        logger.info('Starting with stdio transport...')
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f'Error starting server with stdio transport: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
