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
MCP_SERVER_NAME = 'aws_finops'
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

# Service name abbreviations for tool names
SERVICE_ABBR = {
    'cost_optimization_hub': 'coh',
    'compute_optimizer': 'co',
    'cost_explorer': 'ce',
}

# Method name abbreviations for tool names
METHOD_ABBR = {
    # Cost Optimization Hub
    'list_recommendations': 'list_recs',
    'list_recommendation_summaries': 'list_rec_summaries',
    'get_recommendation': 'get_rec',
    # Compute Optimizer
    'get_auto_scaling_group_recommendations': 'get_asg_recs',
    'get_ebs_volume_recommendations': 'get_ebs_recs',
    'get_ec2_instance_recommendations': 'get_ec2_recs',
    'get_ecs_service_recommendations': 'get_ecs_recs',
    'get_rds_database_recommendations': 'get_rds_recs',
    'get_lambda_function_recommendations': 'get_lambda_recs',
    'get_idle_recommendations': 'get_idle_recs',
    'get_effective_recommendation_preferences': 'get_rec_prefs',
    # Cost Explorer
    'get_reservation_purchase_recommendation': 'get_ri_recs',
    'get_savings_plans_purchase_recommendation': 'get_sp_recs',
    'get_cost_and_usage': 'get_cost_usage',
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
