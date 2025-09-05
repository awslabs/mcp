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

"""Constants for Amazon Bedrock Agent Core MCP Server."""

# Server information
SERVER_NAME = 'amazon-bedrock-agentcore-mcp-server'
SERVER_VERSION = '0.1.0'

# Default AWS configuration
DEFAULT_AWS_REGION = 'us-east-1'
SUPPORTED_REGIONS = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']

# AWS Service names
BEDROCK_AGENT_SERVICE = 'bedrock-agent'
BEDROCK_AGENTCORE_CONTROL_SERVICE = 'bedrock-agentcore-control'
BEDROCK_AGENTCORE_RUNTIME_SERVICE = 'bedrock-agentcore'
COGNITO_IDP_SERVICE = 'cognito-idp'
S3_SERVICE = 's3'

# Memory strategy types
MEMORY_STRATEGY_SEMANTIC = 'semantic'
MEMORY_STRATEGY_SUMMARY = 'summary'
MEMORY_STRATEGY_EPISODIC = 'episodic'

# Gateway target types
GATEWAY_TARGET_LAMBDA = 'lambda'
GATEWAY_TARGET_OPENAPI = 'openApiSchema'
GATEWAY_TARGET_SMITHY = 'smithyModel'

# OAuth configuration
OAUTH_METHOD_ASK = 'ask'
OAUTH_METHOD_GATEWAY_CLIENT = 'gateway_client'
OAUTH_METHOD_MANUAL_CURL = 'manual_curl'
OAUTH_CREDENTIAL_LOCATION_QUERY = 'QUERY_PARAMETER'
OAUTH_CREDENTIAL_LOCATION_HEADER = 'HEADER'

# Default timeouts (in seconds)
DEFAULT_DEPLOYMENT_TIMEOUT = 180
DEFAULT_OAUTH_TIMEOUT = 30
DEFAULT_HTTP_TIMEOUT = 10

# File patterns for discovery
AGENT_FILE_PATTERNS = ['**/*agent*.py', '*.py', '**/*strands*.py']
CONFIG_FILE_PATTERN = '**/.bedrock_agentcore.yaml'

# GitHub repository for examples
AGENTCORE_EXAMPLES_REPO = 'awslabs/amazon-bedrock-agentcore-samples'
GITHUB_API_BASE_URL = 'https://api.github.com/repos'
AWS_API_MODELS_REPO = 'aws/api-models-aws'

# Directory and file names
AGENTCORE_CONFIG_DIR = '.agentcore_gateways'
RUNTIME_CONFIG_SUFFIX = '_runtime.json'

# Common error messages
ERROR_NO_CREDENTIALS = 'AWS credentials not found. Please configure your AWS credentials.'
ERROR_INVALID_REGION = 'Invalid AWS region specified.'
ERROR_CLIENT_INIT = 'Failed to initialize AWS client.'
ERROR_SDK_NOT_AVAILABLE = 'AgentCore SDK not available. Install: uv add bedrock-agentcore bedrock-agentcore-starter-toolkit'
ERROR_FILE_NOT_FOUND = 'File not found. Please check the file path.'
ERROR_AGENT_NOT_FOUND = 'Agent not found in deployment.'

# Success messages
SUCCESS_DEPLOYMENT = 'Agent deployed successfully'
SUCCESS_OAUTH_CONFIG = 'OAuth configuration completed'
SUCCESS_MEMORY_CREATED = 'Memory resource created successfully'
SUCCESS_GATEWAY_CREATED = 'Gateway created successfully'

# Status indicators
STATUS_ACTIVE = 'ACTIVE'
STATUS_CREATING = 'CREATING'
STATUS_UPDATING = 'UPDATING'
STATUS_DELETING = 'DELETING'
STATUS_FAILED = 'FAILED'
STATUS_READY = 'READY'

# Logging configuration
DEFAULT_LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Environment variables
ENV_AWS_REGION = 'AWS_REGION'
ENV_AWS_PROFILE = 'AWS_PROFILE'
ENV_LOG_LEVEL = 'FASTMCP_LOG_LEVEL'
