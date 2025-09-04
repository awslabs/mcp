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

"""Create Domain Name tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_domain_name import (
    create_domain_name_operation,
)
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, Optional


def register_create_domain_name_tool(mcp):
    """Register the create_domain_name tool with the MCP server."""

    @mcp.tool(
        name='create_domain_name',
        description="""Creates a custom domain name for use with AppSync APIs.

        This operation creates a custom domain name that can be associated with
        AppSync APIs, allowing you to use your own domain instead of the default
        AppSync domain. Requires an SSL certificate from AWS Certificate Manager.
        """,
        annotations=ToolAnnotations(
            title='Create Domain Name',
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    @write_operation
    async def create_domain_name(
        domain_name: Annotated[
            str, Field(description='The domain name to create (e.g., api.example.com)')
        ],
        certificate_arn: Annotated[
            str, Field(description='The ARN of the certificate from AWS Certificate Manager')
        ],
        description: Annotated[
            Optional[str], Field(description='A description of the domain name')
        ] = None,
        tags: Annotated[
            Optional[Dict[str, str]], Field(description='A map of tags to assign to the resource')
        ] = None,
    ) -> Dict:
        """Creates a custom domain name for use with AppSync APIs.

        This operation creates a custom domain name that can be associated with
        AppSync APIs, allowing you to use your own domain instead of the default
        AppSync domain. Requires an SSL certificate from AWS Certificate Manager.

        Args:
            domain_name: The domain name to create (e.g., api.example.com).
            certificate_arn: The ARN of the certificate from AWS Certificate Manager
                that covers the domain name.
            description: Optional description of the domain name.
            tags: Optional map of tags to assign to the resource.

        Returns:
            A dictionary containing information about the created domain name, including:
            - domainNameConfig: The domain name configuration with details like domain name,
              certificate ARN, hosted zone ID, etc.

        Example response:
            {
                "domainNameConfig": {
                    "domainName": "api.example.com",
                    "description": "Custom domain for GraphQL API",
                    "certificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012",
                    "appsyncDomainName": "d-abcdefghij.appsync-api.us-east-1.amazonaws.com",
                    "hostedZoneId": "Z1D633PJN98FT9"
                }
            }
        """
        return await create_domain_name_operation(domain_name, certificate_arn, description, tags)
