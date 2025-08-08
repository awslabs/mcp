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

"""CloudWatch Dashboard tools for MCP server."""

import boto3
import json
import os
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.models import DashboardResponse
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict


class CloudWatchDashboardTools:
    """CloudWatch Dashboard tools for MCP server."""

    def __init__(self):
        """Initialize the CloudWatch Dashboard tools."""
        pass

    def _get_cloudwatch_client(self, region: str):
        """Create a CloudWatch client for the specified region."""
        config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')

        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                return boto3.Session(profile_name=aws_profile, region_name=region).client(
                    'cloudwatch', config=config
                )
            else:
                return boto3.Session(region_name=region).client('cloudwatch', config=config)
        except Exception as e:
            logger.error(f'Error creating cloudwatch client for region {region}: {str(e)}')
            raise

    def register(self, mcp):
        """Register all CloudWatch Dashboard tools with the MCP server."""
        # Register get_dashboard tool
        mcp.tool(name='get_dashboard')(self.get_dashboard)

    async def get_dashboard(
        self,
        ctx: Context,
        dashboard_name: Annotated[
            str,
            Field(description='Name of the CloudWatch dashboard to retrieve'),
        ],
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> DashboardResponse:
        """Retrieve a CloudWatch dashboard configuration.

        This tool retrieves the configuration and content of a specified CloudWatch dashboard
        using the AWS CloudWatch get_dashboard API. The dashboard body is parsed as JSON when
        possible, with fallback to raw string format if parsing fails.

        Usage: Use this tool to understand dashboard layouts, widgets, and their configurations
        for troubleshooting and analysis purposes.

        Args:
            ctx: The MCP context object for error handling and logging.
            dashboard_name: Name of the CloudWatch dashboard to retrieve.
            region: AWS region to query. Defaults to 'us-east-1'.

        Returns:
            DashboardResponse: Response containing the dashboard configuration.

        Example:
            result = await get_dashboard(ctx, dashboard_name="MyDashboard")
            if isinstance(result, DashboardResponse):
                print(f"Dashboard: {result.dashboard_name}")
                print(f"Region: {result.region}")
                if isinstance(result.dashboard_body, dict):
                    print(f"Widgets: {len(result.dashboard_body.get('widgets', []))}")
        """
        try:
            # Validate dashboard_name parameter
            if not dashboard_name or not isinstance(dashboard_name, str):
                raise ValueError('dashboard_name must be a non-empty string')

            dashboard_name = dashboard_name.strip()
            if not dashboard_name:
                raise ValueError('dashboard_name cannot be empty or whitespace only')

            # Validate region parameter
            if not region or not isinstance(region, str):
                raise ValueError('region must be a non-empty string')

            region = region.strip()
            if not region:
                raise ValueError('region cannot be empty or whitespace only')

            logger.info(f'Fetching dashboard {dashboard_name} from region {region}')

            # Create CloudWatch client for the specified region
            cloudwatch_client = self._get_cloudwatch_client(region)

            # Call CloudWatch get_dashboard API
            response = cloudwatch_client.get_dashboard(DashboardName=dashboard_name)

            # Extract response data
            dashboard_arn = response.get('DashboardArn')
            dashboard_body_raw = response.get('DashboardBody', '')
            last_modified = response.get('LastModified')

            logger.info(f'Successfully retrieved dashboard {dashboard_name}')

            # Parse dashboard body JSON with error handling
            dashboard_body: Dict[str, Any] | str = dashboard_body_raw
            parsing_warning = None

            if dashboard_body_raw:
                try:
                    dashboard_body = json.loads(dashboard_body_raw)
                    logger.info('Successfully parsed dashboard body as JSON')
                except json.JSONDecodeError as e:
                    parsing_warning = f'Failed to parse dashboard body as JSON: {str(e)}'
                    logger.warning(parsing_warning)
                    # Keep raw string as fallback
                    dashboard_body = dashboard_body_raw
                except Exception as e:
                    parsing_warning = f'Unexpected error parsing dashboard body: {str(e)}'
                    logger.warning(parsing_warning)
                    # Keep raw string as fallback
                    dashboard_body = dashboard_body_raw

            # Create and return response
            return DashboardResponse(
                dashboard_name=dashboard_name,
                dashboard_arn=dashboard_arn,
                dashboard_body=dashboard_body,
                last_modified=last_modified,
                region=region,
                parsing_warning=parsing_warning,
            )

        except ValueError as e:
            # Handle parameter validation errors
            error_msg = f'Invalid parameter: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise
        except Exception as e:
            # Handle any other unexpected errors
            error_msg = f'Error in get_dashboard: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise
