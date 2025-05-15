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
import boto3
import os
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict


mcp = FastMCP(
    'awslabs.amazon-kendra-index-mcp-server',
    instructions='Using the users kendra index id as a parameter, query Amazon Kendra with the provided search query',
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)


@mcp.tool(name='KendraQueryTool')
async def example_tool(
    query: str,
) -> Dict[str, Any]:
    """Query Amazon Kendra and retrieve content from the response.

    This tool queries the specified Amazon Kendra index configured in the environemnt variables with the provided query
    and returns the search results.

    Parameters:
        query (str): The search query to send to Amazon Kendra.

    Returns:
        Dict containing the query results from Amazon Kendra.
    """
    kendra_index_id = os.getenv('KENDRA_INDEX_ID')
    try:
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
        logger.error(f'Error querying Kendra: {str(e)}')
        return {'error': str(e), 'query': query, 'index_id': kendra_index_id}


def get_kendra_client():
    """Get a Kendra runtime client.

    Allows access to Kendra Indexes for RAG via the Kendra runtime client.

    """
    # Initialize the Kendra client with given region or profile
    AWS_PROFILE = os.environ.get('AWS_PROFILE')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

    if AWS_PROFILE:
        kendra_client = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION).client(
            'kendra'
        )
        return kendra_client

    kendra_client = kendra_client = boto3.client('kendra', region_name=AWS_REGION)
    return kendra_client


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for amazon-kendra-index-mcp-server'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    logger.trace('A trace message.')
    logger.debug('A debug message.')
    logger.info('An info message.')
    logger.success('A success message.')
    logger.warning('A warning message.')
    logger.error('An error message.')
    logger.critical('A critical message.')

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
