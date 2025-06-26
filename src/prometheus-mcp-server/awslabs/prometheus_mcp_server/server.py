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
    ENV_LOG_LEVEL,
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
# No need for urlparse anymore


# Configure loguru
logger.remove()
logger.add(sys.stderr, level=os.getenv(ENV_LOG_LEVEL, 'INFO'))


class ConfigManager:
    """Configuration management for the application."""
    
    @staticmethod
    def parse_arguments():
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description='Prometheus MCP Server')
        parser.add_argument('--profile', type=str, help='AWS profile name to use')
        parser.add_argument('--region', type=str, help='AWS region to use')
        parser.add_argument('--debug', action='store_true', help='Enable debug logging')
        return parser.parse_args()
    
    @staticmethod
    def setup_basic_config(args):
        """Setup basic configuration from command line arguments and environment variables."""
        # Load .env file if it exists
        load_dotenv()
        
        # Set debug logging if requested
        if args.debug:
            logger.level('DEBUG')
            logger.debug('Debug logging enabled')
        
        # Get region and profile from args or environment
        region = args.region or os.getenv(ENV_AWS_REGION) or DEFAULT_AWS_REGION
        profile = args.profile or os.getenv(ENV_AWS_PROFILE)
        
        return {'region': region, 'profile': profile}


class AWSCredentials:
    """AWS credentials management."""
    
    @staticmethod
    def validate(region: str, profile: Optional[str] = None) -> bool:
        """Validate AWS credentials.
        
        Args:
            region: AWS region to use
            profile: AWS profile to use (optional)
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        logger.info('Validating AWS credentials...')
        
        try:
            # Create session with profile if specified
            if profile:
                logger.info(f'Using AWS Profile: {profile}')
                session = boto3.Session(profile_name=profile, region_name=region)
            else:
                logger.info('Using default AWS credentials')
                session = boto3.Session(region_name=region)

            # Test AWS credentials
            credentials = session.get_credentials()
            if not credentials:
                logger.error('ERROR: AWS credentials not found')
                logger.error('Please configure AWS credentials using:')
                logger.error('  - AWS CLI: aws configure')
                logger.error('  - Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY')
                logger.error('  - Or specify a profile with --profile')
                return False
                
            # Test if credentials have necessary permissions
            sts = session.client('sts', config=Config(user_agent_extra='prometheus-mcp-server'))
            identity = sts.get_caller_identity()
            logger.info(f'AWS Identity: {identity["Arn"]}')
            logger.info(f'AWS Region: {region}')
            logger.info('AWS credentials validated successfully')
            return True
            
        except (NoCredentialsError, ClientError) as e:
            logger.error(f'ERROR: AWS credentials validation failed: {e}')
            return False


# Define dangerous patterns as a constant
DANGEROUS_PATTERNS = [
    # Command injection attempts
    ';', '&&', '||', '`', '$(', '${',
    # File access attempts
    'file://', '/etc/', '/var/log',
    # Network access attempts
    'http://', 'https://',
]


class SecurityValidator:
    """Security validation utilities."""
    
    @staticmethod
    def validate_string(value: str, context: str = 'value') -> bool:
        """Validate a string for potential security issues.

        Args:
            value: The string to validate
            context: Context description for logging (e.g., 'parameter', 'query')

        Returns:
            bool: True if the string is safe, False otherwise
        """
        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern in value:
                logger.warning(f'Potentially dangerous {context} detected: {pattern}')
                return False

        return True
    
    @staticmethod
    def validate_params(params: Dict) -> bool:
        """Validate request parameters for potential security issues.

        Args:
            params: The parameters to validate

        Returns:
            bool: True if the parameters are safe, False otherwise
        """
        if not params:
            return True

        # Check each parameter value
        for key, value in params.items():
            if not isinstance(value, str):
                continue

            if not SecurityValidator.validate_string(value, f'parameter {key}'):
                return False

        return True
    
    @staticmethod
    def validate_query(query: str) -> bool:
        """Validate a PromQL query for potential security issues.

        Args:
            query: The PromQL query to validate

        Returns:
            bool: True if the query is safe, False otherwise
        """
        return SecurityValidator.validate_string(query, 'query pattern')


class PrometheusClient:
    """Client for interacting with Prometheus API."""
    
    @staticmethod
    async def make_request(
        prometheus_url: str,
        endpoint: str, 
        params: Optional[Dict] = None, 
        region: str = DEFAULT_AWS_REGION,
        profile: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES, 
        retry_delay: int = DEFAULT_RETRY_DELAY, 
        service_name: str = DEFAULT_SERVICE_NAME
    ) -> Any:
        """Make a request to the Prometheus HTTP API with AWS SigV4 authentication.

        Args:
            prometheus_url: The base URL for the Prometheus API
            endpoint: The Prometheus API endpoint to call
            params: Query parameters to include in the request
            region: AWS region to use
            profile: AWS profile to use
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
            service_name: AWS service name for SigV4 authentication

        Returns:
            The data portion of the Prometheus API response

        Raises:
            ValueError: If Prometheus URL or AWS credentials are not configured
            RuntimeError: If the Prometheus API returns an error status
            requests.RequestException: If there's a network or HTTP error
            json.JSONDecodeError: If the response is not valid JSON
        """
        if not prometheus_url:
            raise ValueError('Prometheus URL not configured')

        # Validate endpoint
        if not isinstance(endpoint, str):
            raise ValueError('Endpoint must be a string')

        if ';' in endpoint or '&&' in endpoint or '||' in endpoint:
            raise ValueError('Invalid endpoint: potentially dangerous characters detected')

        # Validate parameters
        if params and not SecurityValidator.validate_params(params):
            raise ValueError('Invalid parameters: potentially dangerous values detected')

        # Ensure the URL ends with /api/v1
        base_url = prometheus_url
        if not base_url.endswith(API_VERSION_PATH):
            base_url = f'{base_url.rstrip("/")}{API_VERSION_PATH}'

        url = f'{base_url}/{endpoint.lstrip("/")}'

        # Send request with retry logic
        retry_count = 0
        last_exception = None
        retry_delay_seconds = retry_delay

        while retry_count < max_retries:
            try:
                # Create a fresh session and client for each attempt
                session = boto3.Session(profile_name=profile, region_name=region)
                credentials = session.get_credentials()
                if not credentials:
                    raise ValueError('AWS credentials not found')
                
                # Create and sign the request
                aws_request = AWSRequest(method='GET', url=url, params=params or {})
                SigV4Auth(credentials, service_name, region).add_auth(aws_request)
                
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
                    retry_delay_seconds = retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    logger.warning(f'Request failed: {e}. Retrying in {retry_delay_seconds}s...')
                    time.sleep(retry_delay_seconds)
                else:
                    logger.error(f'Request failed after {max_retries} attempts: {e}')
                    raise

        if last_exception:
            raise last_exception
        return None


class PrometheusConnection:
    """Handles Prometheus connection testing."""
    
    @staticmethod
    async def test_connection(prometheus_url: str, region: str = DEFAULT_AWS_REGION, profile: Optional[str] = None) -> bool:
        """Test the connection to Prometheus.

        Args:
            prometheus_url: The Prometheus URL to test
            region: AWS region to use
            profile: AWS profile to use
            
        Returns:
            bool: True if connection is successful, False otherwise
        """
        logger.info('Testing Prometheus connection...')
        try:
            # Use the PrometheusClient.make_request method
            await PrometheusClient.make_request(
                prometheus_url=prometheus_url,
                endpoint='label/__name__/values', 
                params={},
                region=region,
                profile=profile,
                max_retries=DEFAULT_MAX_RETRIES,
                retry_delay=DEFAULT_RETRY_DELAY,
                service_name=DEFAULT_SERVICE_NAME
            )
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
                logger.error(f'Please verify the workspace ID in your Prometheus URL: {prometheus_url}')
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

# No global config needed anymore


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


async def get_workspace_details(workspace_id: str, region: str = DEFAULT_AWS_REGION, profile: Optional[str] = None) -> Dict[str, Any]:
    """Get details for a specific Prometheus workspace using DescribeWorkspace API.
    
    Args:
        workspace_id: The Prometheus workspace ID
        region: AWS region where the workspace is located
        profile: AWS profile to use (defaults to None)
        
    Returns:
        Dictionary containing workspace details including URL from API
    """
    # Get a fresh client for this request
    aps_client = get_prometheus_client(region_name=region, profile_name=profile)
    
    try:
        # Get workspace details directly from DescribeWorkspace API
        response = aps_client.describe_workspace(workspaceId=workspace_id)
        workspace = response.get('workspace', {})
        
        # Get the URL from the API response
        prometheus_url = workspace.get('prometheusEndpoint')
        if not prometheus_url:
            raise ValueError(f"No prometheusEndpoint found in workspace response for {workspace_id}")
            
        logger.info(f"Retrieved workspace URL from DescribeWorkspace API: {prometheus_url}")
        
        return {
            'workspace_id': workspace_id,
            'alias': workspace.get('alias', 'No alias'),
            'status': workspace.get('status', {}).get('statusCode', 'UNKNOWN'),
            'prometheus_url': prometheus_url,
            'region': region
        }
    except Exception as e:
        logger.error(f"Error in DescribeWorkspace API: {str(e)}")
        raise


# validate_query function removed - now part of SecurityValidator class


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
    profile: Optional[str] = Field(None, description='AWS profile to use (defaults to None)'),
) -> Dict[str, Any]:
    """Execute a PromQL query against Amazon Managed Prometheus.

    ## Usage
    - Use this tool to execute a PromQL query at a specific instant in time
    - The query will return the current value of the specified metrics
    - For time series data over a range, use execute_range_query instead
    - If workspace_id is not known, use GetAvailableWorkspaces tool first to find available workspaces and ASK THE USER to choose one
    - Uses DescribeWorkspace API to get the exact workspace URL
    - No manual URL construction is performed

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
    try:
        # Configure workspace using the provided workspace_id
        workspace_config = await configure_workspace_for_request(ctx, workspace_id, region, profile)

        logger.info(f'Executing instant query: {query}')

        # Validate query for security
        if not SecurityValidator.validate_query(query):
            error_msg = 'Query validation failed: potentially dangerous query pattern detected'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise ValueError(error_msg)

        params = {'query': query}
        if time:
            params['time'] = time

        return await PrometheusClient.make_request(
            prometheus_url=workspace_config['prometheus_url'],
            endpoint='query', 
            params=params, 
            region=workspace_config['region'],
            profile=workspace_config['profile'],
            max_retries=DEFAULT_MAX_RETRIES,
            retry_delay=DEFAULT_RETRY_DELAY,
            service_name=DEFAULT_SERVICE_NAME
        )
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
    profile: Optional[str] = Field(None, description='AWS profile to use (defaults to None)'),
) -> Dict[str, Any]:
    """Execute a range query and return the result.

    ## Usage
    - Use this tool to execute a PromQL query over a time range
    - The query will return a series of values for the specified time range
    - Useful for generating time series data for graphs or trend analysis
    - If workspace_id is not known, use GetAvailableWorkspaces tool first to find available workspaces and ASK THE USER to choose one
    - Uses DescribeWorkspace API to get the exact workspace URL
    - No manual URL construction is performed

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
    try:
        # Configure workspace using the provided workspace_id
        workspace_config = await configure_workspace_for_request(ctx, workspace_id, region, profile)

        logger.info(f'Executing range query: {query} from {start} to {end} with step {step}')

        # Validate query for security
        if not SecurityValidator.validate_query(query):
            error_msg = 'Query validation failed: potentially dangerous query pattern detected'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise ValueError(error_msg)

        params = {'query': query, 'start': start, 'end': end, 'step': step}

        return await PrometheusClient.make_request(
            prometheus_url=workspace_config['prometheus_url'],
            endpoint='query_range', 
            params=params, 
            region=workspace_config['region'],
            profile=workspace_config['profile'],
            max_retries=DEFAULT_MAX_RETRIES,
            retry_delay=DEFAULT_RETRY_DELAY,
            service_name=DEFAULT_SERVICE_NAME
        )
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
    profile: Optional[str] = Field(None, description='AWS profile to use (defaults to None)'),
) -> MetricsList:
    """Get a list of all metric names.

    ## Usage
    - Use this tool to discover available metrics in the Prometheus server
    - Returns a sorted list of all metric names
    - Useful for exploration before crafting specific queries
    - If workspace_id is not known, use GetAvailableWorkspaces tool first to find available workspaces and ASK THE USER to choose one

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
    try:
        # Configure workspace using the provided workspace_id
        workspace_config = await configure_workspace_for_request(ctx, workspace_id, region, profile)

        logger.info('Listing all available metrics')

        data = await PrometheusClient.make_request(
            prometheus_url=workspace_config['prometheus_url'],
            endpoint='label/__name__/values', 
            params={}, 
            region=workspace_config['region'],
            profile=workspace_config['profile'],
            max_retries=DEFAULT_MAX_RETRIES,
            retry_delay=DEFAULT_RETRY_DELAY,
            service_name=DEFAULT_SERVICE_NAME
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
    profile: Optional[str] = Field(None, description='AWS profile to use (defaults to None)'),
) -> ServerInfo:
    """Get information about the Prometheus server configuration.

    ## Usage
    - Use this tool to retrieve the current server configuration
    - Returns details about the Prometheus URL, AWS region, profile, and service name
    - Useful for debugging connection issues
    - If workspace_id is not known, use GetAvailableWorkspaces tool first to find available workspaces and ASK THE USER to choose one
    - Uses DescribeWorkspace API to get the exact workspace URL
    - No manual URL construction is performed

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
    try:
        # Configure workspace using the provided workspace_id
        workspace_config = await configure_workspace_for_request(ctx, workspace_id, region, profile)

        logger.info('Retrieving server configuration information')

        return ServerInfo(
            prometheus_url=workspace_config['prometheus_url'],
            aws_region=workspace_config['region'],
            aws_profile=workspace_config['profile'] or 'default',
            service_name=DEFAULT_SERVICE_NAME,
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
    profile: Optional[str] = Field(None, description='AWS profile to use (defaults to None)'),
) -> Dict[str, Any]:
    """List all available Prometheus workspaces in the specified region.

    ## Usage
    - Use this tool to see all available Prometheus workspaces
    - Shows workspace ID, alias, status, and URL for active workspaces
    - IMPORTANT: When multiple workspaces are available, present them to the user and ask them to choose one
    - DO NOT automatically select a workspace; always ask the user to choose when multiple options exist
    - Uses DescribeWorkspace API to get the exact URL for each workspace
    - No manual URL construction is performed

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
            "prometheus_url": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345678-abcd-1234-efgh-123456789012"
          },
          {
            "workspace_id": "ws-87654321-dcba-4321-hgfe-210987654321",
            "alias": "development",
            "status": "ACTIVE",
            "prometheus_url": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-87654321-dcba-4321-hgfe-210987654321"
          }
        ],
        "count": 2,
        "region": "us-east-1",
        "requires_user_selection": true
      }
    """
    try:
        # Use provided region or default
        aws_region = region or os.getenv('AWS_REGION') or DEFAULT_AWS_REGION

        logger.info(f'Listing available Prometheus workspaces in region {aws_region}')

        # Get a fresh client for this request
        aps_client = get_prometheus_client(region_name=aws_region, profile_name=profile)
        response = aps_client.list_workspaces()

        workspaces = []
        for ws in response.get('workspaces', []):
            workspace_id = ws['workspaceId']
            
            # Only get details for active workspaces
            if ws['status']['statusCode'] == 'ACTIVE':
                try:
                    # Get full details including URL from DescribeWorkspace API
                    details = await get_workspace_details(workspace_id, aws_region, profile)
                    workspaces.append(details)
                except Exception as e:
                    logger.warning(f"Could not get details for workspace {workspace_id}: {str(e)}")
                    # Skip this workspace if we can't get its details
                    continue
            else:
                # For non-active workspaces, just include basic info without URL
                workspaces.append({
                    'workspace_id': workspace_id,
                    'alias': ws.get('alias', 'No alias'),
                    'status': ws['status']['statusCode'],
                    'region': aws_region
                })

        logger.info(f'Found {len(workspaces)} workspaces in region {aws_region}')
        # Add a flag to indicate if user selection is required (when multiple workspaces exist)
        requires_selection = len(workspaces) > 1
        return {
            'workspaces': workspaces, 
            'count': len(workspaces), 
            'region': aws_region,
            'requires_user_selection': requires_selection
        }
    except Exception as e:
        error_msg = f'Error listing workspaces: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise





async def configure_workspace_for_request(
    ctx: Context,
    workspace_id: str,
    region: Optional[str] = None,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """Configure the workspace for the current request using DescribeWorkspace API.

    Args:
        ctx: The MCP context
        workspace_id: The Prometheus workspace ID to use
        region: Optional AWS region (defaults to current region)
        profile: Optional AWS profile to use
        
    Returns:
        Dictionary with workspace configuration including the URL from DescribeWorkspace API
    """
    try:
        logger.info(f'Configuring workspace ID for request: {workspace_id}')

        # Validate workspace ID format
        if not workspace_id.startswith('ws-'):
            logger.warning(f'Workspace ID "{workspace_id}" does not start with "ws-", which is unusual')

        # Use provided region or default
        aws_region = region or os.getenv('AWS_REGION') or DEFAULT_AWS_REGION

        # Get workspace details from DescribeWorkspace API
        workspace_details = await get_workspace_details(workspace_id, aws_region, profile)
        prometheus_url = workspace_details['prometheus_url']
        logger.info(f'Using Prometheus URL from DescribeWorkspace API: {prometheus_url}')

        # Test connection with the URL
        if not await PrometheusConnection.test_connection(prometheus_url, aws_region, profile):
            error_msg = f'Failed to connect to Prometheus with workspace ID {workspace_id}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f'Successfully configured workspace {workspace_id} for request')
        
        # Return workspace configuration
        return {
            'prometheus_url': prometheus_url,
            'region': aws_region,
            'profile': profile,
            'workspace_id': workspace_id
        }
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
    args = ConfigManager.parse_arguments()

    # Setup basic configuration
    config = ConfigManager.setup_basic_config(args)

    # Validate AWS credentials
    if not AWSCredentials.validate(config['region'], config['profile']):
        logger.error('AWS credentials validation failed')
        sys.exit(1)

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
