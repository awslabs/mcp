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
from botocore.config import Config
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


# find_active_workspace function removed as per requirements


def setup_environment(config_data):
    """Setup and validate environment variables."""
    logger.info('Setting up environment...')

    try:
        # Create session with profile if specified
        if config_data['aws_profile']:
            logger.info(f'  Using AWS Profile: {config_data["aws_profile"]}')
            session = boto3.Session(
                profile_name=config_data['aws_profile'], region_name=config_data['aws_region']
            )
        else:
            logger.info('  Using default AWS credentials')
            session = boto3.Session(region_name=config_data['aws_region'])

        # Validate Prometheus URL if provided
        if config_data['prometheus_url']:
            parsed_url = urlparse(config_data['prometheus_url'])
            if not all([parsed_url.scheme, parsed_url.netloc]):
                logger.error(
                    f'ERROR: Invalid Prometheus URL format: {config_data["prometheus_url"]}'
                )
                logger.error('URL must include scheme (https://) and hostname')
                return False

            # Verify URL points to AWS Prometheus
            if not (
                parsed_url.netloc.endswith('.amazonaws.com')
                and 'aps-workspaces' in parsed_url.netloc
            ):
                logger.warning(
                    f"WARNING: URL doesn't appear to be an AWS Managed Prometheus endpoint: {config_data['prometheus_url']}"
                )
                logger.warning(
                    'Expected format: https://aps-workspaces.[region].amazonaws.com/workspaces/ws-[id]'
                )

            logger.info('Prometheus configuration:')
            logger.info(f'  Server URL: {config_data["prometheus_url"]}')
        else:
            logger.info('Prometheus configuration:')
            logger.info('  Server URL: Will be set when workspace is selected')

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
                sts = session.client(
                    'sts', config=Config(user_agent_extra='prometheus-mcp-server')
                )
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
    global config
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

    # Send request with retry logic
    retry_count = 0
    last_exception = None
    retry_delay_seconds = 1  # Default retry delay if config.retry_delay is None

    while retry_count < max_retries:
        try:
            # Create a fresh session and client for each attempt
            # This ensures credentials are always fresh
            session = boto3.Session(profile_name=config.aws_profile, region_name=config.aws_region)
            credentials = session.get_credentials()
            if not credentials:
                raise ValueError('AWS credentials not found')
            
            # Create and sign the request
            aws_request = AWSRequest(method='GET', url=url, params=params or {})
            SigV4Auth(credentials, config.service_name, config.aws_region).add_auth(aws_request)
            
            # Convert to requests format
            prepared_request = requests.Request(
                method=aws_request.method,
                url=aws_request.url,
                headers=dict(aws_request.headers),
                params=params or {},
            ).prepare()
            
            # Send the request
            with requests.Session() as req_session:
                logger.debug(f'Making request to {url} (attempt {retry_count + 1}/{max_retries})')
                response = req_session.send(prepared_request)
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
    global config
    logger.info('Testing Prometheus connection...')
    try:
        # Use the make_prometheus_request function which now creates a fresh client
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


def get_prometheus_client(region_name: Optional[str] = None, profile_name: Optional[str] = None):
    """Create a boto3 AMP client using credentials from environment variables.
    
    Args:
        region_name: AWS region to use (defaults to environment variable or us-east-1)
        profile_name: AWS profile to use (defaults to None)
        
    Returns:
        boto3 AMP client with fresh credentials
    """
    # Use provided region, or get from env, or fall back to default
    region = region_name or os.getenv('AWS_REGION') or DEFAULT_AWS_REGION
    
    # Configure custom user agent
    config = Config(user_agent_extra='prometheus-mcp-server')
    
    # Create a new session to force credentials to reload
    session = boto3.Session(profile_name=profile_name, region_name=region)
    
    # Return AMP client
    return session.client('amp', config=config)


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
    workspace_id: str = Field(
        ...,
        description='The Prometheus workspace ID to use (e.g., ws-12345678-abcd-1234-efgh-123456789012)',
    ),
    query: str = Field(..., description='The PromQL query to execute'),
    time: Optional[str] = Field(
        None, description='Optional timestamp for query evaluation (RFC3339 or Unix timestamp)'
    ),
    region: Optional[str] = Field(None, description='AWS region (defaults to current region)'),
) -> Dict[str, Any]:
    """Execute an instant query and return the result.

    ## Usage
    - Use this tool to execute a PromQL query at a specific instant in time
    - The query will return the current value of the specified metrics
    - For time series data over a range, use execute_range_query instead
    - You must provide a workspace_id - use GetAvailableWorkspaces to see available workspaces

    ## Example
    Input:
      workspace_id: "ws-12345678-abcd-1234-efgh-123456789012"
      query: "up"
      region: "us-east-1"
      
    Output:
      {
        "resultType": "vector",
        "result": [
          {
            "metric": {"__name__": "up", "instance": "localhost:9090", "job": "prometheus"},
            "value": [1680307200, "1"]
          },
          {
            "metric": {"__name__": "up", "instance": "localhost:9100", "job": "node"},
            "value": [1680307200, "1"]
          }
        ]
      }
      
    Example queries:
    - `up` - Shows which targets are up
    - `rate(node_cpu_seconds_total{mode="system"}[1m])` - CPU usage rate
    - `sum by(instance) (rate(node_network_receive_bytes_total[5m]))` - Network receive rate by instance
    """
    global config
    try:
        # Configure workspace for this request
        await configure_workspace_for_request(ctx, workspace_id, region)

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
    workspace_id: str = Field(
        ...,
        description='The Prometheus workspace ID to use (e.g., ws-12345678-abcd-1234-efgh-123456789012)',
    ),
    query: str = Field(..., description='The PromQL query to execute'),
    start: str = Field(..., description='Start timestamp (RFC3339 or Unix timestamp)'),
    end: str = Field(..., description='End timestamp (RFC3339 or Unix timestamp)'),
    step: str = Field(
        ..., description="Query resolution step width (duration format, e.g. '15s', '1m', '1h')"
    ),
    region: Optional[str] = Field(None, description='AWS region (defaults to current region)'),
) -> Dict[str, Any]:
    """Execute a range query and return the result.

    ## Usage
    - Use this tool to execute a PromQL query over a time range
    - The query will return a series of values for the specified time range
    - Useful for generating time series data for graphs or trend analysis
    - You must provide a workspace_id - use GetAvailableWorkspaces to see available workspaces

    ## Example
    Input:
      workspace_id: "ws-12345678-abcd-1234-efgh-123456789012"
      query: "rate(node_cpu_seconds_total{mode=\"system\"}[5m])"
      start: "2023-04-01T00:00:00Z"
      end: "2023-04-01T01:00:00Z"
      step: "5m"
      
    Output:
      {
        "resultType": "matrix",
        "result": [
          {
            "metric": {"__name__": "rate", "mode": "system", "instance": "localhost:9100"},
            "values": [[1680307200, "0.01"], [1680307500, "0.012"], ...]
          }
        ]
      }
    """
    global config
    try:
        # Configure workspace for this request
        await configure_workspace_for_request(ctx, workspace_id, region)

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
async def list_metrics(
    ctx: Context,
    workspace_id: str = Field(
        ...,
        description='The Prometheus workspace ID to use (e.g., ws-12345678-abcd-1234-efgh-123456789012)',
    ),
    region: Optional[str] = Field(None, description='AWS region (defaults to current region)'),
) -> MetricsList:
    """Get a list of all metric names.

    ## Usage
    - Use this tool to discover available metrics in the Prometheus server
    - Returns a sorted list of all metric names
    - Useful for exploration before crafting specific queries
    - You must provide a workspace_id - use GetAvailableWorkspaces to see available workspaces

    ## Example
    Input:
      workspace_id: "ws-12345678-abcd-1234-efgh-123456789012"
      region: "us-east-1"

    Output:
      {
        "metrics": [
          "go_gc_duration_seconds",
          "go_goroutines",
          "http_requests_total",
          ...
        ]
      }
    """
    global config
    try:
        # Configure workspace for this request
        await configure_workspace_for_request(ctx, workspace_id, region)

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
async def get_server_info(
    ctx: Context,
    workspace_id: str = Field(
        ...,
        description='The Prometheus workspace ID to use (e.g., ws-12345678-abcd-1234-efgh-123456789012)',
    ),
    region: Optional[str] = Field(None, description='AWS region (defaults to current region)'),
) -> ServerInfo:
    """Get information about the Prometheus server configuration.

    ## Usage
    - Use this tool to retrieve the current server configuration
    - Returns details about the Prometheus URL, AWS region, profile, and service name
    - Useful for debugging connection issues
    - You must provide a workspace_id - use GetAvailableWorkspaces to see available workspaces

    ## Example
    Input:
      workspace_id: "ws-12345678-abcd-1234-efgh-123456789012"
      region: "us-east-1"

    Output:
      {
        "prometheus_url": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345678-abcd-1234-efgh-123456789012",
        "aws_region": "us-east-1",
        "aws_profile": "default",
        "service_name": "aps"
      }
    """
    global config
    try:
        # Configure workspace for this request
        await configure_workspace_for_request(ctx, workspace_id, region)

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


@mcp.tool(name='GetAvailableWorkspaces')
async def get_available_workspaces(
    ctx: Context,
    region: Optional[str] = Field(None, description='AWS region (defaults to current region)'),
) -> Dict[str, Any]:
    """List all available Prometheus workspaces in the specified region.

    ## Usage
    - Use this tool to see all available Prometheus workspaces
    - Shows workspace ID, alias, status, and creation date
    - Use this to find workspace IDs needed for other tools
    - Always call this first to get a workspace ID before using other tools

    ## Example
    Input:
      region: "us-east-1"

    Output:
      {
        "workspaces": [
          {
            "workspace_id": "ws-12345678-abcd-1234-efgh-123456789012",
            "alias": "production",
            "status": "ACTIVE",
            "created_at": "2023-01-15T10:30:00Z"
          },
          {
            "workspace_id": "ws-87654321-dcba-4321-hgfe-210987654321",
            "alias": "development",
            "status": "ACTIVE",
            "created_at": "2023-02-20T14:15:00Z"
          }
        ],
        "count": 2,
        "region": "us-east-1"
      }
    """
    try:
        # Use provided region or current config region or default
        aws_region = region
        if not aws_region and config and config.aws_region:
            aws_region = config.aws_region
        if not aws_region:
            aws_region = DEFAULT_AWS_REGION

        logger.info(f'Listing available Prometheus workspaces in region {aws_region}')

        # Get a fresh client for this request
        profile_name = config.aws_profile if config else None
        aps_client = get_prometheus_client(region_name=aws_region, profile_name=profile_name)
        response = aps_client.list_workspaces()

        workspaces = []
        for ws in response.get('workspaces', []):
            workspaces.append(
                {
                    'workspace_id': ws['workspaceId'],
                    'alias': ws.get('alias', 'No alias'),
                    'status': ws['status']['statusCode'],
                    'created_at': ws.get('createdAt', '').isoformat()
                    if ws.get('createdAt')
                    else 'Unknown',
                }
            )

        return {'workspaces': workspaces, 'count': len(workspaces), 'region': aws_region}
    except Exception as e:
        error_msg = f'Error listing workspaces: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise


async def configure_workspace_for_request(
    ctx: Context,
    workspace_id: str,
    region: Optional[str] = None,
) -> None:
    """Configure the workspace for the current request.

    Args:
        ctx: The MCP context
        workspace_id: The Prometheus workspace ID to use
        region: Optional AWS region (defaults to current region)
    """
    global config

    try:
        logger.info(f'Configuring workspace ID for request: {workspace_id}')

        # Validate workspace ID format
        if not workspace_id.startswith('ws-'):
            logger.warning(
                f'Workspace ID "{workspace_id}" does not start with "ws-", which is unusual'
            )

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
            error_msg = f'Failed to connect to Prometheus with workspace ID {workspace_id}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f'Successfully configured workspace {workspace_id} for request')
    except Exception as e:
        error_msg = f'Error configuring workspace: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise


async def async_main():
    """Run the async initialization tasks."""
    # Initialize with default configuration
    # Each tool will configure workspace based on provided workspace_id parameter
    logger.info(
        'Initializing Prometheus MCP Server - workspace ID will be required for each tool invocation'
    )


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting Prometheus MCP Server...')

    # Parse arguments
    args = parse_arguments()

    # Load configuration
    config_data = load_config(args)

    # Setup environment (validate AWS credentials)
    if not setup_environment(config_data):
        logger.error('Environment setup failed')
        sys.exit(1)

    # Create config object with default settings
    # Each tool will configure workspace based on provided workspace_id parameter
    global config
    config = PrometheusConfig(
        prometheus_url=None,  # Will be set per-request based on workspace_id
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
