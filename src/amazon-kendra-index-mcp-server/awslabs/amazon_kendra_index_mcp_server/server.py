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

"""awslabs amazon-kendra-index-mcp-server MCP Server implementation."""

import argparse
import os
from awslabs.amazon_kendra_index_mcp_server.util import get_kendra_client
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, Optional


mcp = FastMCP(
    'awslabs.amazon-kendra-index-mcp-server',
    instructions='Using the users kendra index id as a parameter, query Amazon Kendra with the provided search query',
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)


@mcp.tool(name='KendraListIndexesTool')
async def kendra_list_indexes_tool(
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """List all Amazon Kendra indexes in the specified region.

    This tool lists all the Kendra indexes available in the region specified in the mcp configuration.

    Parameters:
        region (str, optional): The AWS region to list Kendra indexes from.

    Returns:
        Dict containing the list of Kendra indexes.
    """
    try:
        if region:
            kendra_client = get_kendra_client(region)
        else:
            kendra_client = get_kendra_client()

        # List all Kendra indexes
        response = kendra_client.list_indices()

        # Process and return the results
        indexes = []
        for index in response.get('IndexConfigurationSummaryItems', []):
            index_info = {
                'id': index.get('Id'),
                'name': index.get('Name'),
                'status': index.get('Status'),
                'created_at': index.get('CreatedAt').isoformat()
                if index.get('CreatedAt')
                else None,
                'updated_at': index.get('UpdatedAt').isoformat()
                if index.get('UpdatedAt')
                else None,
                'edition': index.get('Edition'),
            }
            indexes.append(index_info)

        # Handle pagination if there are more results
        next_token = response.get('NextToken')
        while next_token:
            response = kendra_client.list_indices(NextToken=next_token)
            for index in response.get('IndexConfigurationSummaryItems', []):
                index_info = {
                    'id': index.get('Id'),
                    'name': index.get('Name'),
                    'status': index.get('Status'),
                    'created_at': index.get('CreatedAt').isoformat()
                    if index.get('CreatedAt')
                    else None,
                    'updated_at': index.get('UpdatedAt').isoformat()
                    if index.get('UpdatedAt')
                    else None,
                    'edition': index.get('Edition'),
                }
                indexes.append(index_info)
            next_token = response.get('NextToken')

        return {
            'region': region or os.environ.get('AWS_REGION', 'us-east-1'),
            'count': len(indexes),
            'indexes': indexes,
        }

    except Exception as e:
        return {'error': str(e), 'region': region or os.environ.get('AWS_REGION', 'us-east-1')}


@mcp.tool(name='KendraQueryTool')
async def kendra_query_tool(
    query: str,
    region: Optional[str] = None,
    indexId: Optional[str] = None,
) -> Dict[str, Any]:
    """Query Amazon Kendra and retrieve content from the response.

    This tool queries the specified Amazon Kendra index with the provided query
    and returns the search results. The specified Kendra Index is either provided by the user in the chat, or the default index configured in the environemnt variables

    Parameters:
        query (str): The search query to send to Amazon Kendra.
        region (str): The region of the Kendra Index to send the search query to.
        indexId (str): The indexId of the Kendra index to send the search query to.

    Returns:
        Dict containing the query results from Amazon Kendra.
    """
    kendra_index_id = indexId or os.getenv('KENDRA_INDEX_ID')
    try:
        if region:
            kendra_client = get_kendra_client(region)
        else:
            kendra_client = get_kendra_client()
        if not kendra_index_id:
            raise ValueError('KENDRA_INDEX_ID environment variable is not set.')
        # Query the Kendra index
        response = kendra_client.query(IndexId=kendra_index_id, QueryText=query)

        # Process and return the results
        results = {
            'query': query,
            'total_results_count': response.get('TotalNumberOfResults', 0),
            'results': [],
        }

        # Extract relevant information from each result item
        for item in response.get('ResultItems', []):
            result_item = {
                'id': item.get('Id'),
                'type': item.get('Type'),
                'document_title': item.get('DocumentTitle', {}).get('Text', ''),
                'document_uri': item.get('DocumentURI', ''),
                'score': item.get('ScoreAttributes', {}).get('ScoreConfidence', ''),
            }

            # Extract document excerpt if available
            if 'DocumentExcerpt' in item and 'Text' in item['DocumentExcerpt']:
                result_item['excerpt'] = item['DocumentExcerpt']['Text']

            # Add additional attributes if available
            if 'AdditionalAttributes' in item:
                result_item['additional_attributes'] = item['AdditionalAttributes']

            results['results'].append(result_item)

        return results

    except Exception as e:
        return {'error': str(e), 'query': query, 'index_id': kendra_index_id}


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for amazon-kendra-index-mcp-server'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
