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
"""Implementation of the describe_schema tool."""

from botocore.client import BaseClient
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Dict, Optional


class DescribeSchemaTool:
    """DescribeSchemaTool class for describing schemas."""

    def __init__(self, mcp: FastMCP, schemas_client: BaseClient):
        """Initialize the DescribeSchemaTool with a FastMCP instance."""
        mcp.tool(name='describe_schema')(self.describe_schema_impl)
        self.schemas_client = schemas_client

    async def describe_schema_impl(
        self,
        ctx: Context,
        registry_name: str = Field(
            description='For AWS service events, use "aws.events" to access the EventBridge schema registry.'
        ),
        schema_name: str = Field(
            description='The name of the schema to retrieve (e.g., "aws.s3@ObjectCreated" for S3 events).'
        ),
        schema_version: Optional[str] = Field(
            default=None,
            description='Version number of the schema. For AWS service events, use latest version (default) to ensure up-to-date event handling.',
        ),
    ) -> Dict:
        """Retrieve the schema definition for the specified schema version.

        REQUIREMENTS:
        - You MUST use this tool to get complete schema definitions before implementing handlers
        - You MUST use this tool when implementing Lambda functions that consume events from EventBridge
        - You MUST use the returned schema structure for type-safe event handling
        - You SHOULD use the latest schema version unless specifically required otherwise
        - You MUST validate all required fields defined in the schema

        USE CASES:

        1. Lambda Function Handlers with EventBridge:
        You MUST:
        - CRITICAL: Required for Lambda functions consuming events from EventBridge
        - Implement handlers using the exact event structure
        - Validate all required fields defined in schema
        - Handle optional fields appropriately
        - Ensure type safety for EventBridge-sourced events

        You SHOULD:
        - Generate strongly typed code based on schema
        - Implement error handling for missing fields
        - Document any assumptions about structure

        2. EventBridge Rules:
        You MUST:
        - Create patterns that exactly match schema
        - Use correct field names and value types
        - Include all required fields in patterns

        You SHOULD:
        - Test patterns against sample events
        - Document pattern matching logic
        - Consider schema versions in design

        The schema content provides complete event structure with all fields and types, ensuring correct event handling.
        """
        try:
            params = {'RegistryName': registry_name, 'SchemaName': schema_name}
            if schema_version is not None:
                params['SchemaVersion'] = schema_version

            response = self.schemas_client.describe_schema(**params)
            return {
                'SchemaName': response.get('SchemaName'),
                'SchemaArn': response.get('SchemaArn'),
                'SchemaVersion': response.get('SchemaVersion'),
                'Content': response.get('Content'),
                'LastModified': response.get('LastModified'),
            }
        except Exception as e:
            logger.error(f'Error describing schema: {str(e)}')
            raise
