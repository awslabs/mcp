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
"""Generators for MCP prompts."""

from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import create_operation_prompt
from awslabs.openapi_mcp_server.prompts.generators.workflow_prompts import (
    identify_workflows,
    create_workflow_prompt,
)

__all__ = ['create_operation_prompt', 'identify_workflows', 'create_workflow_prompt']
