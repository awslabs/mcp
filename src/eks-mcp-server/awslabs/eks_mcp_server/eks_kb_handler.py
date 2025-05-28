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

"""Knowledge Base Retrival handler for the EKS MCP Server."""

import requests
from loguru import logger
from pydantic import Field
from requests_auth_aws_sigv4 import AWSSigV4


# API endpoint for the EKS Knowledge Base
API_ENDPOINT = 'https://mcpserver.eks-beta.us-west-2.api.aws/'
AWS_REGION = 'us-west-2'
AWS_SERVICE = 'eks-mcpserver'


class EKSKnowledgeBaseHandler:
    """Handler for retriving troubleshooting guide from the EKS Knowledge Base.

    This class provides tools for fetching instructions to troubleshoot issues from the EKS Hosted MCP service.
    """

    def __init__(self, mcp):
        """Initialize the EKS Knowledge Base handler.

        Args:
            mcp: The MCP server instance
        """
        self.mcp = mcp

        # Register tools
        self.mcp.tool(name='search_eks_troubleshoot_guide')(self.search_eks_troubleshoot_guide)

    async def search_eks_troubleshoot_guide(
        self,
        query: str = Field(
            ...,
            description='Your specific question or issue description related to EKS troubleshooting',
        ),
    ) -> str:
        """Search the EKS Troubleshoot Guide for troubleshooting information.

        This tool provides troubleshooting guidance for Amazon EKS issues by querying
        a specialized knowledge base of EKS troubleshooting information. It helps identify
        common problems and provides step-by-step solutions for resolving cluster creation issues,
        node group management problems, workload deployment issues, and diagnosing error messages.

        ## Requirements
        - Internet connectivity to access the EKS Knowledge Base API
        - Valid AWS credentials with permissions to access the EKS Knowledge Base
        - IAM permission: eks-mcpserver:QueryKnowledgeBase

        ## Response Information
        The response includes bullet-point instructions for troubleshooting EKS issues.

        ## Usage Tips
        - Provide specific error messages or symptoms in your query
        - Try running this tool 2-3 times with different phrasings or related queries to increase the chance of retrieving the most relevant guidance

        Args:
            query: Your specific question or issue description related to EKS troubleshooting. Question has to be less than 300 characters and can only
            contain letters, numbers, comma, period, question marks, and spaces

        Returns:
            str: Detailed troubleshooting guidance for the EKS issue
        """
        try:
            response = requests.post(
                API_ENDPOINT,
                json={'question': query},
                auth=AWSSigV4(AWS_SERVICE, region=AWS_REGION),
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f'Error in search_eks_troubleshoot_guide: {str(e)}')
            return f'Error: {str(e)}'
