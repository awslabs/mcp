"""Implementation of the search_schema tool."""

from botocore.client import BaseClient
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Dict, Optional


class SearchSchemaTool:
    """Tool for searching EventBridge schemas in AWS Schema Registry.

    This tool enables searching for event schemas in AWS Schema Registry, particularly
    useful for finding AWS service event schemas when implementing Lambda functions
    that consume events from EventBridge.
    """

    def __init__(self, mcp: FastMCP, schemas_client: BaseClient):
        """Initialize the SearchSchemaTool with a FastMCP instance."""
        mcp.tool(name='search_schema')(self.search_schema_impl)
        self.schemas_client = schemas_client

    async def search_schema_impl(
        self,
        ctx: Context,
        keywords: str = Field(
            description='Keywords to search for. Prefix service names with "aws." for better results (e.g., "aws.s3" for S3 events, "aws.ec2" for EC2 events).'
        ),
        registry_name: str = Field(
            description='For AWS service events, use "aws.events" to search the EventBridge schema registry.'
        ),
        limit: Optional[int] = Field(
            default=None,
            description='Maximum number of results to return. If you specify 0, the operation returns up to 10 results.',
            ge=0,
            le=100,
        ),
        next_token: Optional[str] = Field(
            default=None, description='Next token returned by the previous operation.'
        ),
    ) -> Dict:
        """Search for schemas in a registry using keywords.

        REQUIREMENTS:
        - You MUST use this tool to find schemas for AWS service events
        - You MUST search in the "aws.events" registry for AWS service events
        - You MUST use this tool when implementing Lambda functions that consume events from EventBridge
        - You SHOULD prefix search keywords with "aws." for optimal results (e.g., "aws.s3", "aws.ec2")
        - You MAY filter results using additional keywords for specific event types

        USE CASES:

        1. Lambda Function Development with EventBridge:
        - CRITICAL: Required for Lambda functions consuming events from EventBridge
        - Search for event schemas your function needs to process
        - Example: "aws.s3" for S3 events, "aws.dynamodb" for DynamoDB streams
        - Use results with describe_schema to get complete event structure

        2. EventBridge Rule Creation:
        - Find schemas to create properly structured event patterns
        - Example: "aws.ec2" for EC2 instance state changes
        - Ensure exact field names and types in rule patterns

        IMPLEMENTATION FLOW:
        1. Search aws.events registry for service schemas
        2. Note relevant schema names from results
        3. Use describe_schema to get complete definitions
        4. Implement handlers using exact schema structure
        """
        try:
            params = {'Keywords': keywords, 'RegistryName': registry_name}
            if limit is not None:
                params['Limit'] = str(limit)
            if next_token is not None:
                params['NextToken'] = next_token

            response = self.schemas_client.search_schemas(**params)
            return {
                'Schemas': response.get('Schemas', []),
                'NextToken': response.get('NextToken'),
            }
        except Exception as e:
            logger.error(f'Error searching schemas: {str(e)}')
            raise
