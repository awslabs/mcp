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
"""Implementation of the list_registries tool."""

from botocore.client import BaseClient
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Dict, Optional


class ListRegistriesTool:
    """Implementation of the list_registries tool."""

    def __init__(self, mcp: FastMCP, schemas_client: BaseClient):
        """Initialize the ListRegistriesTool with a FastMCP instance."""
        mcp.tool(name='list_registries')(self.list_registries_impl)
        self.schemas_client = schemas_client

    async def list_registries_impl(
        self,
        ctx: Context,
        registry_name_prefix: Optional[str] = Field(
            default=None,
            description='Specifying this limits the results to only those registry names that start with the specified prefix. For EventBridge events, use aws.events registry directly instead of searching.',
        ),
        scope: Optional[str] = Field(
            default=None,
            description="""Can be set to Local or AWS to limit responses to your custom registries, or the ones provided by AWS.
            LOCAL: The registry is created in your account.
            AWS: The registry is created by AWS.

            For EventBridge events, use aws.events registry which is an AWS-managed registry containing all AWS service event schemas.""",
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
        """Lists the registries in your account.

        REQUIREMENTS:
        - For AWS service events, you MUST use the aws.events registry directly
        - For custom schemas, you MAY use LOCAL scope to manage your own registries
        - When searching AWS service events, you SHOULD use the AWS scope

        USAGE PATTERNS:
        1. Finding AWS Service Event Schemas:
        - Use aws.events registry directly instead of searching
        - Filter by AWS scope to see only AWS-provided schemas

        2. Managing Custom Schemas:
        - Use LOCAL scope to view your custom registries
        - Apply registry_name_prefix to find specific registry groups
        """
        try:
            params = {}
            if limit is not None:
                params['Limit'] = limit
            if next_token is not None:
                params['NextToken'] = next_token
            if scope is not None:
                params['Scope'] = scope
            if registry_name_prefix is not None:
                params['RegistryNamePrefix'] = registry_name_prefix

            response = self.schemas_client.list_registries(**params)
            return {
                'Registries': response.get('Registries', []),
                'NextToken': response.get('NextToken'),
            }
        except Exception as e:
            logger.error(f'Error listing registries: {str(e)}')
            raise
