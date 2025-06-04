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

from importlib import resources

with (
    resources.files('awslabs.terraform_mcp_server.static')
    .joinpath('MCP_INSTRUCTIONS.md')
    .open('r', encoding='utf-8') as f
):
    MCP_INSTRUCTIONS = f.read()

with (
    resources.files('awslabs.terraform_mcp_server.static')
    .joinpath('TERRAFORM_WORKFLOW_GUIDE.md')
    .open('r', encoding='utf-8') as f
):
    TERRAFORM_WORKFLOW_GUIDE = f.read()

with (
    resources.files('awslabs.terraform_mcp_server.static')
    .joinpath('AWS_TERRAFORM_BEST_PRACTICES.md')
    .open('r', encoding='utf-8') as f
):
    AWS_TERRAFORM_BEST_PRACTICES = f.read()
