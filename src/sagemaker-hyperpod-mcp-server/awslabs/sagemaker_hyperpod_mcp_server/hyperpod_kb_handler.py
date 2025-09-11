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

"""Knowledge Base handler for the HyperPod MCP Server."""

import requests  # type: ignore
from awslabs.sagemaker_hyperpod_mcp_server.consts import (
    KB_API_ENDPOINT,
    KB_AWS_REGION,
    KB_AWS_SERVICE,
)
from loguru import logger
from pydantic import Field
from requests_auth_aws_sigv4 import AWSSigV4


class HyperPodKnowledgeBaseHandler:
    """Handler for retrieving user guides and troubleshooting guides from the HyperPod Knowledge Base and generating responses to user questions on HyperPod.

    This class provides tools for fetching instructions to usage questions or troubleshoot issues from the HyperPod Hosted knowledge base service.
    """

    def __init__(self, mcp):
        """Initialize the HyperPod Knowledge Base handler.

        Args:
            mcp: The MCP server instance
        """
        self.mcp = mcp

        # Register tools
        self.mcp.tool(name='search_hyperpod_knowledge_base')(self.search_hyperpod_knowledge_base)

    async def search_hyperpod_knowledge_base(
        self,
        query: str = Field(
            ...,
            description='Your specific question related to HyperPod features, usage, or troubleshooting',
        ),
    ) -> str:
        """Generate answers to questions about Amazon SageMaker HyperPod.

        This tool provides comprehensive answers to questions about Amazon SageMaker HyperPod by querying
        a specialized knowledge base of HyperPod user guide and troubleshooting information. It helps answer questions about
        HyperPod features, capabilities, usage instructions, as well as identify
        common problems and provides step-by-step solutions for resolving cluster creation issues,
        node management problems, workload deployment issues, and diagnosing error messages.

        ## Requirements
        - Internet connectivity to access the HyperPod Knowledge Base API
        - Valid AWS credentials with permissions to access the HyperPod Knowledge Base
        - IAM permission: execute-api:Invoke

        ## Response Information
        The response includes instructions for using HyperPod clusters and troubleshooting HyperPod issues.

        ## Usage Tips
        - For troubleshooting: Provide specific error messages or symptoms in your query
        - For feature information: Ask about specific HyperPod capabilities or usage scenarios
        - Try running this tool 2-3 times with different phrasings or related queries to increase the chance of getting the most helpful answer

        ## Fallback Options:
        - If this tool fails, advise consulting AWS SageMaker HyperPod documentation:
            - HyperPod User Guide: https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html
            - API Reference: https://docs.aws.amazon.com/sagemaker/latest/APIReference/
        - Or, as other alternatives: advise searching AWS re:Post community forums or contacting AWS Support

        Args:
            query: Your specific question related to HyperPod features, usage, or troubleshooting. Question has to be less than 300 characters.

        Returns:
            str: Detailed usage or troubleshooting guidance for HyperPod questions
        """
        try:
            response = requests.post(
                KB_API_ENDPOINT,
                json={'question': query},
                auth=AWSSigV4(KB_AWS_SERVICE, region=KB_AWS_REGION),
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f'Error in search_hyperpod_knowledge_base: {str(e)}')
            return f'Error: {str(e)}'
