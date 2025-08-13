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

"""Bedrock Custom Model Import MCP Server implementation.

This module implements the MCP server for managing custom import models in Amazon Bedrock.
It provides tools for creating model import jobs, managing imported models, and tracking
import job status.

The server supports the following operations:
- Creating model import jobs
- Listing model import jobs and their status
- Getting details of specific import jobs
- Listing imported models
- Getting details of specific imported models
- Deleting imported models

Each operation is implemented as a separate tool class and registered with the MCP server
during initialization.
"""

import argparse
import os
import sys
from awslabs.aws_bedrock_custom_model_import_mcp_server import __version__
from awslabs.aws_bedrock_custom_model_import_mcp_server.client import (
    BedrockModelImportClient,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.prompts import Prompts
from awslabs.aws_bedrock_custom_model_import_mcp_server.services import (
    ImportedModelService,
    ModelImportService,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.create_model_import_job import (
    CreateModelImportJob,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.delete_imported_model import (
    DeleteImportedModel,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.get_imported_model import (
    GetImportedModel,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.get_model_import_job import (
    GetModelImportJob,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.list_imported_models import (
    ListImportedModels,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.list_model_import_jobs import (
    ListModelImportJobs,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import AppConfig
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.consts import (
    MCP_INSTRUCTIONS,
    SERVER_NAME,
)
from fastmcp import FastMCP
from loguru import logger


# Initialize MCP server
mcp = FastMCP(
    name=SERVER_NAME,
    version=__version__,
    instructions=MCP_INSTRUCTIONS,
    dependencies=['pydantic', 'boto3', 'loguru'],
)


def main() -> None:
    """Run the MCP server.

    This function initializes and runs the Bedrock Custom Model Import MCP server.
    The server provides tools for managing custom model imports in Amazon Bedrock.
    """
    # Parse the cli arguments
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for EKS'
    )
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow mutating operations)',
    )

    args = parser.parse_args()

    # Intialize app configuration
    app_config = AppConfig.from_env(allow_write=args.allow_write)

    # Initialize logger
    logger.remove()
    logger.add(
        sys.stderr, level=app_config.logging_config.level, format=app_config.logging_config.format
    )

    # Initialize the client
    client = BedrockModelImportClient(app_config.aws_config.region, app_config.aws_config.profile)

    # Initialize services
    model_import_service = ModelImportService(client, app_config)
    imported_model_service = ImportedModelService(client, app_config)

    # Initialize tools
    CreateModelImportJob(mcp, model_import_service)
    GetModelImportJob(mcp, model_import_service)
    ListModelImportJobs(mcp, model_import_service)
    GetImportedModel(mcp, imported_model_service)
    DeleteImportedModel(mcp, imported_model_service)
    ListImportedModels(mcp, imported_model_service)

    # Initialize prompts
    Prompts(mcp)

    # Set the execution environment
    os.environ['AWS_EXECUTION_ENV'] = (
        f'awslabs/mcp/aws-bedrock-custom-model-import-mcp-server/{__version__}'
    )

    mcp.run()


if __name__ == '__main__':
    main()
