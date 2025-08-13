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

"""Prompts for the Bedrock Custom Model Import MCP Server."""

from fastmcp import FastMCP


class Prompts:
    """Prompts for the Bedrock Custom Model Import MCP Server.

    This class contains all the prompt definitions that map natural language requests
    to specific tool invocations for the Bedrock Custom Model Import MCP Server.
    """

    def __init__(self, mcp: FastMCP) -> None:
        """Initialize prompts.

        Args:
            mcp: The FastMCP instance to register prompts with
        """
        mcp.prompt(self.create_model_import_job)
        mcp.prompt(self.list_model_import_jobs)
        mcp.prompt(self.list_imported_models)
        mcp.prompt(self.get_model_import_job)
        mcp.prompt(self.get_imported_model)
        mcp.prompt(self.delete_imported_model)

    def create_model_import_job(self):
        """User wants to import a model into Amazon Bedrock.

        This prompt handles requests to import a custom model into Amazon Bedrock.
        It maps to the create_model_import_job tool which initiates the import process.

        Returns:
            str: prompt message to handle the request
        """
        return 'Use the tool create_model_import_job to create a model import job in Bedrock.'

    def list_model_import_jobs(self):
        """User wants to list model import jobs in Amazon Bedrock.

        This prompt handles requests to view all model import jobs.
        It maps to the list_model_import_jobs tool which retrieves the job list.

        Returns:
            str: prompt message to handle the request
        """
        return 'Use the tool list_model_import_jobs to get the list of import jobs in Bedrock.'

    def list_imported_models(self):
        """User wants to list imported models in Amazon Bedrock.

        This prompt handles requests to view all imported models.
        It maps to the list_imported_models tool which retrieves the model list.

        Returns:
            str: prompt message to handle the request
        """
        return 'Use the tool list_imported_models to get the list of imported models in Bedrock.'

    def get_model_import_job(self):
        """User wants to get a model import job in Amazon Bedrock.

        This prompt handles requests to view details of a specific model import job.
        It maps to the get_model_import_job tool which retrieves the job details.

        Returns:
            str: prompt message to handle the request
        """
        return 'Use the tool get_model_import_job to know about the model import job in Bedrock.'

    def get_imported_model(self):
        """User wants to get an imported model in Amazon Bedrock.

        This prompt handles requests to view details of a specific imported model.
        It maps to the get_imported_model tool which retrieves the model details.

        Returns:
            str: prompt message to handle the request
        """
        return 'Use the tool get_imported_model to know about the imported model in Bedrock.'

    def delete_imported_model(self):
        """User wants to delete an imported model in Amazon Bedrock.

        This prompt handles requests to delete a specific imported model.
        It maps to the delete_imported_model tool which removes the model.

        Returns:
            str: prompt message to handle the request
        """
        return 'Use the tool delete_imported_model to delete the imported model in Bedrock.'
