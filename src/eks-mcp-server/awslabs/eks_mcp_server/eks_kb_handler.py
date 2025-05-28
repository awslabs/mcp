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
from requests_auth_aws_sigv4 import AWSSigV4


# API endpoint for the EKS Knowledge Base
API_ENDPOINT = 'https://mcpserver.eks-beta.us-west-2.api.aws/'
AWS_REGION = 'us-west-2'
AWS_SERVICE = 'execute-api'  # TODO: Update the service name before launch.


class EKSKnowledgeBaseHandler:
    """Handler for retriving troubleshooting guide from the EKS Knowledge Base.

    This class provides tools for fetching step by step instructions to troubleshoot issues from the EKS Hosted service.
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
        query: str,
    ) -> str:
        """Search the EKS Troubleshoot Guide for troubleshooting information.

        This tool provides detailed troubleshooting guidance for Amazon EKS issues.
        The guide covers:
        - EKS Auto mode node provisioning and bootstrap issues
        - EKS Auto mode controllers failure modes and mitigations

        For each issue, the tool provides:
        - Symptoms to identify the issue
        - Step-by-step short and long-term fixes

        The tool will return specific troubleshooting steps and solutions based on your query.
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
