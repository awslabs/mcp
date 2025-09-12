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

# Default AWS configuration
DEFAULT_AWS_REGION = 'us-east-1'

# Memory strategy types
MEMORY_STRATEGY_SEMANTIC = 'semantic'
MEMORY_STRATEGY_SUMMARY = 'summary'
MEMORY_STRATEGY_EPISODIC = 'episodic'

# Gateway target types
GATEWAY_TARGET_LAMBDA = 'lambda'
GATEWAY_TARGET_OPENAPI = 'openApiSchema'
GATEWAY_TARGET_SMITHY = 'smithyModel'

# Status indicators
STATUS_ACTIVE = 'ACTIVE'
STATUS_CREATING = 'CREATING'
STATUS_UPDATING = 'UPDATING'
STATUS_DELETING = 'DELETING'
STATUS_FAILED = 'FAILED'
