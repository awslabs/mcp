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

"""Constants for ETL Replatforming MCP Server."""

# Timeout constants (in seconds)
BEDROCK_REQUEST_TIMEOUT = 30
BEDROCK_FIELD_TIMEOUT = 30
BEDROCK_CONNECT_TIMEOUT = 10
BEDROCK_READ_TIMEOUT = 60

# Retry constants
MAX_BEDROCK_RETRIES = 3
BEDROCK_RETRY_BASE_DELAY = 5
BEDROCK_GENERAL_RETRY_DELAY = 2

# Confidence thresholds
BASE_CONFIDENCE = 0.8
CONFIDENCE_BONUS_COMPLETE_RESPONSE = 0.1
CONFIDENCE_BONUS_FIELD_SPECIFIC = 0.1
CONFIDENCE_BONUS_DYNAMIC_DETECTION = 0.1
MAX_CONFIDENCE = 1.0

# Response size thresholds
MIN_RESPONSE_LENGTH_FOR_BONUS = 50

# Token limits
MAX_TOKENS_SINGLE_FIELD = 1000

# AWS configuration
DEFAULT_AWS_REGION = 'us-east-1'

# Logging configuration
DEFAULT_LOG_LEVEL = 'INFO'
LOG_ROTATION_SIZE = '10 MB'
LOG_FORMAT = '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}'

# File processing
COMPLETENESS_THRESHOLD = 1.0

# Model inference profiles
CLAUDE_SONNET_4_INFERENCE_PROFILE = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
CLAUDE_3_5_SONNET_INFERENCE_PROFILE = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'

# Model IDs
CLAUDE_SONNET_4_MODEL_ID = 'anthropic.claude-sonnet-4-20250514-v1:0'
CLAUDE_3_5_SONNET_MODEL_ID = 'anthropic.claude-3-5-sonnet-20241022-v2:0'

# Framework identifiers
SUPPORTED_SOURCE_FRAMEWORKS = ['step_functions', 'airflow', 'azure_data_factory']
SUPPORTED_TARGET_FRAMEWORKS = ['airflow', 'step_functions']

# Status constants
STATUS_COMPLETE = 'complete'
STATUS_INCOMPLETE = 'incomplete'
STATUS_ERROR = 'error'
STATUS_PARTIAL = 'partial'

# Parsing methods
PARSING_METHOD_DETERMINISTIC = 'deterministic'
PARSING_METHOD_AI_ENHANCED = 'ai_enhanced'
PARSING_METHOD_HYBRID = 'hybrid'

# Field names for AI enhancement
FIELD_SCHEDULE = 'schedule'
FIELD_ERROR_HANDLING = 'error_handling'
FIELD_PARAMETERS = 'parameters'
FIELD_TASK_COMMANDS = 'task_commands'

# Task types
TASK_TYPE_FOR_EACH = 'for_each'

# Directory names
OUTPUT_DIR_PREFIX_TARGET = 'target'
OUTPUT_DIR_PREFIX_FLEX = 'flex_docs'
OUTPUT_DIR_PREFIX_GENERATED = 'generated_jobs'
