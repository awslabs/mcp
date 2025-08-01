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

"""CloudTrail tools for MCP server."""

import boto3
import os
import time
from awslabs.cloudtrail_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudtrail_mcp_server.common import (
    parse_time_input,
    remove_null_values,
    validate_max_results,
)
from awslabs.cloudtrail_mcp_server.models import (
    EventDataStore,
    QueryResult,
    QueryStatus,
)
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List, Literal, Optional


class CloudTrailTools:
    """CloudTrail tools for MCP server."""

    def __init__(self):
        """Initialize the CloudTrail tools."""
        pass

    def _get_cloudtrail_client(self, region: str):
        """Create a CloudTrail client for the specified region."""
        config = Config(user_agent_extra=f'awslabs/mcp/cloudtrail-mcp-server/{MCP_SERVER_VERSION}')

        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                return boto3.Session(profile_name=aws_profile, region_name=region).client(
                    'cloudtrail', config=config
                )
            else:
                return boto3.Session(region_name=region).client('cloudtrail', config=config)
        except Exception as e:
            logger.error(f'Error creating CloudTrail client for region {region}: {str(e)}')
            raise

    def register(self, mcp):
        """Register all CloudTrail tools with the MCP server."""
        # Register simplified lookup_events tool that handles all filtering
        mcp.tool(name='lookup_events')(self.lookup_events)

        # Register lake_query tool
        mcp.tool(name='lake_query')(self.lake_query)

        # Register get_query_status tool
        mcp.tool(name='get_query_status')(self.get_query_status)

        # Register get_query_results tool
        mcp.tool(name='get_query_results')(self.get_query_results)

        # Register list_event_data_stores tool
        mcp.tool(name='list_event_data_stores')(self.list_event_data_stores)

    async def lookup_events(
        self,
        ctx: Context,
        start_time: Annotated[
            Optional[str],
            Field(
                description='Start time for event lookup (ISO format or relative like "1 day ago"). IMPORTANT: When using pagination (next_token), you must provide the exact same start_time as the original request.'
            ),
        ] = None,
        end_time: Annotated[
            Optional[str],
            Field(
                description='End time for event lookup (ISO format or relative like "1 hour ago"). IMPORTANT: When using pagination (next_token), you must provide the exact same end_time as the original request.'
            ),
        ] = None,
        attribute_key: Annotated[
            Optional[
                Literal[
                    'EventId',
                    'EventName',
                    'ReadOnly',
                    'Username',
                    'ResourceType',
                    'ResourceName',
                    'EventSource',
                    'AccessKeyId',
                ]
            ],
            Field(description='Attribute to search by'),
        ] = None,
        attribute_value: Annotated[
            Optional[str], Field(description='Value to search for in the specified attribute')
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='Maximum number of events to return (1-50, default: 10)'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(
                description='Token for pagination to fetch the next page of events. IMPORTANT: When using this token, all other parameters (start_time, end_time, attribute_key, attribute_value) must match exactly the original request that generated this token.'
            ),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> Dict[str, Any]:
        """Look up CloudTrail events based on various criteria.

        This tool searches CloudTrail events using the LookupEvents API, which provides access to the
        last 90 days of management events. You can filter by time range and search for specific
        attribute values.

        Usage: Use this tool to find CloudTrail events by various attributes like username, event name,
        resource name, etc. This is useful for security investigations, troubleshooting, and audit trails.

        IMPORTANT PAGINATION REQUIREMENTS:
        - AWS CloudTrail requires pagination tokens to be used with exactly the same parameters as the original request
        - When using next_token, you must provide the exact same start_time, end_time, attribute_key, and attribute_value
        - Use the 'query_params' returned in the response for subsequent paginated requests

        Returns:
        --------
        Dictionary containing:
            - events: List of CloudTrail events matching the criteria with exact CloudTrail schema
            - next_token: Token for pagination if more results available
            - query_params: Parameters used for the query (includes pagination parameters when next_token is present)
        """
        try:
            # Create CloudTrail client for the specified region
            cloudtrail_client = self._get_cloudtrail_client(region)

            # Handle time input validation and parsing
            if next_token:
                # When using pagination, both start_time and end_time are required
                if not start_time or not end_time:
                    raise ValueError(
                        'Both start_time and end_time are required when using pagination (next_token). '
                        'Use the exact start_time and end_time from the "query_params" in the previous response.'
                    )
                try:
                    # Parse times for pagination (should be in ISO format from previous response)
                    start_dt = parse_time_input(start_time)
                    end_dt = parse_time_input(end_time)
                except Exception as e:
                    raise ValueError(
                        f'Invalid time format for pagination. Use the exact start_time and end_time from the '
                        f"'query_params' in the previous response. Error: {str(e)}"
                    )
            else:
                # First request - use provided times or defaults
                start_time = start_time or '1 day ago'
                end_time = end_time or 'now'
                start_dt = parse_time_input(start_time)
                end_dt = parse_time_input(end_time)

            # Validate max_results
            max_results = validate_max_results(max_results, default=10, max_allowed=50)

            # Build lookup parameters
            lookup_params = {
                'StartTime': start_dt,
                'EndTime': end_dt,
                'MaxResults': max_results,
            }

            # Add attribute filter if provided
            if attribute_key and attribute_value:
                lookup_params['LookupAttributes'] = [
                    {'AttributeKey': attribute_key, 'AttributeValue': attribute_value}
                ]

            # Add next_token for pagination if provided
            if next_token:
                lookup_params['NextToken'] = next_token

            logger.info(f'Looking up CloudTrail events with params: {lookup_params}')

            # Call CloudTrail API
            response = cloudtrail_client.lookup_events(**remove_null_values(lookup_params))

            # Build result with consistent parameter format
            result = {
                'events': response.get('Events', []),
                'next_token': response.get('NextToken'),
                'query_params': {
                    'start_time': start_dt.isoformat(),
                    'end_time': end_dt.isoformat(),
                    'attribute_key': attribute_key,
                    'attribute_value': attribute_value,
                    'max_results': max_results,
                    'region': region,
                },
            }

            logger.info(
                f'Successfully retrieved {len(result["events"])} CloudTrail events from region {region}'
            )
            return result

        except Exception as e:
            logger.error(f'Error in lookup_events: {str(e)}')
            await ctx.error(f'Error looking up CloudTrail events: {str(e)}')
            raise

    async def lake_query(
        self,
        ctx: Context,
        sql: Annotated[
            str,
            Field(
                description="SQL query to execute against CloudTrail Lake. IMPORTANT: You must include a valid Event Data Store (EDS) ID in the FROM clause of your SQL query. Use list_event_data_stores tool to get available EDS IDs first. CloudTrail Lake only supports SELECT statements using Trino-compatible SQL syntax. Example: SELECT * FROM 0233062b-51c6-4d18-8dec-a8c90da840d9 WHERE eventname = 'ConsoleLogin'"
            ),
        ],
        wait_for_completion: Annotated[
            bool,
            Field(
                description='Whether to wait for query completion and return results. If False, returns immediately with query_id for manual result fetching using get_query_results. Default: True'
            ),
        ] = True,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> QueryResult:
        """Execute a SQL query against CloudTrail Lake for complex analytics and filtering.

        CloudTrail Lake allows you to run SQL queries against your CloudTrail events for advanced
        analysis. This is more powerful than the basic lookup functions and allows for complex
        filtering, aggregation, and analysis.

        PAGINATION WORKFLOW:
        For large result sets, you have two options:
        1. Use wait_for_completion=False to get the query_id immediately, then use get_query_results with pagination
        2. Use wait_for_completion=True (default) to get first page of results, then use get_query_results with next_token for additional pages

        IMPORTANT LIMITATIONS:
        - CloudTrail Lake only supports SELECT statements using Trino-compatible SQL syntax
        - INSERT, UPDATE, DELETE, CREATE, DROP, and other DDL/DML operations are not supported
        - Your SQL query MUST include a valid Event Data Store (EDS) ID in the FROM clause
        - Use the list_event_data_stores tool first to get available EDS IDs, then reference the EDS ID
          directly in your FROM clause

        Valid SQL query examples:
        - SELECT eventname, count(*) FROM 0233062b-51c6-4d18-8dec-a8c90da840d9 WHERE eventtime > '2023-01-01' GROUP BY eventname
        - SELECT useridentity.username, eventname, eventtime FROM your-eds-id WHERE errorcode IS NOT NULL
        - SELECT DISTINCT awsregion FROM your-eds-id WHERE eventname = 'CreateUser'

        Returns:
        --------
        QueryResult containing:
            - query_id: Unique identifier for the query
            - query_status: Current status of the query
            - query_result_rows: Results if query completed successfully (only when wait_for_completion=True)
            - next_token: Token for pagination (only when wait_for_completion=True and results are paginated)
            - query_statistics: Performance statistics for the query
        """
        try:
            # Create CloudTrail client for the specified region
            cloudtrail_client = self._get_cloudtrail_client(region)

            logger.info(f'Starting CloudTrail Lake query in region {region}')
            logger.info(f'SQL: {sql}')

            # Start the query directly with the provided SQL
            start_response = cloudtrail_client.start_query(
                QueryStatement=sql,
            )

            query_id = start_response['QueryId']
            logger.info(f'Started query with ID: {query_id}')

            # If not waiting for completion, return immediately with query_id
            if not wait_for_completion:
                # Get initial status to return
                initial_status = cloudtrail_client.describe_query(QueryId=query_id)
                return QueryResult(
                    query_id=query_id,
                    query_status=initial_status['QueryStatus'],
                    query_statistics=initial_status.get('QueryStatistics'),
                    error_message=initial_status.get('ErrorMessage'),
                )

            # Poll for completion (with a reasonable timeout)
            max_wait_time = 300  # 5 minutes
            poll_interval = 2  # 2 seconds
            elapsed_time = 0

            # Initialize variables to avoid "possibly unbound" errors
            query_status = 'RUNNING'
            status_response = {}

            while elapsed_time < max_wait_time:
                status_response = cloudtrail_client.describe_query(QueryId=query_id)
                query_status = status_response['QueryStatus']

                if query_status in ['FINISHED', 'FAILED', 'CANCELLED', 'TIMED_OUT']:
                    break

                time.sleep(poll_interval)
                elapsed_time += poll_interval

            # Get final results
            if query_status == 'FINISHED':
                # Use the existing get_query_results method for consistency and better error handling
                return await self.get_query_results(
                    ctx=ctx, query_id=query_id, max_results=50, next_token=None, region=region
                )
            else:
                return QueryResult(
                    query_id=query_id,
                    query_status=query_status,
                    query_statistics=status_response.get('QueryStatistics'),
                    error_message=status_response.get('ErrorMessage'),
                )

        except Exception as e:
            logger.error(f'Error in lake_query: {str(e)}')
            await ctx.error(f'Error executing CloudTrail Lake query: {str(e)}')
            raise

    async def get_query_status(
        self,
        ctx: Context,
        query_id: Annotated[str, Field(description='The ID of the query to check status for')],
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> QueryStatus:
        """Get the status of a CloudTrail Lake query.

        This tool checks the status of a previously started CloudTrail Lake query. Use this
        when you need to check if a long-running query has completed or if you want to get
        details about query execution.

        Usage: Use this tool to monitor the progress of CloudTrail Lake queries, especially
        long-running ones that may take time to complete.

        Returns:
        --------
        QueryStatus containing:
            - query_id: The query identifier
            - query_status: Current status (QUEUED, RUNNING, FINISHED, FAILED, CANCELLED, TIMED_OUT)
            - query_statistics: Performance and execution statistics
            - error_message: Error details if the query failed
        """
        try:
            # Create CloudTrail client for the specified region
            cloudtrail_client = self._get_cloudtrail_client(region)

            logger.info(f'Checking status for query {query_id} in region {region}')

            # Get query status
            response = cloudtrail_client.describe_query(QueryId=query_id)

            return QueryStatus(
                query_id=query_id,
                query_status=response['QueryStatus'],
                query_statistics=response.get('QueryStatistics'),
                error_message=response.get('ErrorMessage'),
                delivery_s3_uri=response.get('DeliveryS3Uri'),
                delivery_status=response.get('DeliveryStatus'),
            )

        except Exception as e:
            logger.error(f'Error in get_query_status: {str(e)}')
            await ctx.error(f'Error getting query status: {str(e)}')
            raise

    async def get_query_results(
        self,
        ctx: Context,
        query_id: Annotated[str, Field(description='The ID of the query to get results for')],
        max_results: Annotated[
            Optional[int],
            Field(description='Maximum number of results to return per page (1-50, default: 50)'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(
                description='Token for pagination to fetch the next page of results. Use the next_token returned from a previous call to get successive pages.'
            ),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> QueryResult:
        """Get the results of a completed CloudTrail Lake query with pagination support.

        This tool retrieves the results of a previously executed CloudTrail Lake query. It supports
        pagination for large result sets, allowing you to fetch results in chunks.

        Usage: Use this tool to get the results of a query that has completed (status = 'FINISHED').
        For large result sets, use the next_token to fetch subsequent pages of results.

        Pagination workflow:
        1. Call get_query_results with just the query_id to get the first page
        2. If next_token is returned, call again with the same query_id and the next_token
        3. Repeat until next_token is null/empty

        Returns:
        --------
        QueryResult containing:
            - query_id: The query identifier
            - query_status: Current status of the query
            - query_result_rows: Results for this page
            - next_token: Token for next page (null if no more pages)
            - query_statistics: Performance statistics for the query
        """
        try:
            # Create CloudTrail client for the specified region
            cloudtrail_client = self._get_cloudtrail_client(region)

            logger.info(f'Getting results for query {query_id} in region {region}')

            # Validate max_results
            max_results = validate_max_results(max_results, default=50, max_allowed=50)

            # Build parameters for get_query_results
            params = {
                'QueryId': query_id,
                'MaxQueryResults': max_results,
            }

            # Add next_token for pagination if provided
            if next_token:
                params['NextToken'] = next_token

            logger.info(f'Getting query results with params: {params}')

            # Get the query results
            results_response = cloudtrail_client.get_query_results(**remove_null_values(params))

            # Also get the query status to include it in the response
            status_response = cloudtrail_client.describe_query(QueryId=query_id)

            return QueryResult(
                query_id=query_id,
                query_status=status_response['QueryStatus'],
                query_statistics=status_response.get('QueryStatistics'),
                query_result_rows=results_response.get('QueryResultRows', []),
                next_token=results_response.get('NextToken'),
                error_message=status_response.get('ErrorMessage'),
            )

        except Exception as e:
            logger.error(f'Error in get_query_results: {str(e)}')
            await ctx.error(f'Error getting query results: {str(e)}')
            raise

    async def list_event_data_stores(
        self,
        ctx: Context,
        include_details: Annotated[
            bool,
            Field(
                description='Whether to include detailed event selector information (default: true)'
            ),
        ] = True,
        region: Annotated[
            str,
            Field(description='AWS region to query. Defaults to us-east-1.'),
        ] = 'us-east-1',
    ) -> List[Dict[str, Any]]:
        """List available CloudTrail Lake Event Data Stores with their capabilities and event selectors.

        Event Data Stores are the storage and query engines for CloudTrail Lake. This tool helps you
        understand which Event Data Stores are available and their configurations.

        Usage: Use this tool to understand which Event Data Stores are available and their
        configurations. This information is needed when executing CloudTrail Lake queries.

        Returns:
        --------
        List of available Event Data Stores with their configurations
        """
        try:
            # Create CloudTrail client for the specified region
            cloudtrail_client = self._get_cloudtrail_client(region)

            logger.info(f'Listing CloudTrail Lake Event Data Stores in region {region}')

            # List event data stores
            response = cloudtrail_client.list_event_data_stores()
            event_data_stores = response.get('EventDataStores', [])

            # Process and format the data stores
            formatted_stores = []
            for store in event_data_stores:
                formatted_store = EventDataStore.model_validate(store).model_dump()

                # Add detailed information if requested
                if include_details and formatted_store.get('event_data_store_arn'):
                    try:
                        details_response = cloudtrail_client.get_event_data_store(
                            EventDataStore=formatted_store['event_data_store_arn']
                        )
                        # Merge additional details
                        formatted_store.update(
                            {
                                'advanced_event_selectors': details_response.get(
                                    'AdvancedEventSelectors', []
                                ),
                                'multi_region_enabled': details_response.get('MultiRegionEnabled'),
                                'organization_enabled': details_response.get(
                                    'OrganizationEnabled'
                                ),
                            }
                        )
                    except Exception as detail_error:
                        logger.warning(
                            f'Could not get detailed info for store {formatted_store.get("name")}: {detail_error}'
                        )

                # Remove null values from the formatted store
                formatted_stores.append(remove_null_values(formatted_store))

            logger.info(
                f'Successfully retrieved {len(formatted_stores)} Event Data Stores from region {region}'
            )
            return formatted_stores

        except Exception as e:
            logger.error(f'Error in list_event_data_stores: {str(e)}')
            await ctx.error(f'Error listing Event Data Stores: {str(e)}')
            raise
