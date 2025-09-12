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

"""Imported model service class for Bedrock Custom Model Import MCP Server."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.client import (
    BedrockModelImportClient,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    ImportedModel,
    ListImportedModelsRequest,
    ListImportedModelsResponse,
    ModelSummary,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import AppConfig
from fastmcp.exceptions import ToolError
from loguru import logger
from typing import Any, Dict, Optional


class ImportedModelService:
    """Service for imported model operations."""

    def __init__(self, client: BedrockModelImportClient, config: AppConfig):
        """Initialize the service with the given client.

        Args:
            client: The Bedrock Custom Model client
            config: Configuration of the MCP server
        """
        self.client = client
        self.config = config
        logger.info('ImportedModelService initialized')

    async def list_imported_models(
        self, request: Optional[ListImportedModelsRequest] = None
    ) -> ListImportedModelsResponse:
        """List imported models.

        Args:
            request: Optional request parameters including filters and pagination

        Returns:
            ListImportedModelsResponse: List of model summaries
        """
        try:
            logger.info('Listing imported models')
            kwargs = self._prepare_list_models_kwargs(request)

            response = self.client.list_imported_models(**kwargs)
            summaries = [self._create_model_summary(model) for model in response['modelSummaries']]

            logger.info(f'Found {len(summaries)} imported models')
            return ListImportedModelsResponse(
                modelSummaries=summaries,
                nextToken=response.get('nextToken'),
            )
        except Exception as e:
            error_msg = f'Error listing imported models: {str(e)}'
            logger.error(error_msg)
            raise

    def _prepare_list_models_kwargs(
        self, request: Optional[ListImportedModelsRequest]
    ) -> Dict[str, Any]:
        """Prepare kwargs for listing imported models.

        Args:
            request: Optional request parameters

        Returns:
            Dict[str, Any]: Kwargs for listing imported models
        """
        kwargs: Dict[str, Any] = {}
        if request:
            if request.creation_time_after:
                kwargs['creationTimeAfter'] = request.creation_time_after
                logger.info(f'Filtering by creation time after: {request.creation_time_after}')
            if request.creation_time_before:
                kwargs['creationTimeBefore'] = request.creation_time_before
                logger.info(f'Filtering by creation time before: {request.creation_time_before}')
            if request.name_contains:
                kwargs['nameContains'] = request.name_contains
                logger.info(f'Filtering by name contains: {request.name_contains}')
            if request.sort_by:
                kwargs['sortBy'] = request.sort_by
                logger.info(f'Sorting by: {request.sort_by}')
            if request.sort_order:
                kwargs['sortOrder'] = request.sort_order
                logger.info(f'Sort order: {request.sort_order}')
        return kwargs

    async def get_imported_model(self, model_identifier: str) -> ImportedModel:
        """Get imported model details.

        Args:
            model_identifier: Name or ARN of the model to retrieve details for

        Returns:
            ImportedModel: The imported model details

        Raises:
            ValueError: If model cannot be found
            ClientError: If there is an error from the AWS service
        """
        try:
            logger.info(f'Getting imported model details for: {model_identifier}')
            response = self.client.get_imported_model(model_identifier)
            return self._create_imported_model_from_response(response)
        except Exception as e:
            error_msg = f'Error getting imported model: {str(e)}'
            logger.error(error_msg)
            raise

    def _create_imported_model_from_response(self, response: Dict[str, Any]) -> ImportedModel:
        """Create an ImportedModel from the API response.

        Args:
            response: The model data from the API

        Returns:
            ImportedModel: The imported model
        """
        return ImportedModel(
            modelArn=response['modelArn'],
            modelName=response['modelName'],
            jobName=response['jobName'],
            jobArn=response['jobArn'],
            modelDataSource=response['modelDataSource'],
            creationTime=response['creationTime'],
            modelArchitecture=response['modelArchitecture'],
            modelKmsKeyArn=response.get('modelKmsKeyArn'),
            instructSupported=response['instructSupported'],
            customModelUnits=response.get('customModelUnits'),
        )

    async def delete_imported_model(self, model_identifier: str) -> None:
        """Delete an imported model.

        Args:
            model_identifier: ID or ARN of the model to delete

        Raises:
            Exception: If there is an error deleting the model
        """
        # Check if write access is disabled
        if not self.config.allow_write:
            error_message = 'Deleting imported models requires --allow-write flag'
            logger.error(error_message)
            raise ToolError(error_message)

        try:
            logger.info(f'Deleting imported model: {model_identifier}')
            self.client.delete_imported_model(model_identifier)
            logger.info(f'Successfully deleted model: {model_identifier}')
        except Exception as e:
            error_msg = f'Error deleting imported model: {str(e)}'
            logger.error(error_msg)
            raise

    def _create_model_summary(self, model: Dict[str, Any]) -> ModelSummary:
        """Create a model summary from the API response.

        Args:
            model: The model data from the API

        Returns:
            ModelSummary: The model summary
        """
        return ModelSummary(
            modelArn=model['modelArn'],
            modelName=model['modelName'],
            creationTime=model['creationTime'],
            instructSupported=model['instructSupported'],
            modelArchitecture=model['modelArchitecture'],
        )
