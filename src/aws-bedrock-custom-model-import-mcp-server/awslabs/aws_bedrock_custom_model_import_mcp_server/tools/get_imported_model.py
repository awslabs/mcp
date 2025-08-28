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

"""Tool for retrieving imported model details from Amazon Bedrock."""

from typing import Annotated, Optional  # noqa: I001
from fastmcp import Context, FastMCP
from loguru import logger
from pydantic import Field
from awslabs.aws_bedrock_custom_model_import_mcp_server.services.imported_model_service import (
    ImportedModelService,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import ImportedModel
from awslabs.aws_bedrock_custom_model_import_mcp_server.llm_context import (
    build_imported_model_details_context,
)


class GetImportedModel:
    """Tool for retrieving imported model details from Amazon Bedrock.

    This class implements the get_imported_model tool which allows users to
    retrieve detailed information about models that have been imported
    into Amazon Bedrock. It supports looking up models by their name or ARN.

    The tool provides comprehensive model details including the model's ARN,
    creation time, status, and configuration settings. It includes fuzzy matching
    capabilities to help find models even with approximate name matches.

    Attributes:
        mcp: The FastMCP instance to register the tool with
        imported_model_service: The service for managing imported model operations
    """

    def __init__(self, mcp: FastMCP, imported_model_service: ImportedModelService) -> None:
        """Initialize the get imported model tool.

        Args:
            mcp: The FastMCP instance to register the tool with
            imported_model_service: The service for managing imported model operations
        """
        self.imported_model_service = imported_model_service
        mcp.tool(self.get_imported_model)

    async def get_imported_model(
        self,
        ctx: Optional[Context],
        model_identifier: Annotated[str, Field(description='Name or ARN of the model')],
    ) -> str:
        """Get imported model details from Amazon Bedrock.

        This tool retrieves detailed information about a custom model that was previously
        imported into Amazon Bedrock. If the exact model name is not found, it will attempt
        to find a close match using approximate matching.

        ## Usage Instructions
        1. Provide the model name or ARN as the model_identifier parameter
        2. The tool will attempt to find close matches if the exact name isn't found

        ## Information Returned
        - Model ARN and creation time
        - Model architecture details
        - Whether the model supports chat or instructions
        - Custom model units used for billing the model (if applicable)
        - KMS key information (if encrypted)
        - Import job details and data source

        ## How to Use This Information
        - Verify model details before using in applications
        - Check if the model supports instruction for chat applications using Bedrock Converse API
        - Review the model details to trace model provenance
        - Use the model ARN when configuring inference endpoints

        Args:
            ctx: The MCP context
            model_identifier: The ID or name of the model to retrieve

        Returns:
            str: Formatted markdown text containing the model details

        Raises:
            ValueError: If model cannot be found even with approximate matching
            ClientError: If there is an error from the AWS service
        """
        try:
            model = await self.imported_model_service.get_imported_model(model_identifier)

            # Format the response
            formatted_text = self._format_response(model)

            # Add contextual information
            if ctx:
                await ctx.info('Adding contextual information about imported model details')
                formatted_text += build_imported_model_details_context(model)

            return formatted_text
        except ValueError as e:
            if ctx:
                await ctx.error(
                    'Model cannot be found. '
                    'Suggest user to specify the exact model name or ARN to retry.'
                )
            raise ValueError(f'Error getting imported model: {str(e)}')
        except Exception as e:
            logger.error(f'Error getting imported model: {str(e)}')
            if ctx:
                await ctx.error(f'Error getting imported model: {str(e)}')
            raise Exception(f'Error getting imported model: {str(e)}')

    def _format_response(self, model: ImportedModel) -> str:
        """Format the model details into a markdown string.

        Args:
            model: The model details

        Returns:
            str: Formatted markdown text containing the list of models
        """
        instruct = '✅' if model.instruct_supported else '❌'
        formatted_text = f'## Imported Model: `{model.model_name}`\n\n'

        formatted_text += '### Model Details\n\n'
        formatted_text += f'- **Model ARN**: `{model.model_arn}`\n'
        formatted_text += f'- **Created**: `{model.creation_time.strftime("%Y-%m-%d %H:%M:%S")}`\n'
        formatted_text += f'- **Architecture**: `{model.model_architecture}`\n'
        formatted_text += f'- **Instruct Support**: {instruct}\n'

        if model.custom_model_units:
            formatted_text += f"""- **Custom Model Units**: `Units per copy = {model.custom_model_units.custom_model_units_per_model_copy}`
                and `Version = {model.custom_model_units.custom_model_units_version}`\n"""

        if model.model_kms_key_arn:
            formatted_text += f'- **KMS Key ARN**: `{model.model_kms_key_arn}`\n'

        formatted_text += '\n### Import Details\n\n'
        formatted_text += f'- **Import Job**: `{model.job_name}`\n'
        formatted_text += f'- **Job ARN**: `{model.job_arn}`\n'
        formatted_text += f'- **Data Source**: `{model.model_data_source.s3_data_source.s3_uri}`\n'

        return formatted_text
