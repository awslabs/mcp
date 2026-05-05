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

"""AWS IoT SiteWise Asset Hierarchy Visualization Prompt."""

from awslabs.aws_iot_sitewise_mcp_server.validation import (
    validate_asset_id,
)
from mcp.server.fastmcp.prompts import Prompt


def asset_hierarchy_visualization(asset_id: str) -> str:
    """Generate a comprehensive analysis and visualization of AWS IoT SiteWise asset hierarchies.

    This prompt provides detailed analysis \
        of asset relationships, properties, and
        health status.

    Args:
        asset_id: The ID of the root asset to analyze

    Returns:
        Comprehensive asset hierarchy analysis and visualization

    Raises:
        ValidationError: If the asset_id is invalid
    """
    # Validate asset ID
    validate_asset_id(asset_id)
    return f"""
You are an AWS IoT SiteWise expert helping to analyze and visualize asset hierarchies.

Please analyze the asset hierarchy starting from asset ID: {asset_id}

Follow these steps:

1. **Root Asset Analysis**:
   - Use describe_asset to get detailed information about the root asset
   - Extract asset name, model ID, properties, and hierarchies
   - Note the asset status and creation/update dates

2. **Asset Model Analysis**:
   - Use describe_asset_model to understand the asset model structure
   - Identify property definitions, data types, and units
   - Document any composite models or hierarchies defined in the model

3. **Child Assets Discovery**:
   - Use list_associated_assets with traversal_direction="CHILD" to \
       find all child assets
   - For each child asset, recursively analyze their structure
   - Build a complete hierarchy tree

4. **Property Analysis**:
   - For each asset in the hierarchy, analyze all properties
   - Use get_asset_property_value to get current values where possible
   - Identify measurement, attribute, transform, and metric properties

5. **Time Series Analysis**:
   - Use list_time_series to identify associated time series
   - Check for any disassociated time series that might be relevant

6. **Visualization Output**:
   Create a comprehensive report including:
   - ASCII tree diagram of the asset hierarchy
   - Table of all assets with their key properties
   - Summary of data flow and relationships
   - Recommendations for optimization or monitoring

7. **Health Check**:
   - Identify any assets with FAILED status
   - Check for missing property values or stale data
   - Suggest maintenance actions if needed

Format your response as a structured analysis with clear sections and \
    actionable insights.
Include specific asset IDs, property names, and current values where available.

If you encounter any errors, explain what information is missing and \
    suggest alternative approaches.
"""


# Create the prompt using from_function
asset_hierarchy_visualization_prompt = Prompt.from_function(
    asset_hierarchy_visualization,
    name='asset_hierarchy_visualization',
    description=(
        'Generate comprehensive analysis and visualization of AWS IoT SiteWise asset hierarchies'
    ),
)
