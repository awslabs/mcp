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

"""Tool for deleting imported models from Amazon Bedrock."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.services.imported_model_service import (
    ImportedModelService,
)
from fastmcp import Context, FastMCP
from loguru import logger
from typing import Optional


class DeleteImportedModel:
    """Tool for deleting imported models from Amazon Bedrock.

    This class implements the delete_imported_model tool which allows users to
    permanently remove custom models that were previously imported into Amazon Bedrock.
    It handles the deletion process by accepting either a model ID or ARN.

    The tool performs validation of the model identifier and ensures proper cleanup
    of the model resources. This operation is irreversible and should be used with
    caution as it permanently removes the model from Bedrock.

    Attributes:
        imported_model_service: The service for managing imported model operations
    """

    def __init__(self, mcp: FastMCP, imported_model_service: ImportedModelService) -> None:
        """Initialize the delete imported model tool.

        Args:
            mcp: The FastMCP instance to register the tool with
            imported_model_service: The service for managing imported model operations
        """
        self.imported_model_service = imported_model_service
        mcp.tool(self.delete_imported_model)

    async def delete_imported_model(self, ctx: Optional[Context], model_identifier: str) -> str:
        """Delete an imported model from Amazon Bedrock.

        This tool permanently deletes a custom model that was previously imported into Amazon Bedrock.
        This operation cannot be undone and will permanently remove the model from your AWS account.

        ## Usage Instructions
        1. Provide either the model name or ARN as the model_identifier parameter
        2. You can get a list of available models using the list_imported_models tool
        3. Verify you're deleting the correct model before proceeding

        ## Important Considerations
        - This operation is IRREVERSIBLE - the model will be permanently deleted
        - Any applications using this model will fail after deletion
        - Consider backing up important model data before deletion
        - Deletion may take some time to complete for large models

        ## When to Use
        - When you no longer need a specific model
        - To manage costs by removing unused models

        Args:
            ctx: The MCP context
            model_identifier: The name or ARN of the model to delete

        Returns:
            str: Formatted markdown text confirming the deletion

        Raises:
            Exception: If there is an error deleting the model
        """
        try:
            await self.imported_model_service.delete_imported_model(model_identifier)

            # Format the response
            formatted_text = self._format_response(model_identifier)

            logger.info(f'Successfully deleted model: {model_identifier}')
            if ctx:
                await ctx.info(f'Successfully deleted model: {model_identifier}')

            return formatted_text
        except Exception as e:
            logger.error(f'Error deleting imported model: {str(e)}')
            if ctx:
                await ctx.error(f'Error deleting imported model: {str(e)}')
            raise Exception(f'Error deleting imported model: {str(e)}')

    def _format_response(self, model_identifier: str) -> str:
        """Format the response for the deleted model.

        Args:
            model_identifier: The name or ARN of the model of the deleted model

        Returns:
            str: Formatted markdown text confirming the deletion
        """
        formatted_text = '## Model Deletion\n\n'
        formatted_text += f'✅ **Successfully deleted model**: `{model_identifier}`\n\n'
        formatted_text += 'The model has been permanently removed from Amazon Bedrock.\n'

        return formatted_text
