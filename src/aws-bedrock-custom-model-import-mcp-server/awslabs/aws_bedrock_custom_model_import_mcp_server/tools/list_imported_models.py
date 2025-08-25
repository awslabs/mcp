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

"""Tool for listing imported models in Amazon Bedrock."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.llm_context import (
    build_list_imported_models_context,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    ListImportedModelsRequest,
    ListImportedModelsResponse,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.services.imported_model_service import (
    ImportedModelService,
)
from fastmcp import Context, FastMCP
from loguru import logger
from typing import Optional


class ListImportedModels:
    """Tool for listing imported models in Amazon Bedrock.

    This class implements the list_imported_models tool which allows users to
    retrieve a list of all models that have been imported into Amazon Bedrock.
    It supports filtering and sorting options to help users find specific models
    or organize the results according to their needs.

    The tool provides a paginated list of models with their basic details. Users can
    filter models by creation time, name patterns, and other criteria. Results can be
    sorted by various attributes to help locate specific models or understand the
    chronological order of imports.

    Attributes:
        mcp: The FastMCP instance to register the tool with
        imported_model_service: The service for managing imported model operations
    """

    def __init__(self, mcp: FastMCP, imported_model_service: ImportedModelService) -> None:
        """Initialize the list imported models tool.

        Args:
            mcp: The FastMCP instance to register the tool with
            imported_model_service: The service for managing imported model operations
        """
        self.imported_model_service = imported_model_service
        mcp.tool(self.list_imported_models)

    async def list_imported_models(
        self, ctx: Optional[Context], request: Optional[ListImportedModelsRequest] = None
    ) -> str:
        """List imported models in Amazon Bedrock.

        This tool retrieves a list of models that have already been imported into Amazon Bedrock.
        The results can be filtered and sorted using the optional request parameters.

        ## Usage Instructions
        1. Call this tool without parameters to list all imported models
        2. Optionally provide filtering parameters in the request:
           - creationTimeAfter: Filter models created after this time
           - creationTimeBefore: Filter models created before this time
           - nameContains: Filter models by name substring
           - sortBy: Sort results by field (e.g., CreationTime)
           - sortOrder: Sort order (Ascending, Descending)

        ## Information Returned
        - Model name and ARN
        - Creation time
        - Model architecture
        - Whether the model supports instruction tuning (✅ or ❌)

        ## How to Use This Information
        - Note model names for use with other tools like get_imported_model
        - Check instruction support to determine if models can be used for chat applications
        - Review model architectures to understand model capabilities

        ## When to Use
        - Before using get_imported_model to find the exact model name
        - When you need to see all available models in your account
        - To check if a specific model exists by filtering with nameContains
        - To find the most recently imported models by sorting by creation time

        Args:
            ctx: The MCP context
            request: Optional request parameters for filtering and sorting the results

        Returns:
            str: Formatted markdown text containing the list of models

        Raises:
            Exception: If there is an error listing the models
        """
        try:
            response = await self.imported_model_service.list_imported_models(request)

            # Format the response
            formatted_text = self._format_response(response)

            # Add contextual information
            if ctx:
                await ctx.info('Adding contextual information about imported models')
                formatted_text += build_list_imported_models_context(response)

            return formatted_text
        except Exception as e:
            logger.error(f'Error listing imported models: {str(e)}')
            if ctx:
                await ctx.error(f'Error listing imported models: {str(e)}')
            raise Exception(f'Error listing imported models: {str(e)}')

    def _format_response(self, response: ListImportedModelsResponse) -> str:
        """Format the list of models into a markdown table.

        Args:
            response: The response containing the list of models

        Returns:
            str: Formatted markdown text containing the list of models
        """
        formatted_text = '## Imported Models\n\n'

        if response.model_summaries:
            formatted_text += '| Model Name | Created | Architecture | Instruct Support | ARN |\n'
            formatted_text += '|-----------|---------|--------------|-----------------|-----|\n'

            for model in response.model_summaries:
                instruct = '✅' if model.instruct_supported else '❌'
                created_time = (
                    model.creation_time.strftime('%Y-%m-%d %H:%M')
                    if model.creation_time
                    else 'N/A'
                )
                formatted_text += (
                    f'| `{model.model_name}` | '
                    f'`{created_time}` | '
                    f'`{model.model_architecture}` | {instruct} | '
                    f'`{model.model_arn}` |\n'
                )
        else:
            formatted_text += 'No imported models found.\n'

        return formatted_text
