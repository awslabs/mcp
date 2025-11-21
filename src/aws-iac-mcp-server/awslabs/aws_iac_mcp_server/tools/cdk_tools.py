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


SEARCH_TOOL_NEXT_STEPS_GUIDANCE = 'To read the full documentation pages for these search results, use the `read_cdk_documentation_page` tool. If you need to find real code examples for constructs referenced in the search results, use the `search_cdk_samples_and_constructs` tool.'

SEARCH_CDK_DOCUMENTATION_TOPIC = 'cdk_docs'


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
