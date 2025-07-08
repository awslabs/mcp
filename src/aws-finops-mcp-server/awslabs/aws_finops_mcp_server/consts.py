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

"""Constants for the AWS FinOps MCP Server.

This file contains all constants used throughout the AWS FinOps MCP Server project,
organized by functionality and purpose.
"""

# MCP Server configuration
MCP_SERVER_NAME = 'awslabs.aws-finops-mcp-server'
MCP_SERVER_INSTRUCTIONS = 'The AWS FinOps MCP Server is designed to make AWS cost optimization recommendations and insights easily accessible to Large Language Models (LLMs) through the Model Context Protocol (MCP). It wraps boto3 SDK functions for AWS cost optimization services, allowing LLMs to directly interact with AWS cost optimization tools.'
MCP_SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'boto3',
]

# AWS Service name mappings
# Maps our service names to boto3 service names
AWS_SERVICE_NAME_MAP = {
    'cost_optimization_hub': 'cost-optimization-hub',
    'compute_optimizer': 'compute-optimizer',
    'cost_explorer': 'ce',  # Cost Explorer's actual service name in boto3 is "ce"
}

# AWS configuration
DEFAULT_AWS_REGION = 'us-east-1'  # Default region to use if no region is found

# Storage Lens configuration
STORAGE_LENS_DEFAULT_DATABASE = 'storage_lens_db'  # Default database name for Storage Lens data
STORAGE_LENS_DEFAULT_TABLE = 'storage_lens_metrics'  # Default table name for Storage Lens data

# Athena query configuration
ATHENA_MAX_RETRIES = 100  # Maximum number of retries for Athena query completion
ATHENA_RETRY_DELAY_SECONDS = 1  # Delay between retries in seconds

# Environment variable names
ENV_STORAGE_LENS_MANIFEST_LOCATION = (
    'STORAGE_LENS_MANIFEST_LOCATION'  # S3 URI to manifest file or folder
)
ENV_STORAGE_LENS_OUTPUT_LOCATION = (
    'STORAGE_LENS_OUTPUT_LOCATION'  # S3 location for Athena query results
)
ENV_AWS_DEFAULT_REGION = 'AWS_DEFAULT_REGION'  # AWS region environment variable
ENV_AWS_REGION = 'AWS_REGION'  # Alternative AWS region environment variable
