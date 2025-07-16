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

"""MSK Documentation Resources.

This module provides resources for accessing AWS MSK documentation.
"""

import json
from .pdf_utils import PDF_RESOURCES, extract_pdf_content, extract_pdf_toc, get_pdf_content
from mcp.server.fastmcp import FastMCP
from typing import Optional


async def register_module(mcp: FastMCP) -> None:
    """Register MSK documentation resources with the MCP server."""

    @mcp.resource(
        uri='resource://msk-documentation', name='MSKDocumentation', mime_type='application/json'
    )
    async def msk_documentation_index() -> str:
        """Access an index of available MSK documentation resources.

        This resource serves as the entry point for all MSK documentation, providing a comprehensive
        list of available documentation resources with their URIs, names, descriptions, and URLs.

        When to use:
        - As the first step when exploring MSK documentation
        - When you need to discover what documentation resources are available
        - To find the appropriate resource URI for more specific documentation needs

        How to use:
        - Access this resource directly without parameters
        - Parse the returned JSON to find the URI of the specific documentation resource you need
        - Use the URIs provided to access more detailed documentation resources

        Returns:
        - A JSON object containing an array of resources, each with:
          * uri: The resource URI to access the specific documentation
          * name: The human-readable name of the resource
          * description: A brief description of the resource
          * url: The source URL for the documentation
        """
        return json.dumps(
            {
                'resources': [
                    {
                        'uri': 'resource://msk-documentation/developer-guide',
                        'name': 'Amazon MSK Developer Guide',
                        'description': 'Comprehensive reference for MSK features, configurations, security, monitoring, and best practices. Use for detailed technical information and implementation guidance.',
                        'url': PDF_RESOURCES['developer-guide']['url'],
                    },
                    {
                        'uri': 'resource://msk-documentation/developer-guide/toc',
                        'name': 'Amazon MSK Developer Guide Table of Contents',
                        'description': 'Navigation aid for the MSK Developer Guide. Use to quickly locate specific topics, identify relevant sections, and find page numbers for targeted reading.',
                        'url': PDF_RESOURCES['developer-guide']['url'],
                    },
                ]
            }
        )

    @mcp.resource(
        uri='resource://msk-documentation/developer-guide',
        name='MSKDeveloperGuide',
        mime_type='application/json',
    )
    async def msk_developer_guide(start_page: int = 1, end_page: Optional[int] = None) -> str:
        """Access the Amazon MSK Developer Guide.

        This resource provides the content from the official AWS MSK Developer Guide PDF, which is the
        comprehensive reference for Amazon Managed Streaming for Kafka (MSK).

        When to use:
        - When you need detailed information about MSK features, configurations, or operations
        - When troubleshooting MSK-related issues that require in-depth understanding
        - When designing MSK architectures and need best practices or implementation guidance
        - When you need specific technical details about MSK cluster setup, security, monitoring, etc.

        How to use:
        - For targeted reading, use the start_page and end_page parameters to retrieve specific sections
        - For large documents, retrieve content in chunks by making multiple calls with different page ranges
        - Use in conjunction with the TOC resource to first identify relevant sections and their page numbers
        - Parse the returned JSON to access the content and pagination information

        Content overview:
        - Cluster creation and configuration options
        - Security and authentication mechanisms
        - Monitoring and logging capabilities
        - Performance optimization techniques
        - Troubleshooting common issues
        - Integration with other AWS services
        - API reference and CLI commands

        Example scenarios:
        - "I need to understand MSK cluster sizing options" → Use this resource to find the broker instance types
        - "How do I configure MSK security?" → Access the security sections of the guide
        - "What monitoring metrics are available?" → Find the monitoring chapter in the guide

        Args:
            start_page: First page to include (starting from 1)
            end_page: Last page to include (or None for all remaining pages)
        """
        try:
            # Get PDF content directly from URL
            pdf_content = await get_pdf_content('developer-guide')

            # Extract content
            content_result = extract_pdf_content(pdf_content, start_page, end_page)

            # Add metadata
            result = {
                'title': PDF_RESOURCES['developer-guide']['title'],
                'source_url': PDF_RESOURCES['developer-guide']['url'],
                **content_result,
            }

            return json.dumps(result)
        except Exception as e:
            return json.dumps(
                {'error': f'Failed to process PDF resource: {str(e)}', 'content': None}
            )

    @mcp.resource(
        uri='resource://msk-documentation/developer-guide/toc',
        name='MSKDeveloperGuideTOC',
        mime_type='application/json',
    )
    async def msk_developer_guide_toc() -> str:
        """Access the table of contents for the Amazon MSK Developer Guide.

        This resource provides the table of contents extracted from the MSK Developer Guide PDF,
        helping you navigate the comprehensive documentation more efficiently.

        When to use:
        - Before accessing the full developer guide to identify relevant sections
        - When you need to quickly determine if the guide contains information on a specific topic
        - To get an overview of the guide's structure and content organization
        - When planning which sections to read in a large document

        How to use:
        - Access this resource without parameters to retrieve the complete table of contents
        - Parse the returned JSON to find the titles and corresponding page numbers
        - Use the page numbers with the MSKDeveloperGuide resource to retrieve specific sections
        - Look for section titles that match your information needs

        Content overview:
        - A structured list of all major sections and subsections in the developer guide
        - Page numbers for each section to facilitate targeted reading
        - Section titles that indicate the topics covered

        Example scenarios:
        - "I need to find information about MSK security features" → Use the TOC to locate security sections
        - "Where can I find information about MSK pricing?" → Check the TOC for pricing-related sections
        - "I want to read about MSK monitoring" → Find the monitoring section and its page number
        """
        try:
            # Get PDF content directly from URL
            pdf_content = await get_pdf_content('developer-guide')

            # Extract TOC
            toc = extract_pdf_toc(pdf_content)

            return json.dumps(
                {
                    'title': PDF_RESOURCES['developer-guide']['title'],
                    'source_url': PDF_RESOURCES['developer-guide']['url'],
                    'toc': toc,
                }
            )
        except Exception as e:
            return json.dumps({'error': f'Failed to process PDF TOC: {str(e)}', 'toc': []})
