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

"""Configuration settings for RDS Control Plane MCP Server.

This module contains settings that can be configured at runtime through
command line arguments or environment variables.
"""

from mypy_boto3_rds.type_defs import PaginatorConfigTypeDef


# Default values
DEFAULT_MAX_ITEMS = 100
DEFAULT_PAGE_SIZE = 20

# Runtime configurable values (with defaults)
max_items = DEFAULT_MAX_ITEMS
page_size = DEFAULT_PAGE_SIZE


# Dynamic configuration based on above values
def get_pagination_config() -> PaginatorConfigTypeDef:
    """Return a pagination configuration dictionary based on current settings.

    Returns:
        PaginatorConfigTypeDef: Pagination configuration for AWS client paginators
    """
    return {
        'MaxItems': max_items,
        'PageSize': page_size,
    }
