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

from ..client.aws_knowledge_client import search_documentation
from ..knowledge_models import CDKToolResponse
from .cdk_best_practices import CDK_BEST_PRACTICES_KNOWLEDGE
from typing import Literal


SEARCH_TOOL_NEXT_STEPS_GUIDANCE = 'To read the full documentation pages for these search results, use the `read_iac_documentation_page` tool. If you need to find real code examples for constructs referenced in the search results, use the `search_cdk_samples_and_constructs` tool.'

SEARCH_CDK_DOCUMENTATION_TOPIC = 'cdk_docs'
SEARCH_CLOUDFORMATION_DOCUMENTATION_TOPIC = 'cloudformation'
SEARCH_CDK_CONSTRUCTS_TOPIC = 'cdk_constructs'
SAMPLE_CONSTRUCT_SEARCH_TOOL_NEXT_STEPS_GUIDANCE = 'To read the full documentation pages for these search results, use the `read_iac_documentation_page` tool.'

SupportedLanguages = Literal['typescript', 'python', 'java', 'csharp', 'go']


async def search_cdk_documentation_tool(query: str) -> CDKToolResponse:
    """Search CDK documentation.

    Args:
        query: The search query for CDK documentation.

    Returns:
        CDKToolResponse containing search results and guidance.
    """
    knowledge_response = await search_documentation(
        search_phrase=query, topic=SEARCH_CDK_DOCUMENTATION_TOPIC, limit=10
    )
    return CDKToolResponse(
        knowledge_response=knowledge_response, next_step_guidance=SEARCH_TOOL_NEXT_STEPS_GUIDANCE
    )


async def search_cloudformation_documentation_tool(query: str) -> CDKToolResponse:
    """Search CloudFormation documentation.

    Args:
        query: Search query for CloudFormation documentation.

    Returns:
        CDKToolResponse containing search results and guidance.
    """
    knowledge_response = await search_documentation(
        search_phrase=query, topic=SEARCH_CLOUDFORMATION_DOCUMENTATION_TOPIC, limit=10
    )
    return CDKToolResponse(knowledge_response=knowledge_response, next_step_guidance=None)


async def search_cdk_samples_and_constructs_tool(
    query: str, language: SupportedLanguages = 'typescript'
) -> CDKToolResponse:
    """Search CDK samples and constructs.

    Args:
        query: Search query for CDK samples and constructs.
        language: Programming language to filter CDK examples and documentation.

    Returns:
        CDKToolResponse containing search results and guidance.
    """
    search_query_with_language = f'{query} {language}'
    knowledge_response = await search_documentation(
        search_phrase=search_query_with_language, topic=SEARCH_CDK_CONSTRUCTS_TOPIC, limit=10
    )
    return CDKToolResponse(
        knowledge_response=knowledge_response,
        next_step_guidance=SAMPLE_CONSTRUCT_SEARCH_TOOL_NEXT_STEPS_GUIDANCE,
    )


async def cdk_best_practices_tool() -> CDKToolResponse:
    """Returns AWS CDK best practices.

    Returns:
        str: CDKToolResponse containing AWS CDK best practices.
    """
    return CDKToolResponse(
        knowledge_response=[CDK_BEST_PRACTICES_KNOWLEDGE],
        next_step_guidance=None,
    )
