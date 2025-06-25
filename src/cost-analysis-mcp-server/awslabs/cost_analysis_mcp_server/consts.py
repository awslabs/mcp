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

"""awslabs MCP Cost Analysis mcp server constants.

This module provides constant values for analyzing AWS service costs.
"""

import os


MCP_SERVER_NAME = 'awslabs.cost-analysis-mcp-server'

# Environment parameters
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_PROFILE = os.environ.get('AWS_PROFILE')
LOG_LEVEL = os.getenv('FASTMCP_LOG_LEVEL', 'WARNING')

# Supported AWS Pricing API regions
PRICING_API_REGIONS = {
    'classic': ['us-east-1', 'eu-central-1', 'ap-southeast-1'],
    'china': ['cn-northwest-1'],
}
