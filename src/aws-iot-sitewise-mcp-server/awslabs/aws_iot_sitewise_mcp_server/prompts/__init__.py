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

"""Prompts for AWS IoT SiteWise MCP server."""

from .asset_hierarchy import asset_hierarchy_visualization_prompt
from .bulk_import_workflow import bulk_import_workflow_helper_prompt
from .data_exploration import data_exploration_helper_prompt
from .data_ingestion import data_ingestion_helper_prompt

__all__ = [
    'asset_hierarchy_visualization_prompt',
    'bulk_import_workflow_helper_prompt',
    'data_exploration_helper_prompt',
    'data_ingestion_helper_prompt',
]
