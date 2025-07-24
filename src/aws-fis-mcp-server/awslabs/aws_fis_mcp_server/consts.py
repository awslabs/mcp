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

"""Constants for the AWS FIS MCP server."""

# Default configuration values
DEFAULT_AWS_REGION = 'us-east-1'
DEFAULT_MAX_TIMEOUT_SECONDS = 3600  # 1 hour default timeout
DEFAULT_INITIAL_POLL_INTERVAL = 5
DEFAULT_MAX_POLL_INTERVAL = 60
DEFAULT_MAX_RESOURCES = 100

# FIS experiment states
EXPERIMENT_STATE_PENDING = 'pending'
EXPERIMENT_STATE_INITIATING = 'initiating'
EXPERIMENT_STATE_RUNNING = 'running'
EXPERIMENT_STATE_COMPLETED = 'completed'
EXPERIMENT_STATE_STOPPED = 'stopped'
EXPERIMENT_STATE_FAILED = 'failed'

# FIS experiment actions mode
EXPERIMENT_ACTION_RUN_ALL = 'run-all'

# Environment variable names
ENV_AWS_REGION = 'AWS_REGION'
ENV_FASTMCP_LOG_LEVEL = 'FASTMCP_LOG_LEVEL'

# AWS service names
SERVICE_FIS = 'fis'
SERVICE_S3 = 's3'
SERVICE_RESOURCE_EXPLORER = 'resource-explorer-2'
SERVICE_CLOUDFORMATION = 'cloudformation'
SERVICE_CONFIG = 'config'

# AWS config settings
AWS_CONFIG_SIGNATURE_VERSION = 'v4'
AWS_CONFIG_MAX_ATTEMPTS = 10
AWS_CONFIG_RETRY_MODE = 'standard'
