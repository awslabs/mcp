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

"""Constants for the Bedrock Custom Model Import MCP Server."""

import os


# Server information
SERVER_NAME = 'awslabs.aws-bedrock-custom-model-import-mcp-server'

# AWS Region configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_PROFILE = os.getenv('AWS_PROFILE')

# Environment variable names
ENV_S3_BUCKET = 'BEDROCK_MODEL_IMPORT_S3_BUCKET'
ENV_ROLE_ARN = 'BEDROCK_MODEL_IMPORT_ROLE_ARN'

# Default configuration values
DEFAULT_LOG_LEVEL = 'ERROR'
LOG_LEVEL = os.getenv('FASTMCP_LOG_LEVEL', DEFAULT_LOG_LEVEL)
LOG_FORMAT = '{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}'
S3_BUCKET_NAME = os.getenv(ENV_S3_BUCKET)
ROLE_ARN = os.getenv(ENV_ROLE_ARN)

# MCP Server instructions
MCP_INSTRUCTIONS = """Bedrock Custom Model Import MCP

The Bedrock Custom Model Import Model Context Protocol (MCP) Server provides tools for managing
custom model imports in Amazon Bedrock for on-demand inference. It enables developers to create
and manage model import jobs, track their status, and manage imported models.

## Features
1. Handle Model Import Jobs
- Create new model import jobs to import a model: create_model_import_job
- List existing model import jobs: list_model_import_jobs
- Get details of specific model import jobs: get_model_import_job
2. Manage imported models
- List imported models: list_imported_models
- Get details of specific imported models: get_imported_model
- Delete imported models: delete_imported_model

## Instructions
You import a model into Amazon Bedrock by creating a model import job using the MCP server.
In the job you specify the S3 URI if provided by the user for the source of the model artifacts
which are in hugging face .safetensors format. The MCP server can infer the model artifacts path
from the s3 bucket specified in the environment if the model files are provided in the S3 URI.
Similarly, role arn is also inferred from assumed credentials if not provided by the user.

Supported Model Architectures:
- Mistral
- Mixtral
- Flan
- Llama family (2, 3, 3.1, 3.2, 3.3)
- Mllama
- GPTBigCode
- Qwen2 and Qwen2.5 (including VL variants)

CRITICAL: For other architectures, users should receive a warning with documentation reference before proceeding.

More information: https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html

## Usage Notes
- Requires appropriate AWS credentials and permissions to access Bedrock services
- Set AWS_REGION environment variable if not using default
- Set BEDROCK_MODEL_IMPORT_S3_BUCKET for s3 bucket name where all model artifacts are present
- Set BEDROCK_MODEL_IMPORT_ROLE_ARN for execution role arn to import a model

## Examples
- Import a model into Bedrock
- Is my model imported?
- What is the status of my imported model?
- Host a custom model in Bedrock.
"""
