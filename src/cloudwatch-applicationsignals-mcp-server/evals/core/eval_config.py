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

"""Configuration constants for MCP tool evaluation framework.

Centralized location for all configurable values.

These settings apply to both the agent being evaluated and the LLM judge.

Environment variable overrides:
- MCP_EVAL_MODEL_ID: Override default Bedrock model ID
- MCP_EVAL_AWS_REGION: Override default AWS region
- MCP_EVAL_MAX_TURNS: Override default max conversation turns
- MCP_EVAL_TEMPERATURE: Override default model temperature
"""

import os


# Default values (used when environment variables are not set)
_DEFAULT_MODEL_ID = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
_DEFAULT_AWS_REGION = 'us-east-1'
_DEFAULT_MAX_TURNS = 20
_DEFAULT_TEMPERATURE = 0.0

# Configuration values (can be overridden via environment variables)
# Used by both the agent being evaluated and the LLM judge
MODEL_ID = os.environ.get('MCP_EVAL_MODEL_ID', _DEFAULT_MODEL_ID)
AWS_REGION = os.environ.get('MCP_EVAL_AWS_REGION', _DEFAULT_AWS_REGION)
MAX_TURNS = int(os.environ.get('MCP_EVAL_MAX_TURNS', str(_DEFAULT_MAX_TURNS)))
TEMPERATURE = float(os.environ.get('MCP_EVAL_TEMPERATURE', str(_DEFAULT_TEMPERATURE)))
